# Desktop builds

The project ships three desktop apps:

- `Ai Là Triệu Phú (Host)`
- `Ai Là Triệu Phú (Người Chơi)`
- `Ai Là Triệu Phú (Khán Giả)`

The build scripts package `audio/`, `images/`, and every `questions_*.json` file into each app.

App icons are generated from `images/logo.png` during the build. To override them, add `images/app.ico` for Windows or `images/app.icns` for macOS.

Build outputs use stable ASCII technical names so GitHub Actions and Windows zip tooling do not trip on Unicode paths:

- `AiLaTrieuPhu-Host`
- `AiLaTrieuPhu-Client`
- `AiLaTrieuPhu-Viewer`

Installers and shortcuts still use the Vietnamese display names.

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

## Create GitHub Releases

Push an OS-specific tag. Each workflow builds only one operating system and uploads a thin installer plus role-specific packages.

For a Windows release:

```bash
git tag windows_v1.1.4
git push origin windows_v1.1.4
```

The Windows workflow uploads:

- `AiLaTrieuPhu-Windows-Installer-windows_v1.1.4.zip`
- `AiLaTrieuPhu-Windows-host-windows_v1.1.4.zip`
- `AiLaTrieuPhu-Windows-client-windows_v1.1.4.zip`
- `AiLaTrieuPhu-Windows-viewer-windows_v1.1.4.zip`

For a macOS release:

```bash
git tag macos_v1.1.4
git push origin macos_v1.1.4
```

The macOS-only workflow uploads role-specific `.pkg` files and a small installer selector. Users can download the installer selector, choose Host/Người Chơi/Khán Giả, and fetch only the needed package.

The macOS-only workflow targets macOS 14. It builds two packages:

- `arm64-macos14`: for Apple Silicon Macs.
- `intel-macos14`: for Intel Macs.

GitHub's public `macos-14` runner is Apple Silicon, so the Intel package is built on GitHub's Intel macOS runner with `MACOSX_DEPLOYMENT_TARGET=14.0`.

## Direct Python build command

If the helper scripts are not convenient:

```bash
python packaging/build_apps.py --target all
python packaging/build_apps.py --target host --onefile
python packaging/build_apps.py --target all --pkg
```
