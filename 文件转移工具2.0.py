import os
import shutil
import time
import logging
import threading
import concurrent.futures
import sys
import re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtNetwork import QLocalSocket, QLocalServer

# 获取资源路径（兼容 PyInstaller 打包）
def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

# 图标路径（打包时通过 --add-data 包含 icons/app_icon.ico）
icon_path = resource_path("icons/app_icon.ico")

# 设置日志保存位置（文档目录）
log_folder = os.path.join(os.path.expanduser('~'), 'Documents', '文件转移工具日志')
os.makedirs(log_folder, exist_ok=True)
log_file_path = os.path.join(log_folder, 'file_mover.log')

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    filename=log_file_path, filemode='a')

# 全局参数
source_folder = ""
target_folder = ""
max_filename_length = 90
stability_check_interval = 2  # seconds
stability_check_attempts = 3
retry_delay = 3
retry_attempts = 3

stop_event = threading.Event()
allowed_extensions = []
all_files_selected = True
folders_selected = True

file_type_map = {
    '音频文件': ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a'],
    '图片文件': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.heic'],
    '视频文件': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
    '压缩文件': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
}
def ensure_directory_exists(path):
    if os.path.isfile(path):
        logging.warning(f"路径已存在为文件，不能创建目录：{path}")
        return
    if not os.path.exists(path):
        os.makedirs(path)

def is_temporary_file(file_path):
    return file_path.endswith('.tmp') or file_path.endswith('.crdownload')

def is_file_stable(file_path):
    if is_temporary_file(file_path):
        logging.info(f"跳过临时文件: {file_path}")
        return False
    try:
        for _ in range(stability_check_attempts):
            initial_size = os.path.getsize(file_path)
            time.sleep(stability_check_interval)
            current_size = os.path.getsize(file_path)
            if initial_size != current_size:
                return False
        return True
    except FileNotFoundError:
        logging.error(f"稳定性检测时找不到文件: {file_path}")
        return False
    except Exception as e:
        logging.error(f"文件稳定性检测异常: {file_path}, 错误: {e}")
        return False

def sanitize_filename(filename):
    base, ext = os.path.splitext(filename)
    if len(base) > max_filename_length:
        base = base[:max_filename_length]
    return f"{base}{ext}"

def truncate_path(path):
    base, ext = os.path.splitext(path)
    if len(base) > max_filename_length - len(ext):
        base = base[:max_filename_length - len(ext)]
    return f"{base}{ext}"

def resolve_name_conflict(dest_path):
    base, ext = os.path.splitext(dest_path)
    counter = 1
    while os.path.exists(dest_path):
        truncated_base = base[:max_filename_length - len(ext) - len(f"_{counter}")]
        dest_path = f"{truncated_base}_{counter}{ext}"
        counter += 1
    return dest_path

def is_allowed_file(file_path):
    if all_files_selected:
        return True
    if os.path.isdir(file_path):
        return folders_selected
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    return ext in allowed_extensions

def move_with_structure(source_path, dest_root):
    if not os.path.exists(source_path):
        logging.error(f"源路径不存在: {source_path}")
        return
    if not is_allowed_file(source_path):
        return

    relative_path = os.path.relpath(source_path, source_folder)
    sanitized_relative_path = sanitize_filename(relative_path)
    dest_path = os.path.join(dest_root, sanitized_relative_path)
    dest_path = truncate_path(dest_path)

    if os.path.isdir(source_path):
        ensure_directory_exists(dest_path)
        try:
            items = os.listdir(source_path)
        except FileNotFoundError:
            logging.warning(f"目录已不存在，跳过: {source_path}")
            return

        for item in items:
            move_with_structure(os.path.join(source_path, item), dest_root)
        if not os.listdir(source_path):
            os.rmdir(source_path)
            logging.info(f"已删除空目录: {source_path}")
    elif os.path.isfile(source_path):
        if not is_file_stable(source_path):
            return
        dest_path = resolve_name_conflict(dest_path)
        ensure_directory_exists(os.path.dirname(dest_path))
        retry_count = 0
        while retry_count < retry_attempts:
            try:
                shutil.move(source_path, dest_path)
                logging.info(f"已转移文件: {source_path} -> {dest_path}")
                break
            except Exception as e:
                retry_count += 1
                logging.warning(f"转移失败 {retry_count} 次: {e}")
                time.sleep(retry_delay * (2 ** retry_count))
