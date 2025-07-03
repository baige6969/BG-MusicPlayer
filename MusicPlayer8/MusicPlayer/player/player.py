from PyQt5.QtCore import QObject, pyqtSignal, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import logging
import os
import vlc
from MusicPlayer.services import MusicRouter

class VLCPlayer:
    """VLC播放器实现"""
    def __init__(self):
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.current_media = None
        
    def play(self, file_path):
        """播放指定文件"""
        if not os.path.exists(file_path):
            return False
            
        self.current_media = self.instance.media_new(file_path)
        self.player.set_media(self.current_media)
        return self.player.play() == 0
        
    def stop(self):
        """停止播放"""
        self.player.stop()
        
    def pause(self):
        """暂停播放"""
        self.player.pause()
        
    def set_volume(self, volume):
        """设置音量(0-100)"""
        try:
            volume = max(0, min(100, volume))  # 确保音量在有效范围内
            if not hasattr(self.player, 'audio_set_volume'):
                logging.error("VLC播放器缺少音量控制功能")
                return False
                
            if self.player.audio_set_volume(volume) == -1:
                logging.error("VLC设置音量失败")
                return False
                
            logging.debug(f"VLC音量已设置为: {volume}")
            return True
            
        except Exception as e:
            logging.error(f"VLC设置音量失败: {str(e)}")
            return False
        
    def get_volume(self):
        """获取当前音量"""
        return self.player.audio_get_volume()
        
    def get_position(self):
        """获取播放位置(0.0-1.0)
        Returns:
            float: 播放位置(0.0-1.0)，无效时返回0.0
        """
        try:
            pos = self.player.get_position()
            # 验证位置范围
            if pos is None or pos < 0 or pos > 1 or math.isnan(pos):
                logging.debug("VLC返回无效播放位置，已过滤")
                return 0.0
            return pos
        except Exception as e:
            logging.debug(f"获取VLC播放位置失败: {str(e)}")
            return 0.0
        
    def set_position(self, pos):
        """设置播放位置(0.0-1.0)"""
        self.player.set_position(pos)

