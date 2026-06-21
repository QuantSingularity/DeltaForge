"""
Tests for the authentication layer (code/backend/api/auth.py).

These exercise the user store, password hashing, and HMAC token round-trips
directly, so they need no running server and no extra dependencies.
"""

import time

import pytest
from backend.api.auth import UserStore, create_token, verify_token


@pytest.fixture
def store(tmp_path):
    return UserStore(path=str(tmp_path / "users.json"))


class TestUserStore:
    def test_register_returns_public_user(self, store):
        user = store.register("Jane", "jane@desk.com", "hunter2pass")
        assert user["email"] == "jane@desk.com"
        assert user["name"] == "Jane"
        assert "id" in user
        # The public view never leaks the hash or salt.
        assert "password_hash" not in user and "salt" not in user

    def test_register_rejects_duplicate_email(self, store):
        store.register("Jane", "jane@desk.com", "hunter2pass")
        with pytest.raises(KeyError):
            store.register("Other", "JANE@desk.com", "anotherpass")

    def test_register_rejects_short_password(self, store):
        with pytest.raises(ValueError):
            store.register("Jane", "jane@desk.com", "short")

    def test_register_rejects_bad_email(self, store):
        with pytest.raises(ValueError):
            store.register("Jane", "not-an-email", "hunter2pass")

    def test_verify_correct_password(self, store):
        store.register("Jane", "jane@desk.com", "hunter2pass")
        user = store.verify("jane@desk.com", "hunter2pass")
        assert user and user["email"] == "jane@desk.com"

    def test_verify_wrong_password(self, store):
        store.register("Jane", "jane@desk.com", "hunter2pass")
        assert store.verify("jane@desk.com", "wrongpass") is None

    def test_verify_unknown_user(self, store):
        assert store.verify("nobody@desk.com", "whatever12") is None

    def test_persists_across_instances(self, tmp_path):
        path = str(tmp_path / "users.json")
        UserStore(path=path).register("Jane", "jane@desk.com", "hunter2pass")
        # A fresh store reading the same file can authenticate the user.
        assert UserStore(path=path).verify("jane@desk.com", "hunter2pass")

    def test_by_id(self, store):
        user = store.register("Jane", "jane@desk.com", "hunter2pass")
        assert store.by_id(user["id"])["email"] == "jane@desk.com"
        assert store.by_id("does-not-exist") is None


class TestTokens:
    SECRET = b"test-secret-key-do-not-use-in-prod"

    def test_round_trip(self):
        user = {"id": "abc123", "email": "jane@desk.com"}
        token = create_token(user, self.SECRET)
        payload = verify_token(token, self.SECRET)
        assert payload and payload["sub"] == "abc123"
        assert payload["email"] == "jane@desk.com"

    def test_tampered_token_rejected(self):
        token = create_token({"id": "abc123", "email": "j@d.com"}, self.SECRET)
        body, sig = token.split(".", 1)
        tampered = body + "x." + sig
        assert verify_token(tampered, self.SECRET) is None

    def test_wrong_secret_rejected(self):
        token = create_token({"id": "abc123", "email": "j@d.com"}, self.SECRET)
        assert verify_token(token, b"a-different-secret") is None

    def test_malformed_token_rejected(self):
        assert verify_token("not-a-token", self.SECRET) is None
        assert verify_token("", self.SECRET) is None

    def test_expired_token_rejected(self, monkeypatch):
        import backend.api.auth as auth_mod

        token = create_token({"id": "abc123", "email": "j@d.com"}, self.SECRET)
        # Jump past the token TTL.
        real_time = time.time
        monkeypatch.setattr(
            auth_mod.time,
            "time",
            lambda: real_time() + auth_mod._TOKEN_TTL_SECONDS + 10,
        )
        assert verify_token(token, self.SECRET) is None
