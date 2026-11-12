"""Builds the HTML / JS that runs inside the WebView from phosphor/assets/web.

Palettes come from phosphor/themes.py (shared with the sibling apps) so all three
apps stay in sync; the VT323 font is embedded when build.bat / run.bat fetched it.
"""
from __future__ import annotations

import base64
import json
from functools import lru_cache
from pathlib import Path

from . import themes

ASSETS = Path(__file__).parent / "assets"
WEB = ASSETS / "web"
VT323 = ASSETS / "VT323-Regular.ttf"


def _read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def palettes() -> list[dict]:
    return [{"key": k, "name": n, "group": g, "colors": c} for k, n, g, c in themes.PALETTES]


@lru_cache(maxsize=1)
def font_css() -> str:
    if not VT323.exists():
        return ""
    data = base64.b64encode(VT323.read_bytes()).decode("ascii")
    return ('@font-face { font-family: "PW VT323"; '
            f'src: url(data:font/ttf;base64,{data}) format("truetype"); }}')


def chrome_js() -> str:
    head = (f"var PW_PALETTES = {json.dumps(palettes())};\n"
            f"var PW_HAS_VT = {json.dumps(bool(font_css()))};\n")
    return head + _read("chrome.js")


def home_html() -> str:
    return (_read("home.html")
            .replace("/*__FONT__*/", font_css())
            .replace("/*__THEME__*/", _read("theme.css"))
            .replace("/*__CHROME__*/", chrome_js()))


@lru_cache(maxsize=1)
def overlay_js() -> str:
    # Guarded so a second injection into the same document does nothing.
    return ("(function(){ if (window.__phosphorWatch) return; window.__phosphorWatch = true;\n"
            f"var THEME_CSS = {json.dumps(_read('theme.css'))};\n"
            f"var FONT_CSS = {json.dumps(font_css())};\n"
            + chrome_js() + "\n" + _read("overlay.js") + "\n})();")
