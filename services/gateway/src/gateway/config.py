from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    port: int = 8000
    data_dir: str = "/data"
    file_service_url: str = "http://file-service:8001"
    analysis_service_url: str = "http://analysis-service:8002"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir.rstrip('/')}/gateway.db"


settings = Settings()
