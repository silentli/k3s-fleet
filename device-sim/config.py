import json
import logging
from pathlib import Path
from typing import List
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("device-sim.config")

# Define the base directory using modern pathlib
BASE_DIR = Path(__file__).parent.resolve()

class StationConfig(BaseModel):
    name: str
    x: float
    y: float

class Settings(BaseSettings):
    # MQTT Config
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_topic: str = "factory/telemetry"
    
    # Factory Layout File Path
    factory_layout_file: str = "layout.json"
    stations: List[StationConfig] = []
    
    # Factory Floor Dimensions
    factory_max_x: float = 100.0
    factory_max_y: float = 100.0
    
    # Robot Physical Parameters
    robot_speed_mps: float = 1.5
    battery_charge_rate: float = 8.0
    battery_drain_moving: float = 0.2
    battery_drain_idle: float = 0.1
    battery_low_threshold: float = 20.0

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    def model_post_init(self, __context):
        """Pydantic V2 hook: Automatically loads the layout.json after reading .env"""
        layout_path = Path(self.factory_layout_file)
        
        # If it's just a filename (not absolute), anchor it to the script's directory
        if not layout_path.is_absolute():
            layout_path = BASE_DIR / layout_path

        if layout_path.exists():
            try:
                raw_stations = json.loads(layout_path.read_text())
                self.stations = [StationConfig(**s) for s in raw_stations]
            except Exception as e:
                logger.error(f"Failed to parse layout file {layout_path}: {e}")
        else:
            logger.error(f"Layout file {layout_path} not found! Defaulting to empty layout.")
