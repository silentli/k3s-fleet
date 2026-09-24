# Device simulator

Simulates a robot moving between stations in `src/device_sim/layout.json`.
It publishes position, battery, and other telemetry to Mosquitto over MQTT.

The easiest way to run it is with the rest of the stack from the
[repository root](../../README.md). The steps below are for running the
simulator on its own.

## Run with uv

First, from the repository root, create the MQTT credentials and start the
broker:

```bash
bash scripts/setup-local-secrets.sh
docker compose up -d mosquitto
```

Then, from `services/device-sim`:

```bash
cp .env.example .env
uv sync
PYTHONPATH=src uv run --env-file ../../k8s/base/secrets/device-sim-mqtt.env \
  python -m device_sim.main
```

`.env` holds the local broker address, CA path, and simulator settings. The
password stays in the generated `device-sim-mqtt.env` file; you do not need to
copy it into `.env`.

## Run the Docker image separately

With the Compose broker running, build the image and run it from
`services/device-sim`:

```bash
docker build -t device-sim .
docker run -it --rm \
  --env-file ../../k8s/base/secrets/device-sim-mqtt.env \
  --add-host=host.docker.internal:host-gateway \
  -e MQTT_BROKER_HOST=host.docker.internal \
  -e MQTT_BROKER_PORT=8883 \
  -e MQTT_TLS_CA_FILE=/etc/mqtt/ca.crt \
  -v "$PWD/../../k8s/base/secrets/mqtt-ca.crt:/etc/mqtt/ca.crt:ro" \
  device-sim
```

## Checks

```bash
uv run pytest
uv run ruff check .
```
