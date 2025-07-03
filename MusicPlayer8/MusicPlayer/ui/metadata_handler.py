from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool, QRunnable
from MusicPlayer.utils.metadata_manager import MetadataManager

class MetadataHandler(QObject):
    """处理所有元数据相关操作"""
    
    # 信号定义
    metadata_ready = pyqtSignal(dict)  # 单个文件元数据就绪
    batch_progress = pyqtSignal(int, int)  # 批量处理进度
    batch_complete = pyqtSignal(list)  # 批量处理完成
    
    def __init__(self, manager=None):
        super().__init__()
        self.manager = manager or MetadataManager()
        self.thread_pool = QThreadPool.globalInstance()
        self.cache = {}  # 元数据缓存
    
    def get_metadata(self, file_path, use_cache=True):
        """获取单个文件的元数据"""
        if use_cache and file_path in self.cache:
            self.metadata_ready.emit(self.cache[file_path])
            return
            
        # 使用线程处理耗时操作
        worker = MetadataWorker(self.manager, file_path)
        worker.signals.result.connect(self._on_metadata_ready)
        worker.signals.error.connect(self._on_metadata_error)
        self.thread_pool.start(worker)
    
    def _on_metadata_ready(self, result):
        """处理元数据获取完成"""
        file_path, metadata = result
        self.cache[file_path] = metadata
        self.metadata_ready.emit(metadata)
    
    def _on_metadata_error(self, file_path, error):
        """处理元数据获取错误"""
        self.metadata_ready.emit({
            'file_path': file_path,
            'error': str(error)
        })
    
    def batch_process(self, file_list, batch_size=10):
        """批量处理元数据"""
        total = len(file_list)
        processed = 0
        results = []
        
        for i in range(0, total, batch_size):
            batch = file_list[i:i+batch_size]
            batch_results = self.manager.batch_get_metadata(batch)
            results.extend(batch_results)
            processed += len(batch)
            self.batch_progress.emit(processed, total)
            
        self.batch_complete.emit(results)
        return results
    
    def clear_cache(self):
        """清空元数据缓存"""
        self.cache.clear()

class MetadataWorker(QRunnable):
    """后台元数据获取工作线程"""
    
    class WorkerSignals(QObject):
        result = pyqtSignal(tuple)  # (file_path, metadata)
        error = pyqtSignal(str, str)  # (file_path, error)
    
    def __init__(self, manager, file_path):
        super().__init__()
        self.manager = manager
        self.file_path = file_path
        self.signals = self.WorkerSignals()
        
    def run(self):
        try:
            metadata = self.manager.get_metadata(self.file_path)
            self.signals.result.emit((self.file_path, metadata))
        except Exception as e:
            self.signals.error.emit(self.file_path, str(e))