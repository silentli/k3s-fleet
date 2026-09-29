import json
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from telemetry_api import main


@pytest.fixture
def health_dependencies(monkeypatch):
    engine = MagicMock()
    consumer = MagicMock()
    consumer.is_connected.return_value = True
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(main.app.state, "consumer", consumer, raising=False)
    return engine, consumer


@pytest.mark.parametrize(
    "database_connected,mqtt_connected,expected_status",
    [(True, True, 200), (False, True, 503), (True, False, 503)],
)
def test_overall_health_reports_both_connections(
    health_dependencies, database_connected, mqtt_connected, expected_status
):
    engine, consumer = health_dependencies
    if not database_connected:
        engine.connect.side_effect = SQLAlchemyError("Database unavailable")
    consumer.is_connected.return_value = mqtt_connected

    response = main.health()

    assert response.status_code == expected_status
    assert json.loads(response.body) == {
        "status": "ok" if expected_status == 200 else "degraded",
        "database": "connected" if database_connected else "disconnected",
        "mqtt": "connected" if mqtt_connected else "disconnected",
    }


@pytest.mark.parametrize("connected,expected_status", [(True, 200), (False, 503)])
def test_database_readiness_does_not_require_mqtt(health_dependencies, connected, expected_status):
    engine, consumer = health_dependencies
    if not connected:
        engine.connect.side_effect = SQLAlchemyError("Database unavailable")
    consumer.is_connected.return_value = False

    response = main.database_health()

    assert response.status_code == expected_status
    assert json.loads(response.body) == {
        "status": "ok" if expected_status == 200 else "degraded",
        "database": "connected" if connected else "disconnected",
    }
    consumer.is_connected.assert_not_called()


def test_mqtt_health_does_not_require_database(health_dependencies):
    engine, consumer = health_dependencies
    engine.connect.side_effect = SQLAlchemyError("Database unavailable")

    response = main.mqtt_health()

    assert response.status_code == 200
    assert json.loads(response.body) == {"status": "ok", "mqtt": "connected"}
    consumer.is_connected.assert_called_once()
    engine.connect.assert_not_called()


def test_liveness_does_not_check_dependencies(health_dependencies):
    engine, consumer = health_dependencies
    engine.connect.side_effect = SQLAlchemyError("Database unavailable")
    consumer.is_connected.return_value = False

    assert main.live() == {"status": "ok"}
    engine.connect.assert_not_called()
    consumer.is_connected.assert_not_called()
