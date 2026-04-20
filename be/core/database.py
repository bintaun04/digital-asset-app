from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from app.core.config import settings

Base = declarative_base()

class VoiceUser(Base):
    __tablename__ = "voice_users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), unique=True)
    username = Column(String(100))

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()