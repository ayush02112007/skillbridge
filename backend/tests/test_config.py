"""Settings parsing.

The list-valued settings are the ones a human edits by hand in a `.env`, and
they are the ones that used to fail: pydantic-settings JSON-decodes complex
fields straight out of a dotenv file, so `CORS_ORIGINS=http://a,http://b` —
the form `.env.example` documents — raised a SettingsError before any
validator could run. Following the README was enough to trigger it.
"""
from __future__ import annotations

import pytest

from app.core.config import DEV_JWT_SECRET, DEV_REFRESH_SECRET, Settings


def _settings(**overrides: object) -> Settings:
    """Build settings from explicit values, ignoring any .env on disk."""
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


class TestListSettings:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("http://a.test,http://b.test", ["http://a.test", "http://b.test"]),
            ("http://a.test, http://b.test ", ["http://a.test", "http://b.test"]),
            ('["http://a.test","http://b.test"]', ["http://a.test", "http://b.test"]),
            ("http://only.test", ["http://only.test"]),
            ("", []),
            ("   ", []),
        ],
    )
    def test_cors_origins_accepts_both_forms(self, raw: str, expected: list[str]) -> None:
        assert expected == _settings(CORS_ORIGINS=raw).CORS_ORIGINS

    def test_trusted_hosts_accepts_a_comma_separated_list(self) -> None:
        assert _settings(TRUSTED_HOSTS="app.test,api.test").TRUSTED_HOSTS == [
            "app.test",
            "api.test",
        ]

    def test_upload_mime_accepts_a_comma_separated_list(self) -> None:
        value = _settings(ALLOWED_UPLOAD_MIME="application/pdf,image/png")
        assert value.ALLOWED_UPLOAD_MIME == ["application/pdf", "image/png"]

    def test_an_already_parsed_list_passes_through(self) -> None:
        assert _settings(CORS_ORIGINS=["http://a.test"]).CORS_ORIGINS == ["http://a.test"]

    def test_malformed_json_says_what_was_expected(self) -> None:
        with pytest.raises(ValueError, match="comma separated"):
            _settings(CORS_ORIGINS='["unclosed')


class TestDotEnvParsing:
    def test_a_generated_env_file_loads(self, tmp_path) -> None:
        """The exact shapes `.env.example` uses, including inline comments."""
        env = tmp_path / ".env"
        env.write_text(
            "ENVIRONMENT=development\n"
            "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000   # not * in prod\n"
            "TRUSTED_HOSTS=*\n"
            "ALLOWED_UPLOAD_MIME=application/pdf,image/png,image/jpeg\n"
            "MAX_UPLOAD_SIZE_MB=10\n"
            "MATCH_WEIGHT_SKILLS=0.50\n"
        )
        loaded = Settings(_env_file=str(env))  # type: ignore[arg-type]

        assert loaded.CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]
        assert loaded.TRUSTED_HOSTS == ["*"]
        assert loaded.ALLOWED_UPLOAD_MIME == ["application/pdf", "image/png", "image/jpeg"]
        assert loaded.MAX_UPLOAD_SIZE_MB == 10


class TestRuntimeValidation:
    def test_development_defaults_are_accepted(self) -> None:
        assert _settings(ENVIRONMENT="development").validate_runtime() == []

    def test_production_refuses_the_development_secrets(self) -> None:
        problems = _settings(
            ENVIRONMENT="production",
            JWT_SECRET=DEV_JWT_SECRET,
            JWT_REFRESH_SECRET=DEV_REFRESH_SECRET,
        ).validate_runtime()
        assert any("JWT_SECRET" in p for p in problems)
        assert any("JWT_REFRESH_SECRET" in p for p in problems)

    def test_production_refuses_debug_and_wildcards(self) -> None:
        problems = _settings(
            ENVIRONMENT="production",
            DEBUG=True,
            JWT_SECRET="a-real-secret-value-for-testing-only-not-a-default",
            JWT_REFRESH_SECRET="a-different-real-secret-value-for-testing-only",
            CORS_ORIGINS="*",
            TRUSTED_HOSTS="*",
        ).validate_runtime()
        joined = " ".join(problems)
        assert "DEBUG" in joined
        assert "CORS_ORIGINS" in joined
        assert "TRUSTED_HOSTS" in joined

    def test_production_refuses_a_shared_signing_key(self) -> None:
        """Signing both token kinds with one key lets a refresh token be
        replayed as an access token."""
        same = "one-secret-used-for-both-which-is-the-bug-being-caught"
        problems = _settings(
            ENVIRONMENT="production",
            JWT_SECRET=same,
            JWT_REFRESH_SECRET=same,
            SECURE_COOKIES=True,
            CORS_ORIGINS="https://app.test",
            TRUSTED_HOSTS="app.test",
            DEBUG=False,
        ).validate_runtime()
        assert any("must differ" in p for p in problems)

    def test_production_requires_secure_cookies(self) -> None:
        problems = _settings(
            ENVIRONMENT="production",
            JWT_SECRET="a-real-secret-value-for-testing-only-not-a-default",
            JWT_REFRESH_SECRET="a-different-real-secret-value-for-testing-only",
            SECURE_COOKIES=False,
            CORS_ORIGINS="https://app.test",
            TRUSTED_HOSTS="app.test",
            DEBUG=False,
        ).validate_runtime()
        assert any("SECURE_COOKIES" in p for p in problems)

    def test_a_correctly_configured_production_passes(self) -> None:
        assert _settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET="a-real-secret-value-for-testing-only-not-a-default",
            JWT_REFRESH_SECRET="a-different-real-secret-value-for-testing-only",
            CORS_ORIGINS="https://app.test",
            TRUSTED_HOSTS="app.test",
            SECURE_COOKIES=True,
        ).validate_runtime() == []

    def test_match_weights_must_sum_to_one(self) -> None:
        problems = _settings(MATCH_WEIGHT_SKILLS=0.90).validate_runtime()
        assert any("weight" in p.lower() for p in problems)

    def test_default_match_weights_sum_to_one(self) -> None:
        assert sum(_settings().match_weights.values()) == pytest.approx(1.0)
