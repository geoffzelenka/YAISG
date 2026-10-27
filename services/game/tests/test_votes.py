"""Ballot outcomes, immutable eligibility, secrecy and lock serialization."""

import logging
import uuid
from dataclasses import replace
from datetime import timedelta
from types import MappingProxyType

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_actions import action_client as action_client
from test_actions import anyio_backend as anyio_backend
from test_projects import REALM, ApiFixture, _hero, _run
from test_realms import CONTENT, NOW
from test_realms import realm_session as realm_session

from app.db import Base
from app.models import (
    Character,
    Currency,
    Estate,
    Player,
    RealmState,
    RealmVoteEligibility,
)
from app.services.projects import kickoff
from app.services.realms import as_utc, finalize_realm, push_realm_tag, resolve_realm
from app.services.votes import call_vote, cast_vote

UPGRADE = "upgrade.fake_tier"


def _ready(session: Session) -> tuple[Character, RealmState]:
    hero = _hero(session)
    realm = session.get(RealmState, REALM)
    assert realm is not None
    push_realm_tag(session, realm, "bonus.fake", NOW)
    session.flush()
    return hero, realm


def _resident(session: Session) -> Character:
    player = Player(auth_user_id=uuid.uuid4(), created_at=NOW)
    session.add(player)
    session.flush()
    hero = Character(
        player_id=player.id,
        name=player.id.hex[:20],
        name_normalized=player.id.hex[:20],
        current_realm_id=REALM,
        home_estate_id=uuid.uuid4(),
        created_at=NOW,
    )
    session.add(hero)
    session.flush()
    session.add(
        Estate(
            id=hero.home_estate_id,
            owner_character_id=hero.id,
            realm_id=REALM,
            form_id=CONTENT.estate_forms[0].id,
        )
    )
    session.add(Currency(character_id=hero.id, gold=100))
    session.flush()
    return hero


@pytest.mark.parametrize("choices", [[], ["no"], ["yes", "no"]])
def test_tie_abstention_and_no_votes_fail(
    realm_session: Session, choices: list[str]
) -> None:
    """No quorum rescues a zero, negative or tied result."""
    hero, realm = _ready(realm_session)
    other = _resident(realm_session)
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    for character, choice in zip([hero, other], choices, strict=False):
        cast_vote(
            realm_session,
            character,
            realm,
            "yes" if choice == "yes" else "no",
            NOW,
            CONTENT,
        )
    due = NOW if len(choices) == 2 else as_utc(vote.closes_at)
    resolve_realm(realm_session, realm, due, CONTENT)
    assert vote.status == "failed" and realm.pending_transition is None
    assert realm.vote_cooldown_until == due + timedelta(hours=72)


def test_weights_snapshot_excludes_arrivals_keeps_leavers(
    realm_session: Session,
) -> None:
    """Weight and eligibility survive relocation and estate form changes."""
    hero, realm = _ready(realm_session)
    other = _resident(realm_session)
    fixed = next(f for f in CONTENT.estate_forms if f.mobility == "fixed")
    estate = realm_session.get(Estate, other.home_estate_id)
    assert estate is not None
    estate.form_id = fixed.id
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    assert vote.eligible_weight == 1 + 9 + fixed.tier
    late = _resident(realm_session)
    with pytest.raises(HTTPException, match="VOTE_INELIGIBLE"):
        cast_vote(realm_session, late, realm, "yes", NOW, CONTENT)
    estate.realm_id = "realm.ashen_reach"
    # A leaver remains eligible even while absent from the realm.
    other.current_realm_id = "realm.ashen_reach"
    cast_vote(realm_session, other, realm, "yes", NOW, CONTENT)
    assert vote.yes_weight == 9 + fixed.tier and vote.status == "open"
    with pytest.raises(HTTPException, match="ALREADY_VOTED"):
        cast_vote(realm_session, other, realm, "no", NOW, CONTENT)
    cast_vote(realm_session, hero, realm, "no", NOW, CONTENT)
    assert vote.status == "passed"


