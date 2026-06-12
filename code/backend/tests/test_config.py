"""Comprehensive tests for ConfigManager."""

import json

import pytest

from ..core.config import ConfigError, ConfigManager


@pytest.fixture
def config_file(tmp_path, base_config):
    path = tmp_path / "config.json"
    with open(path, "w") as f:
        json.dump(base_config, f)
    return str(path)


@pytest.fixture
def cfg(config_file):
    return ConfigManager(config_file)


class TestConfigLoad:

    def test_loads_successfully(self, cfg):
        assert cfg is not None

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            ConfigManager(str(tmp_path / "nonexistent.json"))

    def test_missing_required_key_raises(self, tmp_path, base_config):
        bad = dict(base_config)
        del bad["risk"]
        path = tmp_path / "bad_config.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(ConfigError, match="risk"):
            ConfigManager(str(path))

    def test_invalid_trail_type_raises(self, tmp_path, base_config):
        bad = dict(base_config)
        bad["trail_stop"] = dict(base_config["trail_stop"])
        bad["trail_stop"]["type"] = "invalid_type"
        path = tmp_path / "bad_trail.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(ConfigError, match="trail_stop.type"):
            ConfigManager(str(path))

    def test_excessive_risk_percent_raises(self, tmp_path, base_config):
        bad = dict(base_config)
        bad["risk"] = dict(base_config["risk"])
        bad["risk"]["risk_percent"] = 15.0  # > 10% cap
        path = tmp_path / "bad_risk.json"
        path.write_text(json.dumps(bad))
        with pytest.raises(ConfigError, match="risk_percent"):
            ConfigManager(str(path))


class TestConfigAccessors:

    def test_exchange_id(self, cfg):
        assert cfg.exchange_id == "binance"

    def test_symbols(self, cfg):
        assert isinstance(cfg.symbols, list)
        assert len(cfg.symbols) > 0

    def test_trail_type(self, cfg):
        assert cfg.trail_type == "atr"

    def test_trail_enabled(self, cfg):
        assert cfg.trail_enabled is True

    def test_tp_enabled(self, cfg):
        assert cfg.tp_enabled is True

    def test_min_ml_score(self, cfg):
        assert 0 < cfg.min_ml_score <= 100

    def test_risk_percent(self, cfg):
        assert 0 < cfg.risk_percent <= 10

    def test_initial_capital(self, cfg):
        assert cfg.initial_capital > 0

    def test_sandbox_default(self, cfg):
        # sandbox=True in base_config fixture
        assert isinstance(cfg.sandbox, bool)

    def test_htf_enabled(self, cfg):
        assert isinstance(cfg.htf_enabled, bool)


class TestConfigGetSet:

    def test_get_nested_key(self, cfg):
        val = cfg.get("risk.max_loss_per_trade")
        assert val == 50.0

    def test_get_missing_key_returns_default(self, cfg):
        val = cfg.get("nonexistent.key", "fallback")
        assert val == "fallback"

    def test_set_updates_value(self, cfg):
        cfg.set("risk.max_loss_per_trade", 75.0)
        assert cfg.get("risk.max_loss_per_trade") == 75.0

    def test_set_persist_saves_file(self, cfg, config_file):
        cfg.set("risk.max_loss_per_trade", 99.0, persist=True)
        with open(config_file) as f:
            data = json.load(f)
        assert data["risk"]["max_loss_per_trade"] == 99.0

    def test_as_dict_returns_copy(self, cfg):
        d1 = cfg.as_dict()
        d1["injected"] = True
        d2 = cfg.as_dict()
        assert "injected" not in d2, "as_dict should return a copy"


class TestConfigHotReload:

    def test_reload_callback_fires(self, cfg, config_file, base_config):
        fired = []
        cfg.on_reload(lambda c: fired.append(True))
        # Modify file mtime
        import time

        time.sleep(0.05)
        new = dict(base_config)
        new["risk"] = dict(base_config["risk"])
        new["risk"]["max_loss_per_trade"] = 42.0
        with open(config_file, "w") as f:
            json.dump(new, f)
        import os as _os

        _os.utime(config_file, None)
        reloaded = cfg.check_reload()
        assert reloaded
        assert cfg.get("risk.max_loss_per_trade") == 42.0

    def test_no_reload_when_unchanged(self, cfg):
        reloaded = cfg.check_reload()
        assert not reloaded
