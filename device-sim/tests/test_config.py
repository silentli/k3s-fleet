import json

import pytest
from pydantic import ValidationError

from config import Settings, StationConfig


def test_station_config():
    station = StationConfig(name="Test", x=1.5, y=2.5)
    assert station.name == "Test"
    assert station.x == 1.5
    assert station.y == 2.5

def test_settings_missing_layout_file():
    """Test that Settings initialization fails if the layout file is missing."""
    with pytest.raises((ValueError, ValidationError), match="not found"):
        Settings(factory_layout_file="does_not_exist.json")

def test_settings_empty_layout(tmp_path):
    """Test that Settings initialization fails if the layout file contains no stations."""
    empty_layout = tmp_path / "empty.json"
    empty_layout.write_text("[]")

    with pytest.raises((ValueError, ValidationError), match="must contain at least one station"):
        Settings(factory_layout_file=str(empty_layout))

def test_settings_malformed_layout(tmp_path):
    """Test that Settings initialization fails if the layout file is invalid JSON."""
    bad_layout = tmp_path / "bad.json"
    bad_layout.write_text("{bad json")

    with pytest.raises((ValueError, ValidationError), match="Failed to parse layout file"):
        Settings(factory_layout_file=str(bad_layout))

def test_settings_valid_layout(tmp_path):
    """Test that Settings initializes correctly with a valid layout file."""
    valid_layout = tmp_path / "valid.json"
    valid_data = [{"name": "Dock", "x": 10.0, "y": 10.0}]
    valid_layout.write_text(json.dumps(valid_data))

    settings = Settings(factory_layout_file=str(valid_layout))
    assert len(settings.stations) == 1
    assert settings.stations[0].name == "Dock"
