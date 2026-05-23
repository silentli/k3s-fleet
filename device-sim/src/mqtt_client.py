import logging
from collections import deque

import paho.mqtt.client as mqtt

logger = logging.getLogger("device-sim.mqtt")

class ResilientMQTTClient:
    def __init__(self, client_id: str, host: str, port: int, topic: str, max_buffer_size: int = 500):
        self.client_id = client_id
        self.host = host
        self.port = port
        self.topic = topic
        self.is_connected = False
        self.message_buffer = deque(maxlen=max_buffer_size)

        # Initialize Paho MQTT client (compatible with v1.6.1)
        self.client = mqtt.Client(client_id=self.client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            self.is_connected = True
            self._flush_buffer()
        else:
            logger.error(f"Failed to connect, return code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        logger.warning("Disconnected from MQTT Broker!")
        self.is_connected = False

    def _flush_buffer(self):
        if self.is_connected and len(self.message_buffer) > 0:
            logger.info(f"Flushing {len(self.message_buffer)} messages from buffer...")
            while self.message_buffer:
                msg = self.message_buffer.popleft()
                try:
                    self.client.publish(self.topic, msg, qos=1)
                except Exception as e:
                    logger.error(f"Failed to publish from buffer: {e}")
                    self.message_buffer.appendleft(msg)
                    break

    def connect(self):
        try:
            self.client.connect_async(self.host, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"Failed to initialize MQTT connection: {e}")

    def publish(self, payload_json: str):
        if self.is_connected:
            try:
                self.client.publish(self.topic, payload_json, qos=1)
                logger.info(f"Published telemetry: {payload_json}")
            except Exception as e:
                logger.error(f"Publish failed: {e}")
                self.message_buffer.append(payload_json)
        else:
            logger.warning("Offline. Buffering telemetry.")
            self.message_buffer.append(payload_json)

    def disconnect(self):
        """Cleanly disconnects from the broker and stops the background thread."""
        logger.info("Initiating graceful disconnect...")
        self.client.disconnect()
        self.client.loop_stop()
