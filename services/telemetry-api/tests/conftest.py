import json

import pytest

from telemetry_api.telemetry import TelemetryPayload


@pytest.fixture
def telemetry_data():
    return {
        "device_id": "robot-test-1",
        "timestamp": 1_700_000_000,
        "location": {"x": 12.5, "y": 8.0, "heading_deg": 90.0},
        "status": "moving",
        "destination": "Assembly_Line_A",
        "metrics": {"battery_soc_pct": 76.5, "payload_weight_kg": 25.0, "wifi_rssi_dbm": -61},
        "diagnostics": {"error_code": 0, "obstacle_detected": False},
    }


@pytest.fixture
def telemetry_payload(telemetry_data):
    return TelemetryPayload.model_validate(telemetry_data)


@pytest.fixture
def telemetry_message(telemetry_data):
    return json.dumps(telemetry_data).encode()
