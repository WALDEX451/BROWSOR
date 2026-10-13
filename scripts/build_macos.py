"""Build a native macOS application bundle and read-only drag-to-install DMG."""

import argparse
import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import urllib.request

TOOLS = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=TOOLS.parent)
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("Build DMG files on macOS. Use the installer workflow from Windows.")
    source = args.source.resolve()
    sys.path.insert(0, str(source))
    from version import VERSION
    architecture = platform.machine()
    if architecture not in ("arm64", "x86_64"):
        raise SystemExit("Unsupported Mac architecture: " + architecture)
    os.chdir(source)
    build, dist = source / "build", source / "dist"
    build.mkdir(exist_ok=True)
    dist.mkdir(exist_ok=True)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication
    from PIL import Image
    from theme import svg
    qt_app = QApplication.instance() or QApplication([])
    mark = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    mark.fill(Qt.GlobalColor.transparent)
    painter = QPainter(mark)
    QSvgRenderer(QByteArray(svg("logo", "#c4b5fd", 1024).encode())).render(painter)
    painter.end()
    mark.save(str(build / "mac-icon.png"))
    with Image.open(build / "mac-icon.png") as image:
        image.save(build / "BROWSOR.icns")
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir",
        "--name", "BROWSOR", "--icon", str(build / "BROWSOR.icns"),
        "--osx-bundle-identifier", "io.github.waldex451.browsor", "--target-arch", architecture,
        "--additional-hooks-dir", str(TOOLS / "hooks"),
        "--add-data", "assets/start.html:assets", "--add-data", "assets/check.svg:assets", "--add-data", "assets/chevron.svg:assets",
        "--exclude-module", "tkinter", "--exclude-module", "matplotlib", "--exclude-module", "numpy", "main.py",
    ], check=True)
    bundle = dist / "BROWSOR.app"
    resources = bundle / "Contents" / "Resources"
    with (bundle / "Contents" / "Info.plist").open("rb") as file:
        info = plistlib.load(file)
    info.update({"CFBundleDisplayName": "BROWSOR", "CFBundleShortVersionString": "1.0.0", "CFBundleVersion": "1.0.0.1",
                 "LSMinimumSystemVersion": "13.0", "NSHighResolutionCapable": True,
                 "NSHumanReadableCopyright": "BROWSOR " + VERSION + " · Third-party notices are included in Resources/LICENSES."})
    with (bundle / "Contents" / "Info.plist").open("wb") as file:
        plistlib.dump(info, file)
    for name in ("README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(source / name, resources / name)
    shutil.copytree(source / "LICENSES", resources / "LICENSES", dirs_exist_ok=True)
    for name in ("PySide6", "PySide6_Addons", "PySide6_Essentials", "shiboken6", "pyinstaller"):
        package = distribution(name)
        for item in package.files or []:
            if "/licenses/" in str(item).replace("\\", "/"):
                target = resources / "LICENSES" / name / Path(item).name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(package.locate_file(item), target)
    python_license = resources / "LICENSES" / "Python.txt"
    candidates = [Path(sys.base_prefix) / "LICENSE.txt", Path(sysconfig.get_path("stdlib")) / "LICENSE.txt"]
    for candidate in candidates:
        if candidate.is_file():
            shutil.copy2(candidate, python_license)
            break
    else:
        url = f"https://raw.githubusercontent.com/python/cpython/v{platform.python_version()}/LICENSE"
        with urllib.request.urlopen(url, timeout=40) as response:
            python_license.write_bytes(response.read())
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=source).strip()
    inventory = {"BROWSOR": VERSION, "Python": platform.python_version(), "architecture": architecture,
                 "source_revision": revision, "packaging_revision": os.environ.get("GITHUB_SHA", "local")}
    inventory.update({name: distribution(name).version for name in ("PySide6", "shiboken6", "PyInstaller")})
    (resources / "BUILD-INFO.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    instructions = f"""BROWSOR {VERSION} for macOS ({architecture})

Drag BROWSOR.app into the Applications shortcut, then open it from Applications.
Requires macOS 13 or later. Use arm64 for Apple Silicon (M-series), x86_64 for Intel.

This beta is ad-hoc signed, not signed with an Apple Developer ID or notarized.
macOS may block the first launch. After trying to open your downloaded copy,
review System Settings > Privacy & Security and use Open Anyway if you trust it.
Do not disable Gatekeeper. No Apple developer credentials are included.

The app contains Python and Qt; no separate installation is needed.
Website compatibility has not received a full Mac compatibility audit.
App preferences and website data stay in your own user Library folder.

Release: https://github.com/WALDEX451/BROWSOR/releases/tag/v{VERSION}
Licenses and build information: BROWSOR.app/Contents/Resources/
"""
    (resources / "INSTALL-macOS.txt").write_text(instructions, encoding="utf-8")
    # Updating the bundle's resource seal keeps the independently signed Qt binaries intact.
    subprocess.run(["codesign", "--force", "--sign", "-", str(bundle)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(bundle)], check=True)
    dmg = dist / f"BROWSOR-{VERSION}-macos-{architecture}.dmg"
    with tempfile.TemporaryDirectory(prefix="dmg-", dir=build) as temporary:
        staging = Path(temporary)
        shutil.copytree(bundle, staging / "BROWSOR.app", symlinks=True)
        (staging / "Applications").symlink_to("/Applications", target_is_directory=True)
        (staging / "READ ME.txt").write_text(instructions, encoding="utf-8")
        subprocess.run(["hdiutil", "create", "-ov", "-volname", "BROWSOR 1.0 beta", "-srcfolder", str(staging),
                        "-fs", "HFS+", "-format", "UDZO", str(dmg)], check=True)
    subprocess.run(["hdiutil", "verify", str(dmg)], check=True)
    with dmg.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    (dist / (dmg.name + ".sha256")).write_text(f"{digest}  {dmg.name}\n", encoding="ascii")
    print(json.dumps({"file": str(dmg), "bytes": dmg.stat().st_size, "sha256": digest}))


if __name__ == "__main__":
    main()
