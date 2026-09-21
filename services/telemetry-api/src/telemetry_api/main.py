import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from .config import Settings
from .database import Base, create_session_factory
from .db_models import TelemetryRecord
from .mqtt_consumer import TelemetryConsumer
from .telemetry import RobotLatest, RobotStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
settings = Settings()
engine, SessionLocal = create_session_factory(settings.database_url)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    consumer = TelemetryConsumer(settings.mqtt_broker_host, settings.mqtt_broker_port, settings.mqtt_topic, SessionLocal)
    consumer.start()
    app.state.consumer = consumer
    yield
    consumer.stop()
    engine.dispose()


app = FastAPI(title="Fleet Telemetry API", lifespan=lifespan)


def as_latest(record: TelemetryRecord) -> RobotLatest:
    return RobotLatest(
        device_id=record.device_id,
        timestamp=record.device_timestamp,
        status=RobotStatus(record.status),
        destination=record.destination,
        x=record.x,
        y=record.y,
        battery_soc_pct=record.battery_soc_pct,
    )


@app.get("/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/robots", response_model=list[RobotLatest])
def list_robots():
    with SessionLocal() as session:
        records = session.query(TelemetryRecord).order_by(TelemetryRecord.device_timestamp.desc()).all()

    latest_by_device = {}
    for record in records:
        latest_by_device.setdefault(record.device_id, as_latest(record))
    return list(latest_by_device.values())


@app.get("/robots/{device_id}/latest", response_model=RobotLatest)
def latest_robot_telemetry(device_id: str):
    with SessionLocal() as session:
        record = (
            session.query(TelemetryRecord)
            .filter(TelemetryRecord.device_id == device_id)
            .order_by(TelemetryRecord.device_timestamp.desc())
            .first()
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Robot has not sent telemetry")
    return as_latest(record)
