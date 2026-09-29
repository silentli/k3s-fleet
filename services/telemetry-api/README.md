# Telemetry API

Validates robot telemetry from MQTT, stores it in PostgreSQL, and shows the
latest readings through the API and factory-floor dashboard.

## Run

The API needs Mosquitto and PostgreSQL, so start the full stack from the
repository root:

```bash
bash scripts/setup-local-secrets.sh
docker compose up --build
```

Open the [dashboard](http://localhost:8000) or [API docs](http://localhost:8000/docs).

- `GET /robots`: latest readings for robots seen in the last 30 seconds.
- `GET /robots/{device_id}/latest`: last stored reading, even if the robot is offline.

## Health checks

| Endpoint | Checks |
| --- | --- |
| `/health` | Database and MQTT |
| `/health/database` | PostgreSQL connection |
| `/health/mqtt` | MQTT consumer connection |
| `/health/live` | API process |

Connection checks return 200 when healthy, otherwise 503. MQTT status checks
the connection, not message delivery.

Kubernetes uses `/health/database` for readiness and `/health/live` for startup
and liveness. `/health` is an overall diagnostic check, not a Kubernetes probe.

## Tests

Tests use fake MQTT messages and database connections; Docker is not needed.

```bash
cd services/telemetry-api
uv sync
uv run pytest
```
