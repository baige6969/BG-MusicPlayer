import os
import sys
import random

import vlc
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, TIT2, TPE1, TALB
import importlib
import sys

# 检查核心依赖
REQUIRED_PACKAGES = {
    'cloudmusic': '1.0.0',
    'mutagen': '1.45.0',
    'PIL': '8.0.0',  # Pillow的导入名是PIL
    'PyQt5': '5.15.0'
}

def check_dependencies():
    missing = []
    for package, min_version in REQUIRED_PACKAGES.items():
        try:
            mod = importlib.import_module(package)
            # 更健壮的版本检测
            version = getattr(mod, '__version__', 
                            getattr(mod, 'version', '0.0.0'))
            if str(version) < min_version:
                missing.append(f"{package}>={min_version}")
        except ImportError as e:
            print(f"导入{package}时出错: {str(e)}")
            # 检查是否在虚拟环境中
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') 
                                            and sys.base_prefix != sys.prefix):
                print("检测到虚拟环境，请确认已激活正确环境")
            missing.append(package)
    
            if missing:
                print("\n依赖检查失败，诊断信息:")
                print(f"Python路径: {sys.executable}")
                print(f"Python版本: {sys.version.split()[0]}")
            
                try:
                    import pkg_resources
                    print("\n已安装包版本:")
                    for pkg in REQUIRED_PACKAGES:
                        try:
                            dist = pkg_resources.get_distribution(pkg)
                            print(f"{pkg}: {dist.version} (要求>={REQUIRED_PACKAGES[pkg]})")
                        except:
                            print(f"{pkg}: 未安装")
                except:
                    pass
            
                print("\n解决方案:")
                print("1. 确认使用正确的Python环境")
                print("2. 安装缺失依赖:")
                print(f"   {sys.executable} -m pip install {' '.join(missing)}")
                print("3. 如需创建虚拟环境:")
                print(f"   {sys.executable} -m venv venv")
                print("   venv\\Scripts\\activate")
                print("   pip install -r requirements.txt")
            
                sys.exit(1)

check_dependencies()

from mutagen.flac import FLAC
try:
    from mutagen.flac import FLACPicture
except ImportError:
    from mutagen.flac import Picture as FLACPicture
from concurrent.futures import ThreadPoolExecutor, as_completed
from mutagen.mp3 import MP3
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from typing import Dict, List, Optional, Tuple, Set, Any
from PyQt5.QtCore import Qt

