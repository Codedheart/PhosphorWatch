import json
import re

from phosphor import themes, web


def test_palettes_follow_shared_themes():
    pals = web.palettes()
    assert [p["key"] for p in pals] == [k for k, *_ in themes.PALETTES]
    roles = {"fg", "mid", "dim", "glow", "bg", "scan", "warn", "late"}
    for p in pals:
        assert roles <= set(p["colors"])


def test_home_html_is_fully_assembled():
    html = web.home_html()
    assert "/*__" not in html
    assert "var PW_PALETTES = " in html and "pwMount(" in html
    data = re.search(r"var PW_PALETTES = (\[.*?\]);\n", html).group(1)
    assert len(json.loads(data)) == len(themes.PALETTES)


def test_overlay_js_is_guarded_and_self_contained():
    js = web.overlay_js()
    assert js.startswith("(function(){ if (window.__phosphorWatch) return;")
    assert js.rstrip().endswith("})();")
    for name in ("THEME_CSS", "FONT_CSS", "PW_PALETTES", "pwMount", "pwBuildOverlay"):
        assert name in js


def test_font_is_optional(monkeypatch, tmp_path):
    web.font_css.cache_clear()
    monkeypatch.setattr(web, "VT323", tmp_path / "missing.ttf")
    assert web.font_css() == ""
    assert "var PW_HAS_VT = false;" in web.chrome_js()
    web.font_css.cache_clear()
