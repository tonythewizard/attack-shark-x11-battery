#!/usr/bin/env python3
"""Attack Shark X11 battery tray and dashboard.

The application reads the mouse's native HID reports, keeps a lightweight
battery history, exposes a dynamic system-tray icon, and shows a Qt dashboard.
It supports Windows and Linux without replacing the mouse driver.
"""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import shlex
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from . import __version__

VID = 0x1D57
PID_ADAPTER = 0xFA60
PID_WIRED = 0xFA55
BATTERY_SIG = (0x03, 0x55, 0x40, 0x01)
HEARTBEAT_SECS = 180
APP_NAME = "Attack Shark X11"
APP_ID = "Antonio.AttackSharkX11"
APP_MUTEX = r"Local\Antonio.AttackSharkX11"
INSTANCE_PORT = 47611
REPO_URL = "https://github.com/tonythewizard/attack-shark-x11-battery"
RELEASE_API_URL = f"{REPO_URL.replace('github.com', 'api.github.com/repos')}/releases/latest"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "AttackSharkX11"
UPDATE_CHECK_INTERVAL = 24 * 3600
BATTERY_ALERT_LEVELS = (20, 10, 5)

DEFAULT_THEME = "minimal_dark"
THEME_ORDER = ("minimal_dark", "tech_blue", "modern_glass", "compact_pro")
THEMES: dict[str, dict[str, Any]] = {
    "minimal_dark": {
        "name": "Minimal Dark",
        "layout": "minimal",
        "geometry": "940x650",
        "minsize": (840, 580),
        "palette": {
            "window": "#081017",
            "card": "#0D1821",
            "card_alt": "#111F2A",
            "border": "#1E3945",
            "text": "#F5F8FA",
            "muted": "#8696A3",
            "soft": "#C5D0D8",
            "button": "#142631",
            "button_hover": "#1B3441",
            "accent": "#22C97A",
            "accent_hover": "#45E399",
            "track_off": "#29404A",
            "separator": "#40525B",
        },
        "chart": {
            "background": "#0D1821",
            "plot": "#0A141B",
            "grid": "#23343D",
            "axis": "#8798A4",
            "border": "#20343E",
            "line": "#29D47F",
            "fill_alpha": 34,
        },
    },
    "tech_blue": {
        "name": "Tech Blue",
        "layout": "tech",
        "geometry": "960x660",
        "minsize": (850, 590),
        "palette": {
            "window": "#050B16",
            "card": "#071426",
            "card_alt": "#091A31",
            "border": "#145FA5",
            "text": "#F5FAFF",
            "muted": "#7593B5",
            "soft": "#B9D7F4",
            "button": "#0C2340",
            "button_hover": "#10335C",
            "accent": "#168CFF",
            "accent_hover": "#4AA8FF",
            "track_off": "#183A59",
            "separator": "#245279",
        },
        "chart": {
            "background": "#071426",
            "plot": "#050F1E",
            "grid": "#153352",
            "axis": "#7C9CBC",
            "border": "#14518C",
            "line": "#1A9BFF",
            "fill_alpha": 48,
        },
    },
    "modern_glass": {
        "name": "Modern Glass",
        "layout": "glass",
        "geometry": "960x650",
        "minsize": (850, 580),
        "palette": {
            "window": "#0D0E14",
            "card": "#171824",
            "card_alt": "#1D1A29",
            "border": "#3D3347",
            "text": "#FFF8F3",
            "muted": "#A19AA8",
            "soft": "#DDD3DE",
            "button": "#2A2532",
            "button_hover": "#3A3042",
            "accent": "#FF7A21",
            "accent_hover": "#FF9A55",
            "track_off": "#423741",
            "separator": "#554B57",
        },
        "chart": {
            "background": "#171824",
            "plot": "#111219",
            "grid": "#38313D",
            "axis": "#A79FAC",
            "border": "#463849",
            "line": "#FF7A21",
            "fill_alpha": 44,
        },
    },
    "compact_pro": {
        "name": "Compact Pro",
        "layout": "compact",
        "geometry": "920x600",
        "minsize": (820, 540),
        "palette": {
            "window": "#090B13",
            "card": "#111421",
            "card_alt": "#171A2A",
            "border": "#2C3150",
            "text": "#F7F4FF",
            "muted": "#8E91A8",
            "soft": "#CDC8E3",
            "button": "#20243A",
            "button_hover": "#2B3050",
            "accent": "#9C4DFF",
            "accent_hover": "#B676FF",
            "track_off": "#34384D",
            "separator": "#4A4E68",
        },
        "chart": {
            "background": "#111421",
            "plot": "#0D101A",
            "grid": "#2A2E45",
            "axis": "#9295AA",
            "border": "#303553",
            "line": "#A558FF",
            "fill_alpha": 46,
        },
    },
}



# ---------------------------------------------------------------------------
# Paths, logging, and settings

def emit(message: object, *, err: bool = False) -> None:
    stream = sys.stderr if err else sys.stdout
    if stream is None:
        return
    try:
        stream.write(f"{message}\n")
        stream.flush()
    except Exception:
        pass