def test_early_close_transition_and_finalize(realm_session: Session) -> None:
    """The final ballot immediately starts the authored transition exactly once."""
    hero, realm = _ready(realm_session)
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    cast_at = NOW + timedelta(minutes=3)
    cast_vote(realm_session, hero, realm, "yes", cast_at, CONTENT)
    assert vote.status == "passed"
    assert realm.pending_transition is not None
    assert realm.pending_transition["started_at"] == cast_at.isoformat()
    due = cast_at + timedelta(days=CONTENT.economy.transition.duration_days)
    # Suppress unrelated historical upkeep when asserting completion.
    realm.last_tick_at = due
    finalize_realm(realm_session, REALM, due, CONTENT)
    assert (
        realm.current_node_id == "node.verdant_t2" and realm.pending_transition is None
    )
    finalize_realm(realm_session, REALM, due, CONTENT)
    assert vote.yes_weight == 1


def test_fee_kept_cooldown_and_exact_deadline(realm_session: Session) -> None:
    """Failed calls transfer gold permanently and cooldown uses the due time."""
    hero, realm = _ready(realm_session)
    node = CONTENT.development_node(realm.current_node_id)
    updated = node.model_copy(
        update={
            "upgrades": tuple(
                u.model_copy(update={"fee_gold": 17}) for u in node.upgrades
            )
        }
    )
    content = replace(
        CONTENT,
        _nodes_by_id=MappingProxyType({**CONTENT._nodes_by_id, node.id: updated}),
    )
    wallet = realm_session.get(Currency, hero.id)
    assert wallet is not None
    initial = realm.treasury + wallet.gold
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, content)
    assert wallet.gold == 83 and realm.treasury + wallet.gold == initial
    deadline = as_utc(vote.closes_at)
    resolve_realm(realm_session, realm, deadline - timedelta(microseconds=1), content)
    assert vote.status == "open"
    resolve_realm(realm_session, realm, deadline + timedelta(hours=1), content)
    assert vote.status == "failed" and wallet.gold == 83
    assert as_utc(realm.vote_cooldown_until) == deadline + timedelta(hours=72)  # type: ignore[arg-type]
    with pytest.raises(HTTPException, match="VOTE_COOLDOWN"):
        call_vote(realm_session, hero, realm, UPGRADE, deadline, content)
    call_vote(
        realm_session, hero, realm, UPGRADE, deadline + timedelta(hours=72), content
    )


def test_vote_project_exclusion_both_ways(realm_session: Session) -> None:
    """D6 blocks both competing lifecycle entry points."""
    hero, realm = _ready(realm_session)
    call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    # The mint is still offered while the upgrade-required tag is held.
    with pytest.raises(HTTPException, match="REALM_VOTING"):
        kickoff(realm_session, hero, realm, "project.fake_mint", NOW, CONTENT)
    cast_vote(realm_session, hero, realm, "no", NOW, CONTENT)
    realm.vote_cooldown_until = None
    _run(realm_session, realm)
    with pytest.raises(HTTPException, match="PROJECT_ACTIVE"):
        call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)


