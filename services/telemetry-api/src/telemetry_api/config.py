from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://fleet:fleet@postgres:5432/fleet"
    mqtt_broker_host: str = "mosquitto"
    mqtt_broker_port: int = 1883
    mqtt_topic: str = "factory/telemetry"
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_tls_ca_file: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
