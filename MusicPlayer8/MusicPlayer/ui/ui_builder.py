from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QSlider, QLabel)
from PyQt5.QtCore import Qt
from MusicPlayer.utils.resource import load_icon, load_style

class UIBuilder:
    """负责构建和配置UI组件"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.theme = "light"  # 默认主题
        
    def build_main_layout(self):
        """构建主窗口布局"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # 主水平布局
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(15)
        
        # 左侧面板 (70%宽度)
        left_panel = self._build_left_panel()
        h_layout.addWidget(left_panel, stretch=7)
        
        # 右侧面板 (30%宽度)
        right_panel = self._build_right_panel()
        h_layout.addWidget(right_panel, stretch=3)
        
        main_layout.addLayout(h_layout)
        
        # 底部控制栏
        bottom_bar = self._build_bottom_bar()
        main_layout.addLayout(bottom_bar)
        
        return main_layout

    def _build_left_panel(self):
        """构建左侧面板"""
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # 播放列表区域
        playlist_card = QWidget()
        playlist_card.setObjectName("playlistCard")
        playlist_layout = QVBoxLayout(playlist_card)
        playlist_layout.setContentsMargins(10, 10, 10, 10)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setObjectName("playlistWidget")
        self.playlist_widget.setStyleSheet("""
            QListWidget#playlistWidget {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                padding: 5px;
            }
        """)
        playlist_layout.addWidget(self.playlist_widget)
        
        # 控制面板
        control_card = QWidget()
        control_card.setObjectName("controlCard")
        control_layout = QVBoxLayout(control_card)
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        self.control_panel = self._build_control_panel()
        control_layout.addWidget(self.control_panel)
        
        left_layout.addWidget(playlist_card, stretch=3)
        left_layout.addWidget(control_card, stretch=1)
        
        return left_panel

    def _build_control_panel(self):
        """构建控制面板"""
        panel = QWidget()
        panel.setObjectName("controlPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 当前播放信息卡片
        info_card = QWidget()
        info_card.setObjectName("infoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignCenter)
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_card)
        
        # 进度条卡片
        progress_card = QWidget()
        progress_card.setObjectName("progressCard")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(5, 5, 5, 5)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setObjectName("progressSlider")
        progress_layout.addWidget(self.progress_slider)
        
        # 时间显示
        time_layout = QHBoxLayout()
        self.current_time = QLabel("00:00")
        self.current_time.setObjectName("timeLabel")
        self.total_time = QLabel("00:00")
        self.total_time.setObjectName("timeLabel")
        time_layout.addWidget(self.current_time)
        time_layout.addStretch()
        time_layout.addWidget(self.total_time)
        progress_layout.addLayout(time_layout)
        
        layout.addWidget(progress_card)
        
        # 控制按钮卡片
        button_card = QWidget()
        button_card.setObjectName("buttonCard")
        button_layout = QHBoxLayout(button_card)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        
        # 播放控制按钮
        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("prevButton")
        self.prev_btn.setToolTip("上一曲")
        
        self.play_btn = QPushButton()
        self.play_btn.setObjectName("playButton")
        self.play_btn.setToolTip("播放/暂停")
        
        self.next_btn = QPushButton()
        self.next_btn.setObjectName("nextButton")
        self.next_btn.setToolTip("下一曲")
        
        # 播放模式按钮
        self.mode_btn = QPushButton()
        self.mode_btn.setObjectName("modeButton")
        self.mode_btn.setToolTip("顺序播放")
        self.mode_btn.setCheckable(True)
        
        button_layout.addStretch()
        button_layout.addWidget(self.prev_btn)
        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.mode_btn)
        button_layout.addStretch()
        
        layout.addWidget(button_card)
        
        # 音量控制卡片
        volume_card = QWidget()
        volume_card.setObjectName("volumeCard")
        volume_layout = QHBoxLayout(volume_card)
        volume_layout.setContentsMargins(5, 5, 5, 5)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setObjectName("volumeSlider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        volume_layout.addWidget(self.volume_slider)
        
        layout.addWidget(volume_card)
        
        return panel

    def _build_right_panel(self):
        """构建右侧面板"""
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # 云音乐卡片
        cloud_card = QWidget()
        cloud_card.setObjectName("cloudCard")
        cloud_card.setProperty("class", "card")
        cloud_layout = QVBoxLayout(cloud_card)
        cloud_layout.setContentsMargins(15, 15, 15, 15)
        cloud_layout.setSpacing(10)
        
        # 标题和刷新按钮
        title_layout = QHBoxLayout()
        self.cloud_title = QLabel("云音乐数据")
        self.refresh_btn = QPushButton("刷新")
        title_layout.addWidget(self.cloud_title)
        title_layout.addStretch()
        title_layout.addWidget(self.refresh_btn)
        cloud_layout.addLayout(title_layout)
        
        # 云音乐列表
        self.cloud_list = QListWidget()
        self.cloud_list.setObjectName("cloudList")
        cloud_layout.addWidget(self.cloud_list)
        
        # 加载状态
        self.loading_label = QLabel("准备加载数据...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        cloud_layout.addWidget(self.loading_label)

        # 音乐信息显示
        self.music_info_label = QLabel()
        self.music_info_label.setObjectName("musicInfo")
        self.music_info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.music_info_label.setWordWrap(True)
        cloud_layout.addWidget(self.music_info_label)
        
        right_layout.addWidget(cloud_card)
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加文件夹")
        right_layout.addWidget(self.add_folder_btn)
        
        return right_panel
    
    def _build_top_bar(self):
        """构建顶部控制栏"""
        layout = QHBoxLayout()
        
        # 添加菜单按钮
        self.menu_button = QPushButton()
        self.menu_button.setIcon(load_icon("menu"))
        layout.addWidget(self.menu_button)
        
        # 添加搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("搜索音乐...")
        layout.addWidget(self.search_box, stretch=1)
        
        # 添加主题切换按钮
        self.theme_button = QPushButton()
        self.theme_button.setIcon(load_icon("theme"))
        layout.addWidget(self.theme_button)
        
        return layout
    
    def _build_content_area(self):
        """构建内容区域"""
        content = QWidget()
        content_layout = QHBoxLayout(content)
        
        # 左侧播放列表
        self.playlist = QListWidget()
        content_layout.addWidget(self.playlist, stretch=1)
        
        # 右侧元数据面板
        self.metadata_panel = self._build_metadata_panel()
        content_layout.addWidget(self.metadata_panel, stretch=2)
        
        return content
    
    def _build_metadata_panel(self):
        """构建元数据显示面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 专辑封面
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cover_label)
        
        # 歌曲信息
        self.info_label = QLabel("未播放")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        return panel
    
    def _build_bottom_bar(self):
        """构建底部控制栏"""
        layout = QHBoxLayout()
        
        # 播放控制按钮
        self.prev_button = QPushButton()
        self.prev_button.setIcon(load_icon("prev"))
        
        self.play_button = QPushButton()
        self.play_button.setIcon(load_icon("play"))
        
        self.next_button = QPushButton()
        self.next_button.setIcon(load_icon("next"))
        
        layout.addWidget(self.prev_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.next_button)
        
        # 进度条
        self.progress_slider = QSlider(Qt.Horizontal)
        layout.addWidget(self.progress_slider, stretch=1)
        
        # 音量控制
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        layout.addWidget(self.volume_slider, stretch=1)
        
        return layout
    
    def apply_theme(self, theme_name):
        """应用主题样式"""
        self.theme = theme_name
        style = load_style(f"themes/{theme_name}.qss")
        self.parent.setStyleSheet(style)