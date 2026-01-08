import os
import sys
import json
from PyQt6.QtGui import QColor

# --- 1. 核心路径适配 ---
# 保持原有的打包/开发环境判断逻辑，确保稳定性
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    INTERNAL_DIR = sys._MEIPASS 
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    INTERNAL_DIR = BASE_DIR

# --- 2. 目录定义 (V0.2 标准) ---
BIN_DIR = os.path.join(BASE_DIR, "bin")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
TOOLS_DIR = os.path.join(BASE_DIR, "tools") # 兼容旧版工具箱
DEFAULT_DOWNLOAD_DIR = os.path.join(BASE_DIR, "Downloads")

# 资源路径
ASSETS_DIR = os.path.join(INTERNAL_DIR, "assets")
ICON_DIR = os.path.join(ASSETS_DIR, "icons")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")

# 关键文件路径
YTDLP_EXE = os.path.join(BIN_DIR, "yt-dlp.exe")
FFMPEG_EXE = os.path.join(BIN_DIR, "ffmpeg.exe")
DB_FILE = os.path.join(DATA_DIR, "downloads.db")
LOG_FILE = os.path.join(LOGS_DIR, "app.log")
TOKEN_FILE = os.path.join(DATA_DIR, "token.txt")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
TOOLS_CONFIG_FILE = os.path.join(DATA_DIR, "tools.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "archive.txt") # 确保下载记录文件定义存在

# 自动创建目录
for d in [DATA_DIR, LOGS_DIR, TOOLS_DIR, BIN_DIR, DEFAULT_DOWNLOAD_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- 3. 环境变量注入 (硬核稳健) ---
# 将 bin 目录加入 PATH，这样子进程能自动找到 ffmpeg
os.environ["PATH"] = BIN_DIR + os.pathsep + os.environ["PATH"]

# --- 4. 配置管理逻辑 (功能完整保留) ---
def load_settings():
    defaults = {
        "download_dir": DEFAULT_DOWNLOAD_DIR,
        "proxy": "",
        "theme": "light"
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                defaults.update(saved)
        except: pass
    return defaults

def save_settings(data):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except: return False

# 初始化配置 (单例模式)
_current_settings = load_settings()
DOWNLOAD_DIR = _current_settings.get("download_dir", DEFAULT_DOWNLOAD_DIR)

# --- 5. UI 设计系统 (V0.3: Ceramic & Air) ---
# 这里是核心改动：使用了新的色彩体系和字体栈

STYLE = {
    # 背景色体系
    "bg_window": "#F2F4F8",       # 更冷、更高级的灰，用于窗口背景 (不再是 F5F5F7)
    "bg_sidebar": "#FFFFFF",      # 侧边栏改为纯白，增加清透感
    "bg_card": "#FFFFFF",         # 卡片纯白
    
    # 文本色体系
    "text_main": "#111827",       # 接近黑色的深灰 (Inter Cool Gray 900)，比纯黑更护眼
    "text_sub": "#6B7280",        # 次级文本 (Inter Cool Gray 500)
    "text_tertiary": "#9CA3AF",   # 占位符/禁用态
    
    # 品牌色 (Brand Blue - Professional)
    "accent": "#2563EB",          # 更鲜艳、更具科技感的蓝 (Royal Blue)
    "accent_hover": "#1D4ED8",    # 悬停深蓝
    "accent_pressed": "#1E40AF",  # 点击深蓝
    
    # 边框与分割线
    "border": "#E5E7EB",          # 极淡的边框 (Cool Gray 200)
    
    # 装饰性元素
    "shadow": QColor(0, 0, 0, 10), # 基础阴影颜色，透明度更低更细腻
    
    # 尺寸与圆角系统 (8px Grid)
    "radius_l": 16,               # 卡片大圆角
    "radius_m": 8,                # 按钮/输入框中圆角
    "radius_s": 6,                # 小标签圆角
}

# 字体栈升级
# 优先寻找 Inter，其次是 Win11 的 Segoe UI Variable，最后回退到 微软雅黑
APP_FONT_MAIN = "Inter, Segoe UI Variable Display, Microsoft YaHei UI, sans-serif"
APP_FONT_MONO = "JetBrains Mono, Cascadia Code, Consolas, monospace"
