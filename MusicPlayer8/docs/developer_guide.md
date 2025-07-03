# MusicPlayer 开发者文档

## 项目结构
```
MusicPlayer/
├── main.py            # 程序入口
├── player.py          # 核心播放逻辑
├── ui/                # 用户界面
├── utils/             # 工具类
├── resources/         # 资源文件
└── docs/              # 文档
```

## 核心模块

### 1. 播放器核心 (player.py)
- 功能：音频播放、元数据获取
- 示例：
  ```python
  player = MusicPlayer()
  player.load("song.mp3")
  player.play()
  ```

### 2. 用户界面 (ui/)
- main_window.py: 主窗口实现
- login_dialog.py: 登录对话框

### 3. 工具类 (utils/)
- metadata_manager.py: 元数据管理
- resource.py: 资源加载

## 开发环境
1. 安装开发依赖：
   ```bash
   pip install -r requirements-dev.txt
   ```
2. 配置IDE：
   - 推荐使用PyCharm或VSCode
   - 设置Python解释器为3.8+

## 代码规范
- PEP 8规范
- 类型注解
- 模块级docstring
- 函数级注释

## 测试指南
运行单元测试：
```bash
pytest tests/
```