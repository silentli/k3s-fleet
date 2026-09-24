from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from telemetry_api.database import Base
from telemetry_api.db_models import TelemetryRecord, latest_robot_records


def test_latest_robot_records_returns_one_newest_record_per_robot(telemetry_payload):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    old_record = TelemetryRecord.from_payload(telemetry_payload.model_copy(update={"timestamp": 10}))
    newest_record = TelemetryRecord.from_payload(telemetry_payload.model_copy(update={"timestamp": 20}))
    another_robot = TelemetryRecord.from_payload(
        telemetry_payload.model_copy(update={"device_id": "robot-test-2", "timestamp": 15})
    )
    session.add_all([old_record, newest_record, another_robot])
    session.commit()

    records = latest_robot_records(session)

    assert {(record.device_id, record.device_timestamp) for record in records} == {
        ("robot-test-1", 20),
        ("robot-test-2", 15),
    }


def test_latest_robot_records_excludes_robots_without_recent_telemetry(telemetry_payload):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    now = datetime.now(timezone.utc)

    stale = TelemetryRecord.from_payload(telemetry_payload)
    stale.received_at = now - timedelta(minutes=2)
    active = TelemetryRecord.from_payload(telemetry_payload.model_copy(update={"device_id": "robot-test-2"}))
    active.received_at = now - timedelta(seconds=5)
    session.add_all([stale, active])
    session.commit()

    records = latest_robot_records(session, received_since=now - timedelta(seconds=30))

    assert [record.device_id for record in records] == ["robot-test-2"]
