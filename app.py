import ctypes
import os
import subprocess
import sys
import threading
import time
import winreg

import pystray
import win32api
import win32con
import win32event
from PIL import Image

APP_NAME = "Keep Awake Lite"
STARTUP_VALUE_NAME = "Keep Awake Lite"
SETTINGS_KEY = r"Software\KeepAwakeLite"
INTERVAL_VALUE_NAME = "IntervalSeconds"
DEFAULT_INTERVAL_SECONDS = 4 * 60
MIN_INTERVAL_SECONDS = 1

_SINGLE_INSTANCE_MUTEX = None
ERROR_ALREADY_EXISTS = 183


class Settings:
    def __init__(self, interval_seconds: int):
        self._lock = threading.Lock()
        self._interval_seconds = interval_seconds
        self._paused = False

    def get_interval_seconds(self) -> int:
        with self._lock:
            return self._interval_seconds

    def set_interval_seconds(self, seconds: int) -> None:
        with self._lock:
            self._interval_seconds = max(MIN_INTERVAL_SECONDS, int(seconds))

    def is_paused(self) -> bool:
        with self._lock:
            return self._paused

    def toggle_paused(self) -> bool:
        with self._lock:
            self._paused = not self._paused
            return self._paused


def load_interval_seconds() -> int:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS_KEY, 0, winreg.KEY_READ)
    except OSError:
        return DEFAULT_INTERVAL_SECONDS

    try:
        value, _ = winreg.QueryValueEx(key, INTERVAL_VALUE_NAME)
        return max(MIN_INTERVAL_SECONDS, int(value))
    except (OSError, TypeError, ValueError):
        return DEFAULT_INTERVAL_SECONDS
    finally:
        winreg.CloseKey(key)


def save_interval_seconds(seconds: int) -> None:
    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, SETTINGS_KEY, 0, winreg.KEY_SET_VALUE)
    try:
        winreg.SetValueEx(key, INTERVAL_VALUE_NAME, 0, winreg.REG_DWORD, max(MIN_INTERVAL_SECONDS, int(seconds)))
    finally:
        winreg.CloseKey(key)


SETTINGS = Settings(load_interval_seconds())


def ensure_single_instance(name=r"Local\KeepAwakeLiteMutex") -> bool:
    global _SINGLE_INSTANCE_MUTEX

    _SINGLE_INSTANCE_MUTEX = win32event.CreateMutex(None, True, name)
    return ctypes.windll.kernel32.GetLastError() != ERROR_ALREADY_EXISTS


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def script_pythonw() -> str:
    executable = sys.executable
    folder = os.path.dirname(executable)
    pythonw = os.path.join(folder, "pythonw.exe")
    return pythonw if os.path.exists(pythonw) else executable


def startup_command() -> str:
    if is_frozen():
        return f'"{sys.executable}"'
    return f'"{script_pythonw()}" "{os.path.abspath(__file__)}"'


def resource_path(rel: str) -> str:
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel)

    if is_frozen():
        exe_dir = os.path.dirname(sys.executable)
        candidates = [
            os.path.join(exe_dir, rel),
            os.path.join(exe_dir, "_internal", rel),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate
        return candidates[0]

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)


def add_to_startup() -> None:
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, startup_command())
    finally:
        winreg.CloseKey(key)


def remove_from_startup() -> None:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
    except FileNotFoundError:
        return

    try:
        winreg.DeleteValue(key, STARTUP_VALUE_NAME)
    except FileNotFoundError:
        pass
    finally:
        winreg.CloseKey(key)


def startup_enabled() -> bool:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
    except OSError:
        return False

    try:
        command, _ = winreg.QueryValueEx(key, STARTUP_VALUE_NAME)
        return command == startup_command()
    except OSError:
        return False
    finally:
        winreg.CloseKey(key)


def format_interval(seconds: int) -> str:
    minutes, seconds = divmod(max(MIN_INTERVAL_SECONDS, int(seconds)), 60)
    return f"{minutes}m {seconds}s"


def jiggle_mouse() -> None:
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 1, 0, 0, 0)
    time.sleep(0.03)
    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, -1, 0, 0, 0)


def update_tray_title(icon: pystray.Icon) -> None:
    if SETTINGS.is_paused():
        icon.title = f"{APP_NAME} | paused"
    else:
        icon.title = f"{APP_NAME} | every {format_interval(SETTINGS.get_interval_seconds())}"


def refresh_tray(icon: pystray.Icon) -> None:
    update_tray_title(icon)
    update_menu = getattr(icon, "update_menu", None)
    if update_menu is not None:
        update_menu()


def on_toggle_startup(icon, item) -> None:
    if startup_enabled():
        remove_from_startup()
    else:
        add_to_startup()
    refresh_tray(icon)


def on_toggle_pause(icon, item, reschedule_event: threading.Event) -> None:
    SETTINGS.toggle_paused()
    reschedule_event.set()
    refresh_tray(icon)


def show_interval_dialog(current_interval_seconds: int) -> int | None:
    current_minutes, current_seconds = divmod(current_interval_seconds, 60)
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$form = New-Object System.Windows.Forms.Form
$form.Text = '{APP_NAME}'
$form.Width = 280
$form.Height = 170
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.TopMost = $true

