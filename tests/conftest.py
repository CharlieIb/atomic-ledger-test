import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ledgerlock.db.models import Base
from ledgerlock.db.session import get_db
from ledgerlock.main import app
from ledgerlock.models import Account


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with testing_session() as session:
        session.add_all(
            [
                Account(id=1, name="Source", balance=100),
                Account(id=2, name="Destination", balance=25),
            ]
        )
        session.commit()
        yield session, testing_session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(database):
    session, _ = database

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
