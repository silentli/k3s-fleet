from models import RobotStatus


def test_telemetry_payload_creation(base_payload):
    assert base_payload.device_id == "robot-1"
    assert base_payload.status == RobotStatus.IDLE
    assert base_payload.location.x == 10.5
    assert base_payload.location.heading_deg == 90.0

    json_data = base_payload.model_dump_json()
    assert "robot-1" in json_data
    assert "idle" in json_data
    assert "10.5" in json_data
    assert "90.0" in json_data