$minutesLabel = New-Object System.Windows.Forms.Label
$minutesLabel.Text = 'Minutes'
$minutesLabel.Location = New-Object System.Drawing.Point(16, 16)
$minutesLabel.Size = New-Object System.Drawing.Size(100, 20)
$form.Controls.Add($minutesLabel)

$minutes = New-Object System.Windows.Forms.NumericUpDown
$minutes.Minimum = 0
$minutes.Maximum = 1440
$minutes.Value = {current_minutes}
$minutes.Location = New-Object System.Drawing.Point(16, 40)
$minutes.Size = New-Object System.Drawing.Size(100, 24)
$form.Controls.Add($minutes)

$secondsLabel = New-Object System.Windows.Forms.Label
$secondsLabel.Text = 'Seconds'
$secondsLabel.Location = New-Object System.Drawing.Point(136, 16)
$secondsLabel.Size = New-Object System.Drawing.Size(100, 20)
$form.Controls.Add($secondsLabel)

$seconds = New-Object System.Windows.Forms.NumericUpDown
$seconds.Minimum = 0
$seconds.Maximum = 59
$seconds.Value = {current_seconds}
$seconds.Location = New-Object System.Drawing.Point(136, 40)
$seconds.Size = New-Object System.Drawing.Size(100, 24)
$form.Controls.Add($seconds)

$cancel = New-Object System.Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.Location = New-Object System.Drawing.Point(78, 86)
$cancel.Size = New-Object System.Drawing.Size(76, 28)
$cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.CancelButton = $cancel
$form.Controls.Add($cancel)

$save = New-Object System.Windows.Forms.Button
$save.Text = 'Save'
$save.Location = New-Object System.Drawing.Point(162, 86)
$save.Size = New-Object System.Drawing.Size(76, 28)
$form.AcceptButton = $save
$form.Controls.Add($save)

$save.Add_Click({{
    $interval = ([int]$minutes.Value * 60) + [int]$seconds.Value
    if ($interval -lt {MIN_INTERVAL_SECONDS}) {{
        [System.Windows.Forms.MessageBox]::Show(
            'Interval must be at least 1 second.',
            '{APP_NAME}',
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        ) | Out-Null
        return
    }}
    $form.Tag = $interval
    $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
    $form.Close()
}})

if ($form.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {{
    [Console]::Out.WriteLine([int]$form.Tag)
}}
"""
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=False,
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            text=True,
        )
    except OSError:
        win32api.MessageBox(0, "Could not open the interval dialog.", APP_NAME, win32con.MB_OK)
        return None

    if completed.returncode != 0:
        win32api.MessageBox(0, "Could not save the interval.", APP_NAME, win32con.MB_OK)
        return None

    output = completed.stdout.strip()
    if not output:
        return None

    try:
        return max(MIN_INTERVAL_SECONDS, int(output.splitlines()[-1]))
    except ValueError:
        win32api.MessageBox(0, "Could not read the interval.", APP_NAME, win32con.MB_OK)
        return None


def on_set_interval(icon, item, reschedule_event: threading.Event) -> None:
    interval = show_interval_dialog(SETTINGS.get_interval_seconds())
    if interval is None:
        return

    SETTINGS.set_interval_seconds(interval)
    save_interval_seconds(interval)
    reschedule_event.set()
    refresh_tray(icon)


def on_quit(icon, item) -> None:
    icon.stop()


def worker_loop(stop_event: threading.Event, reschedule_event: threading.Event, icon: pystray.Icon) -> None:
    while not stop_event.is_set():
        reschedule_event.clear()
        if reschedule_event.wait(SETTINGS.get_interval_seconds()):
            continue
        if stop_event.is_set():
            break
        if SETTINGS.is_paused():
            continue
        jiggle_mouse()
        update_tray_title(icon)


def main() -> None:
    if not ensure_single_instance():
        return

    add_to_startup()

    icon_image = Image.open(resource_path(os.path.join("icons", "app.ico")))
    icon = pystray.Icon(APP_NAME, icon_image, APP_NAME)

    stop_event = threading.Event()
    reschedule_event = threading.Event()
    worker = threading.Thread(
        target=worker_loop,
        args=(stop_event, reschedule_event, icon),
        daemon=True,
    )
    worker.start()

    def startup_checked(item):
        return startup_enabled()

    def pause_text(item):
        return "Resume" if SETTINGS.is_paused() else "Pause"

    def pause_checked(item):
        return SETTINGS.is_paused()

    icon.menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: f"Interval: {format_interval(SETTINGS.get_interval_seconds())}",
            None,
            enabled=False,
        ),
        pystray.MenuItem(
            "Set interval...",
            lambda i, it: on_set_interval(i, it, reschedule_event),
            default=True,
        ),
        pystray.MenuItem(
            pause_text,
            lambda i, it: on_toggle_pause(i, it, reschedule_event),
            checked=pause_checked,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Run at startup", on_toggle_startup, checked=startup_checked),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", on_quit),
    )

    update_tray_title(icon)
    icon.run()
    stop_event.set()
    reschedule_event.set()


if __name__ == "__main__":
    main()