def get_optimal_thread_count():
    return os.cpu_count() or 4

def move_files_in_batch(source_paths, dest_root):
    for source_path in source_paths:
        if stop_event.is_set():
            break
        move_with_structure(source_path, dest_root)

def move_with_structure_multithreaded(source_paths, dest_root):
    thread_count = get_optimal_thread_count()
    logging.info(f"使用 {thread_count} 个线程进行批量转移")
    chunk_size = max(1, len(source_paths) // thread_count)
    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        chunks = [source_paths[i:i + chunk_size] for i in range(0, len(source_paths), chunk_size)]
        futures = [executor.submit(move_files_in_batch, chunk, dest_root) for chunk in chunks]
        concurrent.futures.wait(futures)

class FileEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if stop_event.is_set():
            return
        if not event.is_directory:
            if is_file_stable(event.src_path):
                move_with_structure(event.src_path, target_folder)
        else:
            if os.path.exists(event.src_path):
                move_with_structure(event.src_path, target_folder)

def scan_existing_files():
    logging.info("启动时扫描现有文件...")
    all_files = [os.path.join(root, file)
                 for root, _, files in os.walk(source_folder)
                 for file in files]
    all_dirs = [os.path.join(root, dir)
                for root, dirs, _ in os.walk(source_folder)
                for dir in dirs]
    move_with_structure_multithreaded(all_dirs + all_files, target_folder)

def start_monitoring():
    event_handler = FileEventHandler()
    observer = Observer()
    observer.schedule(event_handler, source_folder, recursive=True)
    observer.start()
    logging.info("文件监控已开启...")
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
    observer.stop()
    observer.join()
    logging.info("文件监控已停止")

def organize_target_folder(window=None, preview=None):
    global target_folder
    app = QtWidgets.QApplication.instance()
    lang = 'zh'

    if window is None:
        for w in app.topLevelWidgets():
            if isinstance(w, FileMoverApp):
                window = w
                break

    if window:
        target_folder = window.target_input.text()
        if preview is None:  # 默认从 UI 获取
            preview = window.preview_checkbox.isChecked()
        if window.language_selector.currentText() == 'English':
            lang = 'en'

    if not target_folder or not os.path.isdir(target_folder):
        QtWidgets.QMessageBox.warning(None, "错误", f"❌ 未设置有效的目标文件夹：\n[{target_folder}]")
        logging.error(f"❌ 未设置有效的目标文件夹：[{target_folder}]")
        return

    # 分类后缀
    video_ext = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
    image_ext = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.svg', '.heic']
    archive_ext = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
    doc_ext = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.rtf']
    audio_ext = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a']

    folder_names = {
        'zh': {'video': '视频素材', 'image': '图片素材', 'archive': '压缩文件', 'document': '文档文件', 'audio': '音频文件', 'folder': '文件夹', 'other': '杂'},
        'en': {'video': 'Videos', 'image': 'Images', 'archive': 'Archives', 'document': 'Documents', 'audio': 'Audio', 'folder': 'Folders', 'other': 'Others'}
    }

    name = lambda k: folder_names[lang][k]
    paths = {k: os.path.join(target_folder, name(k)) for k in folder_names[lang]}
    reserved = list(folder_names[lang].values())
    stats = {k: 0 for k in paths}

    # 整理前统计（预览/正式都用）
    move_plan = []

    for item in os.listdir(target_folder):
        item_path = os.path.join(target_folder, item)
        if os.path.isdir(item_path) and item not in reserved:
            dest_path = os.path.join(paths['folder'], item)
            stats['folder'] += 1
            move_plan.append((item_path, dest_path, 'folder'))

    for item in os.listdir(target_folder):
        item_path = os.path.join(target_folder, item)
        if os.path.isfile(item_path):
            _, ext = os.path.splitext(item)
            ext = ext.lower()
            if ext in video_ext:
                cat = 'video'
            elif ext in image_ext:
                cat = 'image'
            elif ext in archive_ext:
                cat = 'archive'
            elif ext in doc_ext:
                cat = 'document'
            elif ext in audio_ext:
                cat = 'audio'
            else:
                cat = 'other'
            dest_path = os.path.join(paths[cat], sanitize_filename(item))
            stats[cat] += 1
            move_plan.append((item_path, dest_path, 'file'))

    # 生成汇总信息
    total = sum(stats.values())
    label_map = folder_names[lang]
    lines = [f"整理{'预览' if preview else '完成'}，共{'识别' if preview else '处理'} {total} 个项目："]
    for k, v in stats.items():
        lines.append(f"- {label_map[k]}：{v} 个")
    summary = '\n'.join(lines)

    if preview:
        # 弹出预览确认框
        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("整理预览")
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setText(summary)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msg_box.button(QtWidgets.QMessageBox.Ok).setText("开始")
        msg_box.button(QtWidgets.QMessageBox.Cancel).setText("取消")
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)
        result = msg_box.exec_()
        if result != QtWidgets.QMessageBox.Ok:
            logging.info("用户取消了整理操作（预览模式下）")
            return

    # 正式执行整理
    for key in paths:
        ensure_directory_exists(paths[key])
    for src, dst, typ in move_plan:
        try:
            shutil.move(src, dst)
            logging.info(f"Moved {typ}: {src} -> {dst}")
        except Exception as e:
            logging.error(f"整理失败: {src} -> {dst}, 错误: {e}")

    # 完成提示
    final_msg = QtWidgets.QMessageBox()
    final_msg.setWindowTitle("整理完成")
    final_msg.setIcon(QtWidgets.QMessageBox.Information)
    final_msg.setText(summary)
    final_msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    final_msg.exec_()

    # 托盘通知
    if tray_icon:
        tray_icon.showMessage(
            "📂 整理完成",
            f"已完成整理，共 {total} 项",
            QtWidgets.QSystemTrayIcon.Information,
            5000
        )

    logging.info(summary)


