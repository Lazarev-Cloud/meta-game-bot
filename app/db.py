from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


def get_db_url():
    if settings.db_engine == "sqlite":
        return f"sqlite:///./{settings.db_name}.db"
    return (f"{settings.db_engine}://{settings.db_user}:{settings.db_pass}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}")


engine = create_engine(get_db_url(), echo=(settings.log_level == "DEBUG"))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
