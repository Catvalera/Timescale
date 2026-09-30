import jwt
import pytest

from src.core.config import settings
from tests.conftest import ACCESS, REFRESH, run_sql

USER = {"full_name": "Иванов  Иван Иванович", "email": "Ivan@Example.com", "nickname": "ivanov", "password": "Secret123"}
EMAIL = "ivan@example.com"


def verify(client, verify_token, code, **headers):
    return client.post("/api/verify", json={"code": code}, headers={ACCESS: verify_token, **headers})


def register_and_verify(client, mailbox, **overrides):
    data = {**USER, **overrides}
    r = client.post("/api/registration", json=data)
    assert r.status_code == 200, r.text
    email = data["email"].lower()
    r = verify(client, r.json()["token"]["access_token"], mailbox.last_code(email))
    assert r.status_code == 200, r.text
    return r.json()


def start_login(client, email=EMAIL, password="Secret123"):
    return client.post("/api/login", json={"email": email, "password": password})


def login(client, mailbox, email=EMAIL, password="Secret123"):
    r = start_login(client, email, password)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data"]["requires_verification"] is True and body["data"]["purpose"] == "login"
    r = verify(client, body["token"]["access_token"], mailbox.last_code(email),
               **{"User-Agent": "pytest-browser", "X-Forwarded-For": "203.0.113.7"})
    assert r.status_code == 200, r.text
    return r.json()


def claims(token):
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"], issuer="auth-service")


def test_registration_flow(client, mailbox):
    r = client.post("/api/registration", json=USER)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["data"] == {"requires_verification": True, "purpose": "registration", "email": EMAIL,
                            "resend_after": 60, "expires_in": 600}
    assert body["token"]["refresh_token"] == ""
    verify_token = body["token"]["access_token"]
    assert claims(verify_token)["type"] == "verify"

    [(url, payload)] = mailbox.sent
    assert url == "send/verify-code" and payload["purpose"] == "registration"
    assert payload["name"] == "Иванов Иван Иванович"

    # verify-токен не даёт доступа к API
    assert client.get("/api/user/get-data", headers={ACCESS: verify_token}).status_code == 401

    r = verify(client, verify_token, mailbox.last_code(EMAIL))
    assert r.status_code == 200
    body = r.json()
    assert body["data"]["requires_verification"] is False
    assert body["data"]["user"]["nickname"] == "ivanov" and "password" not in body["data"]["user"]
    access = body["token"]["access_token"]
    assert claims(access)["type"] == "access" and claims(access)["nickname"] == "ivanov"
    assert mailbox.urls()[-1] == "send/success-registration"

    me = client.get("/api/user/get-data", headers={ACCESS: access})
    assert me.status_code == 200 and me.json()["data"]["email"] == EMAIL and me.json()["data"]["is_verified"]


def test_password_is_hashed_with_argon2(client, mailbox):
    register_and_verify(client, mailbox)
    import asyncio
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from src.core.database.database import ASYNC_DATABASE_URL

    async def fetch():
        e = create_async_engine(ASYNC_DATABASE_URL)
        async with e.connect() as c:
            row = (await c.execute(text("select password from auth.users"))).scalar_one()
            code = (await c.execute(text("select code from auth.verify"))).scalar_one()
        await e.dispose()
        return row, code
    h, code = asyncio.run(fetch())
    assert h.startswith("$argon2id$") and "Secret123" not in h
    assert code == ""  # код после подтверждения очищен


def test_duplicates(client, mailbox):
    register_and_verify(client, mailbox)
    r = client.post("/api/registration", json=USER)
    assert r.status_code == 409 and r.json()["error"]["code"] == 106
    r = client.post("/api/registration", json={**USER, "email": "other@example.com", "nickname": "IVANOV"})
    assert r.status_code == 409 and r.json()["error"]["code"] == 109


@pytest.mark.parametrize("field, value", [
    ("password", "short1"), ("password", "onlyletters"), ("password", "12345678"),
    ("nickname", "ab"), ("nickname", "имя"), ("email", "bad"), ("full_name", " "),
])
def test_registration_validation(client, mailbox, field, value):
    r = client.post("/api/registration", json={**USER, field: value})
    assert r.status_code == 422 and r.json()["error"]["code"] == 422
    assert field in r.json()["error"]["log"]
    assert mailbox.sent == []


def test_login_flow(client, mailbox):
    register_and_verify(client, mailbox)
    body = login(client, mailbox)
    assert body["token"]["refresh_token"]
    assert body["data"]["user"]["last_login_at"]
    url, notify = mailbox.sent[-1]
    assert url == "send/success-login"
    assert notify["ip"] == "203.0.113.7" and notify["user_agent"] == "pytest-browser"


def test_login_wrong_credentials(client, mailbox):
    register_and_verify(client, mailbox)
    sent = len(mailbox.sent)
    for email, password in [(EMAIL, "Wrong1234"), ("nobody@example.com", "Secret123")]:
        r = start_login(client, email, password)
        assert r.status_code == 400 and r.json()["error"]["code"] == 100
    assert len(mailbox.sent) == sent


