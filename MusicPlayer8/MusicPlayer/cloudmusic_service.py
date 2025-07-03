import os
import tempfile
import time
import logging
import cloudmusic
from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot
try:
    from .spotify import SpotifyAPI
except ImportError:
    from spotify import SpotifyAPI
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, APIC

class CloudMusicService(QObject):
    """使用cloudmusic模块的云音乐元数据服务"""
    # 信号定义
    metadata_found = pyqtSignal(dict)  # 元数据查询成功信号
    metadata_error = pyqtSignal(str)   # 元数据查询错误信号
    cover_downloaded = pyqtSignal(str, str)  # 封面下载完成信号 (文件路径, 封面路径)
    
    # 新增信号
    login_success = pyqtSignal()  # 登录成功信号
    login_failed = pyqtSignal(str)  # 登录失败信号
    
    def __init__(self):
        super().__init__()
        self._logged_in = False  # 改为私有变量
        self.metadata_cache = {}  # 缓存查询结果
        self.session_timeout = 3600  # 1小时会话超时
        self.last_login_time = 0
        self._username = None
        self._password = None
        self.spotify = None
        self._init_spotify()
        
    def _init_spotify(self):
        """初始化Spotify备用服务"""
        try:
            self.spotify = SpotifyAPI()
            logging.info("Spotify备用服务已初始化")
        except Exception as e:
            logging.warning(f"无法初始化Spotify服务: {str(e)}")
            self.spotify = None
        
    @property
    def is_logged_in(self):
        """检查当前登录状态，考虑会话超时"""
        if not self._logged_in:
            return False
        # 检查会话是否超时
        if time.time() - self.last_login_time > self.session_timeout:
            self._logged_in = False
            logging.info("会话已超时，自动登出")
        return self._logged_in
        
    def login(self, username=None, password=None, remember=False):
        """
        登录网易云账号
        :param username: 用户名
        :param password: 密码
        :param remember: 是否记住密码
        :return: 是否成功
        """
        try:
            if not username or not password:
                error_msg = "用户名和密码不能为空"
                logging.warning(error_msg)
                self.login_failed.emit(error_msg)
                return False
                
            # 执行登录
            logging.info(f"尝试登录网易云账号: {username}")
            cloudmusic.login(username, password)
            
            # 更新状态
            self._logged_in = True
            self._username = username
            self._password = password
            self.last_login_time = time.time()
            logging.info("登录成功")
            
            # 记住密码处理
            if remember:
                self._save_credentials(username, password)
                
            self.login_success.emit()
            return True
            
        except cloudmusic.LoginError as e:
            error_msg = f"登录失败: {str(e)}"
            if "captcha" in str(e).lower():
                error_msg += " (需要验证码)"
            self.login_failed.emit(error_msg)
            return False
        except Exception as e:
            self.login_failed.emit(f"登录错误: {str(e)}")
            return False
            
    def logout(self):
        """登出并清理会话"""
        self._logged_in = False
        self._username = None
        self._password = None
        self.last_login_time = 0
        logging.info("用户已登出")
        return True

    def _save_credentials(self, username, password):
        """安全保存凭据"""
        config_dir = os.path.join(os.path.expanduser("~"), ".musicplayer")
        os.makedirs(config_dir, exist_ok=True)
        cred_file = os.path.join(config_dir, "cloudmusic_creds")
        
        try:
            # 使用临时文件+原子重命名确保写入安全
            with tempfile.NamedTemporaryFile(
                mode='w',
                dir=config_dir,
                delete=False
            ) as tmp:
                tmp.write(f"{username}\n{password}")
                tmp_path = tmp.name
            
            # 设置权限并重命名
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, cred_file)
            logging.info("凭据已安全保存")
            
        except Exception as e:
            logging.error(f"保存凭据失败: {str(e)}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except:
                pass

    def _clear_credentials(self):
        """清理保存的凭据"""
        cred_file = os.path.join(
            os.path.expanduser("~"),
            ".musicplayer",
            "cloudmusic_creds"
        )
        try:
            if os.path.exists(cred_file):
                os.remove(cred_file)
                logging.info("已清理保存的凭据")
        except Exception as e:
            logging.error(f"清理凭据失败: {str(e)}")
    
    def get_song_metadata(self, file_path, local_metadata=None):
        """
        获取歌曲元数据（同步版本）
        :param file_path: 音乐文件路径
        :param local_metadata: 本地读取的元数据
        :return: 元数据字典或None
        """
        # 检查缓存
        if file_path in self.metadata_cache:
            return self.metadata_cache[file_path]
            
        metadata = None
            
        try:
            # 1. 优先使用云音乐查询
            if self._logged_in:
                # 准备查询关键词
                query = self._prepare_query(file_path, local_metadata)
                if query:
                    # 搜索匹配的歌曲
                    results = cloudmusic.search(query, limit=5, type='song')
                    if results:
                        # 选择最佳匹配
                        best_match = self._find_best_match(results, local_metadata)
                        if best_match:
                            # 获取完整元数据
                            metadata = self._format_metadata(best_match)
                            # 下载封面（异步）
                            self._download_cover_async(file_path, best_match.album.cover_url)
            
            # 2. 云音乐查询失败时回退到Spotify
            if not metadata and self.spotify and local_metadata:
                try:
                    # 使用本地元数据中的标题和艺术家作为查询条件
                    query = f"{local_metadata.get('title', '')} {local_metadata.get('artist', '')}"
                    if query.strip():
                        tracks = self.spotify.search_tracks(query, limit=1)
                        if tracks:
                            track = tracks[0]
                            metadata = {
                                'title': track['title'],
                                'artist': track['artist'],
                                'album': track['album'],
                                'duration': track['duration'],
                                'cover_url': track['cover_url'],
                                'source': 'spotify'
                            }
                            # 下载封面（异步）
                            if track['cover_url']:
                                self._download_cover_async(file_path, track['cover_url'])
                except Exception as e:
                    logging.error(f"Spotify查询失败: {str(e)}")
            
            # 存入缓存
            if metadata:
                self.metadata_cache[file_path] = metadata
            
        except Exception as e:
            self.metadata_error.emit(f"元数据查询失败: {str(e)}")
            return None
    
    @pyqtSlot(str, dict)
    def get_song_metadata_async(self, file_path, local_metadata=None):
        """异步获取歌曲元数据（通过信号返回结果）"""
        try:
            metadata = self.get_song_metadata(file_path, local_metadata)
            if metadata:
                self.metadata_found.emit({
                    'file_path': file_path,
                    'metadata': metadata
                })
        except Exception as e:
            self.metadata_error.emit(f"异步查询失败: {str(e)}")
    
    # ... [其余方法实现保持不变] ...

class CoverDownloadThread(QThread):
    """封面下载线程"""
    def __init__(self, file_path, cover_url, save_path):
        super().__init__()
        self.file_path = file_path
        self.cover_url = cover_url
        self.save_path = save_path
    
    def run(self):
        """下载封面到指定路径"""
        try:
            cloudmusic.download_cover(self.cover_url, self.save_path)
        except Exception as e:
            print(f"封面下载失败: {str(e)}")
            try:
                os.remove(self.save_path)
            except:
                pass