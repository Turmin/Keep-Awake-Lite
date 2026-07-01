# Keep Awake Lite

Small Windows tray utility that keeps a workstation awake by moving the mouse cursor 1 pixel at a configurable interval.

This is the lite version: no dashboard, no statistics, no idle history, and no continuous timer display.

## Features

- Runs as a Windows tray application.
- Starts automatically with Windows.
- Moves the cursor 1 pixel right and back at the configured interval.
- Lets you set the interval from the tray menu in minutes and seconds.
- Supports Pause/Resume from the tray menu.
- Prevents multiple running instances with a Windows mutex.
- Uses `pythonw.exe` in script mode to avoid a visible CMD window.

## Tray Menu

- `Set interval...`: opens a small Windows dialog for minutes and seconds.
- `Pause` / `Resume`: temporarily stops or resumes cursor movement.
- `Run at startup`: toggles the Windows startup registry entry.
- `Quit`: exits the tray app.

The interval is saved under the current user's registry settings and is reused on the next start. Pause is runtime-only and is not persisted.

## Build

Recommended build:

```bash
pyinstaller --noconsole --onedir --name KeepAwakeLite --icon icons/app.ico app.py
```

## Development

Run from source:

```bash
.venv/Scripts/python.exe app.py
```

Syntax check:

```bash
.venv/Scripts/python.exe -m py_compile app.py
```

## Requirements

- Windows 10 or 11
- Python 3.11+ for development
- PyWin32
- PyStray
- Pillow
- PowerShell with Windows Forms support for the interval dialog
- PyInstaller for packaging

The packaged app does not require admin rights.

## Project Structure

```text
KeepAwakeLite/
├── app.py
├── icons/
│   └── app.ico
└── README.md
```

## Configuration

Default interval:

```python
DEFAULT_INTERVAL_SECONDS = 4 * 60
```

Minimum interval:

```python
MIN_INTERVAL_SECONDS = 1
```

The default can be changed in code, but normal use should go through the tray menu.

## Startup Behavior

The app writes a value under:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

When running from source, the startup command uses `pythonw.exe` when available. When running as a PyInstaller build, the startup command points to the executable.

## License

MIT
