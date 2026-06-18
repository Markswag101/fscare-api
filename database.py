from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fscare.db")

# Railway PostgreSQL URLs use postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Request(Base):
    __tablename__ = "requests"

    id = Column(String, primary_key=True)
    hospital = Column(String, nullable=False)
    contact = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, default="")
    priority = Column(Enum("normal", "urgent", name="priority_enum"), default="normal")
    notes = Column(Text, default="")
    status = Column(
        Enum("pending", "processing", "fulfilled", "cancelled", name="status_enum"),
        default="pending"
    )
    admin_note = Column(Text, default="")
    date_submitted = Column(DateTime, default=datetime.utcnow)
    date_actioned = Column(DateTime, nullable=True)


class RequestItem(Base):
    __tablename__ = "request_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)
    unit = Column(String, default="Tablets")
    category = Column(String, default="Other")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
