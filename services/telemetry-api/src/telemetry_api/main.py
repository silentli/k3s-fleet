import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Settings
from .database import Base, create_session_factory
from .db_models import TelemetryRecord, latest_robot_records
from .mqtt_consumer import TelemetryConsumer
from .telemetry import RobotLatest, RobotStatus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
settings = Settings()
engine, SessionLocal = create_session_factory(settings.database_url)
STATIC_DIR = Path(__file__).parent / "static"
ROBOT_ONLINE_WINDOW = timedelta(seconds=30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    consumer = TelemetryConsumer(
        settings.mqtt_broker_host,
        settings.mqtt_broker_port,
        settings.mqtt_topic,
        SessionLocal,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        tls_ca_file=settings.mqtt_tls_ca_file,
    )
    consumer.start()
    app.state.consumer = consumer
    yield
    consumer.stop()
    engine.dispose()


app = FastAPI(title="Fleet Telemetry API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def as_latest(record: TelemetryRecord) -> RobotLatest:
    return RobotLatest(
        device_id=record.device_id,
        timestamp=record.device_timestamp,
        status=RobotStatus(record.status),
        destination=record.destination,
        x=record.x,
        y=record.y,
        heading_deg=record.heading_deg,
        battery_soc_pct=record.battery_soc_pct,
    )


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/health")
def health():
    return health_response({"database": database_connected(), "mqtt": mqtt_connected()})


@app.get("/health/database")
def database_health():
    return health_response({"database": database_connected()})


@app.get("/health/mqtt")
def mqtt_health():
    return health_response({"mqtt": mqtt_connected()})


def database_connected() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


def mqtt_connected() -> bool:
    consumer = getattr(app.state, "consumer", None)
    return consumer is not None and consumer.is_connected()


def health_response(checks: dict[str, bool]) -> JSONResponse:
    healthy = all(checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            **{name: "connected" if connected else "disconnected" for name, connected in checks.items()},
        },
    )


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/robots", response_model=list[RobotLatest])
def list_robots():
    received_since = datetime.now(timezone.utc) - ROBOT_ONLINE_WINDOW
    with SessionLocal() as session:
        records = latest_robot_records(session, received_since=received_since)
    return [as_latest(record) for record in records]


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
