# Keep Awake Lite

> A deliberately under-engineered tray utility that prevents your Windows workstation from taking a nap by nudging the mouse 1 pixel every now and then.

No live dashboard. No charts. No idle analytics. No cockpit pretending your cursor is mission-critical infrastructure.

Just a tiny tray app that moves the cursor and stays out of the way.

## What Is This?

**Keep Awake Lite** is a lightweight Windows tray application that:

- Starts automatically with Windows.
- Moves the mouse cursor 1 pixel right and back at a configurable interval.
- Lets you configure that interval in minutes and seconds from the tray menu.
- Can be paused and resumed without quitting the app.
- Avoids duplicate tray instances with a Windows mutex.
- Uses `pythonw.exe` in script mode so startup does not leave a console window behind.

It exists because sometimes changing power settings is blocked, ignored, reset, managed, haunted by policy, or simply not worth arguing with.

## Tray Menu

Right-click the tray icon:

- `Set interval...`: choose minutes and seconds.
- `Pause` / `Resume`: temporarily stop or restart cursor movement.
- `Run at startup`: toggle the Windows startup entry.
- `Quit`: leave the workstation to its own sleepy decisions.

The interval is saved for the current Windows user and reused on the next start. Pause is intentionally temporary and resets when the app starts again.

## How It Works

Every configured interval, the app performs a tiny mouse move:

```text
1 pixel right
1 pixel left
```

That is the whole trick.

The lite version does not monitor idle time and does not try to be smart. This is by design. Fewer moving parts, fewer surprises, fewer tiny web dashboards for a tool whose job is basically "poke Windows occasionally."

## Build

Recommended build:

```bash
pyinstaller --noconsole --onedir --name KeepAwakeLite --icon icons/app.ico app.py
```

The `--noconsole` flag matters. Without it, Windows may reward you with a console window you did not ask for.

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

You can change the default in code, but normal use should go through the tray menu. That is why the tray menu exists. It wanted a job.

## Startup Behavior

The app writes a value under:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

When running from source, the startup command uses `pythonw.exe` when available. When running as a PyInstaller build, the startup command points to the executable.

## License

MIT. Use it, change it, ship it, or quietly let it keep your workstation awake while you get coffee.