def data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    target = base / "AttackSharkX11"
    target.mkdir(parents=True, exist_ok=True)
    return target


DATA_DIR = data_dir()
HISTORY_PATH = DATA_DIR / "history.csv"
LOG_PATH = DATA_DIR / "error.log"
SETTINGS_PATH = DATA_DIR / "settings.json"


def log_exc(prefix: str = "") -> None:
    """Append the current traceback to the per-user error log."""
    import traceback

    try:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {prefix} ===\n")
            handle.write(traceback.format_exc())
    except Exception:
        pass


def settings_load() -> dict[str, Any]:
    try:
        with SETTINGS_PATH.open(encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def settings_save(settings: dict[str, Any]) -> None:
    try:
        tmp = SETTINGS_PATH.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=2, sort_keys=True)
        tmp.replace(SETTINGS_PATH)
    except OSError:
        pass


def history_append(timestamp: float, level: Optional[int], state: str) -> None:
    is_new = not HISTORY_PATH.exists()
    try:
        with HISTORY_PATH.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            if is_new:
                writer.writerow(["epoch", "percentage", "state"])
            writer.writerow([int(timestamp), "" if level is None else int(level), state])
    except OSError:
        log_exc("history_append")


def history_load() -> list[tuple[int, Optional[int], str]]:
    rows: list[tuple[int, Optional[int], str]] = []
    if not HISTORY_PATH.exists():
        return rows
    try:
        with HISTORY_PATH.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            for row in reader:
                if len(row) < 3:
                    continue
                try:
                    timestamp = int(row[0])
                    level = int(row[1]) if row[1] else None
                except ValueError:
                    continue
                if level is not None and not 0 <= level <= 100:
                    continue
                rows.append((timestamp, level, row[2]))
    except OSError:
        pass
    rows.sort(key=lambda item: item[0])
    return rows


# ---------------------------------------------------------------------------
# Startup integration

def app_command() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]

    executable = sys.executable
    if os.name == "nt":
        pythonw = str(Path(executable).with_name("pythonw.exe"))
        if Path(pythonw).exists():
            executable = pythonw

    source_launcher = Path(__file__).resolve().parents[2] / "asx11_battery.py"
    if source_launcher.exists():
        return [executable, str(source_launcher)]
    return [executable, "-m", "attack_shark_x11"]


def launch_command_string() -> str:
    if os.name == "nt":
        return " ".join(f'"{part}"' if " " in part else part for part in app_command())
    return shlex.join(app_command())


def autostart_desktop_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "autostart" / "attack-shark-x11.desktop"


def startup_get() -> bool:
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                value, _ = winreg.QueryValueEx(key, RUN_NAME)
                return bool(value)
        except (FileNotFoundError, OSError):
            return False
    return autostart_desktop_path().exists()


def startup_set(enabled: bool) -> None:
    if os.name == "nt":
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, launch_command_string())
            else:
                try:
                    winreg.DeleteValue(key, RUN_NAME)
                except FileNotFoundError:
                    pass
        return

    path = autostart_desktop_path()
    if enabled:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            f"Exec={launch_command_string()}\n"
            "Icon=attack-shark-x11\n"
            "Terminal=false\n"
            "X-GNOME-Autostart-enabled=true\n",
            encoding="utf-8",
        )
    else:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------
# Single-instance broker

class InstanceBroker:
    """Keep one app instance and ask the running instance to show its window."""

    def __init__(self, port: int = INSTANCE_PORT) -> None:
        self.port = port
        self._socket: Optional[socket.socket] = None
        self._mutex_handle: Optional[int] = None
        self._show_requested = threading.Event()
        self._stop = threading.Event()

    def acquire(self) -> bool:
        if os.name == "nt":
            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.restype = ctypes.c_void_p
            handle = kernel32.CreateMutexW(None, False, APP_MUTEX)
            if not handle:
                return True
            self._mutex_handle = int(handle)
            if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                self._send_show()
                kernel32.CloseHandle(ctypes.c_void_p(handle))
                self._mutex_handle = None
                return False

        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind(("127.0.0.1", self.port))
            listener.listen(2)
            listener.settimeout(0.5)
        except OSError:
            listener.close()
            self._send_show()
            if os.name != "nt":
                return False
            return True

        self._socket = listener
        threading.Thread(target=self._listen, name="instance-broker", daemon=True).start()
        return True

    def consume_show_request(self) -> bool:
        if not self._show_requested.is_set():
            return False
        self._show_requested.clear()
        return True

    def _listen(self) -> None:
        assert self._socket is not None
        while not self._stop.is_set():
            try:
                connection, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with connection:
                try:
                    message = connection.recv(64).decode("ascii", errors="ignore").strip()
                except OSError:
                    continue
                if message == "SHOW":
                    self._show_requested.set()
                    try:
                        connection.sendall(b"OK\n")
                    except OSError:
                        pass

    def _send_show(self) -> None:
        for _attempt in range(8):
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.5) as connection:
                    connection.sendall(b"SHOW\n")
                    connection.settimeout(0.5)
                    connection.recv(16)
                    return
            except OSError:
                time.sleep(0.12)

    def close(self) -> None:
        self._stop.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        if os.name == "nt" and self._mutex_handle:
            try:
                ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(self._mutex_handle))
            except Exception:
                pass
            self._mutex_handle = None


