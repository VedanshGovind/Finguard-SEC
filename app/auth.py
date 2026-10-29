"""Minimal session auth: PBKDF2-hashed credential, in-memory bearer tokens, login throttling."""
import hashlib
import hmac
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

_bearer = HTTPBearer(auto_error=False)
_salt = os.urandom(16)
_sessions = {}   # token -> (username, expires_at)
_attempts = {}   # ip -> (failures, locked_until)


def _digest(value: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", value.encode(), _salt, 200_000)


_user_digest = _digest(settings.AUTH_USERNAME)
_pass_digest = _digest(settings.AUTH_PASSWORD)


def login(username: str, password: str, ip: str) -> dict:
    failures, locked_until = _attempts.get(ip, (0, 0.0))
    if locked_until > time.time():
        raise HTTPException(429, "Too many attempts. Try again shortly.")

    ok_user = hmac.compare_digest(_digest(username), _user_digest)
    ok_pass = hmac.compare_digest(_digest(password), _pass_digest)
    if not (ok_user and ok_pass):
        failures += 1
        _attempts[ip] = (failures, time.time() + 30 if failures >= 5 else 0.0)
        raise HTTPException(401, "Invalid credentials.")

    _attempts.pop(ip, None)
    token = secrets.token_urlsafe(32)
    _sessions[token] = (settings.AUTH_USERNAME, time.time() + settings.SESSION_TTL_SECONDS)
    return {"token": token, "username": settings.AUTH_USERNAME, "expires_in": settings.SESSION_TTL_SECONDS}


def logout(token: str) -> None:
    _sessions.pop(token, None)


def require_auth(creds: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    entry = _sessions.get(creds.credentials) if creds else None
    if not entry or entry[1] < time.time():
        if creds:
            _sessions.pop(creds.credentials, None)
        raise HTTPException(401, "Authentication required.")
    return entry[0]


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"
