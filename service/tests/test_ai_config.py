"""Task 3.1 — OpenAI client + config tests.

Covers the deliverable: a server-side OpenAI client whose key comes from the
environment and is **never exposed client-side** (PRD NFR-6).

Run on the default interpreter:
    PYTHONPATH="kernel/src:tools:service/src" python3 -m pytest service/tests/test_ai_config.py -q
"""

from __future__ import annotations

import dataclasses

import pytest
from torenone_ai import (
    DEFAULT_FALLBACK_MODEL,
    DEFAULT_MODEL,
    AIConfig,
    MissingAPIKeyError,
    build_client,
)
from torenone_ai import config as config_mod

FAKE_KEY = "sk-test-ABCDEFGHIJKLMNOP1234"


# ---------------------------------------------------------------------------
# 1. Reading config from the (server-side) environment
# ---------------------------------------------------------------------------

class TestFromEnv:
    def test_reads_api_key_from_env(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        assert cfg.api_key == FAKE_KEY  # real key available for server-side SDK use

    def test_missing_key_raises(self):
        with pytest.raises(MissingAPIKeyError):
            AIConfig.from_env({})  # no OPENAI_API_KEY

    def test_blank_key_raises(self):
        with pytest.raises(MissingAPIKeyError):
            AIConfig.from_env({"OPENAI_API_KEY": "   "})

    def test_key_is_stripped(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": f"  {FAKE_KEY}\n"})
        assert cfg.api_key == FAKE_KEY

    def test_default_model_is_gpt_5_5(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        assert cfg.model == "gpt-5.5" == DEFAULT_MODEL

    def test_default_fallback_model(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        assert cfg.fallback_model == "gpt-5.4-mini" == DEFAULT_FALLBACK_MODEL

    def test_model_override_from_env(self):
        cfg = AIConfig.from_env(
            {"OPENAI_API_KEY": FAKE_KEY, "OPENAI_MODEL": "gpt-5.5-pro"}
        )
        assert cfg.model == "gpt-5.5-pro"

    def test_fallback_override_from_env(self):
        cfg = AIConfig.from_env(
            {"OPENAI_API_KEY": FAKE_KEY, "OPENAI_FALLBACK_MODEL": "gpt-5.4-nano"}
        )
        assert cfg.fallback_model == "gpt-5.4-nano"

    def test_base_url_none_by_default(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        assert cfg.base_url is None

    def test_base_url_from_env(self):
        cfg = AIConfig.from_env(
            {"OPENAI_API_KEY": FAKE_KEY, "OPENAI_BASE_URL": "https://proxy.example/v1"}
        )
        assert cfg.base_url == "https://proxy.example/v1"


# ---------------------------------------------------------------------------
# 2. Key is NEVER exposed (the core security guarantee — NFR-6)
# ---------------------------------------------------------------------------

class TestKeyNeverExposed:
    def _cfg(self) -> AIConfig:
        return AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})

    def test_repr_does_not_contain_key(self):
        assert FAKE_KEY not in repr(self._cfg())

    def test_str_does_not_contain_key(self):
        assert FAKE_KEY not in str(self._cfg())

    def test_repr_is_redacted(self):
        r = repr(self._cfg())
        assert "***" in r  # redaction marker present

    def test_safe_dict_does_not_contain_key(self):
        safe = self._cfg().safe_dict()
        assert FAKE_KEY not in safe.values()
        # also ensure the raw key is not hiding in any stringified value
        assert FAKE_KEY not in repr(safe)

    def test_safe_dict_redacts_api_key_field(self):
        safe = self._cfg().safe_dict()
        assert safe["api_key"] == "***1234"  # last-4 hint only

    def test_safe_dict_exposes_model_metadata(self):
        safe = self._cfg().safe_dict()
        assert safe["model"] == "gpt-5.5"
        assert safe["fallback_model"] == "gpt-5.4-mini"

    def test_no_method_emits_raw_key(self):
        """The config exposes no dict/json method that leaks the raw key."""
        cfg = self._cfg()
        # safe_dict is the only dict representation and it is redacted
        assert not hasattr(cfg, "to_dict")
        assert not hasattr(cfg, "model_dump")


# ---------------------------------------------------------------------------
# 3. Env var names are server-side only (no browser exposure)
# ---------------------------------------------------------------------------

class TestServerSideOnly:
    def test_env_var_names_not_browser_exposed(self):
        for name in (
            config_mod.ENV_API_KEY,
            config_mod.ENV_MODEL,
            config_mod.ENV_FALLBACK_MODEL,
            config_mod.ENV_BASE_URL,
        ):
            assert not name.startswith("NEXT_PUBLIC_"), (
                f"{name} would be exposed to the browser — must stay server-side"
            )

    def test_api_key_env_name_is_canonical(self):
        assert config_mod.ENV_API_KEY == "OPENAI_API_KEY"


# ---------------------------------------------------------------------------
# 4. Immutability — config can't be mutated after construction
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_config_is_frozen(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.api_key = "sk-evil"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. Client factory wires the config into the OpenAI SDK
# ---------------------------------------------------------------------------

class TestBuildClient:
    def test_client_receives_api_key(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        client = build_client(cfg)
        assert client.api_key == FAKE_KEY

    def test_client_receives_base_url(self):
        cfg = AIConfig.from_env(
            {"OPENAI_API_KEY": FAKE_KEY, "OPENAI_BASE_URL": "https://proxy.example/v1"}
        )
        client = build_client(cfg)
        assert str(client.base_url).rstrip("/") == "https://proxy.example/v1"

    def test_default_base_url_when_unset(self):
        cfg = AIConfig.from_env({"OPENAI_API_KEY": FAKE_KEY})
        client = build_client(cfg)
        # SDK default points at OpenAI's API host
        assert "openai.com" in str(client.base_url)
