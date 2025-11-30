import random

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, text

from turf_backend.auth import User
from turf_backend.database import get_connection
from turf_backend.main import app


# -----------------------------
# ENGINE & SESSION FIXTURES
# -----------------------------
@pytest.fixture(scope="session")
def test_engine():
    """Engine in memory (limpio)"""
    engine = create_engine(
        "sqlite:///./test.db",  # archivo SQLite en disco
        echo=True,  # opcional, para ver queries
        connect_args={"check_same_thread": False},  # necesario para TestClient
    )
    # Crear tablas una sola vez para todos los tests
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Session independiente por test"""
    with Session(test_engine) as session:
        yield session


# -----------------------------
# CLIENTE FASTAPI
# -----------------------------
@pytest.fixture
def client(test_session: Session):
    """FastAPI TestClient usando la misma sesión que los tests"""

    def override_get_connection():
        yield test_session

    app.dependency_overrides[get_connection] = override_get_connection
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# -----------------------------
# LIMPIAR TABLA USERS
# -----------------------------
@pytest.fixture(autouse=True)
def _clean_users_table(test_session: Session):
    """Borra todos los usuarios antes de cada test"""
    test_session.exec(text("DELETE FROM user"))
    test_session.commit()


# -----------------------------
# USUARIOS DE TEST
# -----------------------------
@pytest.fixture
def user_email() -> str:
    return "testuser@test.com"


@pytest.fixture
def user_name() -> str:
    return "Test User"


@pytest.fixture
def fake_user(user_email, user_name) -> User:
    """Usuario falso no persistido"""
    return User(
        id=random.randint(1, 10),
        name=user_name,
        email=user_email,
        authorized=False,
        hashed_password="test-120938123",
    )
