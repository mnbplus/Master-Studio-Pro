import os
import psutil
import subprocess
import time
import webbrowser
import threading
import json
import uuid
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, 
                             QTextEdit, QFrame, QGridLayout, QPushButton, QMessageBox, 
                             QComboBox, QListView, QCheckBox, QFileDialog, QListWidget, 
                             QListWidgetItem, QDialog, QMenu, QGraphicsDropShadowEffect)
from PyQt6.QtGui import QFont, QColor, QIcon, QAction, QCursor
from PyQt6.QtCore import Qt, QTimer, QSize, QThread, pyqtSignal

from master_studio.config import STYLE, APP_FONT_MAIN, APP_FONT_MONO, TOOLS_DIR, TOOLS_CONFIG_FILE, ICON_DIR, load_settings, save_settings
import master_studio.config as config_module
from master_studio.ui_components import MacCard, MacInput, MacButton, get_recolored_icon, SmoothScrollArea

# 通用 ComboBox 样式 (优化下拉菜单)
def apply_combo_style(combo, height=40):
    list_view = QListView(combo)
    combo.setView(list_view)
    combo.setFixedHeight(height)
    combo.setStyleSheet(f"""
        QComboBox {{ 
            border: 1px solid {STYLE['border']}; 
            border-radius: {STYLE['radius_m']}px; 
            padding-left: 12px; 
            color: {STYLE['text_main']}; 
            background-color: #FFFFFF; 
            font-family: "{APP_FONT_MAIN}"; 
            font-size: 13px; 
        }}
        QComboBox:hover {{ border: 1px solid #D1D5DB; }}
        QComboBox::drop-down {{ width: 20px; border: none; image: none; }} 
        /* 下拉列表样式 */
        QComboBox QAbstractItemView {{ 
            border: 1px solid {STYLE['border']}; 
            background-color: #FFFFFF; 
            outline: none; 
            padding: 4px; 
            color: {STYLE['text_main']}; 
            selection-background-color: {STYLE['accent']}; 
            selection-color: #FFFFFF; 
            border-radius: 8px;
        }}
        QComboBox QAbstractItemView::item {{ 
            height: 32px; /* 增加选项高度 */
            padding-left: 8px; 
            border-radius: 4px;
        }}
        QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {{ 
            background-color: {STYLE['accent']}; 
            color: #FFFFFF; 
        }}
    """)

# --- 基类页面 ---
class ToolPage(QWidget):
    def __init__(self, title, subtitle):
        super().__init__()
        self.layout = QVBoxLayout(self)
        # 核心改动：增加页面内边距，提升呼吸感
        self.layout.setContentsMargins(48, 48, 48, 48) 
        self.layout.setSpacing(32) # 模块间距增加
        
        title_block = QWidget()
        tb_layout = QVBoxLayout(title_block)
        tb_layout.setContentsMargins(0,0,0,0)
        tb_layout.setSpacing(8) # 标题与副标题间距
        
        lbl_title = QLabel(title)
        # 核心改动：字体加大加粗，使用 ExtraBold
        lbl_title.setFont(QFont(APP_FONT_MAIN, 26, QFont.Weight.ExtraBold))
        lbl_title.setStyleSheet(f"color: {STYLE['text_main']}; letter-spacing: -0.8px; background: transparent;")
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setFont(QFont(APP_FONT_MAIN, 11))
        lbl_sub.setStyleSheet(f"color: {STYLE['text_sub']}; background: transparent;")
        
        tb_layout.addWidget(lbl_title)
        tb_layout.addWidget(lbl_sub)
        self.layout.addWidget(title_block)
        
        self.content_area = QVBoxLayout()
        self.content_area.setSpacing(24) # 内容区域组件间距
        self.layout.addLayout(self.content_area)
        self.layout.addStretch()

