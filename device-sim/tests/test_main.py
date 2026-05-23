from main import FactoryRobot
from models import RobotStatus


def test_factory_robot_init(mock_settings):
    robot = FactoryRobot("test-robot")
    assert robot.device_id == "test-robot"
    assert robot.target_station.name in ["Station_A", "Station_B", "Charging_Dock"]

def test_factory_robot_low_battery_override(mock_settings):
    robot = FactoryRobot("test-robot")
    # Set battery low
    robot.battery_soc = 15.0
    # Set target to a normal station
    robot.target_station = mock_settings.stations[0]  # Station_A
    robot.tick()
    # It should override and head to Charging_Dock
    assert robot.target_station.name == "Charging_Dock"

def test_factory_robot_charging(mock_settings):
    robot = FactoryRobot("test-robot")

    # Snap to charging dock
    robot.target_station = mock_settings.stations[2]
    robot.x, robot.y = robot.target_station.x, robot.target_station.y
    robot.battery_soc = 90.0

    robot.tick()
    assert robot.status == RobotStatus.CHARGING
    assert robot.battery_soc == 98.0  # 90.0 + 8.0

def test_factory_robot_finish_charging(mock_settings):
    robot = FactoryRobot("test-robot")

    robot.target_station = mock_settings.stations[2]
    robot.x, robot.y = robot.target_station.x, robot.target_station.y
    robot.battery_soc = 95.0

    robot.tick()
    # 95.0 + 8.0 = 103.0, but capped at 100.0
    assert robot.battery_soc == 100.0
    # Since it's >= 99.0, it should switch target and become IDLE
    assert robot.status == RobotStatus.IDLE
    assert robot.target_station.name != "Charging_Dock"
