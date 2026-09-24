import logging

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from .db_models import TelemetryRecord
from .telemetry import TelemetryPayload

logger = logging.getLogger("fleet.mqtt")


class TelemetryConsumer:
    def __init__(
        self,
        host: str,
        port: int,
        topic: str,
        session_factory,
        username: str | None = None,
        password: str | None = None,
        tls_ca_file: str | None = None,
    ):
        self.host = host
        self.port = port
        self.topic = topic
        self.session_factory = session_factory
        self.client = mqtt.Client(client_id="fleet-api-consumer")
        if (username is None) != (password is None):
            raise ValueError("MQTT username and password must be configured together")
        if username is not None:
            self.client.username_pw_set(username, password)
        if tls_ca_file is not None:
            self.client.tls_set(ca_certs=tls_ca_file)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error("MQTT connection failed with return code %s", rc)
            return
        client.subscribe(self.topic, qos=1)
        logger.info("Subscribed to MQTT topic %s", self.topic)

    def _on_message(self, client, userdata, message):
        try:
            payload = TelemetryPayload.model_validate_json(message.payload)
        except ValidationError:
            logger.warning("Discarded invalid telemetry message", exc_info=True)
            return

        try:
            with self.session_factory() as session:
                session.add(TelemetryRecord.from_payload(payload))
                session.commit()
        except Exception:
            logger.exception("Could not store telemetry for %s", payload.device_id)

    def start(self):
        self.client.connect_async(self.host, self.port, keepalive=60)
        self.client.loop_start()

    def stop(self):
        self.client.disconnect()
        self.client.loop_stop()
