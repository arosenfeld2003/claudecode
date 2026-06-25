"""Tests for admin authentication module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from monitor.admin_auth import (
    authenticate,
    get_credentials_path,
    hash_password,
    is_password_set,
    load_password_hash,
    save_password_hash,
    verify_password,
)


class TestHashPassword:
    def test_produces_pbkdf2_prefix(self) -> None:
        h = hash_password("secret123")
        assert h.startswith("pbkdf2:sha256:")

    def test_unique_salts(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_five_colon_parts(self) -> None:
        parts = hash_password("x").split(":")
        assert len(parts) == 5


class TestVerifyPassword:
    def test_correct_password_verifies(self) -> None:
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_wrong_password_fails(self) -> None:
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_malformed_hash_fails(self) -> None:
        assert verify_password("pass", "not-a-valid-hash") is False

    def test_empty_password_fails_against_real_hash(self) -> None:
        h = hash_password("realpass")
        assert verify_password("", h) is False


class TestCredentialsPath:
    def test_returns_default_under_home(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADMIN_CREDS_PATH", None)
            os.environ.pop("MONITOR_DATA_DIR", None)
            path = get_credentials_path()
        assert path.name == "admin.creds"
        assert ".openclaw" in str(path)

    def test_respects_admin_creds_path_env(self, tmp_path: Path) -> None:
        custom = str(tmp_path / "custom.creds")
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": custom}):
            assert get_credentials_path() == Path(custom)

    def test_respects_monitor_data_dir_env(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"MONITOR_DATA_DIR": str(tmp_path), "ADMIN_CREDS_PATH": ""}):
            os.environ.pop("ADMIN_CREDS_PATH", None)
            path = get_credentials_path()
        assert path == tmp_path / "admin.creds"


class TestSaveAndLoadPasswordHash:
    def test_round_trip(self, tmp_path: Path) -> None:
        creds = tmp_path / "admin.creds"
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(creds)}):
            h = hash_password("mypassword")
            save_password_hash(h)
            assert load_password_hash() == h

    def test_file_permissions_are_600(self, tmp_path: Path) -> None:
        creds = tmp_path / "admin.creds"
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(creds)}):
            save_password_hash(hash_password("x"))
        assert oct(creds.stat().st_mode)[-3:] == "600"

    def test_env_var_takes_priority(self, tmp_path: Path) -> None:
        env_hash = hash_password("from_env")
        file_hash = hash_password("from_file")
        creds = tmp_path / "admin.creds"
        creds.write_text(file_hash + "\n")
        with patch.dict(
            os.environ,
            {"ADMIN_PASSWORD_HASH": env_hash, "ADMIN_CREDS_PATH": str(creds)},
        ):
            assert load_password_hash() == env_hash

    def test_returns_none_when_nothing_set(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(tmp_path / "missing.creds")}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            assert load_password_hash() is None


class TestIsPasswordSet:
    def test_false_when_no_creds(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(tmp_path / "x.creds")}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            assert is_password_set() is False

    def test_true_after_save(self, tmp_path: Path) -> None:
        creds = tmp_path / "admin.creds"
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(creds)}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            save_password_hash(hash_password("pass1234"))
            assert is_password_set() is True


class TestAuthenticate:
    def test_valid_credentials(self, tmp_path: Path) -> None:
        creds = tmp_path / "admin.creds"
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(creds)}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            save_password_hash(hash_password("correct_pw"))
            assert authenticate("admin", "correct_pw") is True

    def test_wrong_password(self, tmp_path: Path) -> None:
        creds = tmp_path / "admin.creds"
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(creds)}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            save_password_hash(hash_password("correct_pw"))
            assert authenticate("admin", "wrong") is False

    def test_wrong_username(self, tmp_path: Path) -> None:
        creds = tmp_path / "admin.creds"
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(creds)}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            save_password_hash(hash_password("pass"))
            assert authenticate("root", "pass") is False

    def test_no_password_set(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"ADMIN_CREDS_PATH": str(tmp_path / "missing")}):
            os.environ.pop("ADMIN_PASSWORD_HASH", None)
            assert authenticate("admin", "anything") is False
