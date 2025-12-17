import yaml
import pytest  # type: ignore[import-not-found]

from wheatley_V2 import PoC


def _write_config(tmp_path, data):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return cfg_path


def test_poc_require_returns_value():
    cfg = {"secrets": {"token": "abc"}}
    assert PoC._require(cfg, ["secrets", "token"]) == "abc"


def test_poc_require_missing_key_raises_keyerror():
    with pytest.raises(KeyError):
        PoC._require({}, ["secrets", "openai_api_key"])


def test_poc_load_config_valid(tmp_path, monkeypatch):
    cfg_path = _write_config(
        tmp_path,
        {"secrets": {"openai_api_key": "k"}, "llm": {"model": "m"}},
    )
    loaded = PoC.load_config(cfg_path)
    assert loaded["llm"]["model"] == "m"


def test_poc_load_config_invalid_yaml_type(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError):
        PoC.load_config(cfg_path)


def test_poc_load_config_missing_keys(tmp_path):
    cfg_path = _write_config(tmp_path, {"secrets": {}})
    with pytest.raises(KeyError):
        PoC.load_config(cfg_path)


def test_get_weather_uses_location(monkeypatch):
    monkeypatch.setattr(PoC, "randint", lambda a, b: a)
    result = PoC.get_weather("Oslo")
    assert "Oslo" in result
    assert any(cond in result for cond in ["sunny", "cloudy", "rainy", "stormy"])