# --- 添加工具弹窗 (保持逻辑不变，微调 UI) ---
class AddToolDialog(QDialog):
    def __init__(self, parent=None, edit_mode=False, initial_data=None):
        super().__init__(parent)
        self.setWindowTitle("编辑工具" if edit_mode else "添加自定义工具")
        self.resize(500, 480) # 稍微拉高一点
        self.setStyleSheet(f"background-color: #FFFFFF;") # 弹窗纯白背景
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        t = QLabel("编辑信息" if edit_mode else "添加新工具")
        t.setFont(QFont(APP_FONT_MAIN, 18, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {STYLE['text_main']};")
        layout.addWidget(t)
        
        def make_label(txt):
            l = QLabel(txt)
            l.setStyleSheet(f"color: {STYLE['text_main']}; font-weight: 500;")
            return l

        layout.addWidget(make_label("工具名称:"))
        self.inp_name = MacInput("例如: Genshin Impact")
        layout.addWidget(self.inp_name)
        
        layout.addWidget(make_label("启动路径 (.exe):"))
        path_layout = QHBoxLayout()
        self.inp_path = MacInput("点击右侧按钮选择文件...")
        self.inp_path.setReadOnly(True)
        btn_path = MacButton("浏览...", is_primary=False)
        btn_path.setFixedWidth(80)
        btn_path.clicked.connect(self.browse_file)
        path_layout.addWidget(self.inp_path)
        path_layout.addWidget(btn_path)
        layout.addLayout(path_layout)
        
        layout.addWidget(make_label("描述:"))
        self.inp_desc = MacInput("例如: 开放世界冒险游戏")
        layout.addWidget(self.inp_desc)
        
        layout.addWidget(make_label("图标:"))
        self.combo_icon = QComboBox()
        self.combo_icon.setFixedHeight(40)
        
        if os.path.exists(ICON_DIR):
            icon_list = sorted([f for f in os.listdir(ICON_DIR) if f.endswith(".svg")])
            for icon in icon_list:
                self.combo_icon.addItem(icon)
                self.combo_icon.setItemIcon(self.combo_icon.count()-1, QIcon(os.path.join(ICON_DIR, icon)))
        apply_combo_style(self.combo_icon)
        layout.addWidget(self.combo_icon)
        
        layout.addStretch()
        
        btns = QHBoxLayout()
        btns.addStretch()
        b_cancel = MacButton("取消", is_primary=False)
        b_cancel.setFixedWidth(100)
        b_cancel.clicked.connect(self.reject)
        
        b_ok = MacButton("保存" if edit_mode else "添加", is_primary=True)
        b_ok.setFixedWidth(100)
        b_ok.clicked.connect(self.accept)
        
        btns.addWidget(b_cancel)
        btns.addWidget(b_ok)
        layout.addLayout(btns)

        if edit_mode and initial_data:
            self.inp_name.setText(initial_data.get('title', ''))
            self.inp_path.setText(initial_data.get('path', ''))
            self.inp_desc.setText(initial_data.get('desc', ''))
            icon_name = initial_data.get('icon', '')
            index = self.combo_icon.findText(icon_name)
            if index >= 0: self.combo_icon.setCurrentIndex(index)

    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择启动程序", "", "可执行文件 (*.exe);;所有文件 (*.*)")
        if f: self.inp_path.setText(f)
        
    def get_data(self):
        return {
            "title": self.inp_name.text().strip(),
            "path": self.inp_path.text().strip(),
            "desc": self.inp_desc.text().strip(),
            "icon": self.combo_icon.currentText()
        }

# --- 1. 下载页 ---
class DownloaderView(ToolPage):
    def __init__(self, worker):
        super().__init__("下载中心", "支持 YouTube / Bilibili 高速下载")
        self.worker = worker
        
        # 1. 主操作卡片
        card = MacCard()
        l = QVBoxLayout(card)
        l.setContentsMargins(32, 32, 32, 32) # 内边距统一增加
        l.setSpacing(16) 
        
        lbl_input = QLabel("新建任务")
        lbl_input.setStyleSheet(f"color: {STYLE['text_main']}; font-weight: 600; font-size: 14px;")
        l.addWidget(lbl_input)
        
        input_container = QHBoxLayout()
        input_container.setSpacing(12)
        
        self.input = MacInput("在此粘贴视频链接...")
        self.input.returnPressed.connect(self.start)
        
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["智能合成 (MP4)", "仅视频流 (无声)", "仅音频流 (MP3)", "原始分流 (不合并)", "1080p 合成"])
        self.combo_quality.setFixedWidth(140) # 稍微加宽
        self.combo_quality.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_combo_style(self.combo_quality)
        
        self.btn = MacButton("执行", is_primary=True)
        self.btn.setFixedWidth(100)
        self.btn.clicked.connect(self.start)
        
        input_container.addWidget(self.input)
        input_container.addWidget(self.combo_quality)
        input_container.addWidget(self.btn)
        l.addLayout(input_container)
        
        # 2. 选项区域
        opts_widget = QWidget()
        opts_widget.setStyleSheet(f"""
            QWidget {{ 
                background-color: #F9FAFB; 
                border-radius: 8px; 
                border: 1px solid {STYLE['border']}; 
            }} 
            QCheckBox {{ 
                background-color: transparent; 
                border: none; 
                color: {STYLE['text_sub']}; 
                font-size: 13px; 
            }}
            QCheckBox::indicator {{ width: 16px; height: 16px; }}
        """)
        opts_layout = QHBoxLayout(opts_widget)
        opts_layout.setContentsMargins(16, 12, 16, 12)
        
        self.chk_thumbnail = QCheckBox("封面图")
        self.chk_thumbnail.setChecked(True)
        self.chk_embed_sub = QCheckBox("内嵌字幕")
        self.chk_embed_sub.setChecked(True)
        self.chk_save_sub = QCheckBox("字幕文件") 
        self.chk_save_sub.setChecked(False)
        
        lbl_lang = QLabel("字幕:")
        lbl_lang.setStyleSheet(f"color: {STYLE['text_sub']}; font-size: 13px; border: none;")
        self.combo_sub_lang = QComboBox()
        self.combo_sub_lang.addItems(["自动", "中文", "繁中", "英文", "日文"])
        self.combo_sub_lang.setFixedWidth(80)
        apply_combo_style(self.combo_sub_lang, height=32) # 稍微矮一点
        
        opts_layout.addWidget(self.chk_thumbnail)
        opts_layout.addSpacing(16)
        opts_layout.addWidget(self.chk_embed_sub)
        opts_layout.addSpacing(16)
        opts_layout.addWidget(self.chk_save_sub)
        opts_layout.addStretch() 
        opts_layout.addWidget(lbl_lang)
        opts_layout.addWidget(self.combo_sub_lang)
        l.addWidget(opts_widget)
        
        self.content_area.addWidget(card)
        
        # 3. 状态栏
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(4, 8, 4, 0)
        
        info_row = QHBoxLayout()
        self.lbl_status_icon = QLabel("●") 
        self.lbl_status_icon.setStyleSheet(f"color: {STYLE['accent']}; font-size: 8px;")
        
        self.lbl_status = QLabel("等待任务...")
        self.lbl_status.setStyleSheet(f"color: {STYLE['text_main']}; font-weight: 600; font-size: 13px;")
        
        info_row.addWidget(self.lbl_status_icon)
        info_row.addSpacing(8)
        info_row.addWidget(self.lbl_status)
        info_row.addStretch()
        
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(6)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(f"""
            QProgressBar {{ border: none; background: #E5E7EB; border-radius: 3px; }} 
            QProgressBar::chunk {{ background: {STYLE['accent']}; border-radius: 3px; }}
        """)
        
        status_layout.addLayout(info_row)
        status_layout.addWidget(self.pbar)
        self.content_area.addWidget(status_container)
        
        # 4. 日志区域
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)
        
        self.log_box = QTextEdit()
        self.log_box.setFrameShape(QFrame.Shape.NoFrame)
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("任务运行日志...")
        self.log_box.setStyleSheet(f"""
            QTextEdit {{ 
                background-color: #FFFFFF; 
                border: 1px solid {STYLE['border']}; 
                border-radius: 12px; 
                color: #374151; 
                font-family: '{APP_FONT_MONO}'; 
                font-size: 12px; 
                padding: 16px; 
            }}
        """)
        self.log_box.setFixedHeight(220)
        
        queue_container = QWidget()
        qc_layout = QVBoxLayout(queue_container)
        qc_layout.setContentsMargins(0,0,0,0)
        qc_layout.setSpacing(8)
        
        q_label = QLabel("等待队列")
        q_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {STYLE['text_sub']};")
        qc_layout.addWidget(q_label)
        
        self.queue_list = QListWidget()
        self.queue_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.queue_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: #F9FAFB; 
                border: 1px solid {STYLE['border']}; 
                border-radius: 12px; 
                padding: 8px; 
            }} 
            QListWidget::item {{ 
                height: 28px; 
                color: {STYLE['text_main']}; 
                padding-left: 4px;
            }}
        """)
        qc_layout.addWidget(self.queue_list)
        
        split_layout.addWidget(self.log_box, 7)
        split_layout.addWidget(queue_container, 3)
        self.content_area.addLayout(split_layout)
        
        self.worker.signals.task_started.connect(self.on_task_start)
        self.worker.signals.task_finished.connect(self.on_task_finish)

    def start(self):
        url = self.input.text().strip()
        if url:
            params = {'url': url, 'quality_idx': self.combo_quality.currentIndex(), 'save_cover': self.chk_thumbnail.isChecked(), 'embed_sub': self.chk_embed_sub.isChecked(), 'save_sub_file': self.chk_save_sub.isChecked(), 'sub_lang_idx': self.combo_sub_lang.currentIndex()}
            self.queue_list.addItem(QListWidgetItem(f"⏳ {url[:25]}..."))
            self.btn.setEnabled(False)
            self.btn.setText("提交中")
            QTimer.singleShot(800, lambda: self.reset_btn())
            self.worker.add_task(params)
            self.input.clear()
            self.log_box.append(f"▶️ 已提交: {url[:30]}...")

    def on_task_start(self, url):
        if self.queue_list.count() > 0: self.queue_list.takeItem(0)
        self.lbl_status.setText(f"正在下载: {url[:30]}...")
        self.lbl_status_icon.setStyleSheet("color: #F59E0B; font-size: 8px;") # Amber 500

    def on_task_finish(self, url):
        self.lbl_status.setText("系统空闲")
        self.lbl_status_icon.setStyleSheet(f"color: {STYLE['accent']}; font-size: 8px;")

    def reset_btn(self):
        self.btn.setEnabled(True)
        self.btn.setText("执行")

# --- 2. 系统监控 ---
class SystemMonitorWorker(QThread):
    stats_updated = pyqtSignal(float, float) 
    def run(self):
        while True:
            try:
                cpu = psutil.cpu_percent(interval=1)
                ram = psutil.virtual_memory().percent
                self.stats_updated.emit(cpu, ram)
                time.sleep(1)
            except: break

class SystemView(ToolPage):
    def __init__(self):
        super().__init__("系统监控", "实时查看硬件性能")
        grid = QHBoxLayout()
        grid.setSpacing(24) # 卡片间距增加
        
        self.cpu = self.make_card("CPU 负载", "cpu.svg")
        self.ram = self.make_card("内存占用", "activity.svg")
        
        grid.addWidget(self.cpu)
        grid.addWidget(self.ram)
        self.content_area.addLayout(grid)
        
        self.monitor_thread = SystemMonitorWorker()
        self.monitor_thread.stats_updated.connect(self.update_ui)
        self.monitor_thread.start()
        
    def make_card(self, title, icon_name):
        card = MacCard()
        l = QVBoxLayout(card)
        l.setContentsMargins(32, 32, 32, 32)
        
        top = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_recolored_icon(icon_name, STYLE['text_sub'], 24))
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{STYLE['text_sub']}; font-weight:600; font-size:14px; border:none;")
        
        top.addWidget(icon_lbl)
        top.addSpacing(12)
        top.addWidget(title_lbl)
        top.addStretch()
        
        val = QLabel("0%")
        # 使用更干净的字体渲染数字
        val.setStyleSheet(f"color:{STYLE['text_main']}; font-size:48px; font-weight:700; font-family: '{APP_FONT_MAIN}'; letter-spacing: -1px; border:none;")
        val.setObjectName("val")
        
        l.addLayout(top)
        l.addSpacing(24)
        l.addWidget(val)
        return card
        
    def update_ui(self, cpu, ram):
        self.cpu.findChild(QLabel, "val").setText(f"{cpu}%")
        self.ram.findChild(QLabel, "val").setText(f"{ram}%")

# --- 3. 工具箱 ---
class ToolScannerWorker(QThread):
    tools_found = pyqtSignal(list)
    def run(self):
        tools_config = self.load_or_create_config()
        results = []
        known_paths = set()
        
        for item in tools_config:
            path = self.check_tool_exists(item.get("folder", ""), item.get("exes", []))
            if path:
                results.append(item | {"path": path}) 
                known_paths.add(os.path.abspath(path).lower())

        if os.path.exists(TOOLS_DIR):
            try:
                for item in os.listdir(TOOLS_DIR):
                    item_path = os.path.join(TOOLS_DIR, item)
                    if os.path.isfile(item_path) and item.lower().endswith(".exe"):
                        if os.path.abspath(item_path).lower() not in known_paths:
                            name = os.path.splitext(item)[0]
                            results.append({"id": f"auto_{name}", "title": name, "desc": "自动发现的工具", "icon": "package.svg", "path": item_path})
                    elif os.path.isdir(item_path):
                        target_exe = self.find_main_exe_in_folder(item_path, folder_name=item)
                        if target_exe:
                            if os.path.abspath(target_exe).lower() not in known_paths:
                                results.append({"id": f"auto_{item}", "title": item, "desc": "应用文件夹", "icon": "grid.svg", "path": target_exe})
            except Exception as e: print(f"扫描出错: {e}")
        self.tools_found.emit(results)

    def find_main_exe_in_folder(self, folder_path, folder_name):
        try:
            exes = [f for f in os.listdir(folder_path) if f.lower().endswith(".exe")]
            if not exes: return None
            valid_exes = []
            blocklist = ['uninstall', 'update', 'helper', 'crash', 'reporter', 'installer', 'feedback']
            for f in exes:
                if not any(bad in f.lower() for bad in blocklist): valid_exes.append(f)
            if not valid_exes: return None
            for f in valid_exes:
                if os.path.splitext(f)[0].lower() == folder_name.lower(): return os.path.join(folder_path, f)
            for f in valid_exes:
                if f.lower() in ['app.exe', 'main.exe', 'launcher.exe', 'start.exe', 'client.exe']: return os.path.join(folder_path, f)
            valid_exes.sort(key=lambda x: os.path.getsize(os.path.join(folder_path, x)), reverse=True)
            return os.path.join(folder_path, valid_exes[0])
        except: return None
    
    def load_or_create_config(self):
        default = []
        if not os.path.exists(TOOLS_CONFIG_FILE):
            try:
                with open(TOOLS_CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(default, f, indent=4)
            except: pass
            return default
        try:
            with open(TOOLS_CONFIG_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return default
    
    def check_tool_exists(self, folder, exes):
        if os.path.isabs(folder) and os.path.exists(folder):
             for exe in exes:
                 if os.path.exists(os.path.join(folder, exe)): return os.path.join(folder, exe)
        search_paths = [os.path.join(TOOLS_DIR, folder), TOOLS_DIR]
        if folder == "Manga_Reader": search_paths.append(os.path.join(TOOLS_DIR, folder, "bin"))
        for base in search_paths:
            if not os.path.exists(base): continue
            for exe in exes:
                if os.path.exists(os.path.join(base, exe)): return os.path.join(base, exe)
            for root, dirs, files in os.walk(base):
                if root.count(os.sep) - base.count(os.sep) > 2: continue 
                for exe in exes:
                    if exe in files: return os.path.join(root, exe)
        return None

class ToolboxView(ToolPage):
    def __init__(self):
        super().__init__("工具箱", "已安装的生产力工具")
        
        self.scroll_area = SmoothScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(24) # 增加网格间距
        self.scroll_area.setWidget(self.scroll_content)
        self.content_area.addWidget(self.scroll_area)
        
        self.scanner = ToolScannerWorker()
        self.scanner.tools_found.connect(self.on_tools_found)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ 添加工具")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.setStyleSheet(f"background:transparent; color:{STYLE['accent']}; border:none; font-weight:bold; font-size:13px;")
        self.add_btn.clicked.connect(lambda: self.add_or_edit_tool())
        
        self.refresh_btn = QPushButton("↻ 刷新列表")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.setStyleSheet(f"background:transparent; color:{STYLE['text_sub']}; border:none; font-size:13px;")
        self.refresh_btn.clicked.connect(self.start_refresh)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        self.content_area.addLayout(btn_layout)
        self.start_refresh()

    def start_refresh(self):
        while self.grid.count(): 
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.loading_lbl = QLabel("正在扫描工具目录...")
        self.loading_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_lbl.setStyleSheet(f"color: {STYLE['text_sub']};")
        self.grid.addWidget(self.loading_lbl, 0, 0)
        self.refresh_btn.setEnabled(False)
        self.scanner.start()
        
    def add_or_edit_tool(self, edit_mode=False, old_data=None):
        dlg = AddToolDialog(self, edit_mode, old_data)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            if not data['title'] or not data['path']:
                QMessageBox.warning(self, "提示", "名称和路径不能为空")
                return
            
            try:
                config = []
                if os.path.exists(TOOLS_CONFIG_FILE):
                    with open(TOOLS_CONFIG_FILE, 'r', encoding='utf-8') as f: config = json.load(f)
                
                full_path = data['path']
                folder = os.path.dirname(full_path)
                exe_name = os.path.basename(full_path)
                
                if edit_mode and old_data and str(old_data['id']).startswith("custom_"):
                    config = [c for c in config if c['id'] != old_data['id']]
                    new_id = old_data['id']
                else:
                    new_id = f"custom_{uuid.uuid4().hex[:8]}"

                new_item = {
                    "id": new_id,
                    "title": data['title'],
                    "desc": data['desc'],
                    "icon": data['icon'],
                    "folder": folder,
                    "exes": [exe_name]
                }
                config.append(new_item)
                
                with open(TOOLS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                
                QMessageBox.information(self, "成功", "保存成功！")
                self.start_refresh()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存配置文件失败: {e}")

    def delete_tool(self, tool_id):
        reply = QMessageBox.question(self, "确认删除", "确定要移除该工具吗？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(TOOLS_CONFIG_FILE):
                    with open(TOOLS_CONFIG_FILE, 'r', encoding='utf-8') as f: config = json.load(f)
                    config = [c for c in config if c['id'] != tool_id]
                    with open(TOOLS_CONFIG_FILE, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    self.start_refresh()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def on_tools_found(self, tools_data):
        if hasattr(self, 'loading_lbl'): self.loading_lbl.deleteLater()
        col, row, found = 0, 0, False
        for tool in tools_data:
            card = self.create_tool_card(tool)
            self.grid.addWidget(card, row, col)
            col += 1
            if col > 1: col, row = 0, row + 1
            found = True
        if not found:
            lbl = QLabel("暂无工具\n点击下方按钮手动添加")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {STYLE['text_sub']}; padding: 40px; border: 2px dashed {STYLE['border']}; border-radius: {STYLE['radius_l']}px;")
            self.grid.addWidget(lbl, 0, 0, 1, 2)
        self.refresh_btn.setEnabled(True)

    def create_tool_card(self, tool_data):
        card = MacCard()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        l = QVBoxLayout(card)
        l.setContentsMargins(24, 24, 24, 24)
        
        row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(get_recolored_icon(tool_data['icon'], STYLE['accent'], 40)) # 图标稍大
        
        t_layout = QVBoxLayout()
        t1 = QLabel(tool_data['title'])
        t1.setFont(QFont(APP_FONT_MAIN, 12, QFont.Weight.Bold))
        t1.setStyleSheet(f"color: {STYLE['text_main']};")
        
        t2 = QLabel(tool_data['desc'])
        t2.setStyleSheet(f"color: {STYLE['text_sub']}; font-size: 11px;")
        t2.setWordWrap(True)
        
        t_layout.addWidget(t1)
        t_layout.addWidget(t2)
        
        row.addWidget(icon)
        row.addSpacing(16)
        row.addLayout(t_layout)
        row.addStretch()
        l.addLayout(row)
        
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tool_id = str(tool_data['id'])
        is_custom = tool_id.startswith("custom_")
        
        def show_menu(pos):
            menu = QMenu(card)
            menu.setStyleSheet(f"""
                QMenu {{ background-color: #FFFFFF; border: 1px solid {STYLE['border']}; border-radius: 8px; padding: 4px; }}
                QMenu::item {{ padding: 6px 24px; font-family: "{APP_FONT_MAIN}"; font-size: 13px; color: {STYLE['text_main']}; border-radius: 4px; }}
                QMenu::item:selected {{ background-color: {STYLE['accent']}; color: #FFFFFF; }}
                QMenu::separator {{ height: 1px; background: {STYLE['border']}; margin: 4px 0; }}
            """)
            
            act_open_loc = QAction("📂 打开文件位置", card)
            act_open_loc.triggered.connect(lambda: subprocess.Popen(f'explorer /select,"{tool_data["path"]}"'))
            menu.addAction(act_open_loc)
            
            menu.addSeparator()

            act_edit = QAction("✏️ 编辑", card)
            act_edit.triggered.connect(lambda: self.add_or_edit_tool(edit_mode=True, old_data=tool_data))
            menu.addAction(act_edit)
            
            if is_custom:
                act_del = QAction("🗑️ 删除", card)
                act_del.triggered.connect(lambda: self.delete_tool(tool_id))
                menu.addAction(act_del)
                
            menu.exec(card.mapToGlobal(pos))
            
        card.customContextMenuRequested.connect(show_menu)
        
        btn = QPushButton(card)
        btn.setStyleSheet("background:transparent; border:none;")
        btn.resize(card.size())
        
        if tool_data['id'] == "Manga_Reader":
            btn.clicked.connect(lambda: self.launch_suwayomi(tool_data['path']))
        else:
            btn.clicked.connect(lambda _, p=tool_data['path']: self.launch_app(p))
            
        card.resizeEvent = lambda e: btn.resize(e.size())
        return card

    def launch_app(self, path):
        try:
            subprocess.Popen(path, cwd=os.path.dirname(path), shell=True)
        except Exception as e: QMessageBox.warning(self, "错误", f"无法启动: {e}")

    def launch_suwayomi(self, jar_path):
        # 保持特定工具的启动逻辑不变
        try:
            root = os.path.dirname(os.path.dirname(jar_path))
            flare = os.path.join(root, "flaresolverr_windows_x64", "flaresolverr", "flaresolverr.exe")
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            if os.path.exists(flare): subprocess.Popen(flare, cwd=os.path.dirname(flare), creationflags=flags)
            java = os.path.join(root, "jre", "bin", "java.exe")
            if not os.path.exists(java): java = "java"
            local = os.path.join(root, "Local_Manga").replace("\\", "/")
            cmd = [java, "-Djava.net.preferIPv4Stack=true", f"-Dserver.system.localMangaPath={local}", "-jar", jar_path]
            subprocess.Popen(cmd, cwd=root, creationflags=flags)
            def open_browser():
                time.sleep(15)
                webbrowser.open("http://localhost:4567")
            threading.Thread(target=open_browser, daemon=True).start()
            QMessageBox.information(self, "启动中", "Suwayomi 正在后台启动...")
        except Exception as e: QMessageBox.critical(self, "错误", f"启动失败: {e}")

# --- 4. 设置页 ---
class SettingsView(ToolPage):
    def __init__(self):
        super().__init__("偏好设置", "自定义软件行为与路径")
        self.settings = load_settings()
        
        container = MacCard()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 32)
        
        row_path = self.create_row("下载目录", "媒体文件保存位置")
        path_ctrl = QHBoxLayout()
        self.input_path = MacInput(self.settings.get("download_dir", ""))
        self.input_path.setReadOnly(True)
        btn_browse = MacButton("选择...", is_primary=False)
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(self.choose_dir)
        path_ctrl.addWidget(self.input_path)
        path_ctrl.addWidget(btn_browse)
        row_path.addLayout(path_ctrl)
        
        layout.addSpacing(24)
        
        row_proxy = self.create_row("网络代理", "HTTP/HTTPS 代理")
        self.input_proxy = MacInput(self.settings.get("proxy", ""))
        row_proxy.addWidget(self.input_proxy)
        layout.addLayout(row_proxy)
        
        layout.addStretch()
        
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.btn_save = MacButton("保存更改", is_primary=True)
        self.btn_save.setFixedWidth(120)
        self.btn_save.clicked.connect(self.save_all)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)
        self.content_area.addWidget(container)
        
    def create_row(self, title, subtitle):
        v = QVBoxLayout()
        v.setSpacing(6)
        lbl = QLabel(title)
        lbl.setFont(QFont(APP_FONT_MAIN, 11, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {STYLE['text_main']};")
        sub = QLabel(subtitle)
        sub.setStyleSheet(f"color: {STYLE['text_sub']}; font-size: 11px;")
        v.addWidget(lbl)
        v.addWidget(sub)
        return v
        
    def choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录", self.input_path.text())
        if d: self.input_path.setText(d)
        
    def save_all(self):
        new_settings = {"download_dir": self.input_path.text(),"proxy": self.input_proxy.text().strip(),"theme": "light"}
        if save_settings(new_settings):
            config_module.DOWNLOAD_DIR = new_settings["download_dir"]
            p = new_settings["proxy"]
            if p:
                os.environ["http_proxy"] = p
                os.environ["https_proxy"] = p
            else:
                os.environ.pop("http_proxy", None)
                os.environ.pop("https_proxy", None)
            QMessageBox.information(self, "成功", "设置已生效")
