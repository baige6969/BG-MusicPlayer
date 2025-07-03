from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtMultimedia import QMediaPlayer
from MusicPlayer.player import MusicPlayer as Player

class PlayerController(QObject):
    """处理所有播放控制逻辑"""
    
    # 信号定义
    play_state_changed = pyqtSignal(str)  # 播放状态变化(playing/paused/stopped)
    position_changed = pyqtSignal(int)    # 播放位置变化(毫秒)
    volume_changed = pyqtSignal(int)     # 音量变化
    error_occurred = pyqtSignal(str)     # 错误发生
    
    def __init__(self, player=None):
        super().__init__()
        self.player = player or Player()
        self._connect_signals()
        
    def _connect_signals(self):
        """连接播放器信号"""
        self.player.positionChanged.connect(self.position_changed.emit)
        self.player.stateChanged.connect(self._handle_state_change)
        self.player.errorOccurred.connect(self.error_occurred.emit)
        
    def _handle_state_change(self, state):
        """处理播放状态变化"""
        self.play_state_changed.emit(state)
    
    def play(self, file_path=None):
        """播放指定文件"""
        try:
            if file_path:
                success = self.player.play(file_path)
                if not success:
                    self.error_occurred.emit("播放失败: 不支持的格式或文件损坏")
            else:
                self.player.play()
        except Exception as e:
            self.error_occurred.emit(f"播放错误: {str(e)}")
    
    def pause(self):
        """暂停播放"""
        self.player.pause()
    
    def stop(self):
        """停止播放"""
        self.player.stop()
    
    def next(self):
        """播放下一首"""
        # 需要播放列表支持，由主窗口实现
        pass
    
    def prev(self):
        """播放上一首"""
        # 需要播放列表支持，由主窗口实现
        pass
    
    def set_volume(self, value):
        """设置音量(0-100)"""
        self.player.set_volume(value)
        self.volume_changed.emit(value)
    
    def set_position(self, position):
        """设置播放位置(毫秒)"""
        self.player.seek(position)
    
    def toggle_play(self):
        """切换播放/暂停状态"""
        status = self.player.get_playback_status()
        if status['playing']:
            self.pause()
        else:
            self.play()
    
    def get_current_metadata(self):
        """获取当前播放项的元数据"""
        # 需要元数据管理器支持
        return {}