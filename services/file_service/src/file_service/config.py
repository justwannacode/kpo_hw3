from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    port: int = 8001
    data_dir: str = "/data"
    files_dir: str = "/data/files"

    @property
    def db_url(self) -> str:
        # sqlite файл
        return f"sqlite:///{self.data_dir.rstrip('/')}/file_service.db"


settings = Settings()
