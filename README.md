# -
C盘下载东西多了做了一个转移和整理的小工具，并且集合了鼠标右键菜单方便快速选择要整理的文件

文件转移工具 v2.0（完整版）

![image](https://github.com/user-attachments/assets/d6fa12ff-7262-40ec-b896-80af42bcee3a)
![image](https://github.com/user-attachments/assets/4aeee0df-5d92-438a-86ef-221773dae936)![image](https://github.com/user-attachments/assets/6aa67195-e651-41b4-828a-19a9a873b02f)
![image](https://github.com/user-attachments/assets/9a5706e8-920a-4720-a8dd-45ba870a37b8)![image](https://github.com/user-attachments/assets/4fb0adef-5bfe-46b7-aba9-63a143390597)



✅ 功能说明：
- 支持自动监控指定源文件夹，实时同步新增文件/文件夹；
- 支持文件分类整理（视频、图片、文档、音频、压缩包等）；
- 可根据文件扩展名自动分类移动到对应文件夹；
- 提供“预览模式”和“正式同步”两种方式；
- 支持限制文件名长度、防止名称冲突、支持断点重试；
- 支持系统托盘运行、右键菜单调用、日志记录功能；
- 支持中文 / 英文分类名自动切换；
- 支持右键参数启动同步或整理（通过 Inno Setup 注册菜单）；

📂 安装方式：
下载压缩包后解压，运行 `文件转移工具 2.0_Setup.exe` 进行安装。

📎 注意事项：
- 打包使用 PyQt5 + watchdog + Inno Setup；
- Windows 10/11 测试通过；
- 请勿选择根目录（如 `C:\`）作为同步或整理路径，程序会自动拦截。

🛠 日志路径：
`我的文档\文件转移工具日志\file_mover.log`

---

欢迎反馈使用建议或提出功能需求 🙌

# 📂 File Mover v2.0

A lightweight and practical file transfer and organization tool for Windows, designed for users who frequently download content and need to organize or relocate files efficiently.

---

## ✨ Features

- 📁 Monitor a source folder and move files in real time to the target directory
- 🧠 Multithreaded transfer with file stability checking and retry mechanism
- 📦 Organize files by category: Videos, Documents, Images, Archives, Audio, Folders
- 📂 Supports folder structure preservation when moving
- 🖱️ Optional Windows right-click menu for quick operations
- 🚀 Built-in preview mode to simulate file organization
- 🧾 Logs activity to `Documents/文件转移工具日志/file_mover.log`
- 🧮 Supports both Chinese and English folder naming
- 📦 Includes Inno Setup script to generate installer

---

## 📥 Installation

1. Download the latest release from [Releases](https://github.com/sorry123luck/-/releases/tag/v2.0))
2. Run `FileMover_文件转移工具_v2.0.exe` to install
3. Optionally, use the batch scripts to register context menus

---

## 🖱️ Context Menu (Right-click) Setup

To add right-click support:

```bash
register_context_menu.bat
unregister_context_menu.bat