class MusicPlayer(QObject):
    positionChanged = pyqtSignal(int)  # 播放位置改变信号(毫秒)
    stateChanged = pyqtSignal(str)    # 播放状态改变信号
    errorOccurred = pyqtSignal(str)   # 错误发生信号
    playbackFinished = pyqtSignal()   # 播放结束信号
    volumeChanged = pyqtSignal(int, bool)  # 音量改变信号(音量值, 是否静音)

    def __init__(self):
        super().__init__()
        self.current_track = None
        self.playlist = []  # 播放列表
        self.current_index = -1  # 当前播放索引
        self.random_mode = False  # 随机播放模式
        self.supported_formats = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']
        self._is_initialized = False
        self.is_playing = False
        self._backend_available = True
        self._using_vlc = False
        self.media_player = None
        self._track_finished = False  # 标记当前曲目是否播放完毕
        self._is_muted = False  # 标记当前是否静音
        
        # 初始化音乐服务路由器
        self.music_router = MusicRouter()
        self._last_service_used = None  # 记录上次使用的服务('netease', 'spotify'等)
        
        # 初始化引擎标志
        self._using_vlc = False
        self._backend_available = False
        self.vlc_player = None
        self.media_player = None
        
        # 保存当前状态以便恢复
        prev_state = {
            'current_track': None,
            'position': 0,
            'volume': 50,
            'playing': False
        }
        
        # 优先尝试VLC引擎
        try:
            logging.info("正在初始化VLC引擎...")
            self.vlc_player = VLCPlayer()
            self._using_vlc = True
            self._backend_available = True
            
            # 连接VLC信号
            if hasattr(self.vlc_player.player, 'event_manager'):
                self.vlc_player.player.event_manager().event_attach(
                    vlc.EventType.MediaPlayerEndReached, 
                    self._handle_playback_finished
                )
                
            logging.info("VLC引擎初始化成功")
            return  # 成功初始化VLC，直接返回
            
        except vlc.VLCException as e:
            logging.error(f"VLC引擎初始化失败(VLC异常): {str(e)}")
        except ImportError as e:
            logging.error(f"VLC引擎初始化失败(导入错误): {str(e)}")
        except Exception as e:
            logging.error(f"VLC引擎初始化失败(未知错误): {str(e)}")
            
        # 回退到Qt媒体引擎
        try:
            logging.info("正在初始化Qt媒体引擎...")
            self.media_player = QMediaPlayer()
            self.media_player.setMedia(QMediaContent())
            self._backend_available = True
            
            # 连接Qt信号
            self.media_player.mediaStatusChanged.connect(self._handle_media_status_changed)
            self.media_player.positionChanged.connect(self._handle_position_changed)
            self.media_player.durationChanged.connect(self._handle_duration_changed)
            self.media_player.stateChanged.connect(self._handle_state_changed)
            self.media_player.error.connect(self._handle_error)
            
            logging.info("Qt媒体引擎初始化成功")
            
        except ImportError as e:
            logging.error(f"Qt媒体引擎初始化失败(导入错误): {str(e)}")
            self._backend_available = False
            raise RuntimeError("无法初始化任何媒体引擎")
        except Exception as e:
            logging.error(f"Qt媒体引擎初始化失败(未知错误): {str(e)}")
            self._backend_available = False
            raise RuntimeError("无法初始化任何媒体引擎")
        
        # 仅在media_player存在时连接信号
        if self.media_player is not None:
            self.media_player.positionChanged.connect(self._handle_position_changed)
            self.media_player.durationChanged.connect(self._handle_duration_changed)
            self.media_player.stateChanged.connect(self._handle_state_changed)
            self.media_player.error.connect(self._handle_error)
        else:
            logging.warning("无法连接媒体播放器信号: media_player不可用")

    def _handle_position_changed(self, position):
        """处理实际播放位置变化"""
        if self._using_vlc:
            # VLC引擎需要转换为毫秒
            if hasattr(self.vlc_player.player, 'get_length'):
                duration = self.vlc_player.player.get_length()
                if duration > 0:
                    position = int(self.vlc_player.get_position() * duration)
        self.positionChanged.emit(position)

    def _handle_duration_changed(self, duration):
        """处理曲目时长变化"""
        if duration > 0:
            # 发送总时长信号
            self.positionChanged.emit(self.media_player.position(), duration)

    def _handle_state_changed(self, state):
        """处理播放状态变化"""
        self.is_playing = (state == QMediaPlayer.PlayingState)
        state_str = {
            QMediaPlayer.PlayingState: "playing",
            QMediaPlayer.PausedState: "paused",
            QMediaPlayer.StoppedState: "stopped"
        }.get(state, "unknown")
        self.stateChanged.emit(state_str)

    def _handle_error(self, error):
        """处理播放错误"""
        self.errorOccurred.emit(self.media_player.errorString())

    def is_supported_format(self, file_path):
        """检查文件格式是否支持"""
        return any(file_path.lower().endswith(fmt) for fmt in self.supported_formats)

    def get_supported_formats(self):
        """获取支持的音频格式列表"""
        return self.supported_formats

    def add_supported_format(self, format_extension):
        """添加支持的音频格式"""
        if not format_extension.startswith('.'):
            format_extension = '.' + format_extension
        if format_extension.lower() not in self.supported_formats:
            self.supported_formats.append(format_extension.lower())

    def _validate_state(self):
        """验证播放器状态一致性"""
        if self.playlist and 0 <= self.current_index < len(self.playlist):
            if self.current_track != self.playlist[self.current_index]:
                logging.warning("状态不一致: current_track与current_index不匹配")
                return False
        elif self.current_track is not None:
            logging.warning("状态不一致: 有当前曲目但无有效播放列表索引")
            return False
        return True

    def _play_url(self, url):
        """播放在线URL
        Args:
            url: 要播放的音频URL
        Returns:
            bool: 播放是否成功
        """
        if not self._backend_available:
            self.errorOccurred.emit("播放器引擎不可用")
            logging.error("播放失败: 播放器引擎不可用")
            return False
            
        try:
            if self._using_vlc:
                # VLC引擎播放
                media = self.vlc_player.instance.media_new(url)
                self.vlc_player.player.set_media(media)
                success = self.vlc_player.player.play() == 0
            else:
                # Qt引擎播放
                self.media_player.setMedia(QMediaContent(QUrl(url)))
                self.media_player.play()
                success = True
                
            if success:
                self.is_playing = True
                self.stateChanged.emit("playing")
                logging.info(f"正在播放在线音频: {url}")
                return True
            else:
                error_msg = "播放失败: 引擎返回错误"
                self.errorOccurred.emit(error_msg)
                logging.error(error_msg)
                return False
                
        except vlc.VLCException as e:
            error_msg = f"VLC播放失败: {str(e)}"
            logging.error(error_msg)
            self.errorOccurred.emit(error_msg)
            return False
        except Exception as e:
            error_msg = f"播放失败: {type(e).__name__} - {str(e)}"
            logging.error(error_msg)
            self.errorOccurred.emit(error_msg)
            return False

    def play(self, track=None, retry_count=0):
        """播放指定曲目或继续播放
        Args:
            track: 要播放的音频文件路径或URL或包含音乐服务信息的字典
            retry_count: 内部重试计数器(0-2)
        Returns:
            bool: 播放是否成功
        """
        if not self._backend_available:
            self.errorOccurred.emit("播放器引擎不可用")
            logging.error("播放失败: 播放器引擎不可用")
            return False
            
        # 状态验证和恢复
        if not self._validate_state():
            logging.warning("播放前状态验证失败，尝试恢复状态")
            self.current_index = -1
            self.current_track = None
            
        # 处理track参数
        if track is None:
            if self.current_track is None:
                self.errorOccurred.emit("没有指定曲目且当前无曲目在播放")
                logging.error("播放失败: 未指定曲目且无当前曲目")
                return False
        else:
            # 处理不同类型track参数
            if isinstance(track, dict):
                # 字典类型参数
                if 'url' in track:
                    # 直接播放URL
                    success = self._play_url(track['url'])
                    if success:
                        self.current_track = track
                    return success
                elif 'path' in track:
                    # 本地文件路径
                    track = track['path']
                elif 'id' in track and 'source' in track:
                    # 使用音乐服务路由
                    url = self.music_router.get_playback_url(
                        track['id'],
                        track['source']
                    )
                    if url:
                        self._last_service_used = track['source']
                        success = self._play_url(url)
                        if success:
                            self.current_track = track
                        return success
                    else:
                        error_msg = f"无法获取{track['source']}播放URL"
                        self.errorOccurred.emit(error_msg)
                        logging.error(f"播放失败: {error_msg}")
                        return False
                else:
                    error_msg = "无效的曲目信息格式"
                    self.errorOccurred.emit(error_msg)
                    logging.error(f"播放失败: {error_msg}")
                    return False
            
            # 处理字符串类型track参数
            if isinstance(track, str):
                # 检查是否是URL
                if track.startswith(('http://', 'https://')):
                    success = self._play_url(track)
                    if success:
                        self.current_track = track
                    return success
                
                # 检查文件格式
                if not self.is_supported_format(track):
                    error_msg = f"不支持的音频格式: {os.path.splitext(track)[1]}"
                    self.errorOccurred.emit(error_msg)
                    logging.error(f"播放失败: {error_msg}")
                    return False
                    
                # 检查文件存在性
                if not os.path.exists(track):
                    error_msg = f"音频文件不存在: {track}"
                    self.errorOccurred.emit(error_msg)
                    logging.error(f"播放失败: {error_msg}")
                    return False
                    
                self.current_track = track
            else:
                error_msg = "不支持的曲目信息类型"
                self.errorOccurred.emit(error_msg)
                logging.error(f"播放失败: {error_msg}")
                return False
            
        try:
            success = False
            if self._using_vlc:
                # VLC引擎播放
                success = self.vlc_player.play(self.current_track)
                if not success and retry_count < 2:  # 最多重试2次
                    logging.warning(f"VLC播放失败，正在重试({retry_count+1}/2)...")
                    time.sleep(0.5)  # 短暂延迟后重试
                    return self.play(track, retry_count+1)
            else:
                # Qt引擎播放
                if not hasattr(self.media_player, 'setMedia') or not hasattr(self.media_player, 'play'):
                    raise AttributeError("Qt播放器缺少播放功能")
                    
                self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(self.current_track)))
                self.media_player.play()
                success = True
                
            if success:
                self.is_playing = True
                self.stateChanged.emit("playing")
                logging.info(f"正在播放: {os.path.basename(self.current_track)}")
                return True
            else:
                error_msg = "播放失败: 引擎返回错误"
                self.errorOccurred.emit(error_msg)
                logging.error(error_msg)
                return False
                
        except vlc.VLCException as e:
            error_msg = f"VLC播放失败: {str(e)}"
            logging.error(error_msg)
            self.errorOccurred.emit(error_msg)
            self._handle_playback_error(e)
            return False
        except Exception as e:
            error_msg = f"播放失败: {type(e).__name__} - {str(e)}"
            logging.error(error_msg)
            self.errorOccurred.emit(error_msg)
            self._handle_playback_error(e)
            return False

    def _handle_playback_error(self, error):
        """处理播放错误并恢复状态"""
        self.is_playing = False
        self.stateChanged.emit("error")
        
        # 尝试释放资源
        try:
            if self._using_vlc:
                self.vlc_player.stop()
            else:
                self.media_player.stop()
        except Exception as e:
            logging.warning(f"清理播放器资源失败: {str(e)}")
            
        logging.info("已恢复播放器错误状态")

    def pause(self):
        """暂停播放"""
        if not self._backend_available:
            self.errorOccurred.emit("播放器引擎不可用")
            return False
            
        if not self._validate_state():
            logging.warning("暂停前状态验证失败")
            return False
            
        try:
            if self._using_vlc:
                self.vlc_player.pause()
            else:
                self.media_player.pause()
                
            self.is_playing = False
            self.stateChanged.emit("paused")
            logging.debug("播放已暂停")
            return True
            
        except vlc.VLCException as e:
            logging.error(f"VLC暂停失败: {str(e)}")
            self.errorOccurred.emit(f"VLC暂停失败: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"暂停失败: {str(e)}")
            self.errorOccurred.emit(f"暂停失败: {type(e).__name__} - {str(e)}")
            return False

    def stop(self):
        """停止播放"""
        if not self._backend_available:
            self.errorOccurred.emit("播放器引擎不可用")
            return False
            
        if not self._validate_state():
            logging.warning("停止前状态验证失败")
            return False
            
        try:
            if self._using_vlc:
                self.vlc_player.stop()
            else:
                self.media_player.stop()
                
            self.current_track = None
            self.is_playing = False
            self.stateChanged.emit("stopped")
            logging.debug("播放已停止")
            return True
            
        except vlc.VLCException as e:
            logging.error(f"VLC停止失败: {str(e)}")
            self.errorOccurred.emit(f"VLC停止失败: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"停止失败: {str(e)}")
            self.errorOccurred.emit(f"停止失败: {type(e).__name__} - {str(e)}")
            return False

    def set_volume(self, volume):
        """设置音量(0-100)
        Args:
            volume: 音量值(0-100)
        Returns:
            bool: 操作是否成功
        """
        if not self._backend_available:
            self.errorOccurred.emit("播放器引擎不可用")
            logging.error("设置音量失败: 播放器引擎不可用")
            return False
            
        try:
            # 验证音量范围
            if not isinstance(volume, (int, float)) or volume < 0 or volume > 100:
                error_msg = f"无效的音量值: {volume}"
                self.errorOccurred.emit(error_msg)
                logging.error(error_msg)
                return False
                
            # 应用音量设置
            if self._using_vlc:
                if not hasattr(self.vlc_player, 'set_volume'):
                    error_msg = "VLC播放器缺少音量设置功能"
                    self.errorOccurred.emit(error_msg)
                    logging.error(error_msg)
                    return False
                    
                if not self.vlc_player.set_volume(volume):
                    error_msg = "VLC设置音量失败"
                    self.errorOccurred.emit(error_msg)
                    logging.error(error_msg)
                    return False
            else:
                if not hasattr(self.media_player, 'setVolume'):
                    error_msg = "Qt播放器缺少音量设置功能"
                    self.errorOccurred.emit(error_msg)
                    logging.error(error_msg)
                    return False
                    
                self.media_player.setVolume(volume)
                
            # 更新静音状态
            if volume > 0 and self._is_muted:
                self._is_muted = False
                self.volumeChanged.emit(volume, False)
            else:
                self.volumeChanged.emit(volume, self._is_muted)
                
            logging.debug(f"音量已设置为: {volume}")
            return True
            
        except vlc.VLCException as e:
            error_msg = f"VLC设置音量失败: {str(e)}"
            self.errorOccurred.emit(error_msg)
            logging.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"设置音量失败: {str(e)}"
            self.errorOccurred.emit(error_msg)
            logging.error(error_msg)
            return False

    def get_last_service_used(self):
        """获取上次使用的音乐服务
        Returns:
            str: 服务名称('netease', 'spotify'等)或None(如果是本地文件)
        """
        return self._last_service_used

    def get_volume(self):
        """获取当前音量(0-100)
        Returns:
            int: 当前音量值(0-100)
        """
        if not self._backend_available:
            logging.warning("获取音量失败: 播放器引擎不可用")
            return 50
            
        try:
            if self._using_vlc:
                if not hasattr(self.vlc_player, 'get_volume'):
                    logging.error("VLC播放器缺少音量获取功能")
                    return 50
                return self.vlc_player.get_volume()
            else:
                if not hasattr(self.media_player, 'volume'):
                    logging.error("Qt播放器缺少音量获取功能")
                    return 50
                return self.media_player.volume()
                
        except vlc.VLCException as e:
            logging.error(f"获取VLC音量失败: {str(e)}")
            return 50
        except Exception as e:
            logging.error(f"获取音量失败: {str(e)}")
            return 50

    def toggle_mute(self):
        """切换静音状态
        Returns:
            bool: 操作是否成功
        """
        if not self._backend_available:
            self.errorOccurred.emit("播放器引擎不可用")
            logging.error("切换静音失败: 播放器引擎不可用")
            return False
            
        try:
            self._is_muted = not self._is_muted
            
            if self._using_vlc:
                if not hasattr(self.vlc_player, 'audio_set_mute'):
                    error_msg = "VLC播放器缺少静音设置功能"
                    self.errorOccurred.emit(error_msg)
                    logging.error(error_msg)
                    return False
                    
                self.vlc_player.audio_set_mute(self._is_muted)
            else:
                if not hasattr(self.media_player, 'setMuted'):
                    error_msg = "Qt播放器缺少静音设置功能"
                    self.errorOccurred.emit(error_msg)
                    logging.error(error_msg)
                    return False
                    
                self.media_player.setMuted(self._is_muted)
                
            # 发送音量变化信号
            self.volumeChanged.emit(self.get_volume(), self._is_muted)
            logging.info(f"静音状态已切换为: {'静音' if self._is_muted else '取消静音'}")
            return True
            
        except vlc.VLCException as e:
            error_msg = f"设置静音失败: {str(e)}"
            self.errorOccurred.emit(error_msg)
            logging.error(error_msg)
            return False
        except Exception as e:
            error_msg = f"设置静音失败: {str(e)}"
            self.errorOccurred.emit(error_msg)
            logging.error(error_msg)
            return False

    def get_current_track(self):
        """获取当前播放曲目"""
        return self.current_track

    def get_playback_status(self):
        """获取播放状态
        Returns:
            dict: 包含播放状态信息的字典，格式为:
            {
                'current_track': str,  # 当前曲目路径
                'playing': bool,       # 是否正在播放
                'volume': int,         # 当前音量(0-100)
                'position': float,     # 播放位置(0.0-1.0)
                'duration': int,       # 曲目时长(毫秒)
                'state': str,          # 播放状态("playing"/"paused"/"stopped"/"error")
                'error': str or None   # 错误信息(如果有)
            }
        """
        status = {
            'current_track': self.current_track,
            'playing': self.is_playing,
            'volume': self.get_volume(),
            'position': 0.0,
            'duration': 0,
            'state': "stopped",
            'error': None
        }
        
        if not self._backend_available:
            status['state'] = "error"
            status['error'] = "播放器引擎不可用"
            logging.error("获取播放状态失败: 播放器引擎不可用")
            return status
            
        try:
            # 获取播放位置和时长
            if self._using_vlc:
                if hasattr(self.vlc_player, 'get_position'):
                    pos = self.vlc_player.get_position()
                    if pos is not None and 0 <= pos <= 1:
                        status['position'] = pos
                    else:
                        logging.warning(f"VLC返回无效播放位置: {pos}")
                        
                if hasattr(self.vlc_player.player, 'get_length'):
                    duration = self.vlc_player.player.get_length()
                    if duration > 0:
                        status['duration'] = duration
            else:
                if hasattr(self.media_player, 'position'):
                    status['position'] = self.media_player.position()
                if hasattr(self.media_player, 'duration'):
                    status['duration'] = self.media_player.duration()
                    
            # 确定播放状态
            if self._using_vlc:
                if hasattr(self.vlc_player, 'get_state'):
                    state = self.vlc_player.get_state()
                    status['state'] = state if state in ["playing", "paused", "stopped"] else "error"
                else:
                    status['state'] = "playing" if self.is_playing else "stopped"
            else:
                state = self.media_player.state()
                status['state'] = {
                    QMediaPlayer.PlayingState: "playing",
                    QMediaPlayer.PausedState: "paused",
                    QMediaPlayer.StoppedState: "stopped"
                }.get(state, "error")
                
            # 验证状态一致性
            if (status['state'] == "playing" and not self.is_playing) or \
               (status['state'] != "playing" and self.is_playing):
                logging.warning(f"状态不一致: 内部={self.is_playing}, 报告={status['state']}")
                self.is_playing = (status['state'] == "playing")
                
            return status
            
        except vlc.VLCException as e:
            error_msg = f"获取VLC播放状态失败: {str(e)}"
            status['state'] = "error"
            status['error'] = error_msg
            logging.error(error_msg)
            return status
        except Exception as e:
            error_msg = f"获取播放状态失败: {str(e)}"
            status['state'] = "error"
            status['error'] = error_msg
            logging.error(error_msg)
            return status

    def set_position(self, position):
        """跳转到指定位置(毫秒)"""
        if not self._backend_available or not self.is_playing:
            self.errorOccurred.emit("播放器不可用或未在播放状态")
            return False
            
        try:
            if self._using_vlc:
                if not hasattr(self.vlc_player.player, 'get_length'):
                    logging.error("VLC播放器缺少时长获取功能")
                    return False
                    
                duration = self.vlc_player.player.get_length()
                if duration <= 0:
                    logging.warning("VLC播放器返回无效时长")
                    return False
                    
                pos = position / duration
                if not self.vlc_player.set_position(pos):
                    raise RuntimeError("VLC设置位置失败")
            else:
                if not hasattr(self.media_player, 'setPosition'):
                    logging.error("Qt播放器缺少位置设置功能")
                    return False
                    
                self.media_player.setPosition(position)
                
            logging.debug(f"播放位置已设置为: {position}ms")
            self.positionChanged.emit(position)
            return True
            
        except vlc.VLCException as e:
            logging.error(f"VLC设置位置失败: {str(e)}")
            self.errorOccurred.emit(f"VLC设置位置失败: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"设置播放位置失败: {str(e)}")
            self.errorOccurred.emit(f"设置播放位置失败: {type(e).__name__} - {str(e)}")
            return False

    def get_position(self):
        """获取播放位置(0.0-1.0)"""
        if not self._backend_available or not self.is_playing:
            return 0.0
            
        try:
            if self._using_vlc:
                if not hasattr(self.vlc_player, 'get_position'):
                    logging.error("VLC播放器缺少位置获取功能")
                    return 0.0
                    
                pos = self.vlc_player.get_position()
                if pos is None or pos < 0 or pos > 1:
                    logging.warning(f"VLC返回无效播放位置: {pos}")
                    return 0.0
                return pos
            else:
                if not hasattr(self.media_player, 'position') or not hasattr(self.media_player, 'duration'):
                    logging.error("Qt播放器缺少进度获取功能")
                    return 0.0
                    
                duration = self.media_player.duration()
                if duration <= 0:
                    return 0.0
                    
                pos = self.media_player.position() / duration
                if pos < 0 or pos > 1:
                    logging.warning(f"Qt返回无效播放位置: {pos}")
                    return 0.0
                    
                return pos
                
        except vlc.VLCException as e:
            logging.error(f"VLC获取位置失败: {str(e)}")
            return 0.0
        except Exception as e:
            logging.error(f"获取播放位置失败: {str(e)}")
            return 0.0

    def set_position_ratio(self, pos):
        """设置播放位置(0.0-1.0)"""
        pos = max(0.0, min(1.0, pos))
        if self._using_vlc:
            self.vlc_player.set_position(pos)
        else:
            if self.media_player.duration() > 0:
                self.media_player.setPosition(int(pos * self.media_player.duration()))
        
    def set_playlist(self, playlist):
        """设置播放列表
        Args:
            playlist: 要设置的播放列表(列表类型)
        Returns:
            bool: 操作是否成功
        """
        if not isinstance(playlist, list):
            error_msg = "播放列表必须是列表类型"
            logging.error(error_msg)
            self.errorOccurred.emit(error_msg)
            return False
            
        # 验证并过滤播放列表
        valid_tracks = []
        seen_tracks = set()
        unsupported_formats = set()
        missing_files = set()
        
        for track in playlist:
            # 检查重复项
            if track in seen_tracks:
                continue
            seen_tracks.add(track)
            
            # 检查文件格式
            if not self.is_supported_format(track):
                unsupported_formats.add(os.path.splitext(track)[1])
                continue
                
            # 检查文件存在性
            if not os.path.exists(track):
                missing_files.add(track)
                continue
                
            valid_tracks.append(track)
            
        # 记录警告信息
        if unsupported_formats:
            logging.warning(f"移除了{len(unsupported_formats)}种不支持的格式: {', '.join(unsupported_formats)}")
        if missing_files:
            logging.warning(f"移除了{len(missing_files)}个不存在的文件")
            
        # 更新播放列表
        self.playlist = valid_tracks
        self.current_index = -1 if not self.playlist else 0
        self.current_track = None
        
        # 发送播放列表更新信号
        self.stateChanged.emit("playlist_updated")
        logging.info(f"播放列表已更新，共{len(self.playlist)}首曲目")
        return True
        
    def next(self):
        """播放下一首"""
        if not self.playlist:
            logging.warning("播放列表为空，无法播放下一首")
            self.errorOccurred.emit("播放列表为空")
            return False
            
        try:
            # 先停止当前播放
            self.stop()
            
            # 计算下一首索引
            if self.random_mode:
                new_index = random.randint(0, len(self.playlist)-1)
                # 避免重复播放同一首
                while len(self.playlist) > 1 and new_index == self.current_index:
                    new_index = random.randint(0, len(self.playlist)-1)
            else:
                new_index = (self.current_index + 1) % len(self.playlist)
                
            # 验证新索引
            if new_index < 0 or new_index >= len(self.playlist):
                logging.error(f"无效的播放索引: {new_index}")
                return False
                
            track = self.playlist[new_index]
            if not os.path.exists(track):
                logging.error(f"文件不存在: {track}")
                self.errorOccurred.emit(f"文件不存在: {os.path.basename(track)}")
                return False
                
            # 更新索引并播放
            self.current_index = new_index
            success = self.play(track)
            
            if success:
                self.current_track = track
                logging.info(f"正在播放下一首: {os.path.basename(track)}")
                self.stateChanged.emit("track_changed")
            else:
                # 播放失败时恢复索引
                self.current_index = max(0, self.current_index - 1)
                
            return success
            
        except Exception as e:
            logging.error(f"播放下一首失败: {str(e)}")
            self.errorOccurred.emit(f"播放下一首失败: {str(e)}")
            return False
        
    def prev(self):
        """播放上一首"""
        if not self.playlist:
            logging.warning("播放列表为空，无法播放上一首")
            self.errorOccurred.emit("播放列表为空")
            return False
            
        try:
            # 先停止当前播放
            self.stop()
            
            # 计算上一首索引
            if self.random_mode:
                new_index = random.randint(0, len(self.playlist)-1)
                # 避免重复播放同一首
                while len(self.playlist) > 1 and new_index == self.current_index:
                    new_index = random.randint(0, len(self.playlist)-1)
            else:
                new_index = (self.current_index - 1) % len(self.playlist)
                
            # 验证新索引
            if new_index < 0 or new_index >= len(self.playlist):
                logging.error(f"无效的播放索引: {new_index}")
                return False
                
            track = self.playlist[new_index]
            if not os.path.exists(track):
                logging.error(f"文件不存在: {track}")
                self.errorOccurred.emit(f"文件不存在: {os.path.basename(track)}")
                return False
                
            # 更新索引并播放
            self.current_index = new_index
            success = self.play(track)
            
            if success:
                self.current_track = track
                logging.info(f"正在播放上一首: {os.path.basename(track)}")
                self.stateChanged.emit("track_changed")
            else:
                # 播放失败时恢复索引
                self.current_index = min(len(self.playlist)-1, self.current_index + 1)
                
            return success
            
        except Exception as e:
            logging.error(f"播放上一首失败: {str(e)}")
            self.errorOccurred.emit(f"播放上一首失败: {str(e)}")
            return False
        
    def set_play_mode(self, mode):
        """设置播放模式
        Args:
            mode (str): 播放模式，可选值: 'normal', 'repeat', 'shuffle'
        """
        if mode == 'shuffle':
            self.random_mode = True
        else:
            self.random_mode = False
        
    def _handle_playback_finished(self, event):
        """处理VLC播放结束事件"""
        self._track_finished = True
        self.playbackFinished.emit()
        logging.info("当前曲目播放完毕")

    def _handle_media_status_changed(self, status):
        """处理Qt媒体状态变化"""
        if status == QMediaPlayer.EndOfMedia:
            self._track_finished = True
            self.playbackFinished.emit()
            logging.info("当前曲目播放完毕")

    def _disconnect_signals(self):
        """断开所有信号连接"""
        if self._using_vlc and hasattr(self, 'vlc_player'):
            try:
                # VLC信号断开
                if hasattr(self.vlc_player.player, 'event_manager'):
                    self.vlc_player.player.event_manager().event_detach(
                        vlc.EventType.MediaPlayerEndReached
                    )
            except Exception as e:
                logging.warning(f"断开VLC信号失败: {str(e)}")
        elif hasattr(self, 'media_player'):
            try:
                # Qt信号断开
                self.media_player.mediaStatusChanged.disconnect()
                self.media_player.positionChanged.disconnect()
                self.media_player.durationChanged.disconnect()
                self.media_player.stateChanged.disconnect()
                self.media_player.error.disconnect()
            except Exception:
                pass

    def release_resources(self):
        """释放资源"""
        self.stop()
        self._disconnect_signals()
        if not self._using_vlc and self.media_player is not None:
            self.media_player.setMedia(QMediaContent())
        logging.debug("播放器资源已清理")