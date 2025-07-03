# 音乐播放器

基于Python和PyQt5的音乐播放器应用，支持多种音频格式播放。

## 功能特性

- 播放/暂停/停止控制
- 音量调节
- 播放进度控制
- 播放列表管理
- 支持MP3、FLAC、WAV、OGG等格式
- 现代化UI界面

## 安装依赖

```bash
pip install python-vlc PyQt5 pyinstaller
```

## 运行应用

```bash
python main.py
```

## 打包应用

1. 确保已安装PyInstaller
2. 运行以下命令：

```bash
pyinstaller build.spec
```

打包后的应用将生成在`dist`目录中。

## 项目结构

```
MusicPlayer/
├── main.py                # 应用入口
├── player.py              # 播放器核心逻辑
├── ui/
│   └── main_window.py     # 主窗口UI
├── resources/
│   ├── styles.qss         # 样式表
│   └── icons/             # 应用图标
└── build.spec             # PyInstaller打包配置
```

## 截图

![应用截图](resources/screenshot.png)

## 许可证

MIT