# ---------------------------------------------------------------------------
# HID protocol

def get_hid_module() -> Any:
    # The hidapi wheel exposes a hidraw backend on Linux. The default `hid`
    # module may use libusb, which detaches the mouse's kernel input driver and
    # can stop pointer movement while the monitor is running.
    if sys.platform.startswith("linux"):
        try:
            import hidraw

            return hidraw
        except ImportError:
            # Falling back to libusb can detach the kernel mouse driver and
            # leave the pointer unusable while the app is open.
            return None
    try:
        import hid

        return hid
    except ImportError:
        return None


def parse_battery(data: Iterable[int] | None) -> Optional[int]:
    if not data:
        return None
    values = list(data)
    if len(values) < 5 or tuple(values[:4]) != BATTERY_SIG:
        return None
    level = values[4]
    return level if 0 <= level <= 100 else None


def enumerate_mode(hid_module: Any = None) -> tuple[Optional[str], list[Any]]:
    hid_module = hid_module or get_hid_module()
    if hid_module is None:
        raise RuntimeError("hidapi is not installed")
    paths = list(dict.fromkeys(
        device["path"] for device in hid_module.enumerate(VID, PID_ADAPTER)
    ))
    if paths:
        return "adapter", paths
    if hid_module.enumerate(VID, PID_WIRED):
        return "charging", []
    return None, []


def open_devices(paths: Iterable[Any], hid_module: Any = None) -> list[Any]:
    hid_module = hid_module or get_hid_module()
    if hid_module is None:
        raise RuntimeError("hidapi is not installed")
    devices = []
    for path in paths:
        try:
            device = hid_module.device()
            device.open_path(path)
            device.set_nonblocking(1)
            devices.append(device)
        except (OSError, ValueError) as exc:
            _log_hid_open_error(exc)
            continue
    return devices


def _log_hid_open_error(error: BaseException) -> None:
    """Keep HID permission and device errors visible for Linux troubleshooting."""
    try:
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(
                f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} HID open failed ===\n"
                f"{type(error).__name__}: {error}\n"
            )
    except OSError:
        pass


def close_devices(devices: Iterable[Any]) -> None:
    for device in devices:
        try:
            device.close()
        except Exception:
            pass


def read_level_once(devices: Iterable[Any], deadline: float) -> Optional[int]:
    devices = list(devices)
    while time.monotonic() < deadline:
        received = False
        for device in devices:
            try:
                data = device.read(64)
            except OSError:
                continue
            if data:
                received = True
                level = parse_battery(data)
                if level is not None:
                    return level
        if not received:
            time.sleep(0.05)
    return None


def monitor_loop(
    on_update: Callable[[str, Optional[int], bool], None],
    stop_event: threading.Event,
    *,
    reenum_secs: float = 4.0,
    heartbeat: int = HEARTBEAT_SECS,
    hid_module: Any = None,
) -> None:
    hid_module = hid_module or get_hid_module()
    if hid_module is None:
        on_update("error", None, True)
        return

    devices: list[Any] = []
    current_mode = "__init__"
    last_level: Optional[int] = None
    last_enum = 0.0
    last_emit = time.monotonic()
    device_open_failed = False

    def fire(mode: str, level: Optional[int], is_change: bool) -> None:
        nonlocal last_emit
        last_emit = time.monotonic()
        on_update(mode, level, is_change)

    while not stop_event.is_set():
        now = time.monotonic()
        if not devices or (now - last_enum) > reenum_secs:
            mode, paths = enumerate_mode(hid_module)
            last_enum = now
            normalized = mode or "disconnected"

            if normalized != current_mode:
                close_devices(devices)
                devices = []
                current_mode = normalized

                # A real connection-mode change invalidates the previous level.
                # A transient HID read failure does not: while the dongle is still
                # enumerated we keep showing the last valid percentage instead of
                # falling back to the loading/waiting state.
                if normalized != "adapter":
                    last_level = None
                    device_open_failed = False
                    fire(normalized, None, True)
                else:
                    devices = open_devices(paths, hid_module)
                    device_open_failed = not devices
                    if device_open_failed:
                        fire("error", None, True)
                    elif last_level is None:
                        fire("waiting", None, True)
                    else:
                        fire("adapter", last_level, False)
            elif normalized == "adapter" and not devices:
                # Re-open failed handles without changing the visible state.
                devices = open_devices(paths, hid_module)
                if devices:
                    device_open_failed = False
                    fire("waiting" if last_level is None else "adapter", last_level, True)
                elif not device_open_failed:
                    device_open_failed = True
                    fire("error", None, True)

        if current_mode == "adapter" and devices:
            received = False
            healthy_devices: list[Any] = []
            for device in devices:
                try:
                    data = device.read(64)
                except OSError:
                    try:
                        device.close()
                    except Exception:
                        pass
                    continue

                healthy_devices.append(device)
                if data:
                    received = True
                    level = parse_battery(data)
                    if level is not None and level != last_level:
                        last_level = level
                        fire("adapter", level, True)

            # One HID interface can fail while another remains usable. Keep the
            # working handles and retry only the failed ones on the next enum.
            devices = healthy_devices
            if not received:
                time.sleep(0.1)
        else:
            time.sleep(0.3)

        if heartbeat and (time.monotonic() - last_emit) >= heartbeat:
            if current_mode == "adapter":
                fire("adapter" if last_level is not None else "waiting", last_level, False)
            else:
                fire(current_mode, None, False)

    close_devices(devices)