@pytest.mark.anyio
async def test_api_participation_secrecy_and_logs(
    action_client: ApiFixture, caplog: pytest.LogCaptureFixture
) -> None:
    """HTTP logs, persistent schema and response contain no individual choice."""
    client, factory, clock, headers = action_client
    with factory() as session:
        hero, realm = _ready(session)
        _resident(session)
        hero.current_realm_id = "realm.ashen_reach"
        session.commit()
    url = f"/realms/{REALM}"
    caplog.set_level(logging.INFO)
    response = await client.post(f"{url}/upgrades/{UPGRADE}/call", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["yes_weight"] is None
    assert all(p["voted_at"] is None for p in response.json()["participation"])
    response = await client.post(f"{url}/vote", headers=headers, json={"choice": "yes"})
    assert response.status_code == 200, response.text
    assert (
        response.json()["yes_weight"] is None and response.json()["no_weight"] is None
    )
    assert sum(p["voted_at"] is not None for p in response.json()["participation"]) == 1
    duplicate = await client.post(f"{url}/vote", headers=headers, json={"choice": "no"})
    assert duplicate.json()["error"]["code"] == "ALREADY_VOTED"
    assert (
        "choice" not in caplog.text
        and '"yes"' not in caplog.text
        and '"no"' not in caplog.text
    )
    assert set(Base.metadata.tables["realm_vote_eligibility"].columns.keys()) == {
        "vote_id",
        "character_id",
        "weight",
        "voted_at",
    }
    clock.advance(timedelta(hours=72))
    response = await client.get(f"{url}/vote", headers=headers)
    assert response.json()["status"] == "passed"
    assert response.json()["yes_weight"] == 1 and response.json()["no_weight"] == 0
    with factory() as session:
        assert (
            session.scalar(
                select(RealmVoteEligibility.voted_at).where(
                    RealmVoteEligibility.voted_at.is_not(None)
                )
            )
            is not None
        )


@pytest.mark.parametrize("operation", ["call", "cast", "distinct_cast"])
def test_postgres_concurrent_ballot_mutations(
    realm_session: Session, operation: str
) -> None:
    """The realm lock prevents duplicate calls and duplicate aggregate credits."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from test_estates import _wait_for_postgres_blocker

    from app.services.actions import resolve_character

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    hero, realm = _ready(realm_session)
    other = _resident(realm_session)
    if operation != "call":
        call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    hero_id = hero.id
    competing_id = hero.id if operation == "cast" else other.id
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    ready = threading.Event()
    worker_pid: list[int] = []

    def mutate(session: Session, character_id: uuid.UUID) -> None:
        resolve_character(session, character_id, NOW, CONTENT, {REALM})
        character = session.get(Character, character_id)
        state = session.get(RealmState, REALM)
        assert character is not None and state is not None
        if operation == "call":
            call_vote(session, character, state, UPGRADE, NOW, CONTENT)
        else:
            cast_vote(session, character, state, "yes", NOW, CONTENT)

    def competing() -> str:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            pid = session.scalar(text("SELECT pg_backend_pid()"))
            assert isinstance(pid, int)
            worker_pid.append(pid)
            ready.set()
            try:
                mutate(session, competing_id)
            except HTTPException as error:
                return str(error.detail)
            session.commit()
            return "success"

    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        blocker = first.scalar(text("SELECT pg_backend_pid()"))
        assert isinstance(blocker, int)
        mutate(first, hero_id)
        future = pool.submit(competing)
        try:
            assert ready.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pid[0], blocker)
            assert not future.done()
        finally:
            first.commit()
        expected = {
            "call": "REALM_VOTING",
            "cast": "ALREADY_VOTED",
            "distinct_cast": "success",
        }[operation]
        assert expected in future.result(timeout=10)
    realm_session.expire_all()
    from app.models import RealmVote

    ballots = list(realm_session.scalars(select(RealmVote)))
    assert len(ballots) == 1
    assert (
        ballots[0].yes_weight == {"call": 0, "cast": 1, "distinct_cast": 2}[operation]
    )


def test_passed_vote_raises_reserves(realm_session: Session) -> None:
    """A real passed ballot activates the transition reserve overlay."""
    from app.services.stores import recompute_lines

    hero, realm = _ready(realm_session)
    realm_session.add(Estate(form_id=CONTENT.estate_forms[-1].id, realm_id=realm.id))
    realm_session.flush()
    before = {
        line.line_key: (line.reserve, line.draw_per_day)
        for line in recompute_lines(realm_session, realm, CONTENT)
    }
    call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    cast_vote(realm_session, hero, realm, "yes", NOW, CONTENT)
    after = recompute_lines(realm_session, realm, CONTENT)
    assert after
    for line in after:
        reserve, draw = before[line.line_key]
        assert line.reserve == reserve + draw * CONTENT.economy.transition.duration_days


def test_snapshot_includes_unresolved_decay_replacement(realm_session: Session) -> None:
    """Estate ownership determines residence before lazy home-pointer repair."""
    hero, realm = _ready(realm_session)
    other = _resident(realm_session)
    retired = realm_session.get(Estate, other.home_estate_id)
    assert retired is not None
    retired.status = "destroyed"
    retired.owner_character_id = None
    replacement = Estate(
        owner_character_id=other.id,
        realm_id=REALM,
        form_id=CONTENT.progression.basic_mobile_form,
    )
    realm_session.add(replacement)
    realm_session.flush()
    retired.data = {"replacement_estate_id": str(replacement.id)}
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    assert vote.eligible_weight == 2
    assert realm_session.get(RealmVoteEligibility, (vote.id, other.id)) is not None


@pytest.mark.parametrize(
    "reason", ["resident", "offering", "tags", "transition", "fee"]
)
def test_call_gates_leave_wallet_untouched(realm_session: Session, reason: str) -> None:
    """Rejected calls charge nothing and create no eligibility records."""
    hero, realm = _ready(realm_session)
    upgrade = UPGRADE
    codes = {
        "resident": "RESIDENTS_ONLY",
        "offering": "UPGRADE_NOT_OFFERED",
        "tags": "UPGRADE_TAGS_REQUIRED",
        "transition": "REALM_TRANSITIONING",
        "fee": "MISSING_INPUTS",
    }
    if reason == "resident":
        estate = realm_session.get(Estate, hero.home_estate_id)
        assert estate is not None
        estate.realm_id = "realm.ashen_reach"
    elif reason == "offering":
        upgrade = "missing"
    elif reason == "tags":
        from app.models import RealmTag

        tag = realm_session.get(RealmTag, (REALM, "bonus.fake"))
        assert tag is not None
        realm_session.delete(tag)
    elif reason == "transition":
        from app.services.realms import start_transition

        start_transition(realm, "node.verdant_t2", "upgrade", NOW, CONTENT)
    else:
        wallet = realm_session.get(Currency, hero.id)
        assert wallet is not None
        realm_session.delete(wallet)
    realm_session.flush()
    treasury = realm.treasury
    with pytest.raises(HTTPException, match=codes[reason]):
        call_vote(realm_session, hero, realm, upgrade, NOW, CONTENT)
    assert realm.treasury == treasury
    assert list(realm_session.scalars(select(RealmVoteEligibility))) == []


def test_late_resolution_closes_and_finalizes_at_due_times(
    realm_session: Session,
) -> None:
    """An abstainer delays close; late resolution processes both timed events."""
    hero, realm = _ready(realm_session)
    _resident(realm_session)
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    cast_vote(realm_session, hero, realm, "yes", NOW, CONTENT)
    due = as_utc(vote.closes_at) + timedelta(
        days=CONTENT.economy.transition.duration_days
    )
    realm.last_tick_at = due
    finalize_realm(realm_session, REALM, due, CONTENT)
    assert vote.status == "passed" and realm.current_node_id == "node.verdant_t2"
    assert realm.pending_transition is None


def test_vote_cannot_replace_pending_decay_transition(realm_session: Session) -> None:
    """Preserve the transition guard where upgrade/decay precedence is unspecified."""
    from app.models import RealmVote
    from app.services.realms import start_transition

    hero, realm = _ready(realm_session)
    vote = call_vote(realm_session, hero, realm, UPGRADE, NOW, CONTENT)
    start_transition(realm, "node.verdant_t0_stub", "regression", NOW, CONTENT)
    hero_id, vote_id = hero.id, vote.id
    realm_session.commit()
    with pytest.raises(ValueError, match="already transitioning"):
        cast_vote(realm_session, hero, realm, "yes", NOW, CONTENT)
    # HTTP/session ownership rolls back a rejected final cast, including its
    # participation and aggregate changes; neither transition is overwritten.
    realm_session.rollback()
    restored = realm_session.get(RealmVote, vote_id)
    eligibility = realm_session.get(RealmVoteEligibility, (vote_id, hero_id))
    assert restored is not None and restored.status == "open"
    assert restored.yes_weight == 0
    assert eligibility is not None and eligibility.voted_at is None
    assert realm.pending_transition is not None
    assert realm.pending_transition["cause"] == "regression"
