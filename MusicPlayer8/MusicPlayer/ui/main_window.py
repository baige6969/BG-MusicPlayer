import sys
import os
import random
import math
import logging
import traceback
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QSlider, QLabel,
    QFileDialog, QMessageBox, QInputDialog, QAction,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, QSettings, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon
from MusicPlayer.player.player import MusicPlayer as Player
from MusicPlayer.cloud_service import CloudMusicService
from MusicPlayer.utils.metadata_manager import MetadataManager
from MusicPlayer.ui.ui_builder import UIBuilder

class MainWindow(QMainWindow):
    """音乐播放器主窗口"""
    
    def __init__(self, cloud_service=None):
        super().__init__()
        
        # 初始化音乐服务
        self.cloud_service = cloud_service or CloudMusicService()
        self.spotify_service = None
        try:
            from MusicPlayer.services.spotify import SpotifyService
            self.spotify_service = SpotifyService()
        except ImportError:
            logging.warning("Spotify服务不可用")
        
        # 加载样式表 - 增强版本
        loaded_style = ""
        style_paths = [
            os.path.join(os.path.dirname(__file__), "..", "resources", "styles.qss"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "styles", "styles.qss"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "style.qss")
        ]
        
        # 确保资源目录存在
        resources_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
        if not os.path.exists(resources_dir):
            os.makedirs(resources_dir)
            logging.info(f"创建资源目录: {resources_dir}")
        
        for path in style_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        loaded_style = f.read()
                        self.setStyleSheet(loaded_style)
                        logging.info(f"成功加载样式表: {path}")
                        break
                else:
                    # 如果样式表不存在，创建默认样式表
                    default_style = """
                        QMainWindow {
                            background-color: #f0f0f0;
                            font-family: "Microsoft YaHei";
                        }
                        QListWidget {
                            background: white;
                            border: 1px solid #ccc;
                            font: 12px;
                        }
                        QPushButton {
                            min-width: 80px;
                            min-height: 25px;
                        }
                        QSlider::handle {
                            width: 12px;
                            height: 12px;
                            background: #4CAF50;
                        }
                    """
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(default_style)
                    loaded_style = default_style
                    self.setStyleSheet(loaded_style)
                    logging.info(f"创建并加载默认样式表: {path}")
                    break
            except Exception as e:
                logging.warning(f"加载样式表失败({path}): {str(e)}")
        
        if not loaded_style:
            logging.warning("未加载任何样式表，使用默认样式")
            # 设置基本样式作为回退
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                    font-family: "Microsoft YaHei";
                }
                QListWidget {
                    background: white;
                    border: 1px solid #ccc;
                    font: 12px;
                }
                QPushButton {
                    min-width: 80px;
                    min-height: 25px;
                }
            """)
        
        self.setWindowTitle("音乐播放器")
        self.setMinimumSize(800, 600)
        
        # 存储云服务实例
        self.cloud_service = cloud_service or CloudMusicService()
        
        # 初始化UI状态
        self._update_ui_login_state()
        print(f"[DEBUG] 窗口初始尺寸: {self.size()}")
        print(f"[DEBUG] 窗口最小尺寸: {self.minimumSize()}")
        
        # 初始化标志
        self.initialized = False
        self.player_ready = False
        
        # 验证并创建关键资源目录
        required_dirs = [
            os.path.join(os.path.dirname(__file__), "..", "resources"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "icons")
        ]
        
        for dir_path in required_dirs:
            try:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    logging.info(f"创建资源目录: {dir_path}")
                    
                    # 如果是图标目录，添加默认图标
                    if dir_path.endswith("icons"):
                        # 创建默认应用图标
                        default_icon_path = os.path.join(dir_path, "app.ico")
                        if not os.path.exists(default_icon_path):
                            # 使用Qt内置图标作为回退
                            default_icon = QIcon.fromTheme("media-playback-start")
                            if not default_icon.isNull():
                                default_icon.pixmap(64, 64).save(default_icon_path)
                                logging.info(f"创建默认应用图标: {default_icon_path}")
                
                logging.debug(f"资源目录验证通过: {dir_path}")
            except Exception as e:
                logging.error(f"处理资源目录失败({dir_path}): {str(e)}")
                QMessageBox.warning(
                    self, 
                    "资源警告", 
                    f"无法创建资源目录:\n{dir_path}\n部分功能可能受限"
                )
        
        # 初始化关键组件
        try:
            logging.debug("初始化元数据管理器...")
            self.metadata_manager = MetadataManager()
            
            logging.debug("初始化播放器...")
            from MusicPlayer.player.player import MusicPlayer
            self.player = MusicPlayer()
        
            # 验证播放器初始化
            if not hasattr(self.player, 'play') or not self.player._backend_available:
                error_msg = "播放器初始化失败: 缺少必要的媒体组件"
                logging.critical(error_msg)
                QMessageBox.critical(
                    self,
                    "初始化错误",
                    f"{error_msg}\n请确保已安装VLC或Qt多媒体组件"
                )
                raise RuntimeError(error_msg)
            
            # 验证播放器初始化
            if not hasattr(self.player, 'play'):
                raise RuntimeError("播放器初始化失败，缺少必要方法")
            
            # 连接播放器信号（增强安全性和错误处理）
            try:
                if hasattr(self.player, 'positionChanged'):
                    # 先断开已有连接
                    try:
                        self.player.positionChanged.disconnect()
                    except:
                        pass
                    # 确保槽函数存在
                    if hasattr(self, '_update_progress'):
                        self.player.positionChanged.connect(self._update_progress)
                
                if hasattr(self.player, 'stateChanged'):
                    # 先断开已有连接
                    try:
                        self.player.stateChanged.disconnect()
                    except:
                        pass
                    # 确保槽函数存在
                    if hasattr(self, '_handle_player_state'):
                        self.player.stateChanged.connect(self._handle_player_state)
                
                if hasattr(self.player, 'errorOccurred'):
                    # 先断开已有连接
                    try:
                        self.player.errorOccurred.disconnect()
                    except:
                        pass
                    # 确保槽函数存在
                    if hasattr(self, '_handle_player_error'):
                        self.player.errorOccurred.connect(self._handle_player_error)
                        
            except Exception as e:
                logging.error(f"连接播放器信号失败: {str(e)}", exc_info=True)
                QMessageBox.warning(self, "警告", "播放器信号连接失败，部分功能可能不可用")
            
            # 延迟确保播放器初始化完成
            QTimer.singleShot(500, self.mark_player_ready)
            
            print("[DEBUG] MainWindow: 初始化设置...")
            self.settings = QSettings("MusicPlayer", "Player")
            
            print("[DEBUG] MainWindow: 初始化完成")
            
        except Exception as e:
            logging.critical(f"初始化失败: {str(e)}")
            QMessageBox.critical(
                self,
                "初始化错误",
                f"关键组件初始化失败:\n{str(e)}\n程序将退出"
            )
            self.initialized = False
            raise
            
        # 应用设置
        self.settings = QSettings("MusicPlayer", "Player")
        
        # 加载用户保存的主题
        saved_theme = self.settings.value("theme", "light")
        self.load_theme(saved_theme)
        
        # 播放模式相关属性
        self.play_mode = "sequential"  # sequential/random
        self.current_playlist_order = []  # 存储当前播放顺序
        self.current_index = -1  # 当前播放索引
        
        # 主窗口中心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 主布局
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        
        # 初始化UI
        self.init_ui()
        
        # 连接播放器信号
        self.player.positionChanged.connect(self._update_progress)
        
        # 定时器更新UI（增强安全性和错误处理）
        self.timer = QTimer()
        try:
            if hasattr(self.timer, 'timeout'):
                try:
                    self.timer.timeout.disconnect()
                except:
                    pass
                if hasattr(self, 'update_ui'):
                    self.timer.timeout.connect(self.update_ui)
        except Exception as e:
            logging.error(f"连接定时器信号失败: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "警告", "定时器信号连接失败，UI自动更新功能可能不可用")
        self.timer.start(100)
        
        # 初始音量同步
        QTimer.singleShot(500, self.sync_volume_ui)
        
        # 标记初始化完成
        self.initialized = True
        
        # 最后加载播放列表
        self.load_last_playlist()
    
    def format_duration(self, milliseconds):
        """将毫秒数格式化为'分:秒'字符串"""
        if not isinstance(milliseconds, (int, float)) or milliseconds <= 0:
            return "00:00"
        
        total_seconds = int(milliseconds / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def format_file_size(self, bytes_num):
        """将字节数格式化为友好的文件大小字符串"""
        if not isinstance(bytes_num, (int, float)) or bytes_num <= 0:
            return "0B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_num < 1024.0:
                return f"{bytes_num:.1f}{unit}"
            bytes_num /= 1024.0
        return f"{bytes_num:.1f}TB"

    def update_cloud_data(self, data):
        """更新云音乐数据显示"""
        data_type = data['type']
        items = data['data']
        
        if data_type == 'hot_songs':
            self.cloud_list.clear()
            for song in items[:10]:  # 只显示前10首
                self.cloud_list.addItem(f"{song.get('name', '未知')} - {song.get('artist', '未知')}")
            
            # 更新音乐信息
            if items:
                first_song = items[0]
                info_text = (
                    f"<b>热门歌曲</b><br>"
                    f"<br><b>歌曲:</b> {first_song.get('name', '未知')}"
                    f"<br><b>歌手:</b> {first_song.get('artist', '未知')}"
                    f"<br><b>专辑:</b> {first_song.get('album', '未知')}"
                    f"<br><b>时长:</b> {self.format_duration(first_song.get('duration', 0))}"
                    f"<br><b>比特率:</b> {first_song.get('bitrate', '未知')} kbps"
                    f"<br><b>采样率:</b> {first_song.get('sampleRate', '未知')} Hz"
                    f"<br><b>声道:</b> {first_song.get('channels', '未知')}"
                    f"<br><b>编码格式:</b> {first_song.get('codec', '未知')}"
                    f"<br><b>文件大小:</b> {self.format_file_size(first_song.get('fileSize', 0))}"
                    f"<br><b>动态范围:</b> {first_song.get('dynamicRange', '未知')} dB"
                    f"<br><b>格式:</b> {first_song.get('format', '未知')}"
                    f"<br><b>发行日期:</b> {first_song.get('publishTime', '未知')}"
                    f"<br><b>流派:</b> {first_song.get('genre', '未知')}"
                )
                self.music_info_label.setText(info_text)
                
        elif data_type == 'recommend_playlists':
            self.cloud_list.clear()
            for playlist in items[:5]:  # 只显示前5个歌单
                self.cloud_list.addItem(f"♪ {playlist.get('name', '未知歌单')}")
            
            # 更新音乐信息
            if items:
                first_playlist = items[0]
                info_text = (
                    f"<b>推荐歌单</b><br>"
                    f"<br><b>名称:</b> {first_playlist.get('name', '未知歌单')}"
                    f"<br><b>创建者:</b> {first_playlist.get('creator', '未知')}"
                    f"<br><b>歌曲数:</b> {first_playlist.get('trackCount', '未知')}"
                    f"<br><b>播放次数:</b> {first_playlist.get('playCount', '未知')}"
                    f"<br><b>收藏数:</b> {first_playlist.get('bookCount', '未知')}"
                    f"<br><b>更新时间:</b> {first_playlist.get('updateTime', '未知')}"
                    f"<br><b>标签:</b> {', '.join(first_playlist.get('tags', ['无']))}"
                )
                self.music_info_label.setText(info_text)
                
        elif data_type == 'personal_recommend':
            self.cloud_list.clear()
            for rec in items[:5]:  # 只显示前5个推荐
                self.cloud_list.addItem(f"★ {rec.get('title', '未知推荐')}")
            
            # 更新音乐信息
            if items:
                first_rec = items[0]
                info_text = (
                    f"<b>个性化推荐</b><br>"
                    f"<br><b>标题:</b> {first_rec.get('title', '未知推荐')}"
                    f"<br><b>类型:</b> {first_rec.get('type', '未知')}"
                    f"<br><b>匹配度:</b> {first_rec.get('matchScore', '未知')}%"
                    f"<br><b>推荐时间:</b> {first_rec.get('recommendTime', '未知')}"
                    f"<br><b>推荐理由:</b> {first_rec.get('reason', '根据你的听歌习惯推荐')}"
                    f"<br><b>相似歌曲:</b> {', '.join(first_rec.get('similarSongs', ['无']))}"
                )
                self.music_info_label.setText(info_text)

    def init_ui(self):
        """Initialize user interface"""
        print("[DEBUG] MainWindow: Initializing UI...")
        self.ui_builder = UIBuilder(self)
        
        # Main horizontal layout
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(15, 15, 15, 15)
        h_layout.setSpacing(15)
        self.main_layout.addLayout(h_layout)
        
        # Left panel - playback controls (70% width)
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # Playlist area with card style
        playlist_card = QWidget()
        playlist_card.setObjectName("playlistCard")
        playlist_layout = QVBoxLayout(playlist_card)
        playlist_layout.setContentsMargins(10, 10, 10, 10)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setObjectName("playlistWidget")
        try:
            if hasattr(self.playlist_widget, 'itemDoubleClicked'):
                try:
                    self.playlist_widget.itemDoubleClicked.disconnect()
                except:
                    pass
                if hasattr(self, 'play_selected'):
                    self.playlist_widget.itemDoubleClicked.connect(self.play_selected)
        except Exception as e:
            logging.error(f"连接播放列表信号失败: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "警告", "播放列表信号连接失败，双击播放功能可能不可用")
        playlist_layout.addWidget(self.playlist_widget)
        
        left_layout.addWidget(playlist_card, stretch=3)
        
        # Build and add control panel
        control_panel = self.ui_builder._build_control_panel()
        left_layout.addWidget(control_panel, stretch=1)
        
        # Connect signals to UIBuilder components with safety checks
        self.progress_slider = self.ui_builder.progress_slider
        self.volume_slider = self.ui_builder.volume_slider
        self.play_btn = self.ui_builder.play_btn
        self.prev_btn = self.ui_builder.prev_btn
        self.next_btn = self.ui_builder.next_btn
        self.mode_btn = self.ui_builder.mode_btn
        
        try:
            # Progress slider
            if hasattr(self.progress_slider, 'sliderMoved'):
                try:
                    self.progress_slider.sliderMoved.disconnect()
                except:
                    pass
                if hasattr(self, 'set_progress'):
                    self.progress_slider.sliderMoved.connect(self.set_progress)
            
            # Volume slider
            if hasattr(self.volume_slider, 'valueChanged'):
                try:
                    self.volume_slider.valueChanged.disconnect()
                except:
                    pass
                if hasattr(self, 'set_volume'):
                    self.volume_slider.valueChanged.connect(self.set_volume)
            
            # Play button
            if hasattr(self.play_btn, 'clicked'):
                try:
                    self.play_btn.clicked.disconnect()
                except:
                    pass
                if hasattr(self, 'toggle_play'):
                    self.play_btn.clicked.connect(self.toggle_play)
            
            # Previous button
            if hasattr(self.prev_btn, 'clicked'):
                try:
                    self.prev_btn.clicked.disconnect()
                except:
                    pass
                if hasattr(self.player, 'prev'):
                    self.prev_btn.clicked.connect(self.player.prev)
            
            # Next button
            if hasattr(self.next_btn, 'clicked'):
                try:
                    self.next_btn.clicked.disconnect()
                except:
                    pass
                if hasattr(self.player, 'next'):
                    self.next_btn.clicked.connect(self.player.next)
            
            # Play mode button
            if hasattr(self.mode_btn, 'clicked'):
                try:
                    self.mode_btn.clicked.disconnect()
                except:
                    pass
                if hasattr(self.player, 'set_play_mode'):
                    self.mode_btn.clicked.connect(lambda: self.player.set_play_mode("random" if self.mode_btn.isChecked() else "normal"))
                    
        except Exception as e:
            logging.error(f"连接UI控件信号失败: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "警告", "UI控件信号连接失败，部分功能可能不可用")
        
        h_layout.addWidget(left_panel, stretch=7)  # 70% width
        
        # Right panel - cards (30% width)
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # Cloud music card with shadow effect
        cloud_card = QWidget()
        cloud_card.setObjectName("cloudCard")
        cloud_card.setProperty("class", "card")
        cloud_layout = QVBoxLayout(cloud_card)
        cloud_layout.setContentsMargins(15, 15, 15, 15)
        cloud_layout.setSpacing(10)
        
        # Title and refresh button
        title_layout = QHBoxLayout()
        cloud_title = QLabel("云音乐数据")
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_cloud_data)
        title_layout.addWidget(cloud_title)
        title_layout.addStretch()
        title_layout.addWidget(self.refresh_btn)
        cloud_layout.addLayout(title_layout)
        
        # Cloud music list
        self.cloud_list = QListWidget()
        self.cloud_list.setObjectName("cloudList")
        self.cloud_list.setStyleSheet("""
            QListWidget#cloudList {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                padding: 5px;
            }
        """)
        cloud_layout.addWidget(self.cloud_list)
        
        # Loading status
        self.loading_label = QLabel("准备加载数据...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        cloud_layout.addWidget(self.loading_label)

        # Music info display
        self.music_info_label = QLabel()
        self.music_info_label.setObjectName("musicInfo")
        self.music_info_label.setStyleSheet("""
            QLabel#musicInfo {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
                min-height: 80px;
            }
        """)
        self.music_info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.music_info_label.setWordWrap(True)
        cloud_layout.addWidget(self.music_info_label)
        
        right_layout.addWidget(cloud_card)
        
        # Add folder button
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        right_layout.addWidget(self.add_folder_btn)
        
        # Initial data load
        self.load_cloud_data()
        
        h_layout.addWidget(right_panel, stretch=1)
        
        # Create menu
        self.create_menu()
        
        # 初始加载数据
        self.load_cloud_data()
        
        h_layout.addWidget(right_panel, stretch=1)
        
        # 添加菜单
        self.create_menu()
        
        # 添加状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("""
            QLabel#statusLabel {
                background: rgba(255,255,255,0.05);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 4px;
                padding: 5px;
                margin-top: 5px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.main_layout.addWidget(self.status_label)

    def load_cloud_data(self):
        """加载云音乐数据"""
        self.loading_label.setText("正在加载数据...")
        self.cloud_list.clear()
        
        try:
            # 获取各类云音乐数据
            self.cloud_service.get_hot_songs()
            self.cloud_service.get_recommend_playlists()
            self.cloud_service.get_personal_recommend()
            self.loading_label.setText("数据加载完成")
        except Exception as e:
            self.loading_label.setText("加载失败")
            self.cloud_list.addItem("无法加载云音乐数据")
            print(f"加载云音乐数据出错: {e}")

    def add_folder(self):
        """添加整个文件夹的音乐文件"""
        folder = QFileDialog.getExistingDirectory(self, "选择音乐文件夹")
        if folder:
            audio_files = []
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path) and file.lower().endswith(('.mp3', '.flac', '.wav', '.ogg')):
                    audio_files.append(file_path)
            
            if audio_files:
                self.playlist_widget.addItems(audio_files)
            else:
                QMessageBox.information(self, "提示", "该文件夹中没有找到音频文件")
    
    # Control panel creation moved to UIBuilder

    def _setup_button_animations(self):
        """设置按钮动画效果"""
        # 播放按钮动画
        self.play_btn_animation = QPropertyAnimation(self.play_btn, b"geometry")
        self.play_btn_animation.setDuration(150)
        self.play_btn_animation.setEasingCurve(QEasingCurve.OutQuad)
        
        # 连接按钮点击信号（增强安全性和错误处理）
        try:
            if hasattr(self.play_btn, 'pressed'):
                try:
                    self.play_btn.pressed.disconnect()
                except:
                    pass
                if hasattr(self, '_animate_play_button'):
                    self.play_btn.pressed.connect(self._animate_play_button)
            
            if hasattr(self.prev_btn, 'pressed'):
                try:
                    self.prev_btn.pressed.disconnect()
                except:
                    pass
                if hasattr(self, '_animate_prev_button'):
                    self.prev_btn.pressed.connect(self._animate_prev_button)
            
            if hasattr(self.next_btn, 'pressed'):
                try:
                    self.next_btn.pressed.disconnect()
                except:
                    pass
                if hasattr(self, '_animate_next_button'):
                    self.next_btn.pressed.connect(self._animate_next_button)
                    
        except Exception as e:
            logging.error(f"连接按钮动画信号失败: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "警告", "按钮动画信号连接失败，按钮动画效果可能不可用")
        
    def _animate_play_button(self):
        """播放按钮动画"""
        start_rect = self.play_btn.geometry()
        self.play_btn_animation.setStartValue(start_rect)
        self.play_btn_animation.setEndValue(start_rect.adjusted(0, 2, 0, 2))
        self.play_btn_animation.start()
        
    def _animate_prev_button(self):
        """上一曲按钮动画"""
        start_rect = self.prev_btn.geometry()
        self.play_btn_animation.setStartValue(start_rect)
        self.play_btn_animation.setEndValue(start_rect.adjusted(-2, 0, -2, 0))
        self.play_btn_animation.start()
        
    def _animate_next_button(self):
        """下一曲按钮动画"""
        start_rect = self.next_btn.geometry()
        self.play_btn_animation.setStartValue(start_rect)
        self.play_btn_animation.setEndValue(start_rect.adjusted(2, 0, 2, 0))
        self.play_btn_animation.start()
    
    def load_last_playlist(self):
        """加载最近播放列表"""
        last_playlist = self.settings.value("last_playlist", [])
        self.playlist_widget.clear()
        if last_playlist:
            valid_files = [f for f in last_playlist if os.path.exists(f)]
            if valid_files:
                self.playlist_widget.addItems(valid_files)
                # 只有在初始化完成后才自动选择第一首歌
                if hasattr(self, 'initialized') and self.initialized:
                    self.playlist_widget.setCurrentRow(0)
            else:
                # 如果所有文件都无效，确保清空播放列表
                self.playlist_widget.clear()
                if hasattr(self, 'player'):
                    self.player.stop()

    def save_playlist(self):
        """保存当前播放列表"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存播放列表", "", "播放列表文件 (*.m3u)"
        )
        if file_path:
            playlist = [self.playlist_widget.item(i).text() 
                       for i in range(self.playlist_widget.count())]
            self.player.save_playlist(file_path, playlist)

    def load_playlist(self):
        """加载播放列表"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "加载播放列表", "", "播放列表文件 (*.m3u)"
        )
        if file_path:
            try:
                playlist = self.player.load_playlist(file_path)
                self.playlist_widget.clear()
                for file_path in playlist:
                    if os.path.exists(file_path):
                        self.playlist_widget.addItem(file_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法加载播放列表: {str(e)}")

    def load_theme(self, theme_name):
        """加载指定主题"""
        try:
            theme_path = os.path.join(
                os.path.dirname(__file__), 
                "..", 
                "resources", 
                "themes", 
                f"{theme_name}.qss"
            )
            if os.path.exists(theme_path):
                with open(theme_path, "r", encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
                # 保存用户偏好
                self.settings.setValue("theme", theme_name)
            else:
                QMessageBox.warning(
                    self, 
                    "警告", 
                    f"主题文件不存在: {theme_path}"
                )
        except Exception as e:
            QMessageBox.warning(
                self, 
                "错误", 
                f"加载主题失败: {str(e)}"
            )

    def closeEvent(self, event):
        """窗口关闭事件 - 增强版本"""
        try:
            # 1. 确保所有模态对话框关闭
            if hasattr(self, '_login_dialog') and self._login_dialog:
                self._login_dialog.close()
                self._cleanup_login_dialog()

            # 2. 停止播放器并释放资源
            if hasattr(self, 'player'):
                self.player.stop()
                self.player.release_resources()

            # 3. 验证并保存播放列表
            valid_files = []
            if hasattr(self, 'playlist_widget'):
                valid_files = [
                    self.playlist_widget.item(i).text()
                    for i in range(self.playlist_widget.count())
                    if os.path.exists(self.playlist_widget.item(i).text())
                ]
                self.settings.setValue("last_playlist", valid_files)

            # 4. 保存窗口状态
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.setValue("window_state", self.saveState())

            # 5. 清理定时器
            if hasattr(self, 'timer') and self.timer.isActive():
                self.timer.stop()

            # 记录关闭日志
            print("[INFO] 应用程序正常关闭")

        except Exception as e:
            print(f"[ERROR] 关闭时发生异常: {traceback.format_exc()}")
            QMessageBox.warning(self, "警告", 
                f"关闭时发生错误:\n{str(e)}\n部分数据可能未保存")

        finally:
            # 确保父类处理始终执行
            super().closeEvent(event)
        
    def resizeEvent(self, event):
        """窗口大小调整事件"""
        super().resizeEvent(event)
        # 窗口大小变化时同步音量UI
        self.sync_volume_ui()
        
    def sync_volume_ui(self):
        """同步音量UI状态"""
        if not hasattr(self, 'volume_slider'):
            return
            
        # 使用默认音量或当前音量
        if hasattr(self, '_volume'):
            current_volume = self._volume
        else:
            current_volume = 50  # 默认音量
            self._volume = current_volume
            
        # 如果播放器存在且已初始化，获取实际音量
        if hasattr(self, 'player') and self.player_ready:
            try:
                current_volume = self.player.get_volume()
                self._volume = current_volume  # 更新存储的音量
            except Exception as e:
                print(f"[WARNING] 获取音量失败: {str(e)}")
                current_volume = self._volume  # 使用存储的音量
            
        self.volume_slider.setValue(current_volume)

    def create_menu(self):
        """创建菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 主题菜单
        theme_menu = menubar.addMenu("主题")
        theme_menu.addAction("亮色", lambda: self.load_theme('light'))
        theme_menu.addAction("暗色", lambda: self.load_theme('dark'))
        theme_menu.addAction("蓝色", lambda: self.load_theme('blue'))
        file_menu.addAction("添加歌曲", self.add_songs)
        file_menu.addAction("保存播放列表", self.save_playlist)
        file_menu.addAction("加载播放列表", self.load_playlist)
        file_menu.addSeparator()
        
        # 元数据菜单
        metadata_menu = file_menu.addMenu("元数据")
        metadata_menu.addAction("更新当前歌曲元数据", self.update_current_metadata)
        metadata_menu.addAction("批量更新元数据", self.batch_update_metadata)
        
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)
        
        # 歌单菜单
        playlist_menu = menubar.addMenu("歌单")
        playlist_menu.addAction("新建歌单", self.create_playlist)
        playlist_menu.addAction("删除当前歌单", self.delete_playlist)
        playlist_menu.addSeparator()
        
        # 初始化歌单数据
        self.playlists = self.settings.value("playlists", {"默认歌单": []})
        self.current_playlist = self.settings.value("current_playlist", "默认歌单")
        
        # 添加现有歌单到菜单
        for name in self.playlists.keys():
            action = playlist_menu.addAction(name)
            action.triggered.connect(lambda _, n=name: self.switch_playlist(n))
            
        # 网易云菜单
        cloud_menu = menubar.addMenu("网易云")
        login_action = QAction("账号登录", self)
        login_action.triggered.connect(self.show_cloud_login)
        cloud_menu.addAction(login_action)
        
        # 连接云服务信号（仅在用户主动登录时触发）
        try:
            if hasattr(self.cloud_service, 'login_success'):
                # 先断开已有连接
                try:
                    self.cloud_service.login_success.disconnect()
                except:
                    pass
                # 确保槽函数存在
                if hasattr(self, 'on_login_success'):
                    self.cloud_service.login_success.connect(self.on_login_success)
            
            if hasattr(self.cloud_service, 'login_failed'):
                # 先断开已有连接
                try:
                    self.cloud_service.login_failed.disconnect()
                except:
                    pass
                # 确保槽函数存在
                if hasattr(self, 'on_login_failed'):
                    self.cloud_service.login_failed.connect(self.on_login_failed)
                    
        except Exception as e:
            logging.error(f"连接云服务信号失败: {str(e)}", exc_info=True)
            QMessageBox.warning(self, "警告", "云服务信号连接失败，登录功能可能不可用")
        
        # 确保不自动弹出登录UI
        if hasattr(self.cloud_service, 'auto_login') and self.cloud_service.auto_login:
            self.cloud_service.auto_login = False
    
    def add_songs(self):
        """添加歌曲到播放列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音乐文件", "", 
            "音频文件 (*.mp3 *.flac *.wav *.ogg)"
        )
        
        if files:
            for file in files:
                self.playlist_widget.addItem(file)
            self.update_playlist_order()
            self.save_playlists()
    
    def remove_song(self):
        """从播放列表移除歌曲"""
        current_row = self.playlist_widget.currentRow()
        if current_row >= 0:
            self.playlist_widget.takeItem(current_row)
            
    def clear_playlist(self):
        """清空整个播放列表"""
        reply = QMessageBox.question(
            self, "确认", 
            "确定要清空整个播放列表吗?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.playlist_widget.clear()
    
    def mark_player_ready(self):
        """标记播放器初始化完成"""
        self.player_ready = True
        
    def _validate_player_state(self) -> bool:
        """
        验证播放器状态是否就绪
        
        返回:
            bool: True表示就绪，False表示未就绪
        """
        try:
            if not hasattr(self, 'player_ready') or not self.player_ready:
                logging.debug("播放器未初始化就绪")
                return False
                
            if not hasattr(self, 'player') or self.player is None:
                logging.warning("播放器实例不存在")
                return False
                
            if self.playlist_widget.count() == 0:
                logging.info("播放列表为空")
                QMessageBox.information(self, "提示", "播放列表为空")
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"验证播放器状态时出错: {str(e)}")
            return False

    def _update_playback_ui(self, file_path, is_playing):
        """更新播放状态UI"""
        self.play_btn.setText("暂停" if is_playing else "播放")
        
        try:
            metadata = self.metadata_manager.get_metadata(file_path)
            artist = (metadata.get('artist') or 
                     metadata.get('author') or 
                     metadata.get('creator') or 
                     '未知')
    
            source_info = f"[{metadata.get('source', 'local')}]" if metadata.get('source') else ""
            display_text = (
                f"{'正在播放' if is_playing else '暂停'}: {metadata.get('title', os.path.basename(file_path))} {source_info}\n"
                f"艺术家: {artist} | 专辑: {metadata.get('album', '未知')}"
            )
    
            if 'duration' in metadata:
                mins, secs = divmod(int(metadata['duration']), 60)
                display_text += f" | 时长: {mins}:{secs:02d}"
    
            self.status_label.setText(display_text)
        except Exception as e:
            print(f"[WARNING] 更新播放UI失败: {str(e)}")
            self.status_label.setText(f"{'正在播放' if is_playing else '暂停'}: {os.path.basename(file_path)}")

    def play_selected(self, item_or_path=None):
        """播放选中的歌曲
        
        参数:
            item_or_path: 可以是QListWidgetItem或字符串路径
        """
        if not self._validate_player_state():
            QTimer.singleShot(100, lambda: self.play_selected(item_or_path))
            return
            
        # 处理不同类型的参数
        file_path = None
        if isinstance(item_or_path, str):
            file_path = item_or_path
        elif hasattr(item_or_path, 'text'):  # QListWidgetItem
            file_path = item_or_path.text()
        else:
            current_item = self.playlist_widget.currentItem()
            file_path = current_item.text() if current_item else None
            
        # 验证文件路径
        if not file_path or not isinstance(file_path, str):
            QMessageBox.warning(self, "错误", "无效的文件路径")
            return
            
        try:
            # 转换为绝对路径并验证存在性
            file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                # 尝试从Spotify播放
                if self._try_play_from_spotify(file_path):
                    return
                QMessageBox.warning(self, "错误", f"文件不存在: {file_path}")
                return
                
            # 更新播放列表和索引
            self.current_index = self.playlist_widget.currentRow()
            
            # 执行播放
            success = self.player.play(file_path)
            if not success:
                # 尝试从Spotify播放
                if self._try_play_from_spotify(file_path):
                    return
                QMessageBox.warning(self, "错误", "播放失败: 不支持的格式或文件损坏")
                return
                
            self._update_playback_ui(file_path, True)
            
        except Exception as e:
            print(f"[ERROR] 播放失败: {traceback.format_exc()}")
            # 尝试从Spotify播放
            if not self._try_play_from_spotify(file_path):
                QMessageBox.critical(self, "错误", f"播放失败: {str(e)}")
                self.player.stop()
                self._update_playback_ui(file_path or "", False)
                
    def _try_play_from_spotify(self, track_name):
        """尝试从Spotify播放歌曲"""
        if not self.spotify_service:
            return False
            
        try:
            # 检查Spotify是否已授权
            if not self.spotify_service.is_authenticated():
                if not self._authorize_spotify():
                    return False
                    
            # 在Spotify中搜索歌曲
            track = self.spotify_service.search_track(track_name)
            if not track:
                return False
                
            # 使用Spotify播放
            success = self.player.play(track['uri'])
            if success:
                self._update_playback_ui(track['name'], True)
                return True
                
        except Exception as e:
            logging.error(f"Spotify播放失败: {str(e)}")
            
        return False
        
    def _authorize_spotify(self):
        """授权Spotify服务"""
        reply = QMessageBox.question(
            self, "需要授权",
            "需要授权Spotify才能播放音乐，是否现在授权?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                return self.spotify_service.authorize()
            except Exception as e:
                QMessageBox.warning(self, "授权失败", f"Spotify授权失败: {str(e)}")
                
        return False

    def toggle_play(self):
        """切换播放/暂停状态"""
        if not self._validate_player_state():
            QTimer.singleShot(100, self.toggle_play)
            return
            
        if self.player.is_playing:
            self.player.pause()
            current_item = self.playlist_widget.currentItem()
            if current_item:
                self._update_playback_ui(current_item.text(), False)
        else:
            self.play_selected()
    
    def set_volume(self, value):
        """设置音量(对数曲线平滑控制)"""
        try:
            # 确保播放器已初始化
            if not hasattr(self, 'player') or not self.player:
                logging.warning("尝试设置音量时播放器未初始化")
                return
                
            # 限制音量范围(0-100)
            volume = max(0, min(100, int(value)))
            
            # 对数曲线转换(更符合人耳感知)
            linear_volume = volume / 100.0
            logarithmic_volume = math.log10(1 + 9 * linear_volume)
            
            # 应用音量设置 - 确保转换为整数
            self.player.set_volume(int(logarithmic_volume * 100))
            
            # 平滑过渡动画
            if hasattr(self, 'volume_slider'):
                self.volume_anim = QPropertyAnimation(self.volume_slider, b"value")
                self.volume_anim.setDuration(200)
                self.volume_anim.setStartValue(self.volume_slider.value())
                self.volume_anim.setEndValue(volume)
                self.volume_anim.setEasingCurve(QEasingCurve.OutQuad)
                self.volume_anim.start()
            
            # 调试日志
            logging.debug(f"设置音量: {volume}% (线性值: {linear_volume:.2f}, 对数值: {logarithmic_volume:.2f})")
            
        except Exception as e:
            logging.error(f"设置音量失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"无法设置音量: {str(e)}")
    
    def _update_progress(self, position):
        """更新播放进度(来自Player信号)"""
        status = self.player.get_playback_status()
        duration = status.get('duration', 0)
        
        if duration > 0:
            self.progress_slider.setRange(0, duration)
            self.progress_slider.setValue(position)
            
            # 更新显示的时间
            mins, secs = divmod(position // 1000, 60)
            total_mins, total_secs = divmod(duration // 1000, 60)
            self.status_label.setText(
                f"{mins}:{secs:02d} / {total_mins}:{total_secs:02d}"
            )

    def _handle_player_state(self, state):
        """处理播放状态变化"""
        if state == "playing":
            self.play_btn.setText("暂停")
            self.statusBar().showMessage("正在播放")
        elif state == "paused":
            self.play_btn.setText("播放") 
            self.statusBar().showMessage("已暂停")
        elif state == "stopped":
            self.play_btn.setText("播放")
            self.statusBar().showMessage("已停止")
            self.progress_slider.setValue(0)

    def _handle_player_error(self, error_msg):
        """处理播放错误"""
        QMessageBox.critical(self, "播放错误", error_msg)
        self.player.stop()
        self._handle_player_state("stopped")
    
    def update_ui(self):
        """更新UI状态"""
        try:
            status = self.player.get_playback_status()
            self.play_btn.setText("暂停" if status.get('state') == "playing" else "播放")
        except Exception as e:
            logging.error(f"更新UI状态失败: {str(e)}")
            self.play_btn.setText("播放")
    
    def set_progress(self, value):
        """设置播放进度"""
        if self.player.is_playing:
            self.player.set_position(value / 1000.0)

    def toggle_play_mode(self):
        """切换播放模式(顺序/随机)"""
        if not hasattr(self, 'player_ready') or not self.player_ready:
            QTimer.singleShot(100, self.toggle_play_mode)
            return
            
        if self.playlist_widget.count() == 0:
            QMessageBox.information(self, "提示", "播放列表为空，无法切换模式")
            return
            
        try:
            if self.play_mode == "sequential":
                self.play_mode = "random"
                self.mode_btn.setText("随机播放")
                self.mode_btn.setChecked(True)
                self.player.set_play_mode("random")
            else:
                self.play_mode = "sequential"
                self.mode_btn.setText("顺序播放") 
                self.mode_btn.setChecked(False)
                self.player.set_play_mode("sequential")
                
            self.update_playlist_order()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"切换播放模式失败: {str(e)}")

    def update_playlist_order(self):
        """根据当前播放模式更新播放顺序"""
        count = self.playlist_widget.count()
        if count == 0:
            self.current_playlist_order = []
            return
            
        if self.play_mode == "random":
            import random
            self.current_playlist_order = random.sample(range(count), count)
        else:
            self.current_playlist_order = list(range(count))
            
        # 保持当前播放项的位置
        if self.current_index >= 0:
            current_item = self.playlist_widget.item(self.current_index)
            if current_item:
                self.current_index = self.current_playlist_order.index(self.current_index)

    def play_next(self):
        """播放下一首歌曲"""
        if not hasattr(self, 'player_ready') or not self.player_ready:
            QTimer.singleShot(100, self.play_next)
            return
            
        if self.playlist_widget.count() == 0:
            QMessageBox.information(self, "提示", "播放列表为空")
            return
            
        try:
            # 更新播放器中的播放列表
            self.player.current_playlist = [
                self.playlist_widget.item(i).text() 
                for i in range(self.playlist_widget.count())
            ]
            self.player.next()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"播放下一首失败: {str(e)}")

    def play_prev(self):
        """播放上一首歌曲"""
        if not hasattr(self, 'player_ready') or not self.player_ready:
            QTimer.singleShot(100, self.play_prev)
            return
            
        if self.playlist_widget.count() == 0:
            QMessageBox.information(self, "提示", "播放列表为空")
            return
            
        try:
            # 更新播放器中的播放列表
            self.player.current_playlist = [
                self.playlist_widget.item(i).text() 
                for i in range(self.playlist_widget.count())
            ]
            self.player.prev()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"播放上一首失败: {str(e)}")

    def create_playlist(self):
        """创建新歌单"""
        try:
            name, ok = QInputDialog.getText(
                self, "新建歌单", "请输入歌单名称:"
            )
            if not ok:
                return
                
            if not name or not name.strip():
                QMessageBox.warning(self, "错误", "歌单名称不能为空")
                return
                
            if len(name) > 50:
                QMessageBox.warning(self, "错误", "歌单名称过长(最多50个字符)")
                return
                
            if name in self.playlists:
                QMessageBox.warning(self, "错误", "歌单已存在")
                return
                
            self.playlists[name] = []
            self.save_playlists()
            # 刷新歌单菜单
            self.create_menu()
            QMessageBox.information(self, "成功", f"歌单'{name}'创建成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建歌单失败: {str(e)}")

    def delete_playlist(self):
        """删除当前歌单"""
        if len(self.playlists) <= 1:
            QMessageBox.warning(self, "错误", "不能删除最后一个歌单")
            return
            
        reply = QMessageBox.question(
            self, "确认", 
            f"确定要删除歌单'{self.current_playlist}'吗?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.playlists[self.current_playlist]
            # 切换到默认歌单
            self.current_playlist = "默认歌单"
            self.save_playlists()
            # 刷新歌单菜单
            self.create_menu()

    def switch_playlist(self, name):
        """切换到指定歌单"""
        if name == self.current_playlist:
            return
            
        # 停止当前播放
        self.player.stop()
        self.play_btn.setText("播放")
        self.status_label.setText("就绪")
            
        # 保存当前歌单内容
        self.playlists[self.current_playlist] = [
            self.playlist_widget.item(i).text() 
            for i in range(self.playlist_widget.count())
        ]
        
        # 切换到新歌单
        self.current_playlist = name
        self.playlist_widget.clear()
        
        # 只添加存在的文件
        valid_files = [f for f in self.playlists[name] if os.path.exists(f)]
        if valid_files:
            self.playlist_widget.addItems(valid_files)
        else:
            # 如果歌单中所有文件都无效，确保清空播放列表
            self.playlist_widget.clear()
            self.playlists[name] = []  # 清空无效歌单
        
        # 保存设置
        self.save_playlists()

    def save_playlists(self):
        """保存歌单数据"""
        # 保存当前歌单内容
        self.playlists[self.current_playlist] = [
            self.playlist_widget.item(i).text() 
            for i in range(self.playlist_widget.count())
        ]
        
        self.settings.setValue("playlists", self.playlists)
        self.settings.setValue("current_playlist", self.current_playlist)

    def update_current_metadata(self):
        """更新当前播放歌曲的元数据"""
        try:
            current_row = self.playlist_widget.currentRow()
            if current_row == -1:
                QMessageBox.warning(self, "警告", "请先选择一首歌曲")
                return
                
            file_path = self.playlist_widget.item(current_row).text()
            
            # 获取元数据
            metadata = self.metadata_manager.get_cloud_metadata(file_path)
            print(f"更新元数据时获取到的元数据: {metadata}")  # 调试输出
            if not metadata:
                # 尝试获取本地元数据作为回退
                metadata = self.metadata_manager.get_local_metadata(file_path)
                if not metadata:
                    QMessageBox.warning(self, "警告", "无法获取该歌曲的元数据")
                    return
            
            # 构建确认消息
            confirm_msg = "确定要更新这首歌的元数据吗？\n"
            if 'title' in metadata:
                confirm_msg += f"标题: {metadata['title']}\n"
            
            artist = metadata.get('artist') or metadata.get('author') or metadata.get('creator') or '未知'
            confirm_msg += f"艺术家: {artist}\n"
            if 'album' in metadata:
                confirm_msg += f"专辑: {metadata['album']}\n"
            if 'duration' in metadata:
                mins, secs = divmod(int(metadata['duration']), 60)
                confirm_msg += f"时长: {mins}:{secs:02d}"
            
            # 确认更新
            reply = QMessageBox.question(
                self, "确认", confirm_msg,
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.metadata_manager.update_local_metadata(file_path, metadata)
                if success:
                    QMessageBox.information(self, "成功", "元数据更新成功")
                    # 刷新显示
                    self.play_selected()
                else:
                    QMessageBox.warning(self, "错误", "元数据更新失败")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新元数据时出错: {str(e)}")

    def check_login_status(self):
        """检查当前登录状态"""
        if not hasattr(self, 'cloud_service'):
            return False
            
        if not self.cloud_service.is_logged_in:
            self.show_login_prompt()
            return False
        return True

    def show_login_prompt(self):
        """显示登录提示对话框"""
        reply = QMessageBox.question(
            self, "需要登录",
            "需要登录网易云账号才能使用此功能，是否现在登录?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.show_cloud_login()
        return reply == QMessageBox.Yes

    def _update_ui_login_state(self):
        """根据登录状态更新UI"""
        is_logged_in = hasattr(self, 'cloud_service') and self.cloud_service.is_logged_in
        # 这里可以添加UI元素状态更新逻辑
        print(f"[DEBUG] 更新UI登录状态: {'已登录' if is_logged_in else '未登录'}")

    def on_login_success(self):
        """处理登录成功"""
        print("[DEBUG] 登录成功")
        self._update_ui_login_state()
        QMessageBox.information(self, "登录成功", "网易云账号登录成功")

    def on_login_failed(self, error_msg):
        """处理登录失败"""
        print(f"[DEBUG] 登录失败: {error_msg}")
        self._update_ui_login_state()
        QMessageBox.warning(self, "登录失败", f"登录失败: {error_msg}")

    def show_cloud_login(self):
        """显示网易云登录对话框(仅在用户主动点击时调用)"""
        try:
            # 确保只创建一个对话框实例
            if not hasattr(self, '_login_dialog') or not self._login_dialog:
                from MusicPlayer.ui.login_dialog import LoginDialog
                self._login_dialog = LoginDialog(self.cloud_service, self)
                
                # 使用lambda确保在主线程处理信号
                self._login_dialog.login_success.connect(
                    lambda: self.on_login_success(), 
                    Qt.QueuedConnection
                )
                self._login_dialog.login_failed.connect(
                    lambda msg: self.on_login_failed(msg),
                    Qt.QueuedConnection
                )
                self._login_dialog.finished.connect(
                    self._cleanup_login_dialog,
                    Qt.QueuedConnection
                )
            
            # 重置对话框状态
            self._login_dialog.reset_state()
            
            # 设置模态并显示
            self._login_dialog.setWindowModality(Qt.ApplicationModal)
            self._login_dialog.show()
            self._login_dialog.raise_()
            self._login_dialog.activateWindow()
            
            # 添加调试日志
            logging.debug("登录对话框已显示")
            
        except Exception as e:
            error_msg = f"无法显示登录对话框: {str(e)}"
            logging.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "错误", error_msg)
            self._cleanup_login_dialog()

    def _cleanup_login_dialog(self):
        """清理登录对话框资源"""
        if hasattr(self, '_login_dialog') and self._login_dialog:
            try:
                self._login_dialog.deleteLater()
            except:
                pass
            finally:
                self._login_dialog = None
        
    def on_login_success(self):
        """处理登录成功"""
        QMessageBox.information(self, "成功", "网易云账号登录成功")
        # 更新UI状态
        if hasattr(self, 'cloud_menu'):
            for action in self.cloud_menu.actions():
                if action.text() == "账号登录":
                    action.setText("已登录")
                    action.setEnabled(False)
        # 刷新云数据
        self.load_cloud_data()
        
    def on_login_failed(self, error_msg):
        """处理登录失败"""
        QMessageBox.warning(self, "登录失败", error_msg)
        
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        print("[DEBUG] 主窗口显示事件触发")
        
        try:
            # 检查关键组件状态
            print(f"[DEBUG] 播放列表组件状态: {hasattr(self, 'playlist_widget')}")
            if hasattr(self, 'playlist_widget'):
                print(f"播放列表可见性: {self.playlist_widget.isVisible()}")
                print(f"播放列表尺寸: {self.playlist_widget.size()}")
            
            print(f"[DEBUG] 控制面板状态: {hasattr(self, 'control_panel')}")
            if hasattr(self, 'control_panel'):
                print(f"控制面板可见性: {self.control_panel.isVisible()}")
                print(f"控制面板尺寸: {self.control_panel.size()}")
            
            # 检查布局
            if hasattr(self, 'centralWidget') and self.centralWidget().layout():
                print("[DEBUG] 布局信息:")
                print(f"布局间距: {self.centralWidget().layout().spacing()}")
                print(f"布局边距: {self.centralWidget().layout().contentsMargins()}")
            
            # 检查样式表
            if hasattr(self, 'styleSheet') and self.styleSheet():
                print("[DEBUG] 样式表已加载")
            else:
                print("[WARNING] 未检测到样式表")
            
            print(f"[DEBUG] 窗口实际尺寸: {self.size()}")
            
            if not self.initialized:
                print("[DEBUG] 首次初始化UI...")
                self.init_ui()
                self.initialized = True
                print("[DEBUG] UI初始化完成")
                
        except Exception as e:
            print(f"[ERROR] 窗口显示时初始化失败: {str(e)}")
            self.initialized = False

    def batch_update_metadata(self):
        """批量更新播放列表中歌曲的元数据"""
        if self.playlist_widget.count() == 0:
            QMessageBox.warning(self, "警告", "播放列表为空")
            return
            
        reply = QMessageBox.question(
            self, "确认", 
            f"确定要批量更新播放列表中所有歌曲的元数据吗？\n"
            f"共 {self.playlist_widget.count()} 首歌曲",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
            
        progress = QProgressDialog(
            "正在批量更新元数据...", 
            "取消", 
            0, 
            self.playlist_widget.count(), 
            self
        )
        progress.setWindowTitle("批量更新元数据")
        progress.setWindowModality(Qt.WindowModal)
        
        success_count = 0
        for i in range(self.playlist_widget.count()):
            progress.setValue(i)
            if progress.wasCanceled():
                break
                
            file_path = self.playlist_widget.item(i).text()
            metadata = self.metadata_manager.get_cloud_metadata(file_path)
            if metadata:
                if self.metadata_manager.update_local_metadata(file_path, metadata):
                    success_count += 1
            
        progress.setValue(self.playlist_widget.count())
        QMessageBox.information(
            self, 
            "完成", 
            f"元数据更新完成\n成功: {success_count}\n失败: {self.playlist_widget.count() - success_count}"
        )

    def play_by_index(self, index):
        """根据索引播放歌曲"""
        item = self.playlist_widget.item(index)
        if item:
            self.playlist_widget.setCurrentRow(index)
            self.play_selected()
            self.current_index = index

    def get_current_index(self):
        """获取当前播放项的索引"""
        return self.playlist_widget.currentRow()