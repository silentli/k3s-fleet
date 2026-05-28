from enum import StrEnum

from pydantic import BaseModel


class RobotStatus(StrEnum):
    IDLE = "idle"
    MOVING = "moving"
    CHARGING = "charging"
    LOADING = "loading"


class Location(BaseModel):
    x: float
    y: float
    heading_deg: float


class Metrics(BaseModel):
    battery_soc_pct: float
    payload_weight_kg: float
    wifi_rssi_dbm: int


class Diagnostics(BaseModel):
    error_code: int
    obstacle_detected: bool


class TelemetryPayload(BaseModel):
    device_id: str
    timestamp: int
    location: Location
    status: RobotStatus
    destination: str
    metrics: Metrics
    diagnostics: Diagnostics
