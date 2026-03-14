#!/usr/bin/env python3
"""UIDriver — AXe CLI wrapper for iOS Simulator UI automation.

Can be used as a library (import UIDriver) or as a CLI tool.
Requires AXe: brew install cameroncooke/axe/axe
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time


AXE_BIN = "axe"


class UIDriver:
    """Wraps AXe CLI commands for programmatic iOS Simulator UI automation."""

    def __init__(self, udid: str) -> None:
        self.udid = udid
        self._cached_screen_size: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # Low-level AXe runner
    # ------------------------------------------------------------------

    def _axe(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        cmd = [AXE_BIN, *args, "--udid", self.udid]
        return subprocess.run(cmd, capture_output=True, text=True, check=check)

    # ------------------------------------------------------------------
    # Tap
    # ------------------------------------------------------------------

    def tap_label(self, label: str, post_delay: float = 0.3) -> None:
        """Tap an element by its accessibility label.
        Falls back to coordinate-based tap if AXe label tap fails."""
        result = self._axe("tap", "--label", label, check=False)
        if result.returncode != 0:
            center = self.find_element_center(label)
            if center is None:
                raise RuntimeError(f"Element '{label}' not found in UI tree")
            self._axe("tap", "-x", str(center[0]), "-y", str(center[1]))
        if post_delay > 0:
            time.sleep(post_delay)

    def tap_xy(self, x: int, y: int, post_delay: float = 0.3) -> None:
        """Tap at explicit coordinates (points)."""
        self._axe("tap", "-x", str(x), "-y", str(y))
        if post_delay > 0:
            time.sleep(post_delay)

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    def type_text(self, text: str) -> None:
        """Type text into the focused field. Text is a positional arg in AXe."""
        self._axe("type", text)

    def press_return(self) -> None:
        """Press the Return / Enter key (HID usage 0x28 = 40)."""
        self._axe("key", "40")

    def press_delete(self) -> None:
        """Press the Delete / Backspace key (HID usage 0x2A = 42)."""
        self._axe("key", "42")

    def clear_and_type(self, text: str) -> None:
        """Select all existing text then type replacement."""
        self._axe("key", "224+4")  # Cmd+A to select all
        time.sleep(0.1)
        self.type_text(text)

    # ------------------------------------------------------------------
    # Swipe gestures
    # ------------------------------------------------------------------

    def screen_size(self) -> tuple[int, int]:
        """Return (width, height) in points, cached after first call."""
        if self._cached_screen_size is None:
            tree = self.get_ui_tree()
            frame = tree.get("frame", {})
            w = int(frame.get("width", 390))
            h = int(frame.get("height", 844))
            self._cached_screen_size = (w, h)
        return self._cached_screen_size

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration: float = 0.3,
        post_delay: float = 0.5,
    ) -> None:
        """Perform a swipe gesture between two points."""
        self._axe(
            "swipe",
            "--start-x", str(start_x),
            "--start-y", str(start_y),
            "--end-x", str(end_x),
            "--end-y", str(end_y),
            "--duration", str(duration),
        )
        if post_delay > 0:
            time.sleep(post_delay)

    def swipe_right(self, y: int, distance: int = 130) -> None:
        """Swipe right at the given y coordinate."""
        w, _ = self.screen_size()
        start_x = w // 4
        self.swipe(start_x, y, start_x + distance, y)

    def swipe_left(self, y: int, distance: int = 130) -> None:
        """Swipe left at the given y coordinate."""
        w, _ = self.screen_size()
        start_x = (w * 3) // 4
        self.swipe(start_x, y, start_x - distance, y)

    def scroll_down(self, distance: int = 300) -> None:
        """Scroll down in the current view."""
        w, h = self.screen_size()
        cx = w // 2
        start_y = h // 2
        self.swipe(cx, start_y, cx, start_y - distance, duration=0.3)

    def scroll_up(self, distance: int = 300) -> None:
        """Scroll up in the current view."""
        w, h = self.screen_size()
        cx = w // 2
        start_y = h // 2
        self.swipe(cx, start_y, cx, start_y + distance, duration=0.3)

    def pull_to_refresh(self) -> None:
        """Pull-to-refresh: long downward swipe from near top of screen."""
        w, h = self.screen_size()
        cx = w // 2
        self.swipe(cx, h // 5, cx, (h * 3) // 4, duration=0.8, post_delay=1.5)

    # ------------------------------------------------------------------
    # Accessibility tree
    # ------------------------------------------------------------------

    def get_ui_tree(self) -> dict:
        """Return the full accessibility tree as a parsed dict."""
        result = self._axe("describe-ui")
        data = json.loads(result.stdout)
        # AXe returns a JSON array; unwrap to the root element
        return data[0] if isinstance(data, list) else data

    def _flatten_tree(self, node: dict) -> list[dict]:
        """Recursively flatten the accessibility tree into a list of nodes."""
        nodes = [node]
        for child in node.get("children", []):
            nodes.extend(self._flatten_tree(child))
        return nodes

    def _node_label(self, node: dict) -> str:
        """Return the display label for a node (AXLabel or AXValue, lowercased)."""
        return (node.get("AXLabel") or node.get("AXValue") or "").lower()

    def find_element_center(self, label: str) -> tuple[int, int] | None:
        """Find an element by accessibility label (case-insensitive, partial match).
        Returns (x, y) center coordinates or None if not found.
        """
        tree = self.get_ui_tree()
        nodes = self._flatten_tree(tree)
        label_lower = label.lower()
        for node in nodes:
            if label_lower in self._node_label(node):
                frame = node.get("frame", {})
                x = int(frame.get("x", 0) + frame.get("width", 0) / 2)
                y = int(frame.get("y", 0) + frame.get("height", 0) / 2)
                return (x, y)
        return None

    def element_exists(self, label: str) -> bool:
        """Return True if an element with the given label is in the UI tree."""
        return self.find_element_center(label) is not None

    def find_all_elements(self, label: str) -> list[dict]:
        """Return all nodes whose label contains the given string."""
        tree = self.get_ui_tree()
        nodes = self._flatten_tree(tree)
        label_lower = label.lower()
        return [n for n in nodes if label_lower in self._node_label(n)]

    def dump_labels(self) -> list[str]:
        """Return all non-empty labels in the UI tree (useful for debugging)."""
        tree = self.get_ui_tree()
        nodes = self._flatten_tree(tree)
        return [self._node_label(n) for n in nodes if self._node_label(n)]

    def describe_screen(self) -> str:
        """Return a human-readable summary of the current screen."""
        tree = self.get_ui_tree()
        nodes = self._flatten_tree(tree)
        lines = []
        for node in nodes:
            label = node.get("AXLabel") or ""
            value = node.get("AXValue") or ""
            role = node.get("AXRole") or node.get("role") or ""
            frame = node.get("frame", {})
            text = label or value
            if text:
                x = int(frame.get("x", 0) + frame.get("width", 0) / 2)
                y = int(frame.get("y", 0) + frame.get("height", 0) / 2)
                lines.append(f"  [{role}] \"{text}\" @ ({x}, {y})")
        return f"Screen elements ({len(lines)} with labels):\n" + "\n".join(lines)


# ======================================================================
# CLI interface
# ======================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="AXe-based iOS Simulator UI driver")
    parser.add_argument("--udid", required=True, help="Simulator UDID")
    sub = parser.add_subparsers(dest="command", required=True)

    # describe
    sub.add_parser("describe", help="Describe current UI screen")

    # tap
    tap_p = sub.add_parser("tap", help="Tap an element")
    tap_p.add_argument("--label", help="Accessibility label to tap")
    tap_p.add_argument("--x", type=int, help="X coordinate")
    tap_p.add_argument("--y", type=int, help="Y coordinate")

    # swipe
    swipe_p = sub.add_parser("swipe", help="Swipe gesture")
    swipe_p.add_argument("--direction", choices=["left", "right", "up", "down"], required=True)
    swipe_p.add_argument("--y", type=int, help="Y coordinate for horizontal swipes")
    swipe_p.add_argument("--x", type=int, help="X coordinate for vertical swipes")
    swipe_p.add_argument("--distance", type=int, default=130, help="Swipe distance in points")

    # refresh
    sub.add_parser("refresh", help="Pull to refresh")

    # find
    find_p = sub.add_parser("find", help="Find element by label")
    find_p.add_argument("--label", required=True)

    # exists
    exists_p = sub.add_parser("exists", help="Check if element exists")
    exists_p.add_argument("--label", required=True)

    # type-text
    type_p = sub.add_parser("type-text", help="Type text into focused field")
    type_p.add_argument("--text", required=True)

    # clear-and-type
    ct_p = sub.add_parser("clear-and-type", help="Clear field and type new text")
    ct_p.add_argument("--text", required=True)

    # scroll
    scroll_p = sub.add_parser("scroll", help="Scroll the view")
    scroll_p.add_argument("--direction", choices=["up", "down"], required=True)
    scroll_p.add_argument("--distance", type=int, default=300, help="Scroll distance in points")

    # dump-labels
    sub.add_parser("dump-labels", help="List all labels in the UI tree (debug)")

    # screen-size
    sub.add_parser("screen-size", help="Get screen dimensions")

    args = parser.parse_args()
    ui = UIDriver(args.udid)

    if args.command == "describe":
        print(ui.describe_screen())

    elif args.command == "tap":
        if args.label:
            try:
                ui.tap_label(args.label)
                center = ui.find_element_center(args.label)
                coords = f" at ({center[0]}, {center[1]})" if center else ""
                print(f"Tapped \"{args.label}\"{coords}")
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)
        elif args.x is not None and args.y is not None:
            ui.tap_xy(args.x, args.y)
            print(f"Tapped at ({args.x}, {args.y})")
        else:
            print("Provide --label or both --x and --y", file=sys.stderr)
            sys.exit(1)

    elif args.command == "swipe":
        w, h = ui.screen_size()
        if args.direction == "right":
            y = args.y or h // 2
            ui.swipe_right(y, args.distance)
            print(f"Swiped right at y={y}")
        elif args.direction == "left":
            y = args.y or h // 2
            ui.swipe_left(y, args.distance)
            print(f"Swiped left at y={y}")
        elif args.direction == "down":
            x = args.x or w // 2
            start_y = h // 4
            ui.swipe(x, start_y, x, start_y + args.distance, duration=0.5)
            print(f"Swiped down at x={x}")
        elif args.direction == "up":
            x = args.x or w // 2
            start_y = (h * 3) // 4
            ui.swipe(x, start_y, x, start_y - args.distance, duration=0.5)
            print(f"Swiped up at x={x}")

    elif args.command == "refresh":
        ui.pull_to_refresh()
        print("Pull-to-refresh complete")

    elif args.command == "find":
        center = ui.find_element_center(args.label)
        if center:
            print(f"Found \"{args.label}\" at ({center[0]}, {center[1]})")
        else:
            print(f"Element \"{args.label}\" not found", file=sys.stderr)
            sys.exit(1)

    elif args.command == "exists":
        if ui.element_exists(args.label):
            print(f"Element \"{args.label}\" exists")
        else:
            print(f"Element \"{args.label}\" not found")
            sys.exit(1)

    elif args.command == "type-text":
        ui.type_text(args.text)
        print(f"Typed \"{args.text}\"")

    elif args.command == "clear-and-type":
        ui.clear_and_type(args.text)
        print(f"Cleared and typed \"{args.text}\"")

    elif args.command == "scroll":
        if args.direction == "down":
            ui.scroll_down(args.distance)
            print(f"Scrolled down {args.distance}pt")
        else:
            ui.scroll_up(args.distance)
            print(f"Scrolled up {args.distance}pt")

    elif args.command == "dump-labels":
        labels = ui.dump_labels()
        for label in labels:
            print(label)

    elif args.command == "screen-size":
        w, h = ui.screen_size()
        print(f"{w}x{h}")


if __name__ == "__main__":
    main()
