"""Unit test for the Model B note-visibility rule (project risk #2):
a GM secret note targeted at Player A must be visible to Player A and the
GM, but NOT to Player B or to any other player.
"""
import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth import SessionRecord
from app.database import Base
from app.models import Campaign, Note, SessionLog, User
from app.routers.notes import get_visible_notes


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()
    yield session
    session.close()


@pytest.fixture
def fixtures(db):
    gm = User(username="gm_dana", role="gm")
    player_a = User(username="alice", role="player")
    player_b = User(username="bob", role="player")
    db.add_all([gm, player_a, player_b])
    db.commit()

    campaign = Campaign(name="Test Campaign")
    db.add(campaign)
    db.commit()

    log = SessionLog(campaign_id=campaign.id, session_number=1, date=datetime.date.today())
    db.add(log)
    db.commit()

    public_note = Note(session_id=log.id, author_id=gm.id, content="The party enters the tavern.")
    gm_only_note = Note(session_id=log.id, author_id=gm.id, content="The tavern keeper is a disguised lich.", is_private_gm=True)
    secret_for_a = Note(
        session_id=log.id,
        author_id=gm.id,
        content="Alice's character secretly has a cursed ring.",
        is_private_gm=True,
        target_player_id=player_a.id,
    )
    db.add_all([public_note, gm_only_note, secret_for_a])
    db.commit()

    return {
        "db": db,
        "gm": gm,
        "player_a": player_a,
        "player_b": player_b,
        "session_id": log.id,
        "public_note": public_note,
        "gm_only_note": gm_only_note,
        "secret_for_a": secret_for_a,
    }


def _session_record(user: User) -> SessionRecord:
    return SessionRecord(token="test-token", user_id=user.id, username=user.username, role=user.role)


def test_gm_sees_everything(fixtures):
    notes = get_visible_notes(fixtures["db"], fixtures["session_id"], _session_record(fixtures["gm"]))
    assert {n.id for n in notes} == {
        fixtures["public_note"].id,
        fixtures["gm_only_note"].id,
        fixtures["secret_for_a"].id,
    }


def test_targeted_player_sees_own_secret_but_not_gm_only(fixtures):
    notes = get_visible_notes(fixtures["db"], fixtures["session_id"], _session_record(fixtures["player_a"]))
    visible_ids = {n.id for n in notes}
    assert fixtures["public_note"].id in visible_ids
    assert fixtures["secret_for_a"].id in visible_ids
    assert fixtures["gm_only_note"].id not in visible_ids


def test_other_player_does_not_see_targeted_secret(fixtures):
    notes = get_visible_notes(fixtures["db"], fixtures["session_id"], _session_record(fixtures["player_b"]))
    visible_ids = {n.id for n in notes}
    assert fixtures["public_note"].id in visible_ids
    assert fixtures["secret_for_a"].id not in visible_ids
    assert fixtures["gm_only_note"].id not in visible_ids
