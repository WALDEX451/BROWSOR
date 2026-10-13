"""Install/mount an authored release package on a disposable CI runner.

Check that its real, frozen executable starts Chromium and loads the local
start page. The local debug port is enabled only for this child process.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


def check(executable, output):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = dict(os.environ)
    env.update({"QT_QPA_PLATFORM": "offscreen", "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu",
                "QTWEBENGINE_REMOTE_DEBUGGING": f"127.0.0.1:{port}"})
    log = output / "startup.log"
    kwargs = {"start_new_session": True} if platform.system() != "Windows" else {}
    with log.open("wb") as stream:
        process = subprocess.Popen([str(executable)], stdout=stream, stderr=stream, env=env, **kwargs)
        try:
            deadline = time.monotonic() + 50
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError(f"Application exited before loading its start page: {process.returncode}")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as response:
                        pages = json.load(response)
                    for page in pages:
                        if page.get("url") == "browsor://home/" and "Your start" in page.get("title", ""):
                            return {"loaded_start_page": True, "title": page["title"], "url": page["url"]}
                except (OSError, ValueError):
                    pass
                time.sleep(0.5)
            raise RuntimeError("The packaged app did not load its local start page within 50 seconds.")
        finally:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, default=Path("startup-report"))
    args = parser.parse_args()
    package, output = args.package.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with package.open("rb") as file:
        digest = hashlib.file_digest(file, "sha256").hexdigest()
    report = {"package": package.name, "sha256": digest, "os": platform.system(), "architecture": platform.machine()}
    mount = None
    try:
        with tempfile.TemporaryDirectory(prefix="browsor-installer-") as temporary:
            if platform.system() == "Windows":
                installed = Path(temporary) / "BROWSOR"
                subprocess.run([str(package), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/DIR=" + str(installed)], check=True, timeout=120)
                executable = installed / "BROWSOR.exe"
            else:
                data = plistlib.loads(subprocess.check_output(["hdiutil", "attach", "-readonly", "-nobrowse", "-plist", str(package)]))
                mount = next(Path(item["mount-point"]) for item in data["system-entities"] if "mount-point" in item)
                executable = mount / "BROWSOR.app" / "Contents" / "MacOS" / "BROWSOR"
            report.update(check(executable, output))
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        if mount is not None:
            subprocess.run(["hdiutil", "detach", str(mount)], check=False)
        (output / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report), flush=True)
    print("Frozen application loaded the BROWSOR start page. This is a startup check, not a full browser compatibility test.")


if __name__ == "__main__":
    main()
