from __future__ import annotations

import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app_info import (  # noqa: E402
    APP_AUTHOR,
    APP_COPYRIGHT,
    APP_DESCRIPTION,
    APP_IDENTIFIER_ROOT,
    APP_PRODUCT_NAME,
    APP_VERSION,
    version_tuple,
)

DIST_DIR = Path(os.environ.get("AILTP_PYI_DIST_DIR", ROOT_DIR / "dist"))
BUILD_DIR = Path(os.environ.get("AILTP_PYI_BUILD_DIR", ROOT_DIR / "build" / "pyinstaller"))
SPEC_DIR = Path(os.environ.get("AILTP_PYI_SPEC_DIR", ROOT_DIR / "build" / "specs"))
ICON_BUILD_DIR = Path(
    os.environ.get("AILTP_ICON_BUILD_DIR", Path(tempfile.gettempdir()) / "ailatrieuphu-icons")
)
APP_ICON_SOURCE = ROOT_DIR / "images" / "logo.png"

APPS = {
    "host": {
        "entry": "run_host.pyw",
        "name": "AiLaTrieuPhu-Host",
        "display_name": "Ai Là Triệu Phú (Host)",
    },
    "client": {
        "entry": "run_client.pyw",
        "name": "AiLaTrieuPhu-Client",
        "display_name": "Ai Là Triệu Phú (Người Chơi)",
    },
    "viewer": {
        "entry": "run_viewer.pyw",
        "name": "AiLaTrieuPhu-Viewer",
        "display_name": "Ai Là Triệu Phú (Khán Giả)",
    },
}


def app_display_name(app_key: str) -> str:
    return APPS[app_key].get("display_name", APPS[app_key]["name"])


def macos_release_version(version: str) -> str:
    base = str(version).split("-", 1)[0]
    parts = []
    for chunk in base.split("."):
        if chunk.isdigit():
            parts.append(chunk)
    while len(parts) < 3:
        parts.append("0")
    return ".".join(parts[:3])


def macos_build_version(version: str) -> str:
    release = macos_release_version(version)
    suffix = str(version).split("-", 1)[1:] or [""]
    build_number = 0
    for chunk in suffix[0].replace("-", ".").split("."):
        if chunk.isdigit():
            build_number = int(chunk)
    return f"{release}.{build_number}" if build_number else release


def data_files() -> list[tuple[Path, str]]:
    pairs: list[tuple[Path, str]] = []
    for folder_name in ("audio", "images"):
        folder = ROOT_DIR / folder_name
        if folder.exists():
            pairs.append((folder, folder_name))

    for question_pack in sorted(ROOT_DIR.glob("questions_*.json")):
        pairs.append((question_pack, "."))

    legacy_questions = ROOT_DIR / "questions.json"
    if legacy_questions.exists():
        pairs.append((legacy_questions, "."))

    return pairs


def tkinter_data_files() -> list[tuple[Path, str]]:
    python_dir = Path(sys.executable).resolve().parent
    tcl_dir = python_dir / "tcl"
    if not tcl_dir.exists():
        return []
    return [(tcl_dir, "tcl")]


def tkinter_binary_files() -> list[tuple[Path, str]]:
    python_dir = Path(sys.executable).resolve().parent
    dll_dir = python_dir / "DLLs"
    candidates = [
        dll_dir / "_tkinter.pyd",
        dll_dir / "tcl86t.dll",
        dll_dir / "tk86t.dll",
    ]
    return [(path, ".") for path in candidates if path.exists()]


def selected_apps(target: str) -> list[str]:
    if target == "all":
        return list(APPS)
    return [target]


def icon_output_dir() -> Path:
    ICON_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    return ICON_BUILD_DIR


def load_pillow_image():
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit(
            "Pillow is required to generate app icons. Run: python -m pip install -r requirements-build.txt"
        ) from exc
    return Image


def windows_icon_path() -> Path | None:
    explicit_icon = ROOT_DIR / "images" / "app.ico"
    if explicit_icon.exists():
        return explicit_icon
    if not APP_ICON_SOURCE.exists():
        return None

    output = icon_output_dir() / "app.ico"
    if output.exists() and output.stat().st_mtime >= APP_ICON_SOURCE.stat().st_mtime:
        return output

    Image = load_pillow_image()
    image = Image.open(APP_ICON_SOURCE).convert("RGBA")
    image.save(
        output,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    return output


def macos_icon_path() -> Path | None:
    explicit_icon = ROOT_DIR / "images" / "app.icns"
    if explicit_icon.exists():
        return explicit_icon
    if not APP_ICON_SOURCE.exists():
        return None
    if sys.platform != "darwin":
        return APP_ICON_SOURCE

    output = icon_output_dir() / "app.icns"
    if output.exists() and output.stat().st_mtime >= APP_ICON_SOURCE.stat().st_mtime:
        return output

    Image = load_pillow_image()
    lanczos = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    source = Image.open(APP_ICON_SOURCE).convert("RGBA")
    iconset = icon_output_dir() / "app.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)

    for base_size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            pixel_size = base_size * scale
            suffix = "@2x" if scale == 2 else ""
            icon_name = f"icon_{base_size}x{base_size}{suffix}.png"
            source.resize((pixel_size, pixel_size), lanczos).save(iconset / icon_name)

    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(output)], check=True)
    return output


def pyinstaller_icon_path() -> Path | None:
    if sys.platform == "win32":
        return windows_icon_path()
    if sys.platform == "darwin":
        return macos_icon_path()
    return APP_ICON_SOURCE if APP_ICON_SOURCE.exists() else None


