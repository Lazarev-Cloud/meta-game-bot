# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "development"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "mydb"
    db_user: str = "postgres"
    db_pass: str = "postgres"
    db_engine: str = "postgresql"

    log_level: str = "DEBUG"
    bot_token: str

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    @property
    def db_url(self) -> str:
        if self.db_engine == "sqlite":
            return f"sqlite:///./{self.db_name}.db"
        return (f"{self.db_engine}://{self.db_user}:{self.db_pass}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}")


settings = Settings()
