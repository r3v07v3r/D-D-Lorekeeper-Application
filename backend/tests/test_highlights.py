"""Tests for the session-highlights extraction pipeline: parsing the LLM's
JSON response defensively (app/ai/summarization.py:_parse_highlights) and
scoping the roll-log grounding context to a session's actual recording
window (app/ai/pipeline.py:_build_roll_context). Neither hits a real LLM or
database over the network - these test the pure logic in isolation.
"""
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.ai.pipeline import _build_roll_context
from app.ai.summarization import _parse_highlights
from app.database import Base
from app.models import Campaign, RollLogEntry, SessionLog, User


def test_parse_highlights_accepts_a_clean_json_array():
    raw = '[{"category": "kill", "description": "The party defeated the goblin chief."}]'
    result = _parse_highlights(raw)
    assert result == [{"category": "kill", "description": "The party defeated the goblin chief."}]


def test_parse_highlights_strips_a_markdown_fence():
    raw = '```json\n[{"category": "critical", "description": "A natural 20 on the killing blow."}]\n```'
    result = _parse_highlights(raw)
    assert result == [{"category": "critical", "description": "A natural 20 on the killing blow."}]


def test_parse_highlights_returns_empty_list_for_invalid_json():
    assert _parse_highlights("not json at all") == []


def test_parse_highlights_returns_empty_list_for_a_json_object_not_array():
    assert _parse_highlights('{"category": "kill", "description": "oops, not a list"}') == []


def test_parse_highlights_drops_entries_with_unknown_category():
    raw = '[{"category": "not-a-real-category", "description": "should be dropped"}]'
    assert _parse_highlights(raw) == []


def test_parse_highlights_drops_entries_with_empty_description():
    raw = '[{"category": "strange", "description": ""}, {"category": "strange", "description": "   "}]'
    assert _parse_highlights(raw) == []


def test_parse_highlights_caps_at_eight_entries():
    items = [{"category": "other", "description": f"event {i}"} for i in range(12)]
    import json
    result = _parse_highlights(json.dumps(items))
    assert len(result) == 8


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db")
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine)
    session = TestSessionLocal()
    yield session
    session.close()


def _make_campaign_and_user(db_session):
    campaign = Campaign(name="Test Campaign")
    db_session.add(campaign)
    db_session.commit()
    user = User(username="gm", role="gm")
    db_session.add(user)
    db_session.commit()
    return campaign, user


def test_roll_context_empty_when_recording_window_not_set(db_session):
    campaign, _ = _make_campaign_and_user(db_session)
    log = SessionLog(campaign_id=campaign.id, session_number=1, date=date(2026, 7, 16))
    db_session.add(log)
    db_session.commit()

    assert _build_roll_context(db_session, log) == ""


def test_roll_context_includes_only_rolls_within_the_recording_window(db_session):
    campaign, user = _make_campaign_and_user(db_session)
    start = datetime(2026, 7, 16, 20, 0, 0)
    end = datetime(2026, 7, 16, 22, 0, 0)
    log = SessionLog(
        campaign_id=campaign.id, session_number=1, date=date(2026, 7, 16),
        recording_started_at=start, recording_ended_at=end,
    )
    db_session.add(log)
    db_session.commit()

    before = RollLogEntry(
        campaign_id=campaign.id, user_id=user.id, username="gm",
        summary="too early", total=1, created_at=start - timedelta(minutes=5),
    )
    during = RollLogEntry(
        campaign_id=campaign.id, user_id=user.id, username="gm",
        summary="d20 [17] = 17", total=17, created_at=start + timedelta(minutes=30),
    )
    after = RollLogEntry(
        campaign_id=campaign.id, user_id=user.id, username="gm",
        summary="too late", total=1, created_at=end + timedelta(minutes=5),
    )
    db_session.add_all([before, during, after])
    db_session.commit()

    context = _build_roll_context(db_session, log)
    assert "d20 [17] = 17" in context
    assert "too early" not in context
    assert "too late" not in context


def test_roll_context_scoped_to_the_sessions_own_campaign(db_session):
    campaign_a = Campaign(name="Campaign A")
    campaign_b = Campaign(name="Campaign B")
    db_session.add_all([campaign_a, campaign_b])
    db_session.commit()
    user = User(username="gm", role="gm")
    db_session.add(user)
    db_session.commit()

    start = datetime(2026, 7, 16, 20, 0, 0)
    end = datetime(2026, 7, 16, 22, 0, 0)
    log = SessionLog(
        campaign_id=campaign_a.id, session_number=1, date=date(2026, 7, 16),
        recording_started_at=start, recording_ended_at=end,
    )
    db_session.add(log)
    db_session.commit()

    other_campaign_roll = RollLogEntry(
        campaign_id=campaign_b.id, user_id=user.id, username="gm",
        summary="wrong campaign", total=1, created_at=start + timedelta(minutes=10),
    )
    db_session.add(other_campaign_roll)
    db_session.commit()

    assert _build_roll_context(db_session, log) == ""
