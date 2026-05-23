import logging
import math
import os
import random
import socket
import time
import uuid

from config import Settings
from models import Diagnostics, Location, Metrics, RobotStatus, TelemetryPayload
from mqtt_client import ResilientMQTTClient

# ---------------------------------------------------------
# Logging Setup
# Usage: LOG_LEVEL=DEBUG python main.py
# ---------------------------------------------------------
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("device-sim")

# ---------------------------------------------------------
# Configuration Instance
# ---------------------------------------------------------
settings = Settings()

# ---------------------------------------------------------
# Robot Logic
# ---------------------------------------------------------
class FactoryRobot:
    def __init__(self, device_id: str):
        self.device_id = device_id

        # Initial State
        self.x: float = random.uniform(0, settings.factory_max_x)
        self.y: float = random.uniform(0, settings.factory_max_y)
        self.battery_soc: float = random.uniform(40.0, 100.0)
        self.status: RobotStatus = RobotStatus.IDLE
        self.payload_weight: float = 0.0

        self.target_station = random.choice(settings.stations)
        self.heading_deg: float = 0.0

        logger.info(f"Initialized {self.device_id} at ({self.x:.1f}, {self.y:.1f}) heading to {self.target_station.name}")

    def _pick_new_station(self, exclude_name: str | None = None):
        """Picks a random target station, preventing the robot from picking its current location or the charging dock."""
        available = [
            s for s in settings.stations
            if s.name != exclude_name and s.name != "Charging_Dock"]
        return random.choice(available)

    def _handle_charging(self):
        """Manages the robot's state while docked at the charger."""
        self.status = RobotStatus.CHARGING
        self.battery_soc = min(100.0, self.battery_soc + settings.battery_charge_rate)

        if self.battery_soc >= 99.0:
            self.target_station = self._pick_new_station(exclude_name="Charging_Dock")
            self.status = RobotStatus.IDLE

    def tick(self) -> TelemetryPayload:
        # 1. Survival Override: Head to charger if battery is low
        if self.battery_soc < settings.battery_low_threshold and self.target_station.name != "Charging_Dock":
            logger.info(f"Battery low ({self.battery_soc:.1f}%), overriding target to Charging_Dock.")
            self.target_station = next((s for s in settings.stations if s.name == "Charging_Dock"), self.target_station)

        # 2. Distance Calculation
        distance = math.dist((self.x, self.y), (self.target_station.x, self.target_station.y))

        # 3. Calculate Heading
        heading_rad = math.atan2(self.target_station.y - self.y, self.target_station.x - self.x)
        self.heading_deg = (math.degrees(heading_rad) + 360) % 360  # Normalize to 0-360

        # 4. Movement & Station Logic
        if distance < settings.robot_speed_mps:
            # Snap to exact station coordinates
            self.x, self.y = self.target_station.x, self.target_station.y

            if self.target_station.name == "Charging_Dock":
                self._handle_charging()
            else:
                # Randomly decide to load cargo or idle
                self.status = RobotStatus.LOADING if random.random() > 0.5 else RobotStatus.IDLE
                self.payload_weight = random.uniform(10.0, 500.0) if self.status == RobotStatus.LOADING else 0.0
                self.battery_soc -= settings.battery_drain_idle

                # Pick next destination
                self.target_station = self._pick_new_station(exclude_name=self.target_station.name)
        else:
            # Move towards target
            self.x += math.cos(heading_rad) * settings.robot_speed_mps
            self.y += math.sin(heading_rad) * settings.robot_speed_mps
            self.status = RobotStatus.MOVING
            self.battery_soc -= settings.battery_drain_moving

        # 5. Obstacle Simulation
        obstacle_detected = random.random() < 0.05
        if obstacle_detected and self.status == RobotStatus.MOVING:
            self.status = RobotStatus.IDLE  # Pause briefly

        # 6. Build and return structured payload
        return TelemetryPayload(
            device_id=self.device_id,
            timestamp=int(time.time()),
            location=Location(
                x=round(self.x, 2),
                y=round(self.y, 2),
                heading_deg=round(self.heading_deg, 2)
            ),
            status=self.status,
            metrics=Metrics(
                battery_soc_pct=round(self.battery_soc, 1),
                payload_weight_kg=round(self.payload_weight, 1),
                wifi_rssi_dbm=random.randint(-85, -40)
            ),
            diagnostics=Diagnostics(
                error_code=0,
                obstacle_detected=obstacle_detected
            )
        )

# ---------------------------------------------------------
# Main Execution Loop
# ---------------------------------------------------------
def main():
    # Generate unique identity
    hostname = socket.gethostname()
    uuid_str = str(uuid.uuid4())[:6]
    device_id = f"robot-{hostname}-{uuid_str}"

    logger.info(f"Starting Device Simulator: {device_id}")

    # Initialize MQTT
    mqtt_client = ResilientMQTTClient(
        client_id=device_id,
        host=settings.mqtt_broker_host,
        port=settings.mqtt_broker_port,
        topic=settings.mqtt_topic
    )
    mqtt_client.connect()

    # Initialize Robot
    robot = FactoryRobot(device_id=device_id)

    # Run Simulation
    try:
        while True:
            payload = robot.tick()
            payload_json = payload.model_dump_json()

            mqtt_client.publish(payload_json)

            time.sleep(random.uniform(4.5, 5.5))

    except KeyboardInterrupt:
        logger.info("Simulation stopped by user.")
        if hasattr(mqtt_client, 'disconnect'):
            mqtt_client.disconnect()

if __name__ == "__main__":
    main()
