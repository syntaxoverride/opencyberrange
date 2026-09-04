"""Login smoke tests: bad credentials rejected, JWT issued on good ones."""
import pytest

from jose import jwt

from app.config import settings

pytestmark = pytest.mark.db


def test_login_rejects_wrong_password(client, test_user):
    resp = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": "definitely-wrong-pw"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Incorrect username or password"


def test_login_rejects_unknown_user(client, db_schema):
    resp = client.post(
        "/api/auth/login",
        data={"username": "pytest_no_such_user", "password": "whatever123"},
    )
    assert resp.status_code == 401
    # Same generic message as a wrong password, so usernames cannot be
    # enumerated from the login endpoint.
    assert resp.json()["detail"] == "Incorrect username or password"


def test_login_issues_jwt_on_good_creds(client, test_user, test_password):
    resp = client.post(
        "/api/auth/login",
        data={"username": test_user.username, "password": test_password},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["username"] == test_user.username
    assert body["user"]["is_approved"] is True

    # The token must be a real JWT signed with the configured secret and
    # carry the username as its subject.
    claims = jwt.decode(
        body["access_token"], settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert claims["sub"] == test_user.username
    assert "exp" in claims


def test_token_grants_access_to_me_endpoint(client, auth_headers, test_user):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == test_user.username
