import yaml
import pytest  # type: ignore[import-not-found]

from wheatley_V2 import main as v2_main


def _write_config(tmp_path, data):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return cfg_path


def test_require_returns_value():
    cfg = {"level1": {"level2": "value"}}
    assert v2_main._require(cfg, ["level1", "level2"]) == "value"


def test_require_missing_key_raises_keyerror():
    cfg = {"level1": {}}
    with pytest.raises(KeyError) as err:
        v2_main._require(cfg, ["level1", "missing"])
    assert "level1/missing" in str(err.value)


def test_load_config_success(tmp_path):
    data = {
        "secrets": {
            "openai_api_key": "test-key",
            "elevenlabs_api_key": "xi-key",
        },
        "llm": {"model": "gpt"},
        "tts": {"voice_id": "voice", "model_id": "model", "enabled": True},
    }
    cfg_path = _write_config(tmp_path, data)
    loaded = v2_main.load_config(cfg_path)
    assert loaded["secrets"]["openai_api_key"] == "test-key"
    assert loaded["tts"]["enabled"] is True


def test_load_config_missing_file_raises(tmp_path):
    missing = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        v2_main.load_config(missing)


def test_load_config_invalid_yaml_type(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        v2_main.load_config(cfg_path)


def test_load_config_missing_required_key(tmp_path):
    cfg_path = _write_config(tmp_path, {"secrets": {"openai_api_key": "x"}})
    with pytest.raises(KeyError):
        v2_main.load_config(cfg_path)


def test_build_instructions_mentions_vocal_sounds():
    text = v2_main.build_instructions()
    assert "Wheatley" in text
    assert "vocal sounds" in text.lower()
