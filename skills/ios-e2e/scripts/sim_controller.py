#!/usr/bin/env python3
"""SimController — thin wrapper around xcrun simctl for app lifecycle management.

Can be used as a library (import SimController) or as a CLI tool.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path


class SimController:
    """Manages iOS Simulator app lifecycle via xcrun simctl."""

    def __init__(self, udid: str, bundle_id: str | None = None) -> None:
        self.udid = udid
        self.bundle_id = bundle_id

    def _run(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["xcrun", "simctl", *args],
            capture_output=True,
            text=True,
            check=check,
        )

    # ------------------------------------------------------------------
    # Boot / shutdown
    # ------------------------------------------------------------------

    def is_booted(self) -> bool:
        """Check if this simulator is currently booted."""
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted", "--json"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout)
        for runtime_devices in data.get("devices", {}).values():
            for device in runtime_devices:
                if device.get("udid") == self.udid and device.get("state") == "Booted":
                    return True
        return False

    def boot(self, wait: float = 6.0) -> None:
        """Boot the simulator if it's not already booted."""
        if not self.is_booted():
            self._run("boot", self.udid, check=False)
            if wait > 0:
                time.sleep(wait)

    def shutdown(self) -> None:
        """Shut down the simulator."""
        self._run("shutdown", self.udid, check=False)

    # ------------------------------------------------------------------
    # App lifecycle
    # ------------------------------------------------------------------

    def _require_bundle_id(self) -> str:
        if not self.bundle_id:
            raise ValueError("bundle_id is required for this operation")
        return self.bundle_id

    def launch(self, wait: float = 2.0) -> None:
        """Launch the app. Boots the simulator first if needed."""
        bid = self._require_bundle_id()
        self.boot(wait=6.0)
        self._run("launch", self.udid, bid)
        if wait > 0:
            time.sleep(wait)

    def terminate(self) -> None:
        """Terminate the app. Ignores errors if it's not running."""
        bid = self._require_bundle_id()
        self._run("terminate", self.udid, bid, check=False)

    def relaunch(self, wait: float = 2.5) -> None:
        """Terminate then relaunch (fresh state)."""
        self.terminate()
        time.sleep(0.5)
        self.launch(wait=wait)

    def install(self, app_path: str) -> None:
        """Install an .app bundle onto the simulator."""
        self._run("install", self.udid, app_path)

    def uninstall(self) -> None:
        """Uninstall the app from the simulator."""
        bid = self._require_bundle_id()
        self._run("uninstall", self.udid, bid, check=False)

    # ------------------------------------------------------------------
    # App data
    # ------------------------------------------------------------------

    def get_app_container(self, container_type: str = "data") -> str | None:
        """Get the path to the app's container directory."""
        bid = self._require_bundle_id()
        result = subprocess.run(
            ["xcrun", "simctl", "get_app_container", self.udid, bid, container_type],
            capture_output=True, text=True
        )
        path = result.stdout.strip()
        return path if path else None

    def clear_app_data(self) -> None:
        """Delete the app's local data stores (SwiftData/CoreData).

        Removes default.store files from the app's Application Support directory.
        Must be called while the app is NOT running.
        """
        container = self.get_app_container("data")
        if not container:
            return
        app_support = os.path.join(container, "Library", "Application Support")
        for pattern in ["default.store", "default.store-wal", "default.store-shm"]:
            for f in glob.glob(os.path.join(app_support, pattern)):
                try:
                    os.remove(f)
                except OSError:
                    pass

    # ------------------------------------------------------------------
    # Screenshots & media
    # ------------------------------------------------------------------

    def screenshot(self, path: str | Path) -> Path:
        """Capture a PNG screenshot and return the path."""
        path = Path(path)
        self._run("io", self.udid, "screenshot", str(path))
        return path

    # ------------------------------------------------------------------
    # Push notifications
    # ------------------------------------------------------------------

    def push_notification(self, payload: dict) -> None:
        """Push a simulated notification to the app."""
        bid = self._require_bundle_id()
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(payload, f)
            tmp_path = f.name
        try:
            self._run("push", self.udid, bid, tmp_path)
        finally:
            os.unlink(tmp_path)


# ======================================================================
# CLI interface
# ======================================================================

def _find_booted_udid() -> str:
    """Find the first booted simulator UDID."""
    result = subprocess.run(
        ["xcrun", "simctl", "list", "devices", "booted", "--json"],
        capture_output=True, text=True, check=True
    )
    data = json.loads(result.stdout)
    for runtime_devices in data.get("devices", {}).values():
        for device in runtime_devices:
            if device.get("state") == "Booted":
                return device["udid"]
    raise RuntimeError("No booted simulator found. Run: xcrun simctl boot <device>")


def main() -> None:
    parser = argparse.ArgumentParser(description="iOS Simulator app lifecycle manager")
    parser.add_argument("--udid", help="Simulator UDID (auto-detects booted sim if omitted)")
    parser.add_argument("--bundle-id", help="App bundle identifier")
    sub = parser.add_subparsers(dest="command", required=True)

    # boot
    sub.add_parser("boot", help="Boot the simulator")

    # shutdown
    sub.add_parser("shutdown", help="Shut down the simulator")

    # launch
    sub.add_parser("launch", help="Launch the app")

    # terminate
    sub.add_parser("terminate", help="Terminate the app")

    # relaunch
    sub.add_parser("relaunch", help="Terminate and relaunch the app")

    # install
    install_p = sub.add_parser("install", help="Install an .app bundle")
    install_p.add_argument("--app-path", required=True, help="Path to .app bundle")

    # screenshot
    ss_p = sub.add_parser("screenshot", help="Take a screenshot")
    ss_p.add_argument("--path", default="/tmp/screenshot.png", help="Output path")

    # clear-data
    sub.add_parser("clear-data", help="Clear app's local data stores")

    # list-booted
    sub.add_parser("list-booted", help="List all booted simulators")

    args = parser.parse_args()

    if args.command == "list-booted":
        result = subprocess.run(
            ["xcrun", "simctl", "list", "devices", "booted"],
            capture_output=True, text=True
        )
        print(result.stdout.strip())
        return

    udid = args.udid or _find_booted_udid()
    sim = SimController(udid, args.bundle_id)

    if args.command == "boot":
        sim.boot()
        print(f"Simulator {udid} booted")

    elif args.command == "shutdown":
        sim.shutdown()
        print(f"Simulator {udid} shut down")

    elif args.command == "launch":
        sim.launch()
        print(f"Launched {args.bundle_id} on {udid}")

    elif args.command == "terminate":
        sim.terminate()
        print(f"Terminated {args.bundle_id} on {udid}")

    elif args.command == "relaunch":
        sim.relaunch()
        print(f"Relaunched {args.bundle_id} on {udid}")

    elif args.command == "install":
        sim.install(args.app_path)
        print(f"Installed {args.app_path} on {udid}")

    elif args.command == "screenshot":
        path = sim.screenshot(args.path)
        print(f"Screenshot saved to {path}")

    elif args.command == "clear-data":
        sim.terminate()
        time.sleep(0.5)
        sim.clear_app_data()
        print(f"Cleared data for {args.bundle_id} on {udid}")


if __name__ == "__main__":
    main()
