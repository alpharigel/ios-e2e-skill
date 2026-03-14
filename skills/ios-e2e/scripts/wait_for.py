#!/usr/bin/env python3
"""Polling utilities for waiting on UI elements and conditions.

Can be used as a library (import wait_for, wait_for_element) or as a CLI tool.
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class WaitTimeout(TimeoutError):
    """Raised when a polling condition is not met within the timeout."""
    pass


def wait_for(
    condition_fn: Callable[[], T],
    timeout: float = 5.0,
    interval: float = 0.5,
    message: str = "Condition not met",
) -> T:
    """Poll condition_fn() every interval seconds until it returns a truthy value.
    Raises WaitTimeout if timeout seconds elapse without success.
    """
    deadline = time.monotonic() + timeout
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = condition_fn()
            if result:
                return result
        except Exception as exc:
            last_exc = exc
        time.sleep(interval)

    if last_exc:
        raise WaitTimeout(f"{message} (last error: {last_exc})") from last_exc
    raise WaitTimeout(message)


def wait_for_element(
    ui,
    label: str,
    timeout: float = 8.0,
    interval: float = 0.5,
) -> tuple[int, int]:
    """Wait until an element with label appears in the UI tree.
    Returns its (x, y) center coordinates.
    """
    return wait_for(
        lambda: ui.find_element_center(label),
        timeout=timeout,
        interval=interval,
        message=f"Element '{label}' not found within {timeout}s",
    )


# ======================================================================
# CLI interface
# ======================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Wait for UI conditions")
    parser.add_argument("--udid", required=True, help="Simulator UDID")
    sub = parser.add_subparsers(dest="command", required=True)

    # element
    elem_p = sub.add_parser("element", help="Wait for element by label")
    elem_p.add_argument("--label", required=True)
    elem_p.add_argument("--timeout", type=float, default=8.0)
    elem_p.add_argument("--interval", type=float, default=0.5)

    args = parser.parse_args()

    if args.command == "element":
        # Import here to avoid circular deps when used as library
        from ui_driver import UIDriver
        ui = UIDriver(args.udid)
        try:
            x, y = wait_for_element(ui, args.label, args.timeout, args.interval)
            print(f"Found \"{args.label}\" at ({x}, {y})")
        except WaitTimeout as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