# ---------------------------------------------------------------------------
# Notifications and updates

def notify_desktop(title: str, body: str) -> None:
    try:
        if os.name == "nt":
            import subprocess

            safe_title = title.replace("'", "''")
            safe_body = body.replace("'", "''")
            script = (
                "[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,"
                "ContentType=WindowsRuntime]>$null;"
                "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
                "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                f"$x=$t.GetElementsByTagName('text');$x.Item(0).AppendChild($t.CreateTextNode('{safe_title}'))>$null;"
                f"$x.Item(1).AppendChild($t.CreateTextNode('{safe_body}'))>$null;"
                f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_NAME}')"
                ".Show([Windows.UI.Notifications.ToastNotification]::new($t))"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=False,
                creationflags=0x08000000,
            )
        else:
            import shutil
            import subprocess

            if shutil.which("notify-send"):
                subprocess.run(
                    ["notify-send", "-i", "attack-shark-x11", title, body],
                    check=False,
                )
    except Exception:
        pass


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    url: str


def version_tuple(value: str) -> tuple[int, ...]:
    clean = value.strip().lower().lstrip("v")
    numeric = clean.split("-", 1)[0].split("+", 1)[0]
    parts: list[int] = []
    for part in numeric.split("."):
        digits = "".join(character for character in part if character.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts or [0])


