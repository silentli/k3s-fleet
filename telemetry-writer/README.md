# Telemetry Writer

A lightweight, concurrent Go service that consumes JSON telemetry messages from an MQTT broker and persists them to a PostgreSQL database.

## Quick Start

### Local Development
```bash
# Run locally (requires running MQTT broker and Postgres)
go run main.go
```

### Docker
```bash
# Build the container image
docker build -t telemetry-writer:v1.0.0 .
```

## Environment Configuration

| Variable | Default | Description |
|---|---|---|
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker host |
| `MQTT_BROKER_PORT` | `1883` | MQTT broker port |
| `MQTT_TOPIC` | `factory/telemetry` | Topic to subscribe to |
| `DB_HOST` | `postgres` | Postgres database host |
| `DB_USER` | `postgres` | Postgres username |
| `DB_PASSWORD` | `postgres123` | Postgres password |
| `DB_NAME` | `telemetry` | Postgres database name |
