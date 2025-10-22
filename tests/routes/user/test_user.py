# tests/test_users.py
from fastapi.testclient import TestClient
from sqlmodel import Session, select, text

from turf_backend.auth import User, hash_password


def create_user_in_db(
    session: Session, email: str, name: str, password: str, authorized: bool = False
) -> User:
    """Create a user in DB with hashed password."""
    user = User(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        authorized=authorized,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_register_user_success(
    client: TestClient, test_session: Session, user_email, user_name
):
    test_session.exec(text("DELETE FROM user"))
    user = test_session.exec(select(User).where(User.email == user_email)).first()
    payload = {"email": user_email, "password": "securepass"}
    resp = client.post("/users/register", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == user_email
    assert body["authorized"] is False

    # confirm persisted in DB
    user = test_session.exec(select(User).where(User.email == user_email)).first()
    assert user is not None
    assert user.authorized is False


def test_register_duplicate_returns_400(
    client: TestClient, test_session: Session, user_email, user_name
):
    create_user_in_db(test_session, email=user_email, name=user_name, password="pwd1")

    payload = {"email": user_email, "password": "pwd2", "name": "Another"}
    resp = client.post("/users/register", json=payload)
    assert resp.status_code == 400


def test_login_success_returns_token(
    client: TestClient, test_session: Session, user_email, user_name
):
    password = "mysecret"
    create_user_in_db(test_session, email=user_email, name=user_name, password=password)

    payload = {"email": user_email, "password": password}
    resp = client.post("/users/login", json=payload)
    body = resp.json()
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


def test_login_wrong_password_returns_401(
    client: TestClient, test_session: Session, user_email, user_name
):
    create_user_in_db(
        test_session, email=user_email, name=user_name, password="right-password"
    )

    payload = {"email": user_email, "password": "wrong-password", "name": user_name}
    resp = client.post("/users/login", json=payload)
    assert resp.status_code == 401


def test_authorize_user_success(client: TestClient, test_session: Session):
    user = create_user_in_db(test_session, email="a@b.com", name="A", password="p")
    assert user.authorized is False

    resp = client.post(f"/users/authorize/{user.id}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == user.id
    assert body["email"] == user.email
    assert body["authorized"] is True

    # check persisted
    refreshed = test_session.exec(select(User).where(User.id == user.id)).first()
    assert refreshed.authorized is True


def test_authorize_nonexistent_returns_400(client: TestClient):
    resp = client.post("/users/authorize/99999")
    assert resp.status_code == 400


def test_authorize_already_authorized_returns_400(
    client: TestClient, test_session: Session
):
    user = create_user_in_db(
        test_session, email="auth@b.com", name="Auth", password="p", authorized=True
    )
    resp = client.post(f"/users/authorize/{user.id}")
    assert resp.status_code == 400


def test_get_all_users_and_get_by_id(client: TestClient, test_session: Session):
    u1 = create_user_in_db(test_session, email="one@x.com", name="One", password="p1")
    u2 = create_user_in_db(test_session, email="two@x.com", name="Two", password="p2")

    resp_all = client.get("/users/")
    assert resp_all.status_code == 200
    all_body = resp_all.json()
    # # should include both emails
    # emails = {u["email"] for u in all_body}
    # assert u1.email in emails and u2.email in emails

    # # test get by id success
    # resp_one = client.get(f"/users/{u1.id}")
    # assert resp_one.status_code == 200
    # one_body = resp_one.json()
    # assert one_body["email"] == u1.email
    # assert one_body["name"] == u1.name
    # assert one_body["authorized"] == u1.authorized

    # test get by id not found
    resp_missing = client.get("/users/9999999")
    assert resp_missing.status_code == 400
