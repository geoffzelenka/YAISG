"""Realm-development service tests using a deterministic clock."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import CONTENT_DIR
from app.content import load_content
from app.db import Base, configure_sqlite_engine
from app.models import (
    RealmEdgeProgress,
    RealmProject,
    RealmState,
)
from app.services.realms import (
    InvalidEdgeAwardError,
    award_edge_progress,
    finalize_realm,
)

CONTENT = load_content(CONTENT_DIR)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def realm_session() -> Iterator[Session]:
    """Create isolated SQLite graph state."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    configure_sqlite_engine(engine)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(
            RealmState(
                realm_id="realm.verdant_vale",
                node_id="node.verdant_t1",
                treasury=0,
                data={},
            )
        )
        session.commit()
        yield session
    engine.dispose()


def test_award_starts_transition_and_rejects_more_awards(
    realm_session: Session,
) -> None:
    """A filled outgoing edge creates one immutable pending window."""
    progress = award_edge_progress(
        realm_session,
        "realm.verdant_vale",
        "edge.verdant_t1_t2",
        100,
        "test",
        NOW,
        CONTENT,
    )
    state = realm_session.get(RealmState, "realm.verdant_vale")

    assert progress.progress == 100
    assert state is not None
    assert state.node_id == "node.verdant_t1"
    assert state.transition_to_node_id == "node.verdant_t2"
    assert state.transition_completes_at == NOW + timedelta(minutes=5)
    with pytest.raises(InvalidEdgeAwardError):
        award_edge_progress(
            realm_session,
            "realm.verdant_vale",
            "edge.verdant_t1_t2",
            1,
            "test",
            NOW,
            CONTENT,
        )


def test_regression_and_non_outgoing_awards_are_rejected(
    realm_session: Session,
) -> None:
    """The award interface cannot fill pressure or unrelated gauges."""
    for edge_id in ("edge.verdant_regress", "edge.ashen_t1_t2"):
        with pytest.raises(InvalidEdgeAwardError):
            award_edge_progress(
                realm_session,
                "realm.verdant_vale",
                edge_id,
                1,
                "test",
                NOW,
                CONTENT,
            )


def test_finalize_transition_resets_siblings_and_closes_projects(
    realm_session: Session,
) -> None:
    """Finalization changes identity once and abandons departed-node state."""
    state = realm_session.get(RealmState, "realm.verdant_vale")
    assert state is not None
    state.transition_to_node_id = "node.verdant_t2"
    state.transition_completes_at = NOW
    realm_session.add_all(
        [
            RealmEdgeProgress(
                realm_id=state.realm_id,
                edge_id="edge.verdant_t1_t2",
                progress=100,
                updated_at=NOW,
            ),
            RealmEdgeProgress(
                realm_id=state.realm_id,
                edge_id="edge.verdant_regress",
                progress=12,
                updated_at=NOW,
            ),
            RealmProject(
                realm_id=state.realm_id,
                project_id="project.verdant_cardboard",
                contribution_totals={"item.demo_crate": 4},
                status="active",
            ),
        ]
    )
    realm_session.flush()

    first = finalize_realm(realm_session, state.realm_id, NOW, CONTENT)
    second = finalize_realm(realm_session, state.realm_id, NOW, CONTENT)

    assert first is second
    assert state.node_id == "node.verdant_t2"
    assert state.transition_to_node_id is None
    assert list(realm_session.scalars(select(RealmEdgeProgress))) == []
    project = realm_session.get(
        RealmProject, (state.realm_id, "project.verdant_cardboard")
    )
    assert project is not None and project.status == "closed"
