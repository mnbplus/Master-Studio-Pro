import threading
import queue
import os
import subprocess
import sys
import traceback
import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal
from master_studio.config import DOWNLOAD_DIR, BIN_DIR, ARCHIVE_FILE, FFMPEG_EXE

class WorkerSignals(QObject):
    log = pyqtSignal(str)
    progress = pyqtSignal(float)
    status = pyqtSignal(str)
    task_started = pyqtSignal(str)
    task_finished = pyqtSignal(str)

class YtdlLogger:
    def __init__(self, signals):
        self.signals = signals

    def debug(self, msg):
        if not msg.startswith('[debug] '): 
            print(f"[yt-dlp DEBUG] {msg}")

    def warning(self, msg):
        self.signals.log.emit(f"⚠️ {msg}")

    def error(self, msg):
        # 屏蔽 Cookie 相关的报错显示，避免刷屏，由上层逻辑处理
        if "cookie" in msg.lower() or "permission" in msg.lower():
            print(f"[Suppress Error] {msg}")
        else:
            self.signals.log.emit(f"❌ {msg}")

class GlobalWorker(threading.Thread):
    def __init__(self, signals):
        super().__init__(daemon=True)
        self.queue = queue.Queue()
        self.signals = signals
        self.is_working = False 

    def add_task(self, task_data):
        self.queue.put(task_data)

    def run(self):
        while True:
            task = self.queue.get()
            self.is_working = True
            
            current_url = "未知任务"
            if isinstance(task, str): current_url = task
            elif isinstance(task, dict): current_url = task.get('url', '未知')
            
            self.signals.task_started.emit(current_url)
            
            try:
                print(f"[Worker] 处理任务: {task}")
                
                params = {}
                if isinstance(task, str):
                    params = {'url': task, 'quality_idx': 0}
                elif isinstance(task, tuple):
                    params = {'url': task[0], 'quality_idx': task[1]}
                elif isinstance(task, dict):
                    params = task
                
                params.setdefault('quality_idx', 0)
                params.setdefault('save_cover', True)
                params.setdefault('embed_sub', True)
                params.setdefault('save_sub_file', False)
                params.setdefault('sub_lang_idx', 0)
                
                self.process_video_robust(params)
                
            except Exception as e:
                error_msg = f"❌ 严重错误: {str(e)}"
                self.signals.log.emit(error_msg)
            finally:
                self.is_working = False
                self.signals.task_finished.emit(current_url)
                self.queue.task_done()
                self.signals.progress.emit(0)
                self.signals.status.emit("系统空闲")

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                p = d.get('_percent_str', '0%').replace('%', '')
                self.signals.progress.emit(float(p))
                self.signals.status.emit(f"下载中... {p}%")
            except: pass
        elif d['status'] == 'finished':
            self.signals.progress.emit(100)
            self.signals.status.emit("处理中...")

    def process_video_robust(self, params):
        """ 包含重试逻辑的视频处理入口 """
        url = params['url']
        
        # 1. 尝试使用 Cookies 下载 (高画质)
        try:
            self.signals.log.emit(f"🚀 开始任务: {url}")
            self.signals.log.emit("🍪 尝试读取 Edge Cookies (解锁高画质)...")
            self._execute_download(params, use_cookies=True)
            return # 成功则直接返回
        except Exception as e:
            err_msg = str(e).lower()
            # 捕获权限错误或 Cookie 错误
            if "permission denied" in err_msg or "cookie" in err_msg or "lock" in err_msg:
                self.signals.log.emit("⚠️ Edge 浏览器正忙 (文件被锁定)")
                self.signals.log.emit("🔄 自动切换至【游客模式】重试...")
                
                # 2. 降级重试 (无 Cookies)
                try:
                    self._execute_download(params, use_cookies=False)
                except Exception as e2:
                    self.signals.log.emit(f"❌ 游客模式下载失败: {e2}")
            else:
                self.signals.log.emit(f"❌ 下载出错: {e}")

    def _execute_download(self, params, use_cookies=True):
        """ 实际执行 yt-dlp 的内部函数 """
        url = params['url']
        q_idx = params['quality_idx']
        
        mode_names = ['智能合成 (MP4)', '仅视频流', '仅音频流', '原始分流', '1080p 合成']
        mode_name = mode_names[q_idx] if q_idx < len(mode_names) else '未知'
        
        if not use_cookies:
            self.signals.log.emit(f"🔧 模式: {mode_name} (游客)")
        
        lang_map = {
            0: ['ja', 'zh-Hans', 'zh-CN', 'en', 'zh-Hant', 'zh-TW'], 
            1: ['zh-Hans', 'zh-CN', 'zh'], 2: ['zh-Hant', 'zh-TW'], 
            3: ['en', 'en-US'], 4: ['ja']
        }
        sub_langs = lang_map.get(params['sub_lang_idx'], lang_map[0])

        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(uploader)s - %(title)s [%(id)s]', '%(uploader)s - %(title)s [%(id)s].%(ext)s'),
            'ffmpeg_location': BIN_DIR,
            'download_archive': ARCHIVE_FILE,
            'quiet': False, 'verbose': True,
            'nocheckcertificate': True, 'noplaylist': True,
            'progress_hooks': [self.progress_hook],
            'logger': YtdlLogger(self.signals),
            'writethumbnail': params['save_cover'], 
            'writesubtitles': params['embed_sub'] or params['save_sub_file'], 
            'subtitleslangs': sub_langs, 
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
                'Referer': 'https://www.bilibili.com/',
            },
            'retries': 10,
            'fragment_retries': 10,
        }

        # 动态添加 Cookie 配置
        if use_cookies:
            ydl_opts['cookiesfrombrowser'] = ('edge',)

        if q_idx == 0: 
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4' 
        elif q_idx == 1: ydl_opts['format'] = 'bestvideo'
        elif q_idx == 2:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
            ydl_opts['writesubtitles'] = False
        elif q_idx == 3: ydl_opts['format'] = 'bestvideo,bestaudio'
        elif q_idx == 4:
            ydl_opts['format'] = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'

        video_path = None
        
        # 抛出异常由上层捕获
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if 'entries' in info: info = info['entries'][0]
            
            target_dir = os.path.join(DOWNLOAD_DIR, f"{info.get('uploader')} - {info.get('title')} [{info.get('id')}]")
            
            if q_idx in [2, 3]: return

            if os.path.exists(target_dir):
                for f in os.listdir(target_dir):
                    if f.endswith((".mp4", ".webm", ".mkv")) and "_Master" not in f and not f.endswith(".m4a"):
                        video_path = os.path.join(target_dir, f)
                        break

        if video_path and params['embed_sub'] and q_idx in [0, 4, 1]:
            self.burn_subs(video_path, keep_sub_file=params['save_sub_file'])

    def burn_subs(self, input_path, keep_sub_file=False):
        folder = os.path.dirname(input_path)
        filename = os.path.basename(input_path)
        basename_no_ext = os.path.splitext(filename)[0]
        
        ass_file = None
        potential_files = [f for f in os.listdir(folder) if f.startswith(basename_no_ext)]
        for f in potential_files:
            if f.endswith(".ass"): ass_file = f; break
        if not ass_file:
            for f in potential_files:
                 if f.endswith(".srt") and ("zh" in f or "CN" in f or "en" in f): ass_file = f; break
        
        if not ass_file:
             for f in os.listdir(folder): 
                 if f.endswith(".ass"): ass_file = f; break
        if not ass_file:
             for f in os.listdir(folder): 
                 if f.endswith(".srt"): ass_file = f; break

        if ass_file:
            self.signals.status.emit("GPU 渲染中...")
            self.signals.log.emit(f"🔥 烧录字幕: {ass_file}")
            output_name = filename.replace(".mp4", "_Master.mp4")
            if not output_name.endswith(".mp4"): output_name = os.path.splitext(output_name)[0] + "_Master.mp4"

            original_cwd = os.getcwd()
            try:
                os.chdir(folder)
                cmd = [FFMPEG_EXE, "-y", "-hwaccel", "cuda", "-i", filename, "-vf", f"subtitles='{ass_file}'", "-c:v", "h264_nvenc", "-preset", "p7", "-cq", "19", "-c:a", "copy", output_name]
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
                success = False
                try:
                    subprocess.run(cmd, startupinfo=si, capture_output=True, check=True)
                    self.signals.log.emit("✅ 完成: 已生成内嵌版 (GPU)")
                    success = True
                except subprocess.CalledProcessError:
                    self.signals.log.emit("⚠️ GPU 失败，切换 CPU...")
                    cmd_cpu = [FFMPEG_EXE, "-y", "-i", filename, "-vf", f"subtitles='{ass_file}'", "-c:v", "libx264", "-crf", "23", "-c:a", "copy", output_name]
                    try:
                        subprocess.run(cmd_cpu, startupinfo=si, check=True)
                        self.signals.log.emit("✅ 完成: 已生成内嵌版 (CPU)")
                        success = True
                    except: pass
                
                if success and not keep_sub_file:
                    try: os.remove(ass_file)
                    except: pass
            finally:
                os.chdir(original_cwd)
        else:
            self.signals.log.emit("⏩ 未找到字幕，跳过烧录")
