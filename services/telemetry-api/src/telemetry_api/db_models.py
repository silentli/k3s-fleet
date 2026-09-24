from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .database import Base
from .telemetry import TelemetryPayload


class TelemetryRecord(Base):
    __tablename__ = "telemetry_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    device_timestamp: Mapped[int] = mapped_column(Integer, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    heading_deg: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32))
    destination: Mapped[str] = mapped_column(String(255))
    battery_soc_pct: Mapped[float] = mapped_column(Float)
    payload_weight_kg: Mapped[float] = mapped_column(Float)
    wifi_rssi_dbm: Mapped[int] = mapped_column(Integer)
    error_code: Mapped[int] = mapped_column(Integer)
    obstacle_detected: Mapped[bool] = mapped_column(Boolean)
    raw_payload: Mapped[dict] = mapped_column(JSON)

    @classmethod
    def from_payload(cls, payload: TelemetryPayload) -> "TelemetryRecord":
        return cls(
            device_id=payload.device_id,
            device_timestamp=payload.timestamp,
            x=payload.location.x,
            y=payload.location.y,
            heading_deg=payload.location.heading_deg,
            status=payload.status.value,
            destination=payload.destination,
            battery_soc_pct=payload.metrics.battery_soc_pct,
            payload_weight_kg=payload.metrics.payload_weight_kg,
            wifi_rssi_dbm=payload.metrics.wifi_rssi_dbm,
            error_code=payload.diagnostics.error_code,
            obstacle_detected=payload.diagnostics.obstacle_detected,
            raw_payload=payload.model_dump(mode="json"),
        )


def latest_robot_records(session: Session, received_since: datetime | None = None) -> list[TelemetryRecord]:
    """Return one newest record per robot, optionally limited to recent arrivals."""
    ranked_query = (
        select(
            TelemetryRecord.id,
            func.row_number()
            .over(
                partition_by=TelemetryRecord.device_id,
                order_by=(TelemetryRecord.device_timestamp.desc(), TelemetryRecord.id.desc()),
            )
            .label("position"),
        )
    )
    if received_since is not None:
        ranked_query = ranked_query.where(TelemetryRecord.received_at >= received_since)
    ranked_records = ranked_query.subquery()

    statement = (
        select(TelemetryRecord)
        .join(ranked_records, TelemetryRecord.id == ranked_records.c.id)
        .where(ranked_records.c.position == 1)
        .order_by(TelemetryRecord.device_id)
    )
    return list(session.scalars(statement))
