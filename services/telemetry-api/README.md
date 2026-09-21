# Telemetry API

Receives robot telemetry from MQTT, validates it, stores it in PostgreSQL, and
provides an HTTP API for reading the latest robot state.

```text
device-sim -> Mosquitto -> telemetry-api -> PostgreSQL
```

## Run locally

Run the complete system from the repository root:

```bash
docker compose up --build
```

Open the interactive API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).
The factory-floor dashboard is available at [http://localhost:8000](http://localhost:8000).

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Check PostgreSQL connectivity. |
| `GET /robots` | Get the latest telemetry for every robot. |
| `GET /robots/{device_id}/latest` | Get the latest telemetry for one robot. |

## Tests

The unit tests use fake MQTT messages and mocked database sessions, so they do
not need Docker Compose or external services.

```bash
cd services/telemetry-api
uv sync
uv run pytest
```