def windows_version_file(app_key: str, version: str) -> Path:
    app = APPS[app_key]
    output = icon_output_dir() / f"{app['name']}-version.txt"
    file_version = version_tuple(version)
    file_description = f"{APP_DESCRIPTION} - {app_display_name(app_key)}"
    output.write_text(
        f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={file_version},
    prodvers={file_version},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', '{APP_AUTHOR}'),
          StringStruct('FileDescription', '{file_description}'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', '{app['name']}'),
          StringStruct('LegalCopyright', '{APP_COPYRIGHT}'),
          StringStruct('OriginalFilename', '{app['name']}.exe'),
          StringStruct('ProductName', '{APP_PRODUCT_NAME}'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return output


def apply_macos_bundle_metadata(app_key: str, version: str) -> None:
    if sys.platform != "darwin":
        return
    app = APPS[app_key]
    display_name = app_display_name(app_key)
    short_version = macos_release_version(version)
    build_version = macos_build_version(version)
    plist_path = DIST_DIR / f"{app['name']}.app" / "Contents" / "Info.plist"
    if not plist_path.exists():
        return

    with plist_path.open("rb") as file:
        plist = plistlib.load(file)
    plist.update(
        {
            "CFBundleDisplayName": display_name,
            "CFBundleName": display_name,
            "CFBundleGetInfoString": f"{APP_PRODUCT_NAME} {version}, {APP_AUTHOR}",
            "CFBundleIdentifier": f"{APP_IDENTIFIER_ROOT}.{app_key}",
            "CFBundleShortVersionString": short_version,
            "CFBundleVersion": build_version,
            "NSHumanReadableCopyright": APP_COPYRIGHT,
        }
    )
    with plist_path.open("wb") as file:
        plistlib.dump(plist, file)


def run_pyinstaller(app_key: str, onefile: bool, version: str) -> None:
    try:
        import PyInstaller.__main__ as pyinstaller
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is not installed. Run: python -m pip install -r requirements-build.txt"
        ) from exc

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)

    app = APPS[app_key]
    entry = ROOT_DIR / app["entry"]
    if not entry.exists():
        raise SystemExit(f"Missing entrypoint: {entry}")

    args = [
        str(entry),
        "--name",
        app["name"],
        "--noconfirm",
        "--clean",
        "--windowed",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(SPEC_DIR),
    ]
    args.append("--onefile" if onefile else "--onedir")

    icon_path = pyinstaller_icon_path()
    if icon_path:
        args.extend(["--icon", str(icon_path)])

    if sys.platform == "win32":
        args.extend(["--version-file", str(windows_version_file(app_key, version))])

    for source, destination in data_files():
        args.extend(["--add-data", f"{source}{os.pathsep}{destination}"])

    for source, destination in tkinter_data_files():
        args.extend(["--add-data", f"{source}{os.pathsep}{destination}"])

    for source, destination in tkinter_binary_files():
        args.extend(["--add-binary", f"{source}{os.pathsep}{destination}"])

    runtime_hook = ROOT_DIR / "packaging" / "rth_tkinter.py"
    if runtime_hook.exists():
        args.extend(["--runtime-hook", str(runtime_hook)])

    args.extend(["--hidden-import", "tkinter", "--hidden-import", "_tkinter"])

    print(f"\n==> Building {app_display_name(app_key)} [{app['name']}]")
    pyinstaller.run(args)
    apply_macos_bundle_metadata(app_key, version)


def build_macos_pkg(app_keys: list[str], version: str) -> None:
    if sys.platform != "darwin":
        raise SystemExit(".pkg can only be built on macOS. Build the Windows .exe on Windows.")

    pkg_root = ROOT_DIR / "build" / "pkgroot"
    applications_dir = pkg_root / "Applications"
    if pkg_root.exists():
        shutil.rmtree(pkg_root)
    applications_dir.mkdir(parents=True, exist_ok=True)

    for app_key in app_keys:
        app_name = APPS[app_key]["name"]
        display_name = app_display_name(app_key)
        app_bundle = DIST_DIR / f"{app_name}.app"
        if not app_bundle.exists():
            raise SystemExit(f"Missing app bundle for pkg: {app_bundle}")
        shutil.copytree(app_bundle, applications_dir / f"{display_name}.app")

    package_name = "AiLaTrieuPhu.pkg" if len(app_keys) > 1 else f"{APPS[app_keys[0]]['name']}.pkg"
    package_path = DIST_DIR / package_name
    identifier_suffix = "suite" if len(app_keys) > 1 else app_keys[0]

    subprocess.run(
        [
            "pkgbuild",
            "--root",
            str(pkg_root),
            "--identifier",
            f"{APP_IDENTIFIER_ROOT}.{identifier_suffix}",
            "--version",
            version,
            "--install-location",
            "/",
            str(package_path),
        ],
        check=True,
    )
    print(f"\n==> Built {package_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Ai La Trieu Phu desktop apps.")
    parser.add_argument("--target", choices=["all", *APPS.keys()], default="all")
    parser.add_argument("--onefile", action="store_true", help="Build one executable file per app.")
    parser.add_argument("--pkg", action="store_true", help="On macOS, also build a .pkg installer.")
    parser.add_argument("--version", default=APP_VERSION)
    args = parser.parse_args()

    if args.pkg and args.onefile:
        raise SystemExit("--pkg requires macOS .app bundles. Remove --onefile.")

    app_keys = selected_apps(args.target)
    for app_key in app_keys:
        run_pyinstaller(app_key, args.onefile, args.version)

    if args.pkg:
        build_macos_pkg(app_keys, args.version)

    print(f"\nDone. Output: {DIST_DIR}")


if __name__ == "__main__":
    main()
