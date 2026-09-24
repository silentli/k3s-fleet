from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from telemetry_api.mqtt_consumer import TelemetryConsumer


@patch("telemetry_api.mqtt_consumer.mqtt.Client")
def test_consumer_configures_authentication_and_tls(mock_mqtt_class):
    TelemetryConsumer(
        "mosquitto",
        8883,
        "factory/telemetry",
        MagicMock(),
        username="telemetry-api",
        password="test-password",
        tls_ca_file="/etc/mqtt/ca.crt",
    )

    mock_mqtt_class.return_value.username_pw_set.assert_called_once_with("telemetry-api", "test-password")
    mock_mqtt_class.return_value.tls_set.assert_called_once_with(ca_certs="/etc/mqtt/ca.crt")


def test_consumer_validates_and_persists_an_mqtt_message(telemetry_message):
    session = MagicMock()
    session_factory = MagicMock()
    session_factory.return_value.__enter__.return_value = session
    consumer = TelemetryConsumer("mosquitto", 1883, "factory/telemetry", session_factory)

    consumer._on_message(None, None, SimpleNamespace(payload=telemetry_message))

    session.add.assert_called_once()
    session.commit.assert_called_once()
    record = session.add.call_args.args[0]
    assert record.device_id == "robot-test-1"
    assert record.x == 12.5
    assert record.heading_deg == 90.0
    assert record.status == "moving"
    assert record.raw_payload["metrics"]["battery_soc_pct"] == 76.5


def test_consumer_discards_invalid_mqtt_message_without_writing():
    session_factory = MagicMock()
    consumer = TelemetryConsumer("mosquitto", 1883, "factory/telemetry", session_factory)

    consumer._on_message(None, None, SimpleNamespace(payload=b'{"not": "telemetry"}'))

    session_factory.assert_not_called()
