import os
import sys
import shutil
import subprocess
import zipfile
import requests
from functools import lru_cache
from PyQt6.QtGui import QFontDatabase, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt
from master_studio.config import FONTS_DIR, ICON_DIR, BIN_DIR, FFMPEG_EXE

def load_custom_fonts():
    if os.path.exists(FONTS_DIR):
        for f in os.listdir(FONTS_DIR):
            if f.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, f))

# 全局图标缓存
_ICON_CACHE = {}

def get_recolored_icon(filename, color_hex, size=24):
    """ 
    [UI 修复版] 获取重着色的图标 
    修复了部分环境下图标显示为“黑方块”的渲染 Bug
    """
    cache_key = f"{filename}_{color_hex}_{size}"
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    path = os.path.join(ICON_DIR, filename)
    
    # 1. 创建透明画布
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    # 2. 如果文件不存在，直接返回透明图 (防止显示黑块)
    if not os.path.exists(path):
        return pixmap

    # 3. 渲染 SVG (作为底图)
    painter = QPainter(pixmap)
    renderer = QSvgRenderer(path)
    renderer.render(painter)
    
    # 4. 核心着色逻辑 (SourceIn: 只在有像素的地方上色)
    # 这种方式比原来的 DestinationIn 更稳定
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color_hex))
    painter.end()
    
    # 5. 存入缓存
    _ICON_CACHE[cache_key] = pixmap
    return pixmap

class DependencyManager:
    FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

    @staticmethod
    def check_ffmpeg():
        ffprobe_exe = os.path.join(BIN_DIR, "ffprobe.exe")
        if not os.path.exists(FFMPEG_EXE) or not os.path.exists(ffprobe_exe):
            return False, "组件缺失"
        try:
            # 兼容不同系统
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.run([FFMPEG_EXE, "-version"], capture_output=True, creationflags=flags)
            return True, "已就绪"
        except Exception as e:
            return False, f"损坏: {str(e)}"

    @staticmethod
    def install_ffmpeg(progress_callback=None):
        try:
            if not os.path.exists(BIN_DIR): os.makedirs(BIN_DIR)
            if progress_callback: progress_callback("正在连接服务器...", 0)
            
            response = requests.get(DependencyManager.FFMPEG_URL, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024 * 1024
            downloaded = 0
            zip_path = os.path.join(BIN_DIR, "ffmpeg_temp.zip")
            
            with open(zip_path, 'wb') as f:
                for data in response.iter_content(block_size):
                    f.write(data)
                    downloaded += len(data)
                    if total_size > 0 and progress_callback:
                        percent = int((downloaded / total_size) * 80)
                        progress_callback(f"正在下载核心组件... {percent}%", percent)

            if progress_callback: progress_callback("正在解压...", 85)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                target_files = {}
                for name in zip_ref.namelist():
                    if name.endswith("bin/ffmpeg.exe"): target_files["ffmpeg.exe"] = name
                    elif name.endswith("bin/ffprobe.exe"): target_files["ffprobe.exe"] = name
                
                if not target_files: raise Exception("下载包结构异常")

                for target_name, source_path in target_files.items():
                    with zip_ref.open(source_path) as source, open(os.path.join(BIN_DIR, target_name), "wb") as target:
                        shutil.copyfileobj(source, target)

            if progress_callback: progress_callback("正在清理...", 95)
            os.remove(zip_path)
            
            if progress_callback: progress_callback("安装完成！", 100)
            return True, "安装成功"

        except Exception as e:
            if os.path.exists(os.path.join(BIN_DIR, "ffmpeg_temp.zip")):
                os.remove(os.path.join(BIN_DIR, "ffmpeg_temp.zip"))
            return False, f"安装失败: {str(e)}"

    @staticmethod
    def update_ytdlp():
        try:
            flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            subprocess.run(cmd, capture_output=True, check=True, creationflags=flags)
            return True, "更新成功"
        except Exception as e:
            return False, f"更新失败: {e}"
