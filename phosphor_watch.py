"""PhosphorWatch - a tiny always-on-top Twitch stream window with a CRT look."""
import sys
import traceback

WEBVIEW2_HELP = ("PhosphorWatch uses Microsoft Edge WebView2, which comes with Windows 10 and 11 "
                 "but seems to be missing or broken here.\n\nInstall the \"Evergreen Bootstrapper\" "
                 "from https://developer.microsoft.com/microsoft-edge/webview2/ and try again.")


def _fatal(msg: str) -> None:
    """Show a message box (works without a console)."""
    try:
        from phosphor.winapi import message_box
        message_box("PhosphorWatch", msg)
    except Exception:
        print(msg, file=sys.stderr)


def main() -> int:
    if sys.version_info < (3, 10):
        _fatal("PhosphorWatch needs Python 3.10 or newer (this is %d.%d).\n\n"
               "Install the latest Python from python.org, then start PhosphorWatch with run.bat."
               % sys.version_info[:2])
        return 1
    try:
        import webview  # noqa: F401
    except ImportError:
        _fatal("PhosphorWatch needs the 'pywebview' package.\n\nStart it with run.bat, which "
               "installs it for you, or run:  pip install -r requirements.txt")
        return 1
    try:
        from phosphor.app import App
        App().run()
    except Exception:
        tb = traceback.format_exc()
        try:
            from phosphor.config import data_dir
            (data_dir() / "error.log").write_text(tb, encoding="utf-8")
        except Exception:
            pass
        hint = WEBVIEW2_HELP + "\n\n" if "WebView2" in tb or "edgechromium" in tb.lower() else ""
        _fatal(hint + "PhosphorWatch crashed:\n\n" + traceback.format_exc(limit=3))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
