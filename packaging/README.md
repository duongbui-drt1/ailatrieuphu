# Desktop builds

The project ships three desktop apps:

- `AiLaTrieuPhu-Host`
- `AiLaTrieuPhu-Client`
- `AiLaTrieuPhu-Viewer`

The build scripts package `audio/`, `images/`, and every `questions_*.json` file into each app.

## Windows .exe

Run from the repo root:

```powershell
.\packaging\build_windows.bat
```

If you prefer PowerShell directly:

```powershell
.\packaging\build_windows.ps1
```

Build only one role:

```powershell
.\packaging\build_windows.bat -Target host
.\packaging\build_windows.bat -Target client
.\packaging\build_windows.bat -Target viewer
```

Default output is a stable one-folder app under `dist/`, for example:

```text
dist/AiLaTrieuPhu-Host/AiLaTrieuPhu-Host.exe
```

For a single-file executable:

```powershell
.\packaging\build_windows.bat -OneFile
```

Single-file builds are easier to copy, but start slower because bundled audio/images must be unpacked at launch.

If Python Manager fails on Windows, install Python 3.10+ from python.org or point the script to a specific interpreter:

```powershell
$env:AILTP_PYTHON="C:\Path\To\python.exe"
.\packaging\build_windows.bat
```

## macOS .app and .pkg

Build this on a Mac:

```bash
bash packaging/build_macos.sh
```

Build only one role:

```bash
bash packaging/build_macos.sh host
bash packaging/build_macos.sh client
bash packaging/build_macos.sh viewer
```

The script creates `.app` bundles in `dist/` and an unsigned `.pkg` installer. The full-suite package installs all selected apps into `/Applications`.

Unsigned macOS apps may require right-clicking and choosing Open the first time, or signing/notarization for public distribution.

## Build on GitHub Actions

If you do not have a Mac, push the repo to GitHub and run the `Build desktop apps` workflow:

1. Open the repo on GitHub.
2. Go to `Actions`.
3. Choose `Build desktop apps`.
4. Click `Run workflow`.
5. Choose `all`, `host`, `client`, or `viewer`.
6. Download `AiLaTrieuPhu-macOS` from the workflow artifacts.

The macOS artifact contains unsigned `.app` bundles and `.pkg` installers. For public distribution without Gatekeeper warnings, sign and notarize them with an Apple Developer ID.

## Direct Python build command

If the helper scripts are not convenient:

```bash
python packaging/build_apps.py --target all
python packaging/build_apps.py --target host --onefile
python packaging/build_apps.py --target all --pkg
```
