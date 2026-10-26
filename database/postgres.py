import os
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import DateTime, ForeignKey, String, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

load_dotenv()

# collected info for connecting to DB from env and returned prepared URL for SQLalchemy
def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "infra"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "infrawatch"),
    )

#Checking if connecting is sucessfull
@lru_cache
def get_engine():
    return create_engine(database_url(), pool_pre_ping=True)

#One session for 1 request. Then we reach endpoint and close it by "with"
def get_session():
    with Session(get_engine()) as session:
        yield session


#Returned real time
def utcnow():
    return datetime.now(timezone.utc)


#Block with tables

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    servers: Mapped[list["Server"]] = relationship(back_populates="owner")

class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    owner: Mapped[User] = relationship(back_populates="servers")


#in case if there are no tables
def init_postgres():
    Base.metadata.create_all(get_engine())
