import yaml
import pytest  # type: ignore[import-not-found]

from wheatley_V2.MCP import agent_MCP


def _write_config(tmp_path, data):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return cfg_path


def test_agent_mcp_load_config_success(tmp_path):
    cfg_path = _write_config(
        tmp_path, {"secrets": {"openai_api_key": "k"}, "llm": {"model": "m"}}
    )
    loaded = agent_MCP.load_config(cfg_path)
    assert loaded["secrets"]["openai_api_key"] == "k"


def test_agent_mcp_load_config_invalid_yaml_type(tmp_path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("- not a map", encoding="utf-8")
    with pytest.raises(ValueError):
        agent_MCP.load_config(cfg_path)


def test_agent_mcp_load_config_missing_required_key(tmp_path):
    cfg_path = _write_config(tmp_path, {"llm": {"model": "m"}})
    with pytest.raises(KeyError):
        agent_MCP.load_config(cfg_path)
