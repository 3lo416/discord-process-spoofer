# 🎮 Discord Process Spoofer & RPC Simulator

[![Release](https://img.shields.io/github/v/release/3lo416/discord-process-spoofer?color=brightgreen&label=Download%20.exe)](https://github.com/3lo416/discord-process-spoofer/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(64--bit)-lightgrey.svg)](https://www.microsoft.com/windows)
[![Discord IPC](https://img.shields.io/badge/Discord-Local%20IPC%20v1-7289DA.svg)](https://discord.com/developers/docs/rich-presence/how-to)
[![IGDB API](https://img.shields.io/badge/IGDB-API%20v4%20Integrated-9146FF.svg)](https://api-docs.igdb.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An advanced, dual-engine Windows utility designed to simulate game processes and inject custom **Discord Rich Presence (RPC)** in real time. Perfect for showcasing upcoming titles (like **Grand Theft Auto VI** and **EA SPORTS FC 27**), testing Discord game detection algorithms, or customizing your profile activity without running resource-heavy game engines.

---

### ⚡ Direct Download
👉 **[Download Latest Standalone Executable (`process_simulator.exe`)](https://github.com/3lo416/discord-process-spoofer/releases/latest)** *(No Python setup required)*

---

## 🌟 Key Highlights

- **⚡ Dual-Engine Architecture**: Operates via both a **Local Win32 Process Sandbox** (for native Discord scanner detection) and a direct **Discord Local IPC Named Pipe** (`\\.\pipe\discord-ipc-0`) for pixel-perfect Rich Presence.
- **👻 Silent Background Mode**: Spoofer worker processes run 100% silently in the background with hidden windows (`withdraw()`). No disruptive console popups or blank windows.
- **🛑 Bulletproof Stop & Clean Up**: Recursively tracks and terminates all worker processes and child PIDs via native Windows `taskkill /F /T /PID`, safely closing IPC pipes and resetting presence.
- **🎯 First-Class Game Presets**:
  - **Grand Theft Auto VI (GTA 6)**: Pre-calibrated with full-bleed, edge-to-edge artwork (`https://iili.io/nOgh0ox.png`) matching the exact visual size of verified titles like GTA V.
  - **EA SPORTS FC 27**: Seamlessly bridges Discord's game registry for unreleased entries.
- **🔍 Live IGDB API Integration**: Connects to the official Twitch / IGDB v4 database to search, preview, and import metadata and high-res cover art from over 300,000 video games.

---

## 📐 Architecture & How It Works

```
                                  +---------------------------+
                                  |   Process Simulator GUI   |
                                  |   (Tkinter Desktop App)   |
                                  +-------------+-------------+
                                                |
                       +------------------------+------------------------+
                       |                                                 |
                       v                                                 v
         [Engine 1: Local Sandbox]                          [Engine 2: Named Pipe IPC]
  +-------------------------------------+             +-------------------------------------+
  |   Spawn Silent Background Process   |             |   Connect to Discord Named Pipe     |
  |     - Custom Executable Name        |             |     - Path: \\.\pipe\discord-ipc-0  |
  |     - Hidden Window Handle (HWND)   |             |     - Handshake (Opcode 0)          |
  |     - Isolated Child PID Tracking   |             |     - SET_ACTIVITY Frame (Opcode 1) |
  +------------------+------------------+             +------------------+------------------+
                     |                                                   |
                     v                                                   v
         +-----------------------+                           +-----------------------+
         | Discord Process Scan  |                           |  Discord Local Client |
         |   (Native Detection)  |                           | (Rich Presence UI)    |
         +-----------------------+                           +-----------------------+
```

### 1. Engine 1: Local Process Sandbox
Discord's desktop client periodically calls Win32 APIs (`EnumProcesses`, `OpenProcess`, `GetModuleBaseName`) to detect running executables. Engine 1 launches a customized, lightweight Python worker masquerading as the target game's executable. By utilizing window state virtualization (`root.withdraw()`), the process registers in the OS process table without cluttering your desktop.

### 2. Engine 2: Native Discord Named Pipe IPC
For rich metadata (timestamps, party status, detail strings, custom large/small art), the app communicates directly with Discord's local IPC server (`\\.\pipe\discord-ipc-0` through `\\.\pipe\discord-ipc-9`). It transmits binary-framed JSON packets using Discord's standard handshake and activity framing:
- **Opcode 0 (Handshake)**: Authenticates client application ID.
- **Opcode 1 (Frame)**: Sends `SET_ACTIVITY` command containing state, details, timestamps, and CDN image assets.
- **Opcode 2 (Close)**: Gracefully terminates the session.

---

## 🎮 Game Presets & Calibrations

### Grand Theft Auto VI (GTA 6)
When rendering game icons in Discord's user popout, standard square cover art often appears shrunken or letterboxed compared to verified titles. This app features a **Full-Bleed 100% Width Asset** calibration:
- **Aspect Ratio**: 1:1 Edge-to-Edge full bleed.
- **Asset URL**: `https://iili.io/nOgh0ox.png`
- **Result**: Exactly matches the visual scale and padding of verified games like *Grand Theft Auto V*.

### EA SPORTS FC 27
Discord's cloud game registry often lacks executable definitions for upcoming iterations. The FC 27 preset provides both the Discord Application ID and automatic executable matching, enabling instant activity status.

---

## 🔍 Live IGDB API Integration

The application features a built-in search client for the **Internet Game Database (IGDB)**:
1. Navigate to the **IGDB Search** tab.
2. Enter your **Twitch Client ID** and **Client Secret** (obtained free from the [Twitch Developer Console](https://dev.twitch.tv/console)).
3. Search for any game across 300,000+ entries.
4. Preview title, release date, summary, and cover art.
5. Click **Apply to Presets** to automatically configure Discord RPC parameters.

---

## 🚀 Getting Started

### Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Python**: Version 3.10 or higher
- **Discord Desktop App**: Running on the same machine

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/3lo416/discord-process-spoofer.git
   cd discord-process-spoofer
   ```

2. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the application**:
   ```bash
   python process_simulator.py
   ```

---

## 🛠️ Building Standalone Executable (.exe)

You can compile the application into a standalone Windows executable that runs without Python installed.

### Method 1: Using the 1-Click Batch Script
Simply double-click:
```cmd
build.bat
```

### Method 2: Manual PyInstaller Build
Run the following command from the repository root:
```bash
pyinstaller --clean --noconfirm --onedir --windowed --name "process_simulator" process_simulator.py
```
The compiled executable will be placed in:
```
dist/process_simulator/process_simulator.exe
```

---

## 📖 User Guide

1. **Launch Discord**: Ensure Discord is open and running on your system.
2. **Open Process Spoofer**: Launch `process_simulator.exe`.
3. **Select or Configure Game**:
   - Choose a preset (**Grand Theft Auto VI**, **EA SPORTS FC 27**, **Grand Theft Auto V**, etc.) from the dropdown.
   - Or enter custom Details, State, and Asset keys.
4. **Click "Start Spoofing"**:
   - Engine 1 launches the silent background worker.
   - Engine 2 establishes the Discord IPC connection.
   - Your Discord profile will instantly display the game status.
5. **Click "Stop & Clean Up"**:
   - Instantly terminates all background workers and cleans up system resources.

---

## 📁 Repository Structure

```
discord-process-spoofer/
├── assets/
│   └── gta6_fullbleed.png       # Calibrated edge-to-edge artwork for GTA 6
├── .gitignore                   # Standard Git exclusions for Python & PyInstaller
├── LICENSE                      # MIT License
├── README.md                    # Comprehensive documentation
├── build.bat                    # 1-click Windows build script
├── process_simulator.py         # Main application source code
└── requirements.txt             # Python dependencies (Pillow, pefile, PyInstaller)
```

---

## ❓ Troubleshooting & FAQ

#### Q: Discord is not displaying the game status.
- Ensure Discord Desktop is running (web version does not support local named pipes).
- In Discord, go to **User Settings** -> **Activity Privacy** and make sure **"Display current activity as a status message"** is turned **ON**.
- If Discord was restarted, click **Stop & Clean Up** in the spoofer, then click **Start Spoofing** again to rebind the named pipe.

#### Q: The game window doesn't appear on screen.
- This is intentional! The spoofer runs in **Silent Background Mode** so it doesn't interrupt your work or gaming sessions. Check Task Manager to see the background worker.

#### Q: How do I completely terminate all spoofer processes?
- Simply click the **Stop & Clean Up** button inside the app. It executes recursive tree termination on all associated worker PIDs.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Developed with ❤️ by [3lo416](https://github.com/3lo416).