def test_login_twice_quickly_does_not_resend(client, mailbox):
    register_and_verify(client, mailbox)
    first = start_login(client).json()
    code = mailbox.last_code(EMAIL)
    sent = len(mailbox.sent)
    second = start_login(client).json()
    assert len(mailbox.sent) == sent  # код уже в почте
    assert verify(client, second["token"]["access_token"], code).status_code == 200
    assert first["data"]["purpose"] == "login"


def test_wrong_code_attempts(client, mailbox):
    register_and_verify(client, mailbox)
    token = start_login(client).json()["token"]["access_token"]
    good = mailbox.last_code(EMAIL)
    bad = "000000" if good != "000000" else "111111"
    for left in range(4, -1, -1):
        r = verify(client, token, bad)
        assert r.status_code == 400 and f"Осталось попыток: {left}" in r.json()["error"]["log"]
    r = verify(client, token, good)
    assert r.status_code == 429 and r.json()["error"]["code"] == 110


def test_expired_code(client, mailbox):
    token = client.post("/api/registration", json=USER).json()["token"]["access_token"]
    run_sql("UPDATE auth.verify SET expires_at = now() - interval '1 second'")
    r = verify(client, token, mailbox.last_code(EMAIL))
    assert r.status_code == 400 and r.json()["error"]["code"] == 108


def test_verify_token_purpose_must_match(client, mailbox):
    """verify-токен регистрации нельзя использовать для подтверждения входа и наоборот."""
    register_and_verify(client, mailbox)
    start_login(client)
    code = mailbox.last_code(EMAIL)
    from src.core.security import TokenService
    reg_token = TokenService.create_verify_token(1, "registration")
    assert verify(client, reg_token, code).status_code == 400


def test_resend_code(client, mailbox, monkeypatch):
    token = client.post("/api/registration", json=USER).json()["token"]["access_token"]
    first = mailbox.last_code(EMAIL)
    r = client.post("/api/verify/resend", headers={ACCESS: token})
    assert r.status_code == 429 and r.json()["error"]["code"] == 107

    monkeypatch.setattr(settings, "CODE_RESEND_SECONDS", 0)
    r = client.post("/api/verify/resend", headers={ACCESS: token})
    assert r.status_code == 200
    second = mailbox.last_code(EMAIL)
    new_token = r.json()["token"]["access_token"]
    if first != second:
        assert verify(client, new_token, first).status_code == 400
    assert verify(client, new_token, second).status_code == 200


def test_login_unverified_continues_registration(client, mailbox):
    client.post("/api/registration", json=USER)
    run_sql("UPDATE auth.verify SET expires_at = now() - interval '1 second', sent_at = now() - interval '1 hour'")
    r = start_login(client)
    assert r.status_code == 200
    assert r.json()["data"]["purpose"] == "registration"
    assert mailbox.sent[-1][1]["purpose"] == "registration"
    r = verify(client, r.json()["token"]["access_token"], mailbox.last_code(EMAIL))
    assert r.status_code == 200 and mailbox.urls()[-1] == "send/success-registration"


def test_register_again_before_verification_updates_data(client, mailbox, monkeypatch):
    client.post("/api/registration", json=USER)
    assert client.post("/api/registration", json=USER).status_code == 429  # код только что отправлен
    monkeypatch.setattr(settings, "CODE_RESEND_SECONDS", 0)
    r = client.post("/api/registration", json={**USER, "nickname": "ivan2", "password": "NewPass123"})
    assert r.status_code == 200
    body = verify(client, r.json()["token"]["access_token"], mailbox.last_code(EMAIL)).json()
    assert body["data"]["user"]["nickname"] == "ivan2"
    login(client, mailbox, password="NewPass123")


def test_mail_down_rolls_back(client, mailbox):
    mailbox.down = True
    r = client.post("/api/registration", json=USER)
    assert r.status_code == 503 and r.json()["error"]["code"] == 111
    mailbox.down = False
    assert client.post("/api/registration", json=USER).status_code == 200  # пользователь не «завис»


def test_refresh_logout_and_token_types(client, mailbox):
    tokens = register_and_verify(client, mailbox)["token"]
    r = client.post("/api/tokens/refresh", headers={REFRESH: tokens["refresh_token"]})
    assert r.status_code == 200 and claims(r.json()["token"]["access_token"])["type"] == "access"
    assert client.post("/api/tokens/refresh", headers={REFRESH: tokens["access_token"]}).status_code == 401
    assert client.get("/api/user/get-data", headers={ACCESS: tokens["refresh_token"]}).status_code == 401
    assert client.get("/api/user/get-data").status_code == 401
    forged = jwt.encode({"sub": "1", "type": "access", "iss": "auth-service", "iat": 0, "exp": 9999999999},
                        "wrong-secret-wrong-secret-wrong-secret", algorithm="HS256")
    assert client.get("/api/user/get-data", headers={ACCESS: forged}).status_code == 401
    r = client.post("/api/logout", headers={ACCESS: tokens["access_token"]})
    assert r.status_code == 200 and r.json()["token"] == {"access_token": "", "refresh_token": ""}