class MusicPlayer(QObject):
    positionChanged = pyqtSignal(float, int)  # (position, length_ms)
    metadata_updated = pyqtSignal(str, dict)  # (file_path, metadata)
    
    """音乐播放器核心功能"""
    
    def __init__(self, cloud_service: Optional[Any] = None) -> None:
    
    def _handle_cloud_metadata(self, data):
        """处理云元数据查询结果"""
        file_path = data['file_path']
        metadata = data['metadata']
        
        # 更新缓存
        if file_path in self.metadata_cache:
            self.metadata_cache[file_path].update(metadata)
        else:
            self.metadata_cache[file_path] = metadata
            
        # 通知更新
        self.metadata_updated.emit(file_path, metadata)
        
    def _handle_cover_download(self, file_path, cover_path):
        """处理封面下载完成"""
        try:
            if file_path in self.metadata_cache:
                # 更新文件元数据
                self._update_file_metadata(file_path, cover_path)
                
                # 通知UI更新封面
                self.metadata_updated.emit(file_path, self.metadata_cache[file_path])
                
            # 清理临时文件
            if os.path.exists(cover_path):
                os.remove(cover_path)
        except Exception as e:
            print(f"封面处理失败: {str(e)}")
            
    def _handle_cloud_error(self, error_msg):
        """处理云服务错误"""
        print(f"云服务错误: {error_msg}")
    
    def __init__(self, cloud_service=None):
        super().__init__()
        
        # 元数据缓存 {file_path: metadata}
        self.metadata_cache = {}
        self._executor = None  # 线程池
        
        # 初始化云服务
        self.cloud_service = cloud_service
        
        # 连接云服务信号(确保线程安全)
        if self.cloud_service:
            try:
                # 检查云服务是否可用
                if not hasattr(self.cloud_service, 'is_available') or not self.cloud_service.is_available():
                    raise RuntimeError("云服务不可用")
                    
                # 连接信号
                self.cloud_service.metadata_found.connect(
                    self._handle_cloud_metadata,
                    Qt.QueuedConnection)
                self.cloud_service.cover_downloaded.connect(
                    self._handle_cover_download,
                    Qt.QueuedConnection)
                self.cloud_service.metadata_error.connect(
                    self._handle_cloud_error,
                    Qt.QueuedConnection)
                    
                print("云服务连接成功")
            except Exception as e:
                print(f"云服务初始化失败: {str(e)}")
                self.cloud_service = None
                # 记录详细错误信息
                import traceback
                traceback.print_exc()
                
        # 自动检测VLC路径
        vlc_paths = []
        if getattr(sys, 'frozen', False):
            # 打包后从多个可能位置查找
            base_dir = os.path.dirname(sys.executable)
            possible_paths = [
                os.path.join(base_dir, 'vlc'),
                os.path.join(base_dir, '..', 'vlc'),
                os.path.join(base_dir, 'lib', 'vlc')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    vlc_paths.append(path)
                    # Windows下添加到系统路径
                    if os.name == 'nt':
                        os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
        
        # 初始化VLC实例
        self.vlc_loaded = False
        self.instance = None
        self.player = None
        
        # 尝试多个初始化方案
        init_attempts = [
            # 尝试使用检测到的路径
            *(vlc.Instance([f'--plugin-path={path}']) for path in vlc_paths),
            # 尝试默认路径
            vlc.Instance(),
            # 尝试最小化插件路径
            vlc.Instance(['--plugin-path=/usr/lib/vlc/plugins'])
        ]
        
        last_error = None
        for attempt in init_attempts:
            try:
                self.instance = attempt
                self.player = self.instance.media_player_new()
                if self.player:
                    self.vlc_loaded = True
                    # 设置合理的VLC参数
                    self.player.video_set_scale(0)  # 禁用视频缩放
                    print("VLC初始化成功")
                    break
            except Exception as e:
                last_error = e
                continue
                
        if not self.vlc_loaded:
            error_msg = "VLC初始化失败:\n"
            if getattr(sys, 'frozen', False):
                error_msg += "1. 请确保已安装VLC播放器\n"
                error_msg += "2. 或从应用目录中解压vlc文件夹\n"
                error_msg += f"尝试的路径: {', '.join(vlc_paths) or '无'}\n"
            error_msg += f"错误详情: {str(last_error)}"
            
            # 记录详细错误信息
            import traceback
            traceback.print_exc()
            
            raise RuntimeError(error_msg) from last_error
        
        # 播放状态
        self.is_playing = False
        self.current_media = None
        self.current_playlist = []
        self.current_index = -1
        self.play_mode = "sequential"  # sequential/random
        self.played_indices = set()    # 记录已播放索引(随机模式用)
        
        # 云服务实例
        self.cloud_service = cloud_service
        
        # 进度更新定时器
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.start(100)  # 每100ms更新一次
        
        # 支持的音频格式
        self.supported_formats = (
            '.mp3', '.wav', '.flac', '.ogg',
            '.m4a', '.aac', '.wma', '.opus'
        )
        
    def is_supported_format(self, file_path):
        """检查文件格式是否支持"""
        return any(file_path.lower().endswith(fmt) for fmt in self.supported_formats)
        
    def load(self, file_path: str) -> None:
        """加载音乐文件
        :param file_path: 要加载的音乐文件路径
        :raises FileNotFoundError: 当文件不存在时
        :raises ValueError: 当文件格式不支持时
        :raises RuntimeError: 当文件加载失败时
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        if not self.is_supported_format(file_path):
            raise ValueError(f"不支持的音频格式: {os.path.splitext(file_path)[1]}")
            
        self.current_media = self.instance.media_new(file_path)
        self.player.set_media(self.current_media)
        
    def play(self, file_path: Optional[str] = None) -> bool:
        """播放音乐
        :param file_path: 可选，要播放的文件路径。如果提供，会先加载文件
        :return: 是否成功开始播放
        :raises FileNotFoundError: 当文件不存在时
        :raises RuntimeError: 当播放器初始化失败时
        :raises ValueError: 当文件格式不支持时
        """
        try:
            if not self.vlc_loaded:
                raise RuntimeError("VLC播放器未初始化")
                
            if file_path:
                self.load(file_path)
                
            if not self.current_media:
                raise RuntimeError("未加载有效的媒体文件")
                
            # 执行播放
            if self.player.play() == -1:
                raise RuntimeError("VLC播放失败")
                
            self.is_playing = True
            print(f"[INFO] 开始播放: {file_path or '当前媒体'}")
            return True
            
        except Exception as e:
            error_msg = f"播放失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            logging.error(error_msg)
            self.is_playing = False
            raise
    
    def pause(self) -> None:
        """暂停播放
        :raises RuntimeError: 当播放器未初始化或控制失败时
        """
        try:
            if not self.vlc_loaded:
                raise RuntimeError("VLC播放器未初始化")
                
            if not self.is_playing:
                print("[WARN] 尝试暂停但播放器未在播放状态")
                return
                
            if self.player.pause() == -1:
                raise RuntimeError("VLC暂停失败")
                
            self.is_playing = False
            print("[INFO] 播放已暂停")
            
        except Exception as e:
            error_msg = f"暂停失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            logging.error(error_msg)
            raise
    
    def stop(self) -> None:
        """停止播放
        :raises RuntimeError: 当播放器未初始化或控制失败时
        """
        try:
            if not self.vlc_loaded:
                raise RuntimeError("VLC播放器未初始化")
                
            # 检查当前状态
            if not self.is_playing and (not self.player or self.player.get_state() == vlc.State.Stopped):
                print("[INFO] 播放器已在停止状态")
                return
                
            # 执行停止操作
            if self.player.stop() == -1:
                raise RuntimeError("VLC停止失败")
                
            # 确保状态同步
            self.is_playing = False
            print("[INFO] 播放已停止")
            
            # 释放当前媒体资源
            self.player.set_media(None)
            self.current_media = None
            
        except Exception as e:
            error_msg = f"停止失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            logging.error(error_msg)
            raise

    def release_resources(self):
        """释放所有资源
        :raises RuntimeError: 当资源释放失败时
        """
        try:
            # 1. 停止播放
            if self.is_playing or (self.player and self.player.get_state() != vlc.State.Stopped):
                self.stop()
            
            # 2. 停止定时器
            if hasattr(self, 'position_timer') and self.position_timer.isActive():
                self.position_timer.stop()
                self.position_timer = None
            
            # 3. 释放VLC资源(按正确顺序)
            if self.player:
                try:
                    self.player.release()
                except Exception as e:
                    print(f"[WARN] 播放器释放失败: {str(e)}")
                finally:
                    self.player = None
                    self.vlc_loaded = False
                
            if self.instance:
                try:
                    self.instance.release()
                except Exception as e:
                    print(f"[WARN] VLC实例释放失败: {str(e)}")
                finally:
                    self.instance = None
                
            # 4. 关闭线程池
            if hasattr(self, '_executor'):
                try:
                    self._executor.shutdown(wait=False)
                except Exception as e:
                    print(f"[WARN] 线程池关闭失败: {str(e)}")
                finally:
                    self._executor = None
                
            # 5. 清理缓存和状态
            self.metadata_cache.clear()
            self.current_playlist = []
            self.current_index = -1
            self.played_indices = set()
            
            print("[INFO] 播放器资源已完全释放")
            
        except Exception as e:
            error_msg = f"资源释放失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            logging.error(error_msg)
            raise

    def _update_position(self):
        """更新播放进度"""
        if self.is_playing:
            pos = self.player.get_time()
            length = self.player.get_length()
            if pos >= 0 and length > 0:
                self.positionChanged.emit(pos, length)

    def set_play_mode(self, mode):
        """设置播放模式
        :param mode: "sequential" 或 "random"
        """
        if mode not in ("sequential", "random"):
            raise ValueError("播放模式必须是'sequential'或'random'")
        self.play_mode = mode
        self.played_indices = set()
        if self.current_index >= 0:
            self.played_indices.add(self.current_index)

    def prev(self):
        """播放上一首"""
        if not self.current_playlist:
            return
            
        if self.play_mode == "sequential":
            self.current_index = max(0, self.current_index - 1)
        else:  # random模式不支持后退，保持当前歌曲
            pass
            
        self.play(self.current_playlist[self.current_index])

    def next(self):
        """播放下一首"""
        if not self.current_playlist:
            return
            
        if self.play_mode == "sequential":
            self.current_index = (self.current_index + 1) % len(self.current_playlist)
        else:  # random模式
            # 记录当前播放
            if self.current_index >= 0:
                self.played_indices.add(self.current_index)
                
            # 获取未播放歌曲
            unplayed = [i for i in range(len(self.current_playlist)) 
                       if i not in self.played_indices]
            
            if not unplayed:  # 全部播放过则重置
                self.played_indices = set()
                unplayed = list(range(len(self.current_playlist)))
                if self.current_index in unplayed and len(unplayed) > 1:
                    unplayed.remove(self.current_index)
            
            # 随机选择下一首
            self.current_index = random.choice(unplayed)
            
        self.play(self.current_playlist[self.current_index])
    
    def set_volume(self, value: int) -> None:
        """设置音量
        :param value: 音量值，范围0-100
        :raises ValueError: 当音量值超出范围时
        :raises RuntimeError: 当音量设置失败时
        """
        # 确保值在有效范围内
        volume = max(0, min(100, value))
        print(f"[DEBUG] Setting volume to: {volume}")  # 调试输出
        self.player.audio_set_volume(volume)
    
    def get_volume(self) -> int:
        """获取当前音量
        :return: 当前音量值(0-100)
        :raises RuntimeError: 当获取音量失败时
        """
        return self.player.audio_get_volume()
        
    def save_playlist(self, file_path, playlist):
        """
        保存播放列表到文件
        :param file_path: 保存路径
        :param playlist: 播放列表(文件路径列表)
        """
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                'version': 1,
                'playlist': playlist
            }, f, ensure_ascii=False, indent=2)
            
    def load_playlist(self, file_path):
        """
        从文件加载播放列表
        :param file_path: 播放列表文件路径
        :return: 播放列表(文件路径列表)
        """
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('playlist', [])
    
    def get_position(self):
        """获取播放进度(0.0-1.0)"""
        return self.player.get_position()
    
    def set_position(self, position):
        """设置播放进度(0.0-1.0)"""
        self.player.set_position(position)
    
    def get_length(self):
        """获取歌曲长度(毫秒)"""
        return self.player.get_length()
    
    def is_playing(self):
        """检查是否正在播放"""
        return self.is_playing
    
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
            
    def get_metadata(self, file_path, async_cloud=True):
        """
        获取音频文件元数据
        :param file_path: 音频文件路径
        :param async_cloud: 是否异步获取云数据
        :return: 元数据字典
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
            
        # 1. 检查缓存
        if file_path in self.metadata_cache:
            return self.metadata_cache[file_path]
            
        # 2. 获取本地元数据
        metadata = self._get_local_metadata(file_path)
        self.metadata_cache[file_path] = metadata
        
        # 3. 异步获取云元数据
        if self.cloud_service and async_cloud:
            self._fetch_cloud_metadata_async(file_path)
            
        return metadata
        
    def _get_local_metadata(self, file_path: str) -> Dict[str, Any]:
        """获取本地元数据
        :param file_path: 音频文件路径
        :return: 包含元数据的字典，可能包含以下键:
            - title: 歌曲标题
            - artist: 艺术家
            - album: 专辑
            - duration: 时长(秒)
            - bitrate: 比特率(kbps)
            - source: 元数据来源('local')
        :raises RuntimeError: 当元数据读取失败时
        """
        try:
            ext = os.path.splitext(file_path)[1].lower()
            metadata = {'source': 'local'}
            
            if ext == '.mp3':
                audio = MP3(file_path, ID3=EasyID3)
                metadata.update({
                    'title': audio.get('title', [''])[0],
                    'artist': audio.get('artist', [''])[0],
                    'album': audio.get('album', [''])[0],
                    'duration': audio.info.length,
                    'bitrate': audio.info.bitrate // 1000
                })
            elif ext == '.flac':
                audio = FLAC(file_path)
                metadata.update({
                    'title': audio.get('title', [''])[0],
                    'artist': audio.get('artist', [''])[0],
                    'album': audio.get('album', [''])[0],
                    'duration': audio.info.length,
                    'bitrate': audio.info.bitrate // 1000
                })
                
            return metadata
        except Exception as e:
            print(f"本地读取元数据失败: {e}")
            return {}

    def _update_file_metadata(self, file_path: str, cover_path: Optional[str] = None) -> None:
        """更新音频文件元数据
        :param file_path: 要更新的音频文件路径
        :param cover_path: 封面图片路径(可选)
        :raises FileNotFoundError: 当文件不存在时
        :raises PermissionError: 当没有写入权限时
        :raises RuntimeError: 当元数据写入失败时
        """
        if file_path not in self.metadata_cache:
            return
            
        metadata = self.metadata_cache[file_path]
        if not metadata:
            return
            
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == '.mp3':
                audio = MP3(file_path, ID3=EasyID3)
                # 更新文本元数据
                if metadata.get('title'):
                    audio['title'] = metadata['title']
                if metadata.get('artist'):
                    audio['artist'] = metadata['artist']
                if metadata.get('album'):
                    audio['album'] = metadata['album']
                    
                # 更新封面
                if cover_path and os.path.exists(cover_path):
                    with open(cover_path, 'rb') as f:
                        audio.tags.add(APIC(
                            encoding=3,
                            mime='image/jpeg' if cover_path.lower().endswith(('.jpg', '.jpeg')) else 'image/png',
                            desc='Cover',
                            data=f.read()
                        ))
                
                audio.save()
                
            elif ext == '.flac':
                audio = FLAC(file_path)
                # 更新文本元数据
                if metadata.get('title'):
                    audio['title'] = metadata['title']
                if metadata.get('artist'):
                    audio['artist'] = metadata['artist']
                if metadata.get('album'):
                    audio['album'] = metadata['album']
                    
                # 更新封面
                if cover_path and os.path.exists(cover_path):
                    with open(cover_path, 'rb') as f:
                        cover_data = f.read()
                        try:
                            # 尝试使用FLACPicture
                            picture = FLACPicture()
                        except (ImportError, NameError):
                            # 回退到Picture类
                            from mutagen.flac import Picture
                            picture = Picture()
                        
                        # 设置图片属性
                        picture.type = 3  # Front cover
                        picture.mime = 'image/jpeg' if cover_data.startswith(b'\xff\xd8') else 'image/png'
                        picture.desc = 'Cover'
                        picture.data = cover_data
                        
                        audio.clear_pictures()
                        audio.add_picture(picture)
                
                audio.save()
                
            print(f"元数据更新成功: {file_path}")
            
        except Exception as e:
            print(f"更新文件元数据失败: {str(e)}")
        
    def _fetch_cloud_metadata_async(self, file_path: str) -> None:
        """异步获取云元数据
        :param file_path: 音频文件路径
        :raises RuntimeError: 当云服务不可用时
        """
        if not self.cloud_service:
            return
            
        # 获取本地元数据作为查询基础
        local_metadata = self.get_metadata(file_path, async_cloud=False)
        
        # 使用新的云服务接口异步查询
        self.cloud_service.get_song_metadata_async(file_path, local_metadata)
        
    def get_metadata_batch(self, file_paths, progress_callback=None):
        """
        批量获取音频文件元数据(多线程)
        :param file_paths: 文件路径列表
        :param progress_callback: 进度回调函数，格式: callback(current, total)
        :return: 元数据字典列表，顺序与输入路径一致
        """
        results = [None] * len(file_paths)
        
        def process_file(idx, path):
            try:
                return idx, self.get_metadata(path)
            except Exception as e:
                print(f"处理文件 {path} 失败: {e}")
                return idx, None
                
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for idx, path in enumerate(file_paths):
                futures.append(executor.submit(process_file, idx, path))
                
            for i, future in enumerate(as_completed(futures)):
                idx, result = future.result()
                results[idx] = result
                if progress_callback:
                    progress_callback(i+1, len(file_paths))
                    
        return results
        
    def query_cloud_metadata(self, file_path):
        """
        查询云服务获取元数据
        :param file_path: 音频文件路径
        :return: 元数据字典或None
        """
        if not self.cloud_service:
            print("警告: 未配置云服务，无法查询云端元数据")
            return None
            
        try:
            # 调用云服务查询元数据
            metadata = self.cloud_service.query_song_metadata(file_path)
            if metadata:
                metadata['source'] = 'cloud'  # 确保标记来源
                return metadata
        except Exception as e:
            print(f"云服务查询失败: {e}")
            
        return None