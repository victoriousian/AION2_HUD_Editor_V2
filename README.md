# AION2 HUD Editor & Dat Decoder ⚙️

[🇰🇷 한국어](README_ko.md) | [🇯🇵 日本語](README_ja.md) | [🇨🇳 简体中文](README_zh.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Unreal Engine](https://img.shields.io/badge/Unreal_Engine-5-black)

A standalone reverse-engineering tool to decode, preview, and edit the `DeviceSetting.dat` file for AION2. 
This tool bypasses the client's localized HUD restrictions, allowing you to freely copy, backup, and modify HUD layouts and Chat Tab settings across multiple characters—including a fail-safe mechanism for virtual ID assignment on unparsed headers.

*(Insert a 10-second GIF here demonstrating: Open .dat -> Select Character -> Copy Layout -> Save)*

## 📥 Quick Download
Don't want to compile from source? Download the pre-compiled standalone executable directly:
👉 **[Download AION2_HUD_Editor_V2.exe (v2.0)](https://github.com/victoriousian/AION2_HUD_Editor_V2/releases/tag/v2.0)**

## ⚠️ Disclaimer
This is an unofficial, community-driven reverse-engineering tool. Modifying client files (`.dat`) is done at your own risk. Always ensure you have a backup of your original settings. The tool automatically creates a `.bak` file upon saving.

## 🚀 Features
* **XOR & UTF-16LE/UTF-8 Decoding:** Completely unpacks the hybrid container structure of AION2's local save data.
* **Virtual ID Recovery:** Prevents silent data corruption (Silent Drop) by assigning `0xFF0000XX` virtual IDs to characters with shifted binary header offsets caused by client patches.
* **Visual HUD Preview:** Renders exact anchors and offsets of UI elements (Minimap, Chat, QuickSlots, etc.) in a scalable canvas.
* **Layout Cloning:** Copy HUD configurations and Chat Tabs from your main character to alt characters with a single click.
* **JSON Import/Export:** Extract raw JSON payloads for individual characters to share layouts with other players.

## 🛠️ Build from Source
If you prefer to build the executable yourself:

1. Clone the repository:
   ```bash
   git clone [https://github.com/victoriousian/AION2_HUD_Editor_V2.git](https://github.com/victoriousian/AION2_HUD_Editor_V2.git)
   cd AION2_HUD_Editor_V2

2. Install PyInstaller:
   ```bash
   pip install pyinstaller

3. Run the build script (Windows):
   ```bash
   build.bat
The executable will be generated in the dist/ folder.

## 📖 Usage
1. Launch AION2_HUD_Editor.exe.
2. Browse and select your DeviceSetting.dat file.
    - Default path: C:\Users\{Username}\AppData\Local\AION2\Saved\PersistentDownloadDir\UserSetting\DeviceSetting.dat
3. Click Open (Decode). The tool will parse the binary headers and JSON payloads.
4. If your main character's header offset has changed due to a patch, it will safely load under a Virtual ID (e.g., 0xFF000000). Select it from the dropdown.
5. Use the Copy Layout button to clone the setup to your other characters.
6. Click Save to DAT. A timestamped .bak file will be created automatically before overriding.

## 🤝 Support & Donate
If this tool saved you hours of setting up UI for your alts, consider supporting the continuous maintenance and reverse-engineering efforts for future client patches.

🎁 BTC Wallet: 1JADombahDcTHR4yNywfWKtckt7zKyNHwF

## 📝 License
Distributed under the MIT License. See LICENSE for more information.
