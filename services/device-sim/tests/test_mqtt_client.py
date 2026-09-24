from unittest.mock import patch

from device_sim.mqtt_client import ResilientMQTTClient


def test_mqtt_client_initialization():
    """Test that ResilientMQTTClient initializes correctly with given parameters."""
    client = ResilientMQTTClient(
        client_id="test-client",
        host="localhost",
        port=1883,
        topic="test/topic",
        max_buffer_size=10,
    )
    assert client.client_id == "test-client"
    assert client.topic == "test/topic"
    assert client.is_connected is False
    assert client.message_buffer.maxlen == 10


@patch("device_sim.mqtt_client.mqtt.Client")
def test_mqtt_client_configures_authentication_and_tls(mock_mqtt_class):
    ResilientMQTTClient(
        "test-client",
        "mosquitto",
        8883,
        "test/topic",
        username="robot-sim",
        password="test-password",
        tls_ca_file="/etc/mqtt/ca.crt",
    )

    mock_mqtt_class.return_value.username_pw_set.assert_called_once_with("robot-sim", "test-password")
    mock_mqtt_class.return_value.tls_set.assert_called_once_with(ca_certs="/etc/mqtt/ca.crt")


@patch("device_sim.mqtt_client.mqtt.Client")
def test_mqtt_client_publish_when_offline(mock_mqtt_class):
    """Test that publish buffers messages when the client is offline."""
    client = ResilientMQTTClient("test-client", "localhost", 1883, "test/topic")
    client.is_connected = False

    client.publish('{"data": 123}')

    # Should buffer the message instead of publishing
    assert len(client.message_buffer) == 1
    assert client.message_buffer[0] == '{"data": 123}'


@patch("device_sim.mqtt_client.mqtt.Client")
def test_mqtt_client_publish_when_online(mock_mqtt_class):
    """Test that publish sends messages immediately when the client is online."""
    mock_instance = mock_mqtt_class.return_value
    client = ResilientMQTTClient("test-client", "localhost", 1883, "test/topic")

    # Override the client object to use our mock instance
    client.client = mock_instance
    client.is_connected = True

    client.publish('{"data": 123}')

    # Should call publish on the inner client
    mock_instance.publish.assert_called_once_with("test/topic", '{"data": 123}', qos=1)
    assert len(client.message_buffer) == 0
