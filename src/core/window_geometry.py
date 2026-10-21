from __future__ import annotations

import ctypes
from dataclasses import dataclass
from ctypes import wintypes


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("El rectángulo debe tener ancho y alto positivos.")

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


@dataclass(frozen=True)
class WindowGeometry:
    frame: Rect
    client: Rect
    dpi: int | None


def leer_geometria_ventana(hwnd: int) -> WindowGeometry:
    """Lee marco y área cliente en coordenadas de pantalla; no envía entradas."""
    if not hasattr(ctypes, "WinDLL"):
        raise OSError("La geometría de ventanas scrcpy solo está disponible en Windows.")

    class WinRect(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class Point(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    get_window_rect = user32.GetWindowRect
    get_window_rect.argtypes = [wintypes.HWND, ctypes.POINTER(WinRect)]
    get_window_rect.restype = wintypes.BOOL
    get_client_rect = user32.GetClientRect
    get_client_rect.argtypes = [wintypes.HWND, ctypes.POINTER(WinRect)]
    get_client_rect.restype = wintypes.BOOL
    client_to_screen = user32.ClientToScreen
    client_to_screen.argtypes = [wintypes.HWND, ctypes.POINTER(Point)]
    client_to_screen.restype = wintypes.BOOL

    frame = WinRect()
    client = WinRect()
    if not get_window_rect(hwnd, ctypes.byref(frame)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not get_client_rect(hwnd, ctypes.byref(client)):
        raise ctypes.WinError(ctypes.get_last_error())

    client_top_left = Point(client.left, client.top)
    client_bottom_right = Point(client.right, client.bottom)
    if not client_to_screen(hwnd, ctypes.byref(client_top_left)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not client_to_screen(hwnd, ctypes.byref(client_bottom_right)):
        raise ctypes.WinError(ctypes.get_last_error())

    get_dpi_for_window = getattr(user32, "GetDpiForWindow", None)
    dpi = None
    if get_dpi_for_window is not None:
        get_dpi_for_window.argtypes = [wintypes.HWND]
        get_dpi_for_window.restype = wintypes.UINT
        dpi_value = get_dpi_for_window(hwnd)
        dpi = int(dpi_value) if dpi_value else None

    return WindowGeometry(
        frame=Rect(frame.left, frame.top, frame.right, frame.bottom),
        client=Rect(
            client_top_left.x,
            client_top_left.y,
            client_bottom_right.x,
            client_bottom_right.y,
        ),
        dpi=dpi,
    )
