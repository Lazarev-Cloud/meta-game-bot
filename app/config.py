"""
Application configuration module.

Defines and initializes environment-specific settings using Pydantic BaseSettings.
Loads environment variables from a `.env` file.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Centralized application configuration using environment variables.

    Attributes:
        env (str): Current environment name (e.g., 'development', 'production').
        db_host (str): Database host address.
        db_port (int): Database port number.
        db_name (str): Database name.
        db_user (str): Database user name.
        db_pass (str): Database user password.
        db_engine (str): Database engine (e.g., 'postgresql', 'sqlite').
        log_level (str): Logging level (e.g., 'DEBUG', 'INFO').
        bot_token (str): Token for the bot service.
    """

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
        """Loads environment variables from `.env` file using UTF-8 encoding."""

        env_file = ".env"
        env_file_encoding = 'utf-8'

    @property
    def db_url(self) -> str:
        """
        Construct the full database connection URL based on current settings.

        Returns:
            str: A connection string compatible with SQLAlchemy.
        """
        if self.db_engine == "sqlite":
            return f"sqlite:///./{self.db_name}.db"
        return (f"{self.db_engine}://{self.db_user}:{self.db_pass}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}")


settings = Settings()
