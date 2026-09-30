"""Tests for secret redaction (no real secrets used)."""

import pytest
from utils.distillation.redactor import redact_secrets, REDACTED


class TestRedactor:
    def test_sk_key_redacted(self):
        text = "мой ключ: sk-abc123def456ghi789jkl012"
        result, counts = redact_secrets(text)
        assert "sk-abc123def456ghi789jkl012" not in result
        assert REDACTED in result
        assert counts.get("sk_key") == 1

    def test_bearer_token_redacted(self):
        text = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9"
        result, counts = redact_secrets(text)
        assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert counts.get("bearer") == 1 or counts.get("jwt") == 1

    def test_jwt_redacted(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        text = f"token is {jwt} here"
        result, counts = redact_secrets(text)
        assert jwt not in result
        assert counts.get("jwt") == 1

    def test_linear_key_redacted(self):
        text = "lin_api_" + "a" * 48
        result, counts = redact_secrets(text)
        assert "lin_api_" + "a" * 48 not in result
        assert counts.get("linear_key") == 1

    def test_github_token_redacted(self):
        token = "ghp_" + "A" * 36
        result, counts = redact_secrets(f"use {token}")
        assert token not in result
        assert counts.get("github_token") == 1

    def test_google_api_key_redacted(self):
        key = "AIza" + "B" * 35
        result, counts = redact_secrets(f"key={key}")
        assert key not in result
        assert counts.get("google_api_key") == 1

    def test_aws_key_redacted(self):
        text = "AKIAIOSFODNN7EXAMPLE"
        result, counts = redact_secrets(text)
        assert text not in result
        assert counts.get("aws_key") == 1

    def test_slack_token_redacted(self):
        token = "xoxb-1234567890-abcdef"
        result, counts = redact_secrets(token)
        assert token not in result
        assert counts.get("slack_token") == 1

    def test_url_param_token_redacted(self):
        text = "https://example.com?token=abcdefghij1234567890&foo=bar"
        result, counts = redact_secrets(text)
        assert "abcdefghij1234567890" not in result
        assert "token=" in result  # key name preserved
        assert counts.get("url_param_token") == 1

    def test_kv_secret_redacted(self):
        text = '"apiKey": "super_secret_value_12345678"'
        result, counts = redact_secrets(text)
        assert "super_secret_value_12345678" not in result
        assert counts.get("kv_secret") == 1

    def test_pem_key_redacted(self):
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWep4PAtGoRBh1h5H\n"
            "-----END RSA PRIVATE KEY-----"
        )
        result, counts = redact_secrets(f"here:\n{pem}\ndone")
        assert "MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn" not in result
        assert counts.get("pem_private_key") == 1

    def test_no_false_positive_on_short_strings(self):
        text = "sk-short, token=abc, normal text"
        result, counts = redact_secrets(text)
        assert result == text
        assert counts == {}

    def test_no_false_positive_on_sha_or_uuid(self):
        text = "commit 538a658d and uuid 550e8400-e29b-41d4-a716-446655440000"
        result, counts = redact_secrets(text)
        assert result == text

    def test_counts_only_no_values_leaked(self):
        """Return value must not contain matched secrets."""
        secret = "sk-" + "x" * 30
        _, counts = redact_secrets(secret)
        counts_str = str(counts)
        assert secret not in counts_str

    def test_multiple_secrets_counted(self):
        text = "sk-" + "a" * 25 + " and sk-" + "b" * 25
        result, counts = redact_secrets(text)
        assert counts.get("sk_key") == 2
