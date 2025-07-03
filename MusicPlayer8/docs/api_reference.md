# MusicPlayer API参考

## 核心类

### MusicPlayer (player.py)
主播放器类，负责音频播放控制。

#### 方法
```python
load(file_path: str) -> bool
```
- 功能：加载音频文件
- 参数：
  - file_path: 音频文件路径
- 返回：加载是否成功
- 异常：FileNotFoundError, UnsupportedFormatError

```python
play() -> None
```
- 功能：开始播放当前加载的音频
- 异常：NoAudioLoadedError

## 元数据管理

### MetadataManager (utils/metadata_manager.py)
负责音频元数据获取和管理。

#### 方法
```python
get_metadata(file_path: str) -> dict
```
- 功能：获取音频元数据
- 参数：
  - file_path: 音频文件路径
- 返回：包含元数据的字典
- 示例返回值：
  ```python
  {
    "title": "Song Name",
    "artist": "Artist Name",
    "album": "Album Name",
    "duration": 240.5
  }
  ```

## UI组件

### MainWindow (ui/main_window.py)
主窗口类，提供用户界面。

#### 方法
```python
add_folder(path: str) -> None
```
- 功能：添加音乐文件夹到播放列表
- 参数：
  - path: 文件夹路径
- 异常：InvalidPathError