"""Add complete installer assets to the existing beta without moving its tag."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = "WALDEX451/BROWSOR"
TAG = "v1.0.0-beta.1"
EXPECTED = ["BROWSOR-1.0.0-beta.1-windows-x64-setup.exe", "BROWSOR-1.0.0-beta.1-macos-arm64.dmg", "BROWSOR-1.0.0-beta.1-macos-x86_64.dmg"]


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def main():
    root = Path(sys.argv[1]).resolve()
    release = json.loads(gh("api", f"repos/{REPO}/releases/tags/{TAG}"))
    if release["draft"] or not release["prerelease"]:
        raise SystemExit("Expected the published 1.0 beta prerelease; refusing to change release type.")
    assets = {item["name"]: item for item in release["assets"]}
    hashes = []
    for name in EXPECTED:
        file = root / name
        if not file.is_file() or file.stat().st_size < 10_000_000:
            raise SystemExit("Missing or incomplete installer: " + name)
        with file.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        hashes.append(f"{digest}  {name}\n")
        if name in assets:
            if assets[name].get("digest") != "sha256:" + digest:
                raise SystemExit("A different installer already exists; will not overwrite " + name)
        else:
            subprocess.run(["gh", "release", "upload", TAG, str(file), "--repo", REPO], check=True)
    checksums = root / "INSTALLERS-SHA256SUMS.txt"
    checksums.write_text("".join(hashes), encoding="ascii")
    subprocess.run(["gh", "release", "upload", TAG, str(checksums), "--repo", REPO, "--clobber"], check=True)
    print("Uploaded Windows setup and both macOS DMGs to the existing prerelease.")


if __name__ == "__main__":
    main()
