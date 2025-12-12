from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    port: int = 8002
    data_dir: str = "/data"
    reports_dir: str = "/data/reports"
    file_service_url: str = "http://file-service:8001"

    @property
    def db_url(self) -> str:
        return f"sqlite:///{self.data_dir.rstrip('/')}/analysis_service.db"


settings = Settings()
