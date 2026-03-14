---
name: ios-e2e
description: End-to-end iOS app testing in the Simulator. Use when the user asks to test iOS UI, interact with the simulator, verify app behavior, inspect accessibility trees, take screenshots, or automate swipe/tap/type gestures.
---

# iOS Simulator Testing with AXe

Build, test, and automate iOS applications running in the Simulator using [AXe](https://github.com/nicklama/axe) — a fast, modern CLI for accessibility-based UI automation.

## Why AXe

AXe is a Swift CLI binary that talks directly to the Accessibility API. No Python version issues, no daemon, no Facebook idb dependency. Install with:

```bash
brew install cameroncooke/axe/axe
```

## Prerequisites

Before testing, ensure:
1. **Xcode** is installed with iOS Simulator runtimes
2. **AXe** is installed (`axe --version`)
3. A simulator is **booted** (`xcrun simctl boot "iPhone 16 Pro"`)
4. Your app is **built and installed** on the simulator

## Finding the Simulator UDID

```bash
# List booted simulators
xcrun simctl list devices booted

# List all available simulators
xcrun simctl list devices available
```

Store the UDID for use in all subsequent commands.

## Core AXe Commands

### Inspect the UI (Accessibility Tree)

```bash
axe describe-ui --udid <UDID>
```

Returns a **JSON array** — always unwrap with `[0]` to get the root element.

**Key JSON fields:**
- `AXLabel` — the element's accessibility label (NOT `label`)
- `AXValue` — the element's current value (NOT `value`)
- `children` — child elements (NOT `AXChildren`)
- `frame` — `{x, y, width, height}` in points

### Tap

```bash
# By accessibility label
axe tap --label "Save" --udid <UDID>

# By coordinates (points)
axe tap -x 200 -y 400 --udid <UDID>
```

### Swipe

```bash
axe swipe --start-x 100 --start-y 400 --end-x 300 --end-y 400 --duration 0.3 --udid <UDID>
```

Common patterns:
- **Swipe right**: `start-x` < `end-x` (same y)
- **Swipe left**: `start-x` > `end-x` (same y)
- **Pull to refresh**: long downward swipe from top, `--duration 0.8`

### Type Text

```bash
# IMPORTANT: text is a POSITIONAL argument, NOT --text
axe type "Hello world" --udid <UDID>
```

### Press Keys

```bash
# By HID usage code
axe key 40 --udid <UDID>    # Return/Enter (0x28)
axe key 42 --udid <UDID>    # Delete/Backspace (0x2A)

# Hardware buttons
axe button home --udid <UDID>
```

### Common HID Key Codes

| Key | Code | Hex |
|-----|------|-----|
| Return/Enter | 40 | 0x28 |
| Escape | 41 | 0x29 |
| Delete/Backspace | 42 | 0x2A |
| Tab | 43 | 0x2B |
| Space | 44 | 0x2C |
| Arrow Right | 79 | 0x4F |
| Arrow Left | 80 | 0x50 |
| Arrow Down | 81 | 0x51 |
| Arrow Up | 82 | 0x52 |

Key combinations use `+` syntax: `axe key "224+4" --udid <UDID>` (Cmd+A / Select All)

## Simulator Management (xcrun simctl)

```bash
# Boot
xcrun simctl boot <UDID>

# Launch app
xcrun simctl launch <UDID> com.example.app

# Terminate app
xcrun simctl terminate <UDID> com.example.app

# Install app
xcrun simctl install <UDID> /path/to/App.app

# Screenshot
xcrun simctl io <UDID> screenshot /tmp/screenshot.png

# Open Simulator.app window
open -a Simulator

# Clear app data (get container, then delete files)
xcrun simctl get_app_container <UDID> com.example.app data
# Then delete files in Library/Application Support/ or relevant paths

# Push notification
xcrun simctl push <UDID> com.example.app /path/to/payload.json
```

## Helper Scripts

This skill includes Python helper scripts in `${CLAUDE_SKILL_DIR}/scripts/` for more complex operations. They require Python 3.10+ and no external dependencies.

### ui_driver.py — AXe Wrapper

Provides a `UIDriver` class for programmatic UI automation:

```bash
# Describe current UI as formatted text
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py describe --udid <UDID>

# Tap by label
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py tap --label "Save" --udid <UDID>

# Tap by coordinates
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py tap --x 200 --y 400 --udid <UDID>

# Swipe right (e.g. to complete an item)
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py swipe --direction right --y 400 --udid <UDID>

# Swipe left (e.g. to dismiss or skip)
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py swipe --direction left --y 400 --udid <UDID>

# Pull to refresh
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py refresh --udid <UDID>

# Scroll down/up
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py scroll --direction down --udid <UDID>
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py scroll --direction up --distance 500 --udid <UDID>

# Find an element by label (returns coordinates)
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py find --label "Submit" --udid <UDID>

# Check if element exists
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py exists --label "Error" --udid <UDID>

# Type text into focused field
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py type-text --text "hello" --udid <UDID>

# Clear field and type new text
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py clear-and-type --text "new value" --udid <UDID>

# Dump all labels in the UI tree (useful for debugging)
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py dump-labels --udid <UDID>

# Get screen size
python3 ${CLAUDE_SKILL_DIR}/scripts/ui_driver.py screen-size --udid <UDID>
```

**Note:** `tap --label` automatically falls back to coordinate-based tapping if AXe's native label tap fails.

### sim_controller.py — Simulator Lifecycle

Provides a `SimController` class for app lifecycle management:

```bash
# Launch app
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py launch --bundle-id com.example.app --udid <UDID>

# Terminate app
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py terminate --bundle-id com.example.app --udid <UDID>

# Relaunch (terminate + launch)
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py relaunch --bundle-id com.example.app --udid <UDID>

# Screenshot
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py screenshot --path /tmp/screenshot.png --udid <UDID>

# Clear all app data (uninstall/reinstall — also wipes UserDefaults)
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py clear-data --bundle-id com.example.app --udid <UDID>

# Clear data with explicit app path for reinstall
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py clear-data --bundle-id com.example.app --app-path /path/to/App.app --udid <UDID>

# Read app debug log from container
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py get-log --filename debug.log --bundle-id com.example.app --udid <UDID>

# Boot simulator (if not already booted)
python3 ${CLAUDE_SKILL_DIR}/scripts/sim_controller.py boot --udid <UDID>
```

### wait_for.py — Polling Utilities

Wait for UI elements to appear or disappear before interacting:

```bash
# Wait for element to appear (default 8s timeout)
python3 ${CLAUDE_SKILL_DIR}/scripts/wait_for.py element --label "Welcome" --udid <UDID>

# Wait with custom timeout
python3 ${CLAUDE_SKILL_DIR}/scripts/wait_for.py element --label "Loaded" --timeout 15 --udid <UDID>

# Wait for element to disappear (e.g. loading spinner)
python3 ${CLAUDE_SKILL_DIR}/scripts/wait_for.py gone --label "Loading..." --udid <UDID>
```

## Testing Workflow

A typical interactive testing session:

1. **Boot & launch**: Boot the simulator, install and launch your app
2. **Inspect**: Run `axe describe-ui` to see what's on screen
3. **Interact**: Tap buttons, type text, swipe — verify each step
4. **Screenshot**: Capture screenshots to verify visual state
5. **Repeat**: Navigate through flows, checking state at each step

## Common Gotchas

1. **AXe returns a JSON array** — `describe-ui` output is `[{...}]`, not `{...}`. Always index `[0]`.
2. **Field names are prefixed** — `AXLabel` and `AXValue`, not `label` and `value`. Children are under `children`, not `AXChildren`.
3. **`axe type` text is positional** — `axe type "hello" --udid X`, NOT `axe type --text "hello" --udid X`.
4. **Tab bars may not be in the accessibility tree** — some custom tab bars require coordinate-based taps instead of label-based.
5. **Apps don't always sync on launch** — if your app uses server-side data, you may need to pull-to-refresh after launch to trigger a sync.
6. **Wait before asserting** — UI updates are async. Use the `wait_for.py` script or add short delays after interactions.
7. **Terminate before data setup** — if your app has background sync, terminate it before writing test data to the backend to avoid database lock contention.
8. **UserDefaults persists outside the app container** — deleting container files won't clear UserDefaults on the simulator. Use uninstall/reinstall (`clear-data` command) for a true clean slate.
9. **Multiple elements with same label** — buttons and headings often share labels (e.g. "Create Account"). Use `find_all_elements()` and pick the right match (usually the last one is the button).
