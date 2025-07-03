# 音乐播放器 - 零环境依赖版

## 用户指南

### 直接运行（无需安装任何环境）

1. 下载完整发布包 [MusicPlayer_Full.zip](https://example.com/download/MusicPlayer_Full.zip)
2. 解压到任意目录
3. 运行 `MusicPlayer.exe`

> 注意：首次运行会自动配置VLC运行时，可能需要几分钟时间

### 系统要求
- Windows 7/10/11 (64位)
- 50MB可用磁盘空间
- 支持MP3解码的声卡

## 开发者打包指南

### 快速打包
1. 运行 `package.bat`
2. 等待打包完成
3. 获取 `dist/MusicPlayer.exe`

### 自定义选项
编辑 `build.spec` 文件：
```python
# 修改程序图标
exe = EXE(..., icon='assets/icon.ico')

# 添加额外数据文件
a.datas += [('config.ini', 'config.ini', 'DATA')]
```

### 常见问题

#### 1. 运行时报"VLC not found"
解决方案：
- 确保已安装VLC播放器
- 或解压包内vlc文件夹到程序目录

#### 2. 打包后程序过大
优化建议：
- 使用UPX压缩：`pyinstaller --upx-dir=path/to/upx ...`
- 排除不必要的包

#### 3. 在无Python环境的电脑运行
必须包含：
- Python解释器(已内置)
- VLC运行时(已包含)
- 所有依赖库(已打包)

## 高级功能

### 命令行参数
```bash
MusicPlayer.exe --mode=random  # 启动时设置播放模式
MusicPlayer.exe --playlist=myplaylist.m3u  # 加载播放列表
```

### 配置文件
编辑 `config.ini`：
```ini
[player]
default_mode=random
volume=80
```

## 技术支持
遇到问题请联系：support@musicplayer.example.com