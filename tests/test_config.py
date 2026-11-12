import json

import pytest


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOSPHOR_WATCH_DATA", str(tmp_path))
    return tmp_path


def test_clean_channel():
    from phosphor.config import clean_channel
    assert clean_channel("Shroud") == "shroud"
    assert clean_channel("  @Lirik ") == "lirik"
    assert clean_channel("https://www.twitch.tv/xQc?sr=a") == "xqc"
    assert clean_channel("twitch.tv/popout/foo_bar/player") == "foo_bar"
    for bad in ("", None, "two words", "a" * 26, "name!", "https://youtube.com/x y"):
        assert clean_channel(bad) == ""


def test_defaults_and_roundtrip(cfg_dir):
    from phosphor.config import Config
    c = Config()
    assert c["theme"] == "green" and c["on_top"] is True and c["favorites"] == []
    c["favorites"].append("shroud")
    c["opacity"] = 0.8
    c.save()
    c2 = Config()
    assert c2["favorites"] == ["shroud"] and c2["opacity"] == 0.8


def test_bad_values_are_repaired(cfg_dir):
    from phosphor.config import Config, MIN_W
    (cfg_dir / "config.json").write_text(json.dumps({
        "favorites": ["Shroud", "shroud", "bad name", 5], "opacity": "x", "width": 10,
        "x": "left", "unknown_key": 1}))
    c = Config()
    assert c["favorites"] == ["shroud"]
    assert c["opacity"] == 1.0 and c["width"] == MIN_W and c["x"] is None
    assert "unknown_key" not in c


def test_corrupt_file_falls_back_to_defaults(cfg_dir):
    from phosphor.config import Config
    (cfg_dir / "config.json").write_text("{not json")
    assert Config()["theme"] == "green"