def scan_existing_files():
    logging.info("启动时扫描现有文件...")
    all_files = [os.path.join(root, file)
                 for root, _, files in os.walk(source_folder)
                 for file in files]
    all_dirs = [os.path.join(root, dir)
                for root, dirs, _ in os.walk(source_folder)
                for dir in dirs]
    move_with_structure_multithreaded(all_dirs + all_files, target_folder)

    # 🔔 托盘通知
    if tray_icon:
        total = len(all_dirs + all_files)
        tray_icon.showMessage(
            "✅ 同步完成",
            f"共转移 {total} 项文件/文件夹",
            QtWidgets.QSystemTrayIcon.Information,
            5000
        )


class FileMoverApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # UI 初始化结尾加入监控定时器
        self.input_monitor_timer = QTimer()
        self.input_monitor_timer.timeout.connect(self.monitor_inputs)
        self.input_monitor_timer.start(5000)    

    def initUI(self):
        self.setWindowTitle("文件转移工具")
        layout = QtWidgets.QVBoxLayout()

        # 文件类型选择（横向一排）
        file_type_layout = QtWidgets.QHBoxLayout()
        self.checkboxes = {}

        self.all_files_checkbox = QtWidgets.QCheckBox("所有文件")
        self.all_files_checkbox.setChecked(True)
        self.all_files_checkbox.stateChanged.connect(self.on_file_type_changed)
        file_type_layout.addWidget(self.all_files_checkbox)

        for label in ['音频文件', '图片文件', '视频文件', '压缩文件', '文件夹']:
            cb = QtWidgets.QCheckBox(label)
            cb.stateChanged.connect(self.on_file_type_changed)
            self.checkboxes[label] = cb
            file_type_layout.addWidget(cb)

        layout.addLayout(file_type_layout)

        # 最大长度 + 语言选择（同一行）
        setting_row = QtWidgets.QHBoxLayout()

        self.filename_length_label = QtWidgets.QLabel("转移后文件名长度（30-255）：")
        self.filename_length_input = QtWidgets.QSpinBox()
        self.filename_length_input.setRange(30, 255)
        self.filename_length_input.setValue(max_filename_length)
        self.filename_length_input.setToolTip("限制移动文件时的文件名长度")

        language_label = QtWidgets.QLabel("分类文件夹语言：")
        self.language_selector = QtWidgets.QComboBox()
        self.language_selector.addItems(["中文", "English"])
        self.language_selector.setCurrentIndex(0)

        setting_row.addWidget(self.filename_length_label)
        setting_row.addWidget(self.filename_length_input)
        setting_row.addSpacing(20)
        setting_row.addWidget(language_label)
        setting_row.addWidget(self.language_selector)

        layout.addLayout(setting_row)

        # 源文件夹
        self.source_label = QtWidgets.QLabel("源文件夹:")
        self.source_input = QtWidgets.QLineEdit()
        self.source_browse_button = QtWidgets.QPushButton("...")
        self.source_browse_button.clicked.connect(self.browse_source_folder)
        source_layout = QtWidgets.QHBoxLayout()
        source_layout.addWidget(self.source_label)
        source_layout.addWidget(self.source_input)
        source_layout.addWidget(self.source_browse_button)
        layout.addLayout(source_layout)

        # 目标文件夹
        self.target_label = QtWidgets.QLabel("目标文件夹:")
        self.target_input = QtWidgets.QLineEdit()
        self.target_browse_button = QtWidgets.QPushButton("...")
        self.target_browse_button.clicked.connect(self.browse_target_folder)
        target_layout = QtWidgets.QHBoxLayout()
        target_layout.addWidget(self.target_label)
        target_layout.addWidget(self.target_input)
        target_layout.addWidget(self.target_browse_button)
        layout.addLayout(target_layout)

        # 稳定性设置
        self.stability_interval_label = QtWidgets.QLabel("稳定性检查间隔(秒):")
        self.stability_interval_input = QtWidgets.QSpinBox()
        self.stability_interval_input.setValue(stability_check_interval)

        self.stability_attempts_label = QtWidgets.QLabel("检查次数:")
        self.stability_attempts_input = QtWidgets.QSpinBox()
        self.stability_attempts_input.setValue(stability_check_attempts)

        advanced_layout = QtWidgets.QHBoxLayout()
        advanced_layout.addWidget(self.stability_interval_label)
        advanced_layout.addWidget(self.stability_interval_input)
        advanced_layout.addWidget(self.stability_attempts_label)
        advanced_layout.addWidget(self.stability_attempts_input)
        layout.addLayout(advanced_layout)

        # 整理按钮 + 预览复选框 + 控制按钮（横向一排）
        button_layout = QtWidgets.QHBoxLayout()

        # 整理预览模式复选框
        self.preview_checkbox = QtWidgets.QCheckBox("预览模式")
        self.preview_checkbox.setChecked(True)
        button_layout.addWidget(self.preview_checkbox)

        # 整理按钮
        self.organize_button = QtWidgets.QPushButton("整理目标文件夹")
        self.organize_button.clicked.connect(lambda: organize_target_folder(self))
        button_layout.addWidget(self.organize_button)

        # 开始同步按钮
        self.start_button = QtWidgets.QPushButton("开始同步")
        self.start_button.clicked.connect(self.start_sync)
        button_layout.addWidget(self.start_button)

        # 停止运行按钮
        self.stop_button = QtWidgets.QPushButton("停止运行")
        self.stop_button.clicked.connect(self.stop_sync)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)


        self.setLayout(layout)
        

    def monitor_inputs(self):
        source = self.source_input.text().strip()
        target = self.target_input.text().strip()

        if source:
            logging.info(f"[输入监控] 源文件夹输入框：{source}")
        else:
            logging.warning("[输入监控] 源文件夹为空！")

        if target:
            logging.info(f"[输入监控] 目标文件夹输入框：{target}")
        else:
            logging.warning("[输入监控] 目标文件夹为空！")

    def closeEvent(self, event):  
        event.ignore()
        self.hide()
        if tray_icon:
            tray_icon.showMessage(
                "程序后台运行中",
                "文件转移工具已最小化至托盘，点击托盘图标可恢复窗口",
                QtWidgets.QSystemTrayIcon.Information,
                4000
            )

    def browse_source_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if folder:
            self.source_input.setText(folder)
            logging.info(f"[用户选择] 源文件夹：{folder}")

    def browse_target_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if folder:
            self.target_input.setText(folder)
            logging.info(f"[用户选择] 目标文件夹：{folder}")

    def on_file_type_changed(self):
        global allowed_extensions, all_files_selected, folders_selected
        all_files_selected = self.all_files_checkbox.isChecked()
        folders_selected = self.checkboxes['文件夹'].isChecked()
        allowed_extensions = []

        if not all_files_selected:
            for label, cb in self.checkboxes.items():
                if cb.isChecked() and label in file_type_map:
                    allowed_extensions.extend(file_type_map[label])
    def run_transfer_preview(self):
        global source_folder, allowed_extensions, all_files_selected, folders_selected

        source_folder = self.source_input.text()
        if not source_folder or not os.path.exists(source_folder):
            QtWidgets.QMessageBox.warning(self, "错误", "未设置有效的源文件夹")
            return False

        # 构建分类统计
        stats = {
            '音频文件': 0, '图片文件': 0, '视频文件': 0, '压缩文件': 0, '文件夹': 0, '其他': 0
        }

        for root, dirs, files in os.walk(source_folder):
            for file in files:
                path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                ext = ext.lower()

                matched = False
                for label, exts in file_type_map.items():
                    if ext in exts:
                        if all_files_selected or ext in allowed_extensions:
                            stats[label] += 1
                            matched = True
                        break
                if not matched and all_files_selected:
                    stats['其他'] += 1

            if folders_selected:
                for d in dirs:
                    stats['文件夹'] += 1

        total = sum(stats.values())
        lines = [f"将从源文件夹转移：共识别 {total} 项"]
        for k, v in stats.items():
            if v > 0:
                lines.append(f"- {k}: {v} 个")

        summary = "\n".join(lines)
        msg_box = QtWidgets.QMessageBox()
        msg_box.setWindowTitle("预览转移内容")
        msg_box.setIcon(QtWidgets.QMessageBox.Information)
        msg_box.setText(summary)
        msg_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowStaysOnTopHint)

        start_button = msg_box.button(QtWidgets.QMessageBox.Ok)
        start_button.setText("开始")
        cancel_button = msg_box.button(QtWidgets.QMessageBox.Cancel)
        cancel_button.setText("取消")

        result = msg_box.exec_()
        return result == QtWidgets.QMessageBox.Ok


    def stop_sync(self):
        global stop_event
        stop_event.set()
        logging.info("已请求停止同步")  
    def start_sync(self):
        global source_folder, target_folder, stop_event
        global stability_check_interval, stability_check_attempts
        global max_filename_length
        
        max_filename_length = self.filename_length_input.value()
        source_folder = self.source_input.text()
        target_folder = self.target_input.text()
        stability_check_interval = self.stability_interval_input.value()
        stability_check_attempts = self.stability_attempts_input.value()

        if source_folder and target_folder:
            if self.preview_checkbox.isChecked():
                proceed = self.run_transfer_preview()
                if not proceed:
                    return  # 用户取消或关闭窗口，不执行同步

            stop_event.clear()
            self.hide()
            threading.Thread(target=scan_existing_files, daemon=True).start()
            threading.Thread(target=start_monitoring, daemon=True).start()
            logging.info("已启动同步任务")      

