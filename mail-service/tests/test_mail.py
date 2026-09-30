import email
import socket
from email import policy

import pytest
from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient
from fastapi_mail import FastMail

from src.email import service
from src.email.service import MailService, build_connection_config
from src.core.config import settings
from src.main import app


class _Collector:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(email.message_from_bytes(envelope.content, policy=policy.default))
        return "250 OK"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _use_smtp(monkeypatch, port: int):
    monkeypatch.setattr(settings, "EMAIL_HOST", "127.0.0.1")
    monkeypatch.setattr(settings, "EMAIL_PORT", port)
    monkeypatch.setattr(settings, "EMAIL_TIMEOUT", 3)
    monkeypatch.setattr(MailService, "fm", FastMail(build_connection_config()))


@pytest.fixture
def smtp(monkeypatch):
    collector = _Collector()
    port = _free_port()
    controller = Controller(collector, hostname="127.0.0.1", port=port)
    controller.start()
    _use_smtp(monkeypatch, port)
    yield collector
    controller.stop()


client = TestClient(app)


def _html(msg) -> str:
    return msg.get_body(("html",)).get_content()


def test_verification_code(smtp):
    r = client.post("/api/send/verify-code", json={
        "email": "ivan@example.com", "code": "482913", "purpose": "registration", "name": "Иванов Иван"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "success"
    [msg] = smtp.messages
    assert "<ivan@example.com>" in msg["To"]
    assert msg["Subject"] == "Код подтверждения регистрации: 482913"
    html = _html(msg)
    assert "482913" in html and "Иванов Иван" in html and "завершить регистрацию" in html


def test_login_code_and_notifications(smtp):
    client.post("/api/send/verify-code", json={"email": "a@example.com", "code": "000123", "purpose": "login"})
    client.post("/api/send/success-registration",
                json={"email": "a@example.com", "name": "А Б", "nickname": "ab_nick"})
    client.post("/api/send/success-login", json={
        "email": "a@example.com", "name": "А Б", "logged_in_at": "2026-09-30T17:00:00Z",
        "ip": "10.0.0.1", "user_agent": "Firefox"})
    assert [m["Subject"] for m in smtp.messages] == [
        "Код для входа в аккаунт: 000123", "Регистрация завершена", "Выполнен вход в аккаунт"]
    assert "ab_nick" in _html(smtp.messages[1])
    login_html = _html(smtp.messages[2])
    assert "30.09.2026 20:00 (МСК)" in login_html and "10.0.0.1" in login_html and "Firefox" in login_html


def test_html_is_escaped(smtp):
    client.post("/api/send/success-registration",
                json={"email": "a@example.com", "name": "<script>x</script>", "nickname": "n"})
    html = _html(smtp.messages[0])
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_smtp_down(monkeypatch):
    _use_smtp(monkeypatch, _free_port())
    r = client.post("/api/send/verify-code", json={"email": "a@b.ru", "code": "123456", "purpose": "login"})
    assert r.status_code == 502
    assert r.json()["status"] == "error" and r.json()["error"]["code"] == 200


def test_validation_error_format():
    r = client.post("/api/send/verify-code", json={"email": "bad", "code": "12", "purpose": "other"})
    assert r.status_code == 422 and r.json()["error"]["code"] == 422


def test_healthy():
    assert client.get("/api/healthy").json()["status"] == "success"
