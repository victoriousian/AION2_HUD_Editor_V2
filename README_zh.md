# AION2 HUD 编辑器 & Dat 解码器 ⚙️

[🇺🇸 English](README.md) | [🇰🇷 한국어](README_ko.md) | [🇯🇵 日本語](README_ja.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Unreal Engine](https://img.shields.io/badge/Unreal_Engine-5-black)

一个独立的逆向工程工具，用于解码、预览和编辑 AION2 的 `DeviceSetting.dat` 文件。
该工具绕过客户端本地 HUD 的限制，允许您在多个角色之间自由复制、备份和修改 HUD 布局与聊天选项卡设置。针对因客户端更新导致标头无法解析的情况，内置了分配虚拟 ID (Virtual ID) 的故障保护机制。

*(在此处插入 10 秒的演示 GIF: 打开 .dat -> 选择角色 -> 复制布局 -> 保存)*

## 📥 快速下载
不想从源代码编译？您可以直接下载预编译的独立可执行文件：
👉 **[下载 AION2_HUD_Editor_V2.exe (v2.0)](https://github.com/victoriousian/AION2_HUD_Editor_V2/releases/tag/v2.0)**

## ⚠️ 免责声明
这是一个非官方的、由社区驱动的逆向工程工具。修改客户端文件（`.dat`）的风险由您自行承担。请务必备份您的原始设置。工具在保存时会自动生成一个 `.bak` 备份文件。

## 🚀 主要功能
* **XOR & UTF-16LE/UTF-8 解码:** 完全解包 AION2 本地保存数据的混合容器结构。
* **虚拟 ID 恢复:** 针对客户端补丁导致二进制标头偏移变化的情况，为未识别的数据块分配 `0xFF0000XX` 虚拟 ID，彻底防止数据静默损坏 (Silent Drop)。
* **可视化 HUD 预览:** 在可缩放的画布上精准渲染 UI 元素（小地图、聊天框、快捷栏等）的锚点和偏移量。
* **布局克隆:** 一键将主角色的 HUD 配置和聊天选项卡设置复制到其他小号上。
* **JSON 导入/导出:** 提取单个角色的原始 JSON 数据，方便与其他玩家共享布局。

## 🛠️ 从源码构建
如果您更喜欢自己编译可执行文件，请按照以下步骤操作：

1. 克隆仓库:
   ```bash
   git clone https://github.com/victoriousian/AION2_HUD_Editor_V2.git
   cd AION2_HUD_Editor_V2
   ```
2. 安装 PyInstaller:
   ```bash
   pip install pyinstaller
   ```
3. 运行构建脚本 (Windows):
   ```bash
   build.bat
   ```
   *可执行文件将生成在 `dist/` 文件夹中。*

## 📖 使用说明
1. 运行 `AION2_HUD_Editor.exe`。
2. 浏览并选择您的 `DeviceSetting.dat` 文件。
    * *默认路径: `C:\Users\{用户名}\AppData\Local\AION2\Saved\PersistentDownloadDir\UserSetting\DeviceSetting.dat`*
3. 点击 **Open (Decode)**。工具将解析二进制标头和 JSON 数据。
4. 如果主角色的标头偏移量因补丁而发生改变，它将安全地加载为一个虚拟 ID（例如 `0xFF000000`）。请在下拉菜单中选择它。
5. 使用 **Copy Layout** 按钮将设置克隆给其他角色。
6. 点击 **Save to DAT**。在覆盖文件之前，将自动创建一个带有时间戳的 `.bak` 备份文件。

## 🤝 支持与捐赠
如果这个工具为您节省了大量为小号设置 UI 的时间，请考虑支持我们，以便在未来的客户端更新中继续进行维护和逆向工程工作。

🎁 **BTC 钱包地址:** `1JADombahDcTHR4yNywfWKtckt7zKyNHwF`

## 📝 许可证
本项目采用 MIT 许可证进行分发。有关详细信息，请参阅 `LICENSE` 文件。
