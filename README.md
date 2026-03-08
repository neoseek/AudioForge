# AudioForge

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin that brings full audio DSP processing to SteamOS devices. Built on [DeckSP](https://github.com/jessebofill/DeckSP) and [JamesDSP for Linux](https://github.com/Audio4Linux/JDSP4Linux), AudioForge packages everything together with patches for reliable operation on SteamOS.

## Features

- **Parametric & Graphic EQ** — Fine-tune your audio with fully adjustable equalizer
- **Bass Boost** — Dynamic bass enhancement
- **Reverb** — Configurable room reverb effect
- **Compander** — Dynamic range compression/expansion
- **Tube Modeling** — Analog warmth simulation
- **Crossfeed** — Improved headphone stereo imaging
- **Stereo Wideness** — Adjustable stereo field width
- **Convolver** — Impulse response-based processing
- **ViPER DDC** — Device-specific correction from a built-in database
- **Limiter** — Output limiter for clipping prevention
- **LiveProg (EEL)** — Scriptable audio effects with parameter editing
- **Per-game Profiles** — Automatically switch DSP presets per game
- **Multi-user Support** — Separate settings for each Steam account

## What's Different from DeckSP

AudioForge ships a **patched JamesDSP flatpak** (`org.audioforge.jamesdsp`) that includes:

- **PipeWire loopback fix** — Prevents the audio feedback loop caused by JamesDSP's PipeWire loopback picking up its own output. The fix filters out loopback stream nodes that lack a `PW_KEY_APP_ID` (loopback streams never have one, real applications always do).
- **Improved hardware backend compatibility** — Better handling of different audio backends across SteamOS builds and hardware (Steam Deck, Legion Go, ROG Ally, etc.)
- **Automatic flatpak management** — The plugin installs, updates, and manages the JamesDSP flatpak automatically; no manual setup needed.

## Installation

### Prerequisites

- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) installed on your SteamOS device

### Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/neoseek/AudioForge/main/install.sh | bash
```

This downloads the latest release, extracts it to the Decky plugins directory, and restarts Decky Loader.

### Manual Install (from source)

```bash
git clone https://github.com/neoseek/AudioForge.git
cd AudioForge

# Install dependencies and build frontend
pnpm install
pnpm build

# Copy plugin files to Decky
sudo mkdir -p /home/deck/homebrew/plugins/AudioForge
sudo cp -r plugin.json main.py dist py_modules bin resources /home/deck/homebrew/plugins/AudioForge/

# Restart Decky Loader
sudo systemctl restart plugin_loader.service
```

> **Note:** Building from source requires `pnpm` and `node`. The flatpak bundle (`bin/jamesdsp.flatpak`) must be built separately — see the build section below.

## Building

### Frontend

```bash
pnpm install
pnpm build
```

### Patched JamesDSP Flatpak

Requires `flatpak-builder`:

```bash
flatpak run org.flatpak.Builder --user --repo=repo --force-clean build-dir org.audioforge.jamesdsp.yaml
flatpak build-bundle repo bin/jamesdsp.flatpak org.audioforge.jamesdsp
```

### Release Package

```bash
pnpm run package
```

This creates `out/AudioForge.zip` ready for distribution.

## Uninstallation

The plugin cleanly uninstalls the JamesDSP flatpak when removed through Decky Loader. To manually remove:

```bash
flatpak --user uninstall org.audioforge.jamesdsp
sudo rm -rf /home/deck/homebrew/plugins/AudioForge
sudo systemctl restart plugin_loader.service
```

## Troubleshooting

- **No audio effect:** Open the plugin in the Decky quick access menu, ensure JamesDSP is running (it starts automatically).
- **Audio feedback/echo:** You should not experience this with the patched JamesDSP. If you do, try `Force PW Relink` from the plugin menu.
- **Plugin not showing in Decky:** Verify files are in `/home/deck/homebrew/plugins/AudioForge/` and restart Decky (`sudo systemctl restart plugin_loader.service`).
- **JamesDSP logs:** Check `~/homebrew/plugins/AudioForge/log/jdsp/jdsp.log` for JamesDSP process output.

## Credits

- [DeckSP](https://github.com/jessebofill/DeckSP) by Jesse Bofill — Original Decky plugin for JamesDSP
- [JamesDSP for Linux](https://github.com/Audio4Linux/JDSP4Linux) by James Fung (ThePBone) — The DSP engine
- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) — Plugin framework for SteamOS

## License

Dual licensed:
- **GPL-3.0** — JamesDSP / DSP engine components
- **BSD-3-Clause** — Plugin framework code (Copyright 2025 Jesse Bofill, original Copyright 2022 Steam Deck Homebrew)

See [LICENSE](LICENSE) for full details.
