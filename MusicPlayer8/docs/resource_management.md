# 资源管理规范

## 1. 图标资源使用
- 存放位置：`resources/icons/`
- 命名规范：`功能_状态.png` (如`play_normal.png`, `play_hover.png`)
- 使用方式：
  ```python
  from utils.resource import load_icon
  
  icon = load_icon("play_normal")
  ```

## 2. 自动清理机制
资源自动清理规则：
- 30天未访问的缓存资源
- 超过100MB的临时文件
- 错误格式的资源文件

## 3. 样式表管理
- 主样式表：`resources/styles/main.qss`
- 备用样式加载流程：
  1. 尝试加载主样式表
  2. 失败时加载默认样式
  3. 记录加载错误日志