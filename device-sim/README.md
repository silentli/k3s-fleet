# Device Simulator (`device-sim`)

An IoT Device Simulator that mimics an robot moving around a factory floor. The simulator tracks battery life, payload weight, heading, and distance, sending structured telemetry over MQTT.

---

## Tech Stack

- **[uv](https://github.com/astral-sh/uv)**: Dependency management (`uv.lock`) and virtual environment creation. It replaces `pip` and `venv`.
- **[Pydantic V2 & Pydantic Settings](https://docs.pydantic.dev/)**: Used for configuration and validation. It guarantees that environment variables and `layout.json` data are valid before the application logic starts.
- **[Paho MQTT](https://pypi.org/project/paho-mqtt/)**: An MQTT client used to stream JSON telemetry payloads to the message broker.
- **[Pytest](https://docs.pytest.org/)**: A testing framework.
- **Docker**: Uses a `Dockerfile` with BuildKit cache mounts and a `.dockerignore` to reduce image size.

---

## Getting Started

### 1. Prerequisites
Ensure [uv](https://github.com/astral-sh/uv) is installed.

### 2. Local Setup
Clone the repository and install the dependencies using `uv`:

```bash
# Sync dependencies and create a virtual environment (.venv)
uv sync

# Activate the virtual environment (macOS/Linux)
source .venv/bin/activate
```

### 3. Configuration
The simulator requires a `layout.json` file in the `src/` directory to define the factory stations (e.g., Charging Docks, Assembly Lines).
A `.env` file can also be created in the root directory to override default MQTT configurations:

```ini
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
```

### 4. Running the Simulator
The simulator can be run directly via `uv`:

```bash
uv run python src/main.py
```

### 5. Running Tests
```bash
uv run pytest tests
```

---

## Docker

To build and run the simulator using Docker:

```bash
# Build the image
docker build -t device-sim .

# Run the container
docker run -it --rm --network host device-sim
```

*(Note: The Dockerfile uses `uv`'s cache mounting to speed up rebuilds).*