def check_latest_release(timeout: float = 5.0) -> tuple[bool, Optional[UpdateInfo]]:
    request = urllib.request.Request(
        RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"AttackSharkX11/{__version__}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return False, None

    tag = str(payload.get("tag_name", "")).strip()
    url = str(payload.get("html_url", "")).strip()
    if not tag or not url:
        return False, None
    release_version = tag.lstrip("vV")
    if version_tuple(release_version) > version_tuple(__version__):
        return True, UpdateInfo(release_version, url)
    return True, None


# ---------------------------------------------------------------------------
# Dynamic fin icon and status text

def status_color(state: str, level: Optional[int]) -> tuple[int, int, int]:
    if state == "charging":
        return 0, 190, 255
    if state in {"loading", "waiting", "disconnected", "error"} or level is None:
        return 130, 136, 148
    if level > 35:
        return 40, 200, 90
    if level > 15:
        return 240, 195, 40
    return 232, 64, 64


FIN = [
    (11, 55),
    (15, 45),
    (21, 33),
    (29, 21),
    (38, 11),
    (42, 8),
    (43, 17),
    (45, 29),
    (48, 42),
    (53, 55),
]


def make_fin_icon(state: str, level: Optional[int], size: int = 64):
    from PIL import Image, ImageDraw

    scale = size / 64.0
    fin = [(x * scale, y * scale) for x, y in FIN]
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(fin, fill=255)
    top = min(point[1] for point in fin)
    bottom = max(point[1] for point in fin)
    if state == "adapter" and level is not None:
        fill_y = bottom - (level / 100.0) * (bottom - top)
    elif state == "charging":
        fill_y = top
    else:
        fill_y = top + (bottom - top) * 0.72

    color = status_color(state, level) + (255,)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rectangle([0, fill_y, size, size], fill=color)
    draw.rectangle([0, 0, size, fill_y], fill=(72, 76, 86, 255))
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    image.paste(layer, (0, 0), mask)
    ImageDraw.Draw(image).line(
        fin + [fin[0]],
        fill=(22, 24, 30, 255),
        width=max(2, int(2 * scale)),
        joint="curve",
    )
    return image


def make_ico(path: str | os.PathLike[str]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    base = make_fin_icon("adapter", 100, size=256)
    base.save(
        destination,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def make_png(path: str | os.PathLike[str], size: int = 256) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    make_fin_icon("adapter", 100, size=size).save(destination, format="PNG")


def state_label(mode: str, level: Optional[int] = None, threshold: int = 20) -> str:
    if mode == "adapter":
        return "Low battery" if level is not None and level <= threshold else "Connected"
    return {
        "loading": "Loading device...",
        "waiting": "Connected",
        "charging": "Charging",
        "disconnected": "Not connected",
        "error": "Unavailable",
    }.get(mode, "Not connected")


@dataclass(frozen=True)
class BatteryMetrics:
    estimate: str
    rate: str
    summary: str


def _format_duration(seconds: float) -> str:
    seconds = max(0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours >= 24:
        days = hours // 24
        remaining_hours = hours % 24
        return f"{days}d {remaining_hours}h"
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def battery_metrics(
    rows: Iterable[tuple[int, Optional[int], str]],
    mode: str,
    level: Optional[int],
    now: float,
) -> BatteryMetrics:
    if mode != "adapter" or level is None:
        return BatteryMetrics("Not available", "Not available", "")

    window = [
        (timestamp, value)
        for timestamp, value, state in rows
        if state == "adapter" and value is not None and timestamp >= now - 60 * 60
    ]
    if len(window) < 2 or window[-1][0] - window[0][0] < 10 * 60:
        return BatteryMetrics("Learning", "Monitoring", "Collecting battery history")

    # Least-squares slope is less sensitive to one noisy report than first/last.
    origin = window[0][0]
    xs = [timestamp - origin for timestamp, _ in window]
    ys = [float(value) for _, value in window]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator <= 0:
        return BatteryMetrics("Pending", "Stable", "Waiting for a measurable battery change")
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    rate_per_hour = slope * 3600

    if rate_per_hour >= -0.05:
        return BatteryMetrics("Pending", "Stable", "Waiting for a measurable battery change")

    drain_rate = -rate_per_hour
    seconds_remaining = level / drain_rate * 3600
    duration = _format_duration(seconds_remaining)
    return BatteryMetrics(duration, f"{drain_rate:.1f}% / h", f"About {duration} remaining")


def estimate_text(
    rows: Iterable[tuple[int, Optional[int], str]],
    mode: str,
    level: Optional[int],
    now: float,
) -> str:
    metrics = battery_metrics(rows, mode, level, now)
    if metrics.estimate in {"Not available", "Learning", "Pending"}:
        return metrics.summary
    return f"~{metrics.estimate} remaining  •  {metrics.rate}"


# ---------------------------------------------------------------------------
# Chart renderer

RANGES: list[tuple[str, Optional[int]]] = [
    ("1h", 3600),
    ("6h", 6 * 3600),
    ("24h", 24 * 3600),
    ("7d", 7 * 86400),
    ("All", None),
]


def _font(size: int):
    from PIL import ImageFont

    font_candidates = []
    if os.name == "nt":
        font_candidates.extend(
            [
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "segoeui.ttf",
                Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "seguisb.ttf",
            ]
        )
    else:
        font_candidates.extend(
            [
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
            ]
        )
    for candidate in font_candidates:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def render_chart(
    rows: Iterable[tuple[int, Optional[int], str]],
    range_secs: Optional[int],
    now: float,
    *,
    width: int = 760,
    height: int = 310,
    theme: Optional[dict[str, Any]] = None,
):
    from PIL import Image, ImageDraw

    selected_theme = theme or THEMES[DEFAULT_THEME]
    chart_theme = selected_theme["chart"]

    def rgba(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
        value = value.lstrip("#")
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha)

    width = max(420, width)
    height = max(220, height)
    background = rgba(chart_theme["background"])
    plot_background = rgba(chart_theme["plot"])
    grid = rgba(chart_theme["grid"])
    axis = rgba(chart_theme["axis"])
    border = rgba(chart_theme["border"])
    line_color = rgba(chart_theme["line"])
    image = Image.new("RGBA", (width, height), background)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=12, fill=background)

    font = _font(12)
    left, right, top, bottom = 48, 16, 16, 32
    plot_width = width - left - right
    plot_height = height - top - bottom
    draw.rounded_rectangle(
        [left, top, left + plot_width, top + plot_height],
        radius=8,
        fill=plot_background,
        outline=border,
        width=1,
    )

    for value in (0, 25, 50, 75, 100):
        y = top + plot_height - value / 100.0 * plot_height
        draw.line([(left, y), (left + plot_width, y)], fill=grid, width=1)
        draw.text((10, y - 7), str(value), font=font, fill=axis)

    rows = list(rows)
    start = (rows[0][0] if rows else now) if range_secs is None else now - range_secs
    span = max(1.0, now - start)
    points = [(timestamp, level, state) for timestamp, level, state in rows if timestamp >= start]

    def px(timestamp: float) -> float:
        return left + (timestamp - start) / span * plot_width

    def py(level: int) -> float:
        return top + plot_height - (level / 100.0) * plot_height

    use_clock = (range_secs or span) <= 26 * 3600
    for index in range(5):
        timestamp = start + span * index / 4
        x = px(timestamp)
        draw.line([(x, top), (x, top + plot_height)], fill=grid, width=1)
        label = time.strftime("%H:%M" if use_clock else "%d/%m", time.localtime(timestamp))
        bbox = draw.textbbox((0, 0), label, font=font)
        label_width = bbox[2] - bbox[0]
        label_x = min(max(left, x - label_width / 2), left + plot_width - label_width)
        draw.text((label_x, top + plot_height + 8), label, font=font, fill=axis)

    valid = [(timestamp, level, state) for timestamp, level, state in points if level is not None]
    if not valid:
        message = "Waiting for battery history"
        wait_font = _font(14)
        bbox = draw.textbbox((0, 0), message, font=wait_font)
        draw.text(
            (left + (plot_width - (bbox[2] - bbox[0])) / 2, top + plot_height / 2 - 8),
            message,
            font=wait_font,
            fill=axis,
        )
        return image

    gap = max(900.0, (range_secs or span) / 30)
    segments: list[list[tuple[int, int, str]]] = []
    current: list[tuple[int, int, str]] = []
    previous_timestamp: Optional[int] = None
    for timestamp, level, state in points:
        if level is None:
            if current:
                segments.append(current)
                current = []
            previous_timestamp = timestamp
            continue
        if previous_timestamp is not None and timestamp - previous_timestamp > gap and current:
            segments.append(current)
            current = []
        current.append((timestamp, level, state))
        previous_timestamp = timestamp
    if current:
        segments.append(current)

    for segment in segments:
        if len(segment) < 2:
            continue
        pixel_points = [(px(timestamp), py(level)) for timestamp, level, _ in segment]
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        polygon = pixel_points + [
            (pixel_points[-1][0], top + plot_height),
            (pixel_points[0][0], top + plot_height),
        ]
        overlay_draw.polygon(
            polygon,
            fill=line_color[:3] + (int(chart_theme.get("fill_alpha", 36)),),
        )
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)
        for first, second in zip(segment, segment[1:]):
            draw.line(
                [(px(first[0]), py(first[1])), (px(second[0]), py(second[1]))],
                fill=line_color,
                width=3,
            )

    timestamp, level, state = valid[-1]
    x, y = px(timestamp), py(level)
    endpoint = status_color(state, level)
    draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill=endpoint + (55,))
    draw.ellipse(
        [x - 4, y - 4, x + 4, y + 4],
        fill=endpoint + (255,),
        outline=(255, 255, 255, 255),
        width=1,
    )
    return image



# ---------------------------------------------------------------------------
# Qt dashboard lives in attack_shark_x11.ui_qt


# ---------------------------------------------------------------------------
# Main application

class App:
    def __init__(self, threshold: int, broker: InstanceBroker) -> None:
        self.threshold = max(1, min(99, threshold))
        self.broker = broker
        self._notified_battery_levels: set[int] = set()
        self._has_battery_sample = False
        self._lock = threading.Lock()
        self._history = history_load()
        self._mode = "loading"
        self._level: Optional[int] = None
        self.stop_event = threading.Event()

        self.qt_app = None
        self.bridge = None
        self.dash = None
        self.tray = None
        self.battery_action = None
        self.dashboard_action = None
        self.instance_timer = None

        saved_settings = settings_load()
        saved_version = str(saved_settings.get("available_version", "")).strip()
        saved_url = str(saved_settings.get("available_url", "")).strip()
        self.update_info: Optional[UpdateInfo] = (
            UpdateInfo(saved_version, saved_url)
            if saved_version and saved_url and version_tuple(saved_version) > version_tuple(__version__)
            else None
        )
        self.update_checking = False

    def state_snapshot(self) -> tuple[str, Optional[int]]:
        with self._lock:
            return self._mode, self._level

    def history_snapshot(self) -> list[tuple[int, Optional[int], str]]:
        with self._lock:
            return list(self._history)

    def on_update(self, mode: str, level: Optional[int], is_change: bool) -> None:
        try:
            now = int(time.time())
            stored_level = level if mode == "adapter" else None
            with self._lock:
                self._mode = mode
                self._level = stored_level
                self._history.append((now, stored_level, mode))
            history_append(now, stored_level, mode)

            if mode == "adapter" and level is not None:
                alerts: list[int] = []
                if not self._has_battery_sample:
                    reached = [value for value in BATTERY_ALERT_LEVELS if level <= value]
                    if reached:
                        # If monitoring starts below several milestones, report
                        # the most urgent one and mark earlier milestones seen.
                        alerts.append(min(reached))
                        self._notified_battery_levels.update(reached)
                    self._has_battery_sample = True
                else:
                    self._notified_battery_levels = {
                        value for value in self._notified_battery_levels if level <= value
                    }
                    for value in BATTERY_ALERT_LEVELS:
                        if level <= value and value not in self._notified_battery_levels:
                            alerts.append(value)
                            self._notified_battery_levels.add(value)
                for alert_level in alerts:
                    self._notify(f"Mouse battery reached {alert_level}%")

            if self.bridge is not None:
                self.bridge.state_changed.emit()
        except Exception:
            log_exc("on_update")

    def _notify(self, message: str) -> None:
        if self.bridge is not None:
            try:
                self.bridge.notification.emit(message)
                return
            except Exception:
                pass
        notify_desktop(APP_NAME, message)

    def _menu_status(self) -> str:
        mode, level = self.state_snapshot()
        if mode == "adapter" and level is not None:
            return f"Battery: {level}%"
        if mode == "waiting":
            return "Connected — waiting for battery data"
        if mode == "charging":
            return "Charging"
        if mode == "loading":
            return "Loading device..."
        if mode == "error":
            return "HID interface unavailable"
        return "Not connected"

    def _title(self) -> str:
        mode, level = self.state_snapshot()
        if mode == "adapter" and level is not None:
            return f"{APP_NAME} — {level}%"
        return f"{APP_NAME} — {state_label(mode, level, self.threshold)}"

    def run(self) -> None:
        from PySide6.QtCore import QObject, QTimer, Signal
        from PySide6.QtGui import QAction, QFont, QIcon
        from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

        from .ui_qt import DashboardWindow, pil_to_qpixmap

        class UiBridge(QObject):
            state_changed = Signal()
            update_changed = Signal()
            notification = Signal(str)
            show_requested = Signal()

        set_windows_app_id()
        self.qt_app = QApplication.instance() or QApplication([sys.argv[0]])
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setApplicationDisplayName(APP_NAME)
        self.qt_app.setOrganizationName("Antonio")
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.qt_app.setFont(QFont("Segoe UI", 10))

        self.bridge = UiBridge()
        self.dash = DashboardWindow(self)
        self.dash.hide()

        mode, level = self.state_snapshot()
        icon = QIcon(pil_to_qpixmap(make_fin_icon(mode, level, size=128)))
        self.qt_app.setWindowIcon(icon)
        self.dash.setWindowIcon(icon)

        self.tray = QSystemTrayIcon(icon, self.qt_app)
        self.tray.setToolTip(self._title())
        menu = QMenu()
        self.battery_action = QAction(self._menu_status(), menu)
        self.battery_action.triggered.connect(self._open)
        menu.addAction(self.battery_action)
        menu.addSeparator()
        self.dashboard_action = QAction("Dashboard", menu)
        self.dashboard_action.triggered.connect(self._open)
        menu.addAction(self.dashboard_action)
        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)

        self.bridge.state_changed.connect(self._refresh_gui)
        self.bridge.update_changed.connect(self._refresh_gui)
        self.bridge.notification.connect(self._show_notification)
        self.bridge.show_requested.connect(self._open)

        self.instance_timer = QTimer(self.qt_app)
        self.instance_timer.setInterval(200)
        self.instance_timer.timeout.connect(self._poll_instance_requests)
        self.instance_timer.start()

        threading.Thread(target=self._monitor, name="hid-monitor", daemon=True).start()
        self.start_update_check(force=False)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()
        else:
            # On desktop environments without a tray, keep the app usable.
            self.dash.show_dashboard()

        try:
            self.qt_app.exec()
        finally:
            self.stop_event.set()
            self.broker.close()
            if self.tray is not None:
                self.tray.hide()

    def set_window_icon(self, icon: Any) -> None:
        """Receive the live window icon from the Qt dashboard."""
        if self.qt_app is not None:
            self.qt_app.setWindowIcon(icon)
        if self.tray is not None:
            self.tray.setIcon(icon)

    def _refresh_gui(self) -> None:
        if self.dash is not None:
            self.dash.refresh()
        if self.battery_action is not None:
            self.battery_action.setText(self._menu_status())
        if self.tray is not None:
            self.tray.setToolTip(self._title())

    def _poll_instance_requests(self) -> None:
        if self.broker.consume_show_request():
            self._open()

    def _monitor(self) -> None:
        try:
            monitor_loop(self.on_update, self.stop_event)
        except Exception:
            log_exc("monitor_loop")
            self.on_update("error", None, True)

    def start_update_check(self, *, force: bool) -> None:
        if self.update_checking:
            return
        settings = settings_load()
        last_check = float(settings.get("last_update_check", 0) or 0)
        if not force and time.time() - last_check < UPDATE_CHECK_INTERVAL:
            return

        self.update_checking = True
        if self.bridge is not None:
            self.bridge.update_changed.emit()

        def worker() -> None:
            try:
                success, update = check_latest_release()
                if not success:
                    if force:
                        self._notify("Could not check for updates")
                    return
                current_settings = settings_load()
                current_settings["last_update_check"] = int(time.time())
                if update is not None:
                    self.update_info = update
                    current_settings["available_version"] = update.version
                    current_settings["available_url"] = update.url
                    last_notified = str(current_settings.get("last_notified_version", ""))
                    if last_notified != update.version:
                        self._notify(f"Version {update.version} is available")
                        current_settings["last_notified_version"] = update.version
                else:
                    self.update_info = None
                    current_settings.pop("available_version", None)
                    current_settings.pop("available_url", None)
                    if force:
                        self._notify("You are up to date")
                settings_save(current_settings)
            finally:
                self.update_checking = False
                if self.bridge is not None:
                    self.bridge.update_changed.emit()

        threading.Thread(target=worker, name="update-check", daemon=True).start()

    def _tray_activated(self, reason: Any) -> None:
        from PySide6.QtWidgets import QSystemTrayIcon

        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open()

    def _show_notification(self, message: str) -> None:
        if self.tray is not None and self.tray.isVisible():
            self.tray.showMessage(APP_NAME, message)
        else:
            notify_desktop(APP_NAME, message)

    def _open(self, *_: Any) -> None:
        if self.dash is not None:
            self.dash.show_dashboard()

    def _quit(self, *_: Any) -> None:
        self.stop_event.set()
        self.broker.close()
        if self.tray is not None:
            self.tray.hide()
        if self.qt_app is not None:
            self.qt_app.quit()


