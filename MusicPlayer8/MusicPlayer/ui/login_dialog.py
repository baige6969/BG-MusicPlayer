from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QMessageBox,
    QHBoxLayout, QSpacerItem, QSizePolicy,
    QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QIcon, QFont
import os
import logging

class LoginDialog(QDialog):
    """网易云音乐登录对话框"""
    login_success = pyqtSignal()
    login_failed = pyqtSignal(str)

    def __init__(self, cloud_service=None, parent=None):
        super().__init__(parent)
        self.cloud_service = cloud_service  # 存储服务实例
        self.setWindowTitle("网易云账号登录")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # 增强图标路径处理
        icon_path = os.path.join("resources", "icons", "cloud.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            logging.warning(f"图标文件未找到: {icon_path}")
            
        # 加载样式表
        style_path = os.path.join("MusicPlayer", "resources", "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            logging.warning(f"样式表文件未找到: {style_path}")
            
        # 设置窗口属性
        self.setMinimumSize(300, 200)
        self.setMaximumSize(400, 300)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlag(Qt.FramelessWindowHint)
        
        self._init_ui()
        self._load_saved_credentials()

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 主容器
        container = QWidget()
        container.setObjectName("loginContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(15)
        
        # 用户名输入
        self.username_label = QLabel("用户名:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入网易云用户名")
        self.username_input.setObjectName("usernameInput")
        container_layout.addWidget(self.username_label)
        container_layout.addWidget(self.username_input)
        
        # 密码输入
        self.password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("passwordInput")
        container_layout.addWidget(self.password_label)
        container_layout.addWidget(self.password_input)
        
        # 记住密码选项
        self.remember_check = QCheckBox("记住密码")
        container_layout.addWidget(self.remember_check)
        
        # 添加弹性空间
        container_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setObjectName("cancelButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.login_btn = QPushButton("登录")
        self.login_btn.setObjectName("loginButton")
        self.login_btn.clicked.connect(self._on_login)
        
        button_layout.addStretch(1)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.login_btn)
        
        container_layout.addLayout(button_layout)
        
        # 将容器添加到主布局
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        
        # 设置输入框动画
        self._setup_animations()

    def _load_saved_credentials(self):
        """加载保存的凭据(示例实现)"""
        cred_file = os.path.join(
            os.path.expanduser("~"), 
            ".musicplayer", 
            "cloudmusic_creds"
        )
        
        if os.path.exists(cred_file):
            try:
                with open(cred_file, "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        self.username_input.setText(lines[0].strip())
                        self.password_input.setText(lines[1].strip())
                        self.remember_check.setChecked(True)
            except Exception:
                pass

    def _on_login(self):
        """处理登录按钮点击"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        remember = self.remember_check.isChecked()

        if not username or not password:
            QMessageBox.warning(self, "输入错误", "用户名和密码不能为空")
            return

        # 禁用登录按钮防止重复点击
        self.login_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        try:
            # 验证云服务可用性
            if not self.cloud_service or not hasattr(self.cloud_service, 'login'):
                error_msg = "云音乐服务不可用"
                logging.error(error_msg)
                self.login_failed.emit(error_msg)
                return

            # 使用线程安全方式调用登录
            def handle_login_result(success, error=None):
                self.login_btn.setEnabled(True)
                self.cancel_btn.setEnabled(True)
                
                if success:
                    logging.info("登录成功")
                    if remember:
                        self._save_credentials(username, password)
                    self.login_success.emit()
                    self.accept()
                else:
                    error_msg = error or "登录失败，请检查用户名和密码"
                    logging.error(f"登录失败: {error_msg}")
                    self.login_failed.emit(error_msg)

            # 实际调用登录服务
            try:
                result = self.cloud_service.login(username, password, remember)
                if isinstance(result, tuple) and len(result) == 2:
                    success, error = result
                    handle_login_result(success, error)
                else:
                    handle_login_result(result)
            except Exception as e:
                error_msg = f"登录时发生错误: {str(e)}"
                logging.error(error_msg, exc_info=True)
                handle_login_result(False, error_msg)

        except Exception as e:
            error_msg = f"处理登录时发生错误: {str(e)}"
            logging.error(error_msg, exc_info=True)
            self.login_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.login_failed.emit(error_msg)

    def _save_credentials(self, username, password):
        """保存凭据到文件"""
        cred_dir = os.path.join(os.path.expanduser("~"), ".musicplayer")
        cred_file = os.path.join(cred_dir, "cloudmusic_creds")
        
        try:
            os.makedirs(cred_dir, exist_ok=True)
            with open(cred_file, "w") as f:
                f.write(f"{username}\n{password}")
        except Exception as e:
            logging.error(f"保存凭据失败: {str(e)}")

    def show_error(self, message):
        """显示错误消息"""
        QMessageBox.critical(self, "登录失败", message)
        self.login_failed.emit(message)

    def show_success(self):
        """登录成功处理"""
        self.login_success.emit()
        self.accept()

    def _setup_animations(self):
        """设置UI元素的动画效果"""
        # 登录按钮点击动画
        self.login_btn_animation = QPropertyAnimation(self.login_btn, b"geometry")
        self.login_btn_animation.setDuration(200)
        self.login_btn_animation.setEasingCurve(QEasingCurve.OutQuad)
        
        # 输入框焦点动画
        self.username_animation = QPropertyAnimation(self.username_input, b"geometry")
        self.username_animation.setDuration(150)
        self.username_animation.setEasingCurve(QEasingCurve.OutQuad)
        
        self.password_animation = QPropertyAnimation(self.password_input, b"geometry")
        self.password_animation.setDuration(150)
        self.password_animation.setEasingCurve(QEasingCurve.OutQuad)
        
        # 连接信号
        self.login_btn.pressed.connect(self._animate_button_press)
        self.username_input.focusInEvent = lambda e: (self._animate_input_focus(self.username_input, self.username_animation), QLineEdit.focusInEvent(self.username_input, e))
        self.password_input.focusInEvent = lambda e: (self._animate_input_focus(self.password_input, self.password_animation), QLineEdit.focusInEvent(self.password_input, e))

    def _animate_button_press(self):
        """按钮点击动画"""
        start_rect = self.login_btn.geometry()
        self.login_btn_animation.setStartValue(start_rect)
        self.login_btn_animation.setEndValue(start_rect.adjusted(0, 2, 0, 2))
        self.login_btn_animation.start()

    def _animate_input_focus(self, widget, animation):
        """输入框获取焦点动画"""
        start_rect = widget.geometry()
        animation.setStartValue(start_rect)
        animation.setEndValue(start_rect.adjusted(-2, -2, 2, 2))
        animation.start()
        
    def reset_state(self):
        """重置对话框状态"""
        # 清除错误状态
        self.username_input.setStyleSheet("")
        self.password_input.setStyleSheet("")
        
        # 重新加载保存的凭据
        self._load_saved_credentials()
        
        # 重置按钮状态
        self.login_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)