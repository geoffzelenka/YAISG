"""Graph validation, tag stacks, and deterministic lazy transitions."""

import json
import os
import shutil
from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import MappingProxyType
from typing import Literal, cast

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import CONTENT_DIR
from app.content import ContentError, load_content
from app.db import Base, configure_sqlite_engine
from app.models import RealmState, RealmTag
from app.services.realms import finalize_realm, push_realm_tag, start_transition

CONTENT = load_content(CONTENT_DIR)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def realm_session(tmp_path: Path) -> Iterator[Session]:
    """Exercise the selected disposable test database."""
    engine = create_engine(
        os.environ.get("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'realms.db'}")
    )
    configure_sqlite_engine(engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            RealmState(
                id="realm.verdant_vale",
                template_id="realm.verdant_vale",
                current_node_id="node.verdant_t1",
                last_tick_at=NOW,
            )
        )
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.mark.parametrize("broken", ["required_tags", "cycle", "two_roots"])
def test_graph_rejects_invalid_paths_and_requirements(
    tmp_path: Path, broken: str
) -> None:
    """Upgrade requirements are satisfiable and all regression paths reach one root."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "development.json"
    data = json.loads(path.read_text())
    node = data["nodes"][1]
    if broken == "required_tags":
        node["upgrades"][0]["required_tags"] = ["ashen"]
        message = "unsatisfiable required_tags"
    elif broken == "cycle":
        node["regression"] = {"to_node": node["id"]}
        message = "cannot regress to barren root"
    else:
        node["regression"] = None
        message = "exactly one barren root"
    path.write_text(json.dumps(data))
    with pytest.raises(ContentError, match=message):
        load_content(directory)


def test_upgrade_requirement_satisfied_only_by_carried_tag(tmp_path: Path) -> None:
    """A carried tag satisfies an upgrade without any offered project granting it."""
    directory = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, directory)
    path = directory / "development.json"
    data = json.loads(path.read_text())
    node = next(n for n in data["nodes"] if n["upgrades"])
    node["projects"] = []
    node["carried_tags"] = ["bonus.fake"]
    for upgrade in node["upgrades"]:
        upgrade["required_tags"] = ["bonus.fake"]
    path.write_text(json.dumps(data))

    content = load_content(directory)

    loaded = content.development_node(node["id"])
    assert loaded.projects == ()
    assert loaded.carried_tags == ("bonus.fake",)
    assert all(upgrade.required_tags == ("bonus.fake",) for upgrade in loaded.upgrades)


@pytest.mark.parametrize("cause", ["upgrade", "regression"])
def test_finalize_exact_boundary_idempotent_stamps_and_filters(
    realm_session: Session, cause: str
) -> None:
    """Upgrades preserve D4 stamps; regressions restamp and reset decay state."""
    state = realm_session.get(RealmState, "realm.verdant_vale")
    assert state is not None
    # Target node offers facility.fake_node and carries bonus.fake.
    source_id = "node.verdant_t2" if cause == "regression" else "node.verdant_t1"
    target_id = "node.verdant_t1" if cause == "regression" else "node.verdant_t2"
    state.current_node_id = source_id
    kept = push_realm_tag(realm_session, state, "bonus.fake", NOW)
    offered = push_realm_tag(realm_session, state, "facility.fake_node", NOW)
    push_realm_tag(realm_session, state, "access.fake", NOW)
    state.gauge, state.shed_progress, state.decay_stage = 4, 0.5, "failing"
    start_transition(
        state,
        target_id,
        cast(Literal["upgrade", "regression"], cause),
        NOW,
        CONTENT,
    )
    # The target carries one tag as well as offering the other.
    target = CONTENT.development_node(target_id).model_copy(
        update={
            "carried_tags": ("bonus.fake",),
            "projects": ("project.ashen_placeholder",),
        }
    )
    content = replace(
        CONTENT,
        _nodes_by_id=MappingProxyType(
            {
                n.id: target if n.id == target.id else n
                for n in CONTENT.development_nodes
            }
        ),
    )
    due = NOW + timedelta(days=7)
    finalize_realm(realm_session, state.id, due - timedelta(microseconds=1), content)
    assert state.current_node_id == source_id
    assert state.pending_transition is not None
    assert state.pending_transition["completes_at"] == due.isoformat()
    finalize_realm(realm_session, state.id, due, content)
    snapshot = (
        state.current_node_id,
        state.gauge,
        state.shed_progress,
        state.decay_stage,
        [
            (t.tag_id, t.node_id, t.seq)
            for t in realm_session.scalars(select(RealmTag).order_by(RealmTag.seq))
        ],
    )
    realm_session.commit()
    realm_session.expire_all()
    finalize_realm(realm_session, state.id, due, content)
    assert snapshot == (
        state.current_node_id,
        state.gauge,
        state.shed_progress,
        state.decay_stage,
        [
            (t.tag_id, t.node_id, t.seq)
            for t in realm_session.scalars(select(RealmTag).order_by(RealmTag.seq))
        ],
    )
    assert state.current_node_id == target.id and state.pending_transition is None
    assert realm_session.get(RealmTag, (state.id, "access.fake")) is None
    assert (
        kept.node_id
        == offered.node_id
        == (target.id if cause == "regression" else source_id)
    )
    assert state.gauge == (0 if cause == "regression" else 4)
    assert state.shed_progress == (0 if cause == "regression" else 0.5)
    assert state.decay_stage == ("fed" if cause == "regression" else "failing")


def test_tag_sequence_never_reused(realm_session: Session) -> None:
    """Deleting the latest tag does not allow its sequence to be reused."""
    state = realm_session.get(RealmState, "realm.verdant_vale")
    assert state is not None
    tag = push_realm_tag(realm_session, state, "bonus.fake", NOW)
    realm_session.flush()
    first_seq = tag.seq
    realm_session.delete(tag)
    realm_session.flush()
    new = push_realm_tag(realm_session, state, "bonus.fake", NOW)
    assert new.seq > first_seq


def test_postgres_concurrent_finalizers_wait_for_realm_lock(
    realm_session: Session,
) -> None:
    """A second finalizer waits, then observes the committed completed transition."""
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker
    from test_estates import _wait_for_postgres_blocker

    if realm_session.get_bind().dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    state = realm_session.get(RealmState, "realm.verdant_vale")
    assert state is not None
    start_transition(state, "node.verdant_t2", "upgrade", NOW, CONTENT)
    push_realm_tag(realm_session, state, "bonus.fake", NOW)
    realm_session.commit()
    factory = sessionmaker(bind=realm_session.get_bind())
    ready = threading.Event()
    worker_pid: list[int] = []

    def second_finalizer() -> str:
        with factory() as session:
            session.execute(text("SET LOCAL statement_timeout = '10s'"))
            worker_pid.append(session.scalar(text("SELECT pg_backend_pid()")))
            ready.set()
            result = finalize_realm(
                session, "realm.verdant_vale", NOW + timedelta(days=7), CONTENT
            )
            assert result is not None and result.pending_transition is None
            node_id = result.current_node_id
            session.commit()
            return node_id

    with factory() as first, ThreadPoolExecutor(max_workers=1) as pool:
        blocker_pid = first.scalar(text("SELECT pg_backend_pid()"))
        assert isinstance(blocker_pid, int)
        finalize_realm(first, state.id, NOW + timedelta(days=7), CONTENT)
        future = pool.submit(second_finalizer)
        try:
            assert ready.wait(timeout=5)
            _wait_for_postgres_blocker(factory, worker_pid[0], blocker_pid)
            assert not future.done()
        finally:
            first.commit()
        assert future.result(timeout=10) == "node.verdant_t2"
    realm_session.expire_all()
    tag = realm_session.get(RealmTag, (state.id, "bonus.fake"))
    assert tag is not None and tag.node_id == "node.verdant_t1" and tag.seq == 1


def test_transition_uses_content_duration_and_rejects_replacement(
    realm_session: Session,
) -> None:
    """Transition timing follows the economy pack and cannot be overwritten."""
    state = realm_session.get(RealmState, "realm.verdant_vale")
    assert state is not None
    content = replace(
        CONTENT,
        economy=CONTENT.economy.model_copy(
            update={
                "transition": CONTENT.economy.transition.model_copy(
                    update={"duration_days": 0.5}
                ),
            }
        ),
    )
    start_transition(state, "node.verdant_t2", "upgrade", NOW, content)
    pending = dict(state.pending_transition or {})
    assert pending["completes_at"] == (NOW + timedelta(hours=12)).isoformat()
    with pytest.raises(ValueError, match="already transitioning"):
        start_transition(state, "node.verdant_t0_stub", "regression", NOW, content)
    assert state.pending_transition == pending


@settings(
    max_examples=20,
    derandomize=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(
    cause=st.sampled_from(["upgrade", "regression"]),
    overdue_hours=st.integers(min_value=0, max_value=1000),
    gauge=st.integers(min_value=0, max_value=100),
)
def test_transition_finalization_is_idempotent(
    realm_session: Session,
    cause: Literal["upgrade", "regression"],
    overdue_hours: int,
    gauge: int,
) -> None:
    """Late finalization preserves its first result for either cause."""
    # Each generated example rolls back to the fixture's committed initial realm.
    realm_session.rollback()
    state = realm_session.get(RealmState, "realm.verdant_vale")
    assert state is not None
    state.current_node_id = (
        "node.verdant_t2" if cause == "regression" else "node.verdant_t1"
    )
    target = "node.verdant_t1" if cause == "regression" else "node.verdant_t2"
    state.gauge = gauge
    state.shed_progress = 0.75
    push_realm_tag(realm_session, state, "bonus.fake", NOW)
    push_realm_tag(realm_session, state, "access.fake", NOW)
    start_transition(state, target, cause, NOW, CONTENT)
    due = NOW + timedelta(
        days=CONTENT.economy.transition.duration_days, hours=overdue_hours
    )
    finalize_realm(realm_session, state.id, due, CONTENT)
    first = (
        state.current_node_id,
        state.gauge,
        state.shed_progress,
        [(t.tag_id, t.node_id, t.seq) for t in realm_session.scalars(select(RealmTag))],
    )
    realm_session.expire_all()
    finalize_realm(realm_session, state.id, due + timedelta(days=1), CONTENT)
    second = (
        state.current_node_id,
        state.gauge,
        state.shed_progress,
        [(t.tag_id, t.node_id, t.seq) for t in realm_session.scalars(select(RealmTag))],
    )
    assert first == second
    realm_session.rollback()
