"""Thin Windows helpers (ctypes, user32 only). Everything is a no-op off Windows.

Only our OWN window is touched (its opacity). PhosphorWatch never reads other windows.
"""
from __future__ import annotations

import os
import sys

IS_WIN = sys.platform == "win32"

if IS_WIN:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    LWA_ALPHA = 0x2

    user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
    user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetLayeredWindowAttributes.argtypes = [wintypes.HWND, wintypes.COLORREF, ctypes.c_ubyte,
                                                  wintypes.DWORD]
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]


def find_own_window(title_prefix: str) -> int | None:
    """Top-level visible window of this process whose title starts with title_prefix."""
    if not IS_WIN:
        return None
    pid, found = os.getpid(), []

    def cb(hwnd, _lp):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd) and not user32.GetParent(hwnd):
            buf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, buf, 256)
            if buf.value.startswith(title_prefix):
                found.append(hwnd)
                return False
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found[0] if found else None


def set_opacity(hwnd: int | None, alpha: float) -> bool:
    """0.3 .. 1.0. At 1.0 the layered style is removed again (best for video)."""
    if not IS_WIN or not hwnd:
        return False
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    if alpha >= 0.999:
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex & ~WS_EX_LAYERED)
        return True
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex | WS_EX_LAYERED)
    return bool(user32.SetLayeredWindowAttributes(hwnd, 0, int(max(0.3, alpha) * 255), LWA_ALPHA))


def message_box(title: str, text: str) -> None:
    if IS_WIN:
        user32.MessageBoxW(None, text, title, 0x10)  # MB_ICONERROR
    else:
        print(f"{title}: {text}", file=sys.stderr)


def open_folder(path) -> None:
    if IS_WIN:
        os.startfile(str(path))  # noqa: S606 - our own data folder
