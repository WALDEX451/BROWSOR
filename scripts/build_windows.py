"""Build a Windows x64 portable release with bundled browser resources."""

import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import VERSION, DISPLAY_VERSION


def copy_licenses(source: Path, destination: Path) -> None:
    """Copy notices without Windows path-length failures in installer folders."""
    destination.mkdir(parents=True, exist_ok=True)
    manifest = []
    for item in sorted(source.rglob("*")):
        if not item.is_file():
            continue
        digest = hashlib.sha256(str(item.relative_to(source)).encode("utf-8")).hexdigest()[:10]
        suffix = item.suffix or ".txt"
        safe_stem = "".join(character if character.isalnum() else "-" for character in item.stem)[:52].strip("-")
        target_name = f"{safe_stem or 'notice'}-{digest}{suffix}"
        shutil.copy2(item, destination / target_name)
        manifest.append(f"{target_name}  {item.relative_to(source).as_posix()}\n")
    (destination / "MANIFEST.txt").write_text("".join(manifest), encoding="utf-8")


def main():
    if sys.platform != "win32" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise SystemExit("Build this package using Windows and 64-bit Python.")
    os.chdir(ROOT)
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    # A code-owned vector mark, rendered into native Windows icon sizes.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication
    from PIL import Image
    from theme import svg
    app = QApplication.instance() or QApplication([])
    mark = QImage(256, 256, QImage.Format.Format_ARGB32)
    mark.fill(Qt.GlobalColor.transparent)
    painter = QPainter(mark)
    QSvgRenderer(QByteArray(svg("logo", "#99e2c5", 256).encode())).render(painter)
    painter.end()
    mark.save(str(build / "icon.png"))
    with Image.open(build / "icon.png") as source:
        source.save(build / "BROWSOR.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    version_info = """VSVersionInfo(ffi=FixedFileInfo(filevers=(2,0,0,1), prodvers=(2,0,0,1), mask=0x3f, flags=0x2, OS=0x40004, fileType=0x1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('FileDescription','BROWSOR DISPLAY_VERSION'),StringStruct('FileVersion','VERSION'),StringStruct('ProductName','BROWSOR'),StringStruct('ProductVersion','VERSION'),StringStruct('OriginalFilename','BROWSOR.exe')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])"""
    (build / "version.txt").write_text(version_info.replace("DISPLAY_VERSION", DISPLAY_VERSION).replace("VERSION", VERSION), encoding="utf-8")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--onedir", "--name", "BROWSOR",
               "--icon", str(build / "BROWSOR.ico"), "--version-file", str(build / "version.txt"),
               "--add-data", "assets/start.html:assets", "--add-data", "assets/check.svg:assets", "--add-data", "assets/chevron.svg:assets",
               "--additional-hooks-dir", str(ROOT / "scripts" / "hooks"),
               "--exclude-module", "tkinter", "--exclude-module", "matplotlib", "--exclude-module", "numpy", "main.py"]
    # PyInstaller discovers DLLs through PATH. Keep unrelated workstation
    # runtimes (Poppler, libheif and other Qt installs) out of this bundle.
    windows_root = Path(os.environ.get("WINDIR", r"C:\Windows"))
    build_env = os.environ.copy()
    build_env["PATH"] = os.pathsep.join((
        str(Path(sys.base_prefix)),
        str(Path(sys.base_prefix) / "Scripts"),
        str(windows_root / "System32"),
        str(windows_root),
    ))
    subprocess.run(command, check=True, env=build_env)
    package = ROOT / "dist" / "BROWSOR"
    for name in ("README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, package / name)
    copy_licenses(ROOT / "LICENSES", package / "LICENSES")
    # Preserve all notices shipped by the exact packages used to build this release.
    for name in ("PySide6", "PySide6_Addons", "PySide6_Essentials", "shiboken6", "pyinstaller"):
        dist = distribution(name)
        for file in dist.files or []:
            if "/licenses/" in str(file).replace("\\", "/"):
                destination = package / "LICENSES" / name / Path(file).name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dist.locate_file(file), destination)
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", package / "LICENSES" / "Python.txt")
    inventory = {"BROWSOR": VERSION, "Python": platform.python_version()}
    inventory.update({name: distribution(name).version for name in ("PySide6", "shiboken6", "PyInstaller")})
    (package / "BUILD-INFO.json").write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    archive = ROOT / "dist" / f"BROWSOR-{VERSION}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                output.write(path, path.relative_to(package.parent))
    with archive.open("rb") as source:
        digest = hashlib.file_digest(source, "sha256").hexdigest()
    (ROOT / "dist" / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size, "sha256": digest}))


if __name__ == "__main__":
    main()
