import sys
import os
import traceback

def global_crash_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        with open("crash_log.txt", "w", encoding="utf-8") as f: f.write(error_msg)
    except: pass
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox
        app = QApplication.instance()
        if not app: app = QApplication(sys.argv)
        if exc_type is not SystemExit:
            QMessageBox.critical(None, "程序错误", f"发生未捕获异常:\n{error_msg}")
    except:
        print(error_msg)
        if os.name == 'nt': os.system("pause")

sys.excepthook = global_crash_handler

try:
    import threading
    from flask import Flask, request
    from flask_cors import CORS
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                                 QListWidget, QListWidgetItem, QStackedWidget, QFrame, QGraphicsOpacityEffect,
                                 QMessageBox, QDialog, QProgressBar, QLabel)
    from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QPalette, QColor 
    
    from master_studio.config import STYLE, APP_FONT_MAIN, load_settings
    from master_studio.utils import load_custom_fonts
    from master_studio.core_worker import WorkerSignals, GlobalWorker
    from master_studio.ui_components import SidebarDelegate
    from master_studio.app_pages import DownloaderView, SystemView, ToolboxView, SettingsView

except ImportError as e:
    raise ImportError(f"环境缺失: {str(e)}")

class StartupWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def run(self):
        from master_studio.utils import DependencyManager
        def callback(msg, val): self.progress.emit(msg, val)
        success, msg = DependencyManager.install_ffmpeg(callback)
        self.finished.emit(success, msg)

class StartupDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(380, 180)
        
        self.frame = QFrame(self)
        self.frame.setGeometry(0, 0, 380, 180)
        self.frame.setStyleSheet(f"QFrame {{ background-color: #FFFFFF; border: 1px solid #E5E5EA; border-radius: 16px; }}")
        
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(30, 30, 30, 30)
        
        lbl_title = QLabel("正在初始化环境")
        lbl_title.setFont(QFont(APP_FONT_MAIN, 14, QFont.Weight.Bold))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_status = QLabel("检测到组件缺失，正在自动修复...")
        self.lbl_status.setStyleSheet("color: #86868B; font-size: 12px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(f"QProgressBar {{ border: none; background: #E0E0E0; border-radius: 3px; }} QProgressBar::chunk {{ background: {STYLE['accent']}; border-radius: 3px; }}")
        
        layout.addWidget(lbl_title)
        layout.addSpacing(10)
        layout.addWidget(self.lbl_status)
        layout.addSpacing(20)
        layout.addWidget(self.pbar)
        
        self.worker = StartupWorker()
        self.worker.progress.connect(self.update_status)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_status(self, msg, val):
        self.lbl_status.setText(msg)
        self.pbar.setValue(val)

    def on_finished(self, success, msg):
        if success: self.accept()
        else:
            QMessageBox.critical(self, "失败", f"无法自动下载组件：\n{msg}")
            sys.exit(1)

    def keyPressEvent(self, event): pass

class MasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Master Studio Pro")
        self.resize(1100, 750)
        # [UI微调] 融合标题栏颜色
        self.setStyleSheet(f"QMainWindow {{ background-color: {STYLE['bg_window']}; }} QMessageBox {{ background-color: #FFFFFF; }}")
        
        load_custom_fonts()
        
        self.signals = WorkerSignals()
        self.worker = GlobalWorker(self.signals)
        self.worker.start()
        
        threading.Thread(target=self.run_server, daemon=True).start()

        main = QWidget()
        self.setCentralWidget(main)
        layout = QHBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self.sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sidebar.setStyleSheet(f"QListWidget {{ background-color: {STYLE['bg_sidebar']}; border-right: 1px solid {STYLE['border']}; outline: none; padding-top: 25px; padding-left: 10px; padding-right: 10px; }}")
        self.sidebar.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setItemDelegate(SidebarDelegate())
        self.sidebar.currentRowChanged.connect(self.switch_with_animation)
        
        self.add_item("下载中心", "download.svg") 
        self.add_item("系统状态", "activity.svg")
        self.add_item("工具箱", "grid.svg")
        self.add_item("偏好设置", "settings.svg")
        
        layout.addWidget(self.sidebar)

        self.content_container = QWidget()
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0,0,0,0)
        
        self.stack = QStackedWidget()
        self.dl_page = DownloaderView(self.worker)
        self.sys_page = SystemView()
        self.tools_page = ToolboxView()
        self.set_page = SettingsView()
        
        self.stack.addWidget(self.dl_page)
        self.stack.addWidget(self.sys_page)
        self.stack.addWidget(self.tools_page)
        self.stack.addWidget(self.set_page)
        
        self.content_layout.addWidget(self.stack)
        layout.addWidget(self.content_container)

        self.signals.log.connect(self.dl_page.log_box.append)
        self.signals.progress.connect(self.update_progress)
        self.signals.status.connect(self.dl_page.lbl_status.setText)
        
        self.sidebar.setCurrentRow(0)

    def update_progress(self, val):
        int_val = int(val)
        self.dl_page.pbar.setValue(int_val)
        if 0 < int_val < 100:
            self.setWindowTitle(f"[{int_val}%] Master Studio Pro")
        else:
            self.setWindowTitle("Master Studio Pro")

    def closeEvent(self, event):
        if self.worker.is_working:
            reply = QMessageBox.question(
                self, "任务进行中", 
                "当前有任务正在运行，强制退出会导致文件损坏。\n是否强制退出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes: event.accept()
            else: event.ignore()
        else:
            event.accept()

    def add_item(self, text, icon):
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, icon)
        item.setSizeHint(QSize(0, 48)) 
        self.sidebar.addItem(item)

    def switch_with_animation(self, idx):
        current = self.stack.currentWidget()
        next_w = self.stack.widget(idx)
        if current == next_w: return

        if idx == 2: self.tools_page.start_refresh()

        op_eff = QGraphicsOpacityEffect(next_w)
        next_w.setGraphicsEffect(op_eff)
        
        self.anim = QPropertyAnimation(op_eff, b"opacity")
        self.anim.setDuration(300)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.stack.setCurrentIndex(idx)
        self.anim.start()

    def run_server(self):
        app = Flask(__name__)
        CORS(app)
        @app.route('/trigger')
        def trigger():
            u = request.args.get('url')
            if u: self.worker.add_task(u); return "OK"
            return "Err", 400
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        app.run(port=12345, debug=False, use_reloader=False)

def apply_startup_settings():
    settings = load_settings()
    proxy = settings.get("proxy", "").strip()
    if proxy:
        os.environ["http_proxy"] = proxy
        os.environ["https_proxy"] = proxy

if __name__ == "__main__":
    try:
        apply_startup_settings()
        if hasattr(Qt.HighDpiScaleFactorRoundingPolicy, 'PassThrough'):
            QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        
        app = QApplication(sys.argv)
        app.setStyle("Fusion") 
        
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor("#F5F5F7"))
        palette.setColor(QPalette.ColorRole.WindowText, QColor("#1D1D1F"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F5F5F7"))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#1D1D1F"))
        palette.setColor(QPalette.ColorRole.Text, QColor("#1D1D1F"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor("#1D1D1F"))
        palette.setColor(QPalette.ColorRole.BrightText, QColor("#FF0000"))
        palette.setColor(QPalette.ColorRole.Link, QColor("#007AFF"))
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#007AFF"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        app.setPalette(palette)
        
        font = QFont(APP_FONT_MAIN, 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        app.setFont(font)

        from master_studio.utils import DependencyManager
        is_ready, msg = DependencyManager.check_ffmpeg()
        
        if not is_ready:
            dialog = StartupDialog()
            if dialog.exec() != QDialog.DialogCode.Accepted: sys.exit(0)
        
        win = MasterApp()
        win.show()
        sys.exit(app.exec())
    except Exception as e:
        global_crash_handler(type(e), e, e.__traceback__)
