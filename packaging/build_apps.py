from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DIST_DIR = Path(os.environ.get("AILTP_PYI_DIST_DIR", ROOT_DIR / "dist"))
BUILD_DIR = Path(os.environ.get("AILTP_PYI_BUILD_DIR", ROOT_DIR / "build" / "pyinstaller"))
SPEC_DIR = Path(os.environ.get("AILTP_PYI_SPEC_DIR", ROOT_DIR / "build" / "specs"))

APPS = {
    "host": {
        "entry": "run_host.pyw",
        "name": "AiLaTrieuPhu-Host",
    },
    "client": {
        "entry": "run_client.pyw",
        "name": "AiLaTrieuPhu-Client",
    },
    "viewer": {
        "entry": "run_viewer.pyw",
        "name": "AiLaTrieuPhu-Viewer",
    },
}


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


def run_pyinstaller(app_key: str, onefile: bool) -> None:
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

    print(f"\n==> Building {app['name']}")
    pyinstaller.run(args)


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
        app_bundle = DIST_DIR / f"{app_name}.app"
        if not app_bundle.exists():
            raise SystemExit(f"Missing app bundle for pkg: {app_bundle}")
        shutil.copytree(app_bundle, applications_dir / app_bundle.name)

    package_name = "AiLaTrieuPhu.pkg" if len(app_keys) > 1 else f"{APPS[app_keys[0]]['name']}.pkg"
    package_path = DIST_DIR / package_name
    identifier_suffix = "suite" if len(app_keys) > 1 else app_keys[0]

    subprocess.run(
        [
            "pkgbuild",
            "--root",
            str(pkg_root),
            "--identifier",
            f"vn.duli.ailatrieuphu.{identifier_suffix}",
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
    parser.add_argument("--version", default="1.0.0")
    args = parser.parse_args()

    if args.pkg and args.onefile:
        raise SystemExit("--pkg requires macOS .app bundles. Remove --onefile.")

    app_keys = selected_apps(args.target)
    for app_key in app_keys:
        run_pyinstaller(app_key, args.onefile)

    if args.pkg:
        build_macos_pkg(app_keys, args.version)

    print(f"\nDone. Output: {DIST_DIR}")


if __name__ == "__main__":
    main()
