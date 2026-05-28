from unittest.mock import patch

import pytest

from config import StationConfig
from models import Diagnostics, Location, Metrics, RobotStatus, TelemetryPayload


@pytest.fixture
def mock_settings():
    with patch("main.settings") as mock:
        mock.stations = [
            StationConfig(name="Station_A", x=0.0, y=0.0),
            StationConfig(name="Station_B", x=10.0, y=0.0),
            StationConfig(name="Charging_Dock", x=5.0, y=5.0),
        ]
        mock.factory_max_x = 100.0
        mock.factory_max_y = 100.0
        mock.robot_speed_mps = 1.5
        mock.battery_drain_moving = 0.2
        mock.battery_drain_idle = 0.1
        mock.battery_charge_rate = 8.0
        mock.battery_low_threshold = 20.0
        yield mock


@pytest.fixture
def base_payload():
    return TelemetryPayload(
        device_id="robot-1",
        timestamp=1620000000,
        location=Location(x=10.5, y=20.2, heading_deg=90.0),
        status=RobotStatus.IDLE,
        destination="Station_A",
        metrics=Metrics(battery_soc_pct=100.0, payload_weight_kg=0.0, wifi_rssi_dbm=-50),
        diagnostics=Diagnostics(error_code=0, obstacle_detected=False),
    )