def set_windows_app_id() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# CLI

def bar(level: int, width: int = 20) -> str:
    filled = round(level / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def run_diagnostics() -> int:
    import platform

    emit(f"Attack Shark X11 v{__version__}")
    emit(f"Python {sys.version.split()[0]} ({platform.architecture()[0]})")
    emit(f"Executable: {sys.executable}")
    for module_name in ("hid", "PIL", "PySide6"):
        try:
            module = __import__(module_name)
            emit(f"  {module_name:8s}: OK {getattr(module, '__version__', '')}")
        except Exception as exc:
            emit(f"  {module_name:8s}: FAIL {exc}")

    hid_module = get_hid_module()
    if hid_module is not None:
        emit(f"HID backend: {getattr(hid_module, '__name__', 'unknown')}")
    if hid_module is not None:
        try:
            mode, paths = enumerate_mode(hid_module)
            emit(f"Mouse: {mode} (HID paths: {len(paths)})")
            if mode == "adapter":
                devices = open_devices(paths, hid_module)
                try:
                    if devices:
                        emit(f"HID access: OK ({len(devices)} interface(s) opened)")
                    else:
                        emit("HID access: FAILED (check Linux udev permissions; see README)")
                finally:
                    close_devices(devices)
            for device in hid_module.enumerate(VID):
                emit(
                    f"  found 1d57:{device['product_id']:04x} "
                    f"if={device.get('interface_number')} usage_page={device.get('usage_page')}"
                )
        except Exception as exc:
            emit(f"Enumeration failed: {exc}")
    emit(f"Data directory: {DATA_DIR}")
    emit(f"Log file: {LOG_PATH}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Attack Shark X11 battery tray and dashboard.")
    parser.add_argument("--make-ico", metavar="PATH", help="write the fin .ico and exit")
    parser.add_argument("--make-png", metavar="PATH", help="write the fin .png and exit")
    parser.add_argument("--check", action="store_true", help="diagnostics: dependencies and mouse detection")
    parser.add_argument("--debug", action="store_true", help="run the GUI with console output")
    parser.add_argument("--once", action="store_true", help="read the battery once and exit")
    parser.add_argument("--watch", action="store_true", help="continuous text monitor")
    parser.add_argument("--json", action="store_true", help="JSON output with --once")
    parser.add_argument("--threshold", type=int, default=20, help="low-battery notification percentage")
    parser.add_argument("--timeout", type=float, default=8.0, help="one-shot wait time in seconds")
    args = parser.parse_args(argv)

    if args.make_ico:
        make_ico(args.make_ico)
        emit(f"Icon written: {args.make_ico}")
        return 0
    if args.make_png:
        make_png(args.make_png)
        emit(f"Icon written: {args.make_png}")
        return 0
    if args.check:
        return run_diagnostics()

    hid_module = get_hid_module()
    if args.watch:
        if hid_module is None:
            emit("hidapi is not installed", err=True)
            return 2

        def callback(mode: str, level: Optional[int], _changed: bool) -> None:
            timestamp = time.strftime("%H:%M:%S")
            if mode == "adapter" and level is not None:
                emit(f"{timestamp}  {level:3d}%  {bar(level)}")
            else:
                emit(f"{timestamp}  {state_label(mode, level).lower()}")

        event = threading.Event()
        try:
            monitor_loop(callback, event, hid_module=hid_module)
        except KeyboardInterrupt:
            event.set()
        return 0

    if args.once:
        if hid_module is None:
            emit("hidapi is not installed", err=True)
            return 2
        mode, paths = enumerate_mode(hid_module)
        if mode is None:
            emit("Mouse not found (is the dongle connected?)", err=True)
            return 1
        if mode == "charging":
            emit("Charging (percentage is unavailable over USB)", err=True)
            return 3
        devices = open_devices(paths, hid_module)
        try:
            level = read_level_once(devices, time.monotonic() + args.timeout)
        finally:
            close_devices(devices)
        if level is None:
            emit("No battery report received. Move the mouse and try again.", err=True)
            return 5
        history_append(time.time(), level, "adapter")
        emit(json.dumps({"percentage": level}) if args.json else f"Battery: {level}%  {bar(level)}")
        return 0

    broker = InstanceBroker()
    if not broker.acquire():
        return 0

    try:
        if args.debug:
            emit(f"{APP_NAME} v{__version__}: starting GUI...")
        App(args.threshold, broker).run()
    except ImportError as exc:
        broker.close()
        log_exc("ImportError")
        emit(f"Missing GUI dependency: {exc}", err=True)
        return 2
    except Exception as exc:
        broker.close()
        log_exc("GUI crash")
        emit(f"Error: {exc} (see {LOG_PATH})", err=True)
        if args.debug:
            raise
        return 1
    return 0
