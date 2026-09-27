from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_legacy_database_compatibility():
    if not settings.database_url.startswith("postgresql"):
        return

    with engine.begin() as conn:
        constraint_exists = conn.execute(
            text("""
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'public.payments'::regclass
                  AND conname = 'payments_booking_id_key'
            """)
        ).fetchone()

        if constraint_exists:
            conn.execute(text("ALTER TABLE payments DROP CONSTRAINT IF EXISTS payments_booking_id_key;"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
