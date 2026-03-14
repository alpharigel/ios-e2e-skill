# iOS E2E Skill

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin for end-to-end iOS app testing in the Simulator. Gives coding agents the ability to interact with, inspect, and verify iOS app behavior using accessibility-driven UI automation.

Currently powered by [AXe](https://github.com/cameroncooke/axe) — a fast, modern CLI that talks directly to the macOS Accessibility API.

## What it does

When installed, this plugin teaches Claude Code how to:

- **Inspect** the iOS Simulator UI via the accessibility tree
- **Interact** with your app — tap buttons, type text, swipe gestures, pull-to-refresh
- **Manage** the simulator lifecycle — boot, launch, terminate, relaunch, clear app data
- **Wait** for UI elements to appear before interacting
- **Screenshot** the simulator for visual verification

All interactions use accessibility-driven automation, which is more reliable than pixel-based approaches and survives UI layout changes.

## Prerequisites

- **macOS** with Xcode installed
- **AXe CLI**: `brew install cameroncooke/axe/axe`
- **Python 3.10+** (for helper scripts)
- A booted iOS Simulator with your app installed

## Installation

### Via Plugin Marketplace (recommended)

```
/plugin marketplace add alpharigel/claude-plugins
/plugin install ios-e2e-skill@alpharigel-tools
```

### Manual (per-project)

```bash
cd your-project
mkdir -p .claude/plugins
cd .claude/plugins
git clone https://github.com/alpharigel/ios-e2e-skill.git
```

### Manual (global)

```bash
mkdir -p ~/.claude/plugins
cd ~/.claude/plugins
git clone https://github.com/alpharigel/ios-e2e-skill.git
```

## Usage

Once installed, Claude Code automatically detects the skill when you ask about iOS simulator testing. Example prompts:

```
> Test that the login flow works on the simulator
> Tap the "Save" button and verify the success message appears
> Swipe right on the first item in the list
> Take a screenshot of the current screen
> What's on the simulator screen right now?
```

You can also invoke the skill directly with `/ios-e2e-skill:ios-e2e`.

### Helper Scripts

The plugin includes Python helper scripts that Claude Code invokes automatically:

- **`ui_driver.py`** — AXe wrapper for taps, swipes, text input, element search, and screen inspection
- **`sim_controller.py`** — Simulator lifecycle management (boot, launch, terminate, clear data, screenshots)
- **`wait_for.py`** — Polling utilities for waiting on UI elements

These scripts can also be imported as Python libraries in your own test code.

## Why AXe?

| Tool | Status | Issues |
|------|--------|--------|
| **AXe** | Actively maintained | None — Swift binary, works everywhere |
| Facebook idb | Unmaintained | Broken on Python 3.14+, requires daemon |
| Appium | Heavy | Requires server, complex setup |
| XCUITest | Xcode-only | Can't be driven by external tools |

AXe is a Swift CLI binary that talks directly to the Accessibility API. No Python version issues, no daemon, no complex setup.

## Key gotchas

These are non-obvious things we learned the hard way:

1. **`describe-ui` returns a JSON array** — always index `[0]` to get the root element
2. **Field names are prefixed** — `AXLabel` and `AXValue`, not `label` and `value`; children under `children`, not `AXChildren`
3. **`axe type` text is positional** — `axe type "hello"`, NOT `axe type --text "hello"`
4. **Tab bars may not be in the accessibility tree** — custom tab bars often need coordinate-based taps
5. **Apps don't always sync on launch** — pull-to-refresh may be needed to trigger a backend sync

## License

MIT
