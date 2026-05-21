import pytest
from models import Location, Metrics, Diagnostics, TelemetryPayload, RobotStatus

@pytest.fixture
def base_payload():
    return TelemetryPayload(
        device_id="robot-1",
        timestamp=1620000000,
        location=Location(x=10.5, y=20.2, heading_deg=90.0),
        status=RobotStatus.IDLE,
        metrics=Metrics(battery_soc_pct=100.0, payload_weight_kg=0.0, wifi_rssi_dbm=-50),
        diagnostics=Diagnostics(error_code=0, obstacle_detected=False)
    )