tray_icon = None

def create_tray(app, window):
    global tray_icon
    tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), app)
    tray_icon.setToolTip("文件转移工具")

    menu = QtWidgets.QMenu()
    action_show = menu.addAction("打开主界面")
    action_log = menu.addAction("查看日志")
    action_rescan = menu.addAction("重新扫描文件")
    action_organize = menu.addAction("整理目标文件夹")
    action_exit = menu.addAction("退出")

    action_show.triggered.connect(lambda: window.show())
    action_log.triggered.connect(lambda: os.startfile(log_file_path))
    action_rescan.triggered.connect(scan_existing_files)
    action_organize.triggered.connect(organize_target_folder)
    action_exit.triggered.connect(lambda: stop_event.set())
    action_exit.triggered.connect(app.quit)

    tray_icon.setContextMenu(menu)
    tray_icon.activated.connect(lambda reason: window.show() if reason == QtWidgets.QSystemTrayIcon.Trigger else None)
    tray_icon.show()

# 程序唯一标识
SERVER_NAME = "Jackson_FileMoverServer"

def send_to_running_instance(folder_arg, mode):
    # 拦截盘符根目录，例如 "C:\", "Z:\"
    if os.path.splitdrive(folder_arg)[1] == "\\":
        logging.warning(f"⚠️ 已拦截盘符根目录：{folder_arg}")
        return False  # 不继续发送，避免二次启动

    logging.info(f"🧭 右键菜单触发发送：mode={mode} | path={folder_arg}")
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(1000):
        message = f"{mode}|{folder_arg}"
        socket.write(message.encode("utf-8"))
        socket.flush()
        socket.waitForBytesWritten()
        socket.disconnectFromServer()
        return True
    return False

