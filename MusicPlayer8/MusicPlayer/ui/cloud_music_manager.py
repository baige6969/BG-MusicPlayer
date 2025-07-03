from PyQt5.QtCore import QObject, pyqtSignal
from MusicPlayer.cloud_service import CloudMusicService

class CloudMusicManager(QObject):
    """处理所有云音乐相关功能"""
    
    # 信号定义
    login_success = pyqtSignal()
    login_failed = pyqtSignal(str)
    data_loaded = pyqtSignal(dict)
    loading_state = pyqtSignal(str)
    
    def __init__(self, service=None):
        super().__init__()
        self.service = service or CloudMusicService()
        self._connect_service_signals()
        
    def _connect_service_signals(self):
        """连接云服务信号"""
        self.service.login_success.connect(self._on_login_success)
        self.service.login_failed.connect(self._on_login_failed)
        
    def _on_login_success(self):
        """处理登录成功"""
        self.login_success.emit()
        
    def _on_login_failed(self, error_msg):
        """处理登录失败"""
        self.login_failed.emit(error_msg)
    
    def load_data(self):
        """加载云音乐数据"""
        self.loading_state.emit("正在加载数据...")
        
        try:
            # 获取各类云音乐数据
            hot_songs = self.service.get_hot_songs()
            playlists = self.service.get_recommend_playlists()
            recommends = self.service.get_personal_recommend()
            
            result = {
                'type': 'combined',
                'hot_songs': hot_songs[:10] if hot_songs else [],
                'playlists': playlists[:5] if playlists else [],
                'recommends': recommends[:5] if recommends else []
            }
            
            self.data_loaded.emit(result)
            self.loading_state.emit("数据加载完成")
            
        except Exception as e:
            self.loading_state.emit("加载失败")
            self.data_loaded.emit({
                'type': 'error',
                'message': str(e)
            })
    
    def show_login_dialog(self, parent=None):
        """显示登录对话框"""
        from MusicPlayer.ui.login_dialog import LoginDialog
        dialog = LoginDialog(self.service, parent)
        dialog.login_success.connect(self._on_login_success)
        dialog.login_failed.connect(self._on_login_failed)
        dialog.exec_()
        
    def is_logged_in(self):
        """检查登录状态"""
        return self.service.is_logged_in