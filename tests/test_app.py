"""App / Api logic with a fake window (no GUI needed)."""
import pytest

from phosphor import app as appmod
from phosphor import updater


class FakeWindow:
    def __init__(self):
        self.x, self.y, self.width, self.height = 10, 20, 640, 400
        self.calls, self.on_top, self.title = [], True, ""

    def load_url(self, url): self.calls.append(("url", url))
    def load_html(self, html): self.calls.append(("html", len(html)))
    def set_title(self, t): self.title = t
    def evaluate_js(self, js): self.calls.append(("js", js))
    def resize(self, w, h): self.width, self.height = w, h
    def move(self, x, y): self.x, self.y = x, y
    def clear_cookies(self): self.calls.append(("clear",))
    def destroy(self): self.calls.append(("destroy",))


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOSPHOR_WATCH_DATA", str(tmp_path))
    a = appmod.App()
    a.window = FakeWindow()
    return a


def test_watch_loads_popout_player(app):
    api = appmod.Api(app)
    assert api.watch("https://twitch.tv/Shroud") == {"ok": True}
    assert app.window.calls[-1] == ("url", "https://www.twitch.tv/popout/shroud/player?parent=twitch.tv")
    assert app.current == "shroud" and app.cfg["last_channel"] == "shroud"
    assert "shroud" in app.window.title
    assert api.watch("not a name")["ok"] is False
    api.go_home()
    assert app.current == "" and app.window.calls[-1][0] == "html"


def test_favorites(app):
    api = appmod.Api(app)
    assert api.add_favorite("@Lirik")["ok"]
    assert api.add_favorite("lirik")["error"] == "ALREADY A FAVORITE"
    api.add_favorite("shroud")
    api.move_favorite("shroud", -1)
    assert app.cfg["favorites"] == ["shroud", "lirik"]
    api.remove_favorite("shroud")
    assert app.cfg["favorites"] == ["lirik"]
    pushes = [c for c in app.window.calls if c[0] == "js"]
    assert pushes and "__pwPush" in pushes[-1][1]


def test_geometry_respects_minimum(app):
    api = appmod.Api(app)
    api.set_geometry(5, 6, 50, 50)
    assert (app.window.width, app.window.height) == (appmod.MIN_W, appmod.MIN_H)
    assert (app.window.x, app.window.y) == (5, 6)


def test_theme_and_user(app):
    api = appmod.Api(app)
    api.set_theme("amber")
    api.set_theme("nope")
    assert app.cfg["theme"] == "amber"
    api.set_user("Jenny_DC")
    assert app.cfg["user"] == "jenny_dc"
    api.logout()
    assert app.cfg["user"] == "" and ("clear",) in app.window.calls


def test_update_offer_from_source_points_to_git(app, monkeypatch):
    app.update_rel = updater.Release("v9.9", (9, 9), "https://x/rel", "https://x/z", 1)
    monkeypatch.setattr(updater, "app_dir", lambda: None)
    app.offer_update()
    assert "git pull" in app.window.calls[-1][1]


def test_check_updates_finds_newer(app, monkeypatch):
    monkeypatch.setattr(appmod, "VERSION", "1.0")
    monkeypatch.setattr(updater, "latest_release",
                        lambda: updater.Release("v1.1", (1, 1), "https://x/rel"))
    app.check_updates(manual=False)
    assert app.state()["update_tag"] == "v1.1"
