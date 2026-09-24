# Telemetry API

The API subscribes to MQTT telemetry, validates each message, and writes it to
PostgreSQL. Its HTTP endpoints and dashboard show the latest reading for each
robot.

## Run it

The API needs Mosquitto and PostgreSQL, so start the full stack from the
repository root:

```bash
bash scripts/setup-local-secrets.sh
docker compose up --build
```

Open the [dashboard](http://localhost:8000) or [API docs](http://localhost:8000/docs).

`GET /robots` shows robots seen in the last 30 seconds, with one latest reading
per robot. `GET /robots/{device_id}/latest` still returns the latest stored
reading for a specific robot, even if it is offline. `GET /health` checks
database connectivity.

## Tests

The unit tests use fake MQTT messages and database sessions; they do not need
Docker Compose.

```bash
cd services/telemetry-api
uv sync
uv run pytest
```
