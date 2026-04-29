import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.models.dbmodels import Base

logger = structlog.get_logger("database")

settings = get_settings()

engine = create_engine(
    settings.postgres_dsn,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

def init_db():
    logger.info("Initializing PostgreSQL database schemas (if not exist)...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schemas initialized.")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