def clean_folder_path(path):
    path = path.strip('"').strip("'")              # 去除两侧引号
    path = path.replace("/", "\\")                 # 替换斜杠为反斜杠
    match = re.match(r"^([A-Z]:)[\\/]?$", path, re.IGNORECASE)
    if match:
        return match.group(1) + "\\"
    return os.path.normpath(path)

def main():
    logging.info(f"[启动参数] sys.argv: {sys.argv}")   

    folder_arg, mode = "", ""
    if len(sys.argv) >= 2:
        full_arg = ' '.join(sys.argv[1:]).strip('"')
        logging.info(f"[合并参数处理] full_arg = {full_arg}")

        # 拆分路径与模式
        for m in [" organize", " sync", " gui"]:
            if full_arg.lower().endswith(m):
                folder_arg = clean_folder_path(full_arg[:-len(m)].strip())
                mode = m.strip()
                break

        # ❗提前拦截盘符根目录
        if os.path.splitdrive(folder_arg)[1] == "\\":
            logging.warning(f"[拦截盘符根目录] {folder_arg}")
            return

        # ❗提前判断是否为合法路径
        if not os.path.exists(folder_arg) or not os.path.isdir(folder_arg):
            logging.warning(f"[路径异常] {folder_arg}")
            return

        # ✅ 若已有实例运行，发送参数
        if send_to_running_instance(folder_arg, mode):
            logging.info("[主进程] 已有实例运行，参数已发送，当前进程退出。")
            return
        else:
            logging.info("[主进程] 未检测到运行中的实例，继续本进程启动 GUI。")

        
    app = QtWidgets.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(icon_path))

    window = FileMoverApp()
    window.preview_checkbox.setChecked(True)
    window.show()
    create_tray(app, window)

    # ✅ 首次启动执行逻辑（mode 判断提前）
    if folder_arg and os.path.isdir(folder_arg):
        if mode == "organize":
            window.target_input.setText(folder_arg)
            logging.info(f"[组织整理 - 首次启动] 路径: {folder_arg}")
            QTimer.singleShot(200, lambda: organize_target_folder(window))
        elif mode == "sync":
            window.target_input.setText(folder_arg)
            logging.info(f"[界面赋值] 设置 target_input 成功：{window.target_input.text()}")
        elif mode == "gui":
            window.source_input.setText(folder_arg)
            logging.info(f"[界面赋值] 设置 source_input 成功：{window.source_input.text()}")

    # 启动 socket 服务监听新请求
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    if server.listen(SERVER_NAME):
        def handle_connection():
            socket = server.nextPendingConnection()
            if socket and socket.waitForReadyRead(1000):
                data = socket.readAll().data().decode()
                parts = data.split("|")
                if len(parts) == 2:
                    mode, folder_path = parts
                    folder_path = clean_folder_path(folder_path)
                    logging.info(f"[socket触发] 接收到 mode={mode} | folder={folder_path}")

                    if os.path.isdir(folder_path):
                        if mode == "organize":
                            window.target_input.setText(folder_path)
                            logging.info(f"[socket赋值] 设置 target_input（organize）：{folder_path}")
                            QTimer.singleShot(200, lambda: organize_target_folder(window))
                        elif mode == "sync":
                            window.target_input.setText(folder_path)
                            logging.info(f"[socket赋值] 设置 target_input（sync）：{folder_path}")
                        elif mode == "gui":
                            window.source_input.setText(folder_path)
                            logging.info(f"[socket赋值] 设置 source_input（gui）：{folder_path}")
        server.newConnection.connect(handle_connection)

    app.exec_()
    stop_event.set()
    logging.info("程序已退出")

if __name__ == "__main__":
    main()