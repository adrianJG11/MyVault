import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
    port=5432,
    database=os.environ["POSTGRES_DB"],
)

engine = create_engine(DATABASE_URL)
SessionFactory = sessionmaker(bind=engine)


def get_session() -> Iterator[Session]:
    with SessionFactory() as session:
        yield session
