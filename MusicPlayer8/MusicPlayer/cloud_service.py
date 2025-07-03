import os
"""
云音乐服务模块

提供与云端音乐服务的交互功能，包括：
- 热门歌曲获取
- 元数据查询
- 封面下载

示例用法:
    service = CloudService()
    service.base_url = "https://api.example.com"
    service.get_hot_songs()

注意:
    使用前需要设置有效的base_url
    支持缓存和自动重试机制
"""

import requests
import time
import threading
from typing import Optional, Dict, Any, Tuple
from PyQt5.QtCore import QObject, pyqtSignal


class CloudServiceError(Exception):
    """云服务基础异常"""
    def __init__(self, message, code=None, details=None):
        super().__init__(message)
        self.code = code
        self.details = details
        self.timestamp = time.time()

    def __str__(self):
        if self.code:
            return f"[{self.code}] {super().__str__()}"
        return super().__str__()


class NetworkError(CloudServiceError):
    """网络相关异常"""
    pass


class APIError(CloudServiceError):
    """API业务异常"""
    pass

class CloudMusicService(QObject):
    """云音乐服务类
    
    提供与云端音乐API的交互功能，包括：
    - 热门歌曲和推荐内容获取
    - 歌曲元数据查询
    - 封面图片下载
    - 用户认证管理
    
    信号:
        data_updated(dict): 当新数据(如热门歌曲、推荐内容)可用时触发
        metadata_found(dict): 当查询到歌曲元数据时触发
        login_success(): 当用户登录成功时触发
        login_failed(str): 当用户登录失败时触发，参数为错误信息
        cover_downloaded(str): 当封面下载完成时触发，参数为封面文件路径
        metadata_error(str): 当元数据查询出错时触发，参数为错误信息
    
    属性:
        base_url (str): 云服务API基础URL，留空表示禁用云服务
        token (Optional[str]): 用户认证令牌
    
    示例:
        >>> service = CloudMusicService()
        >>> service.base_url = "https://api.example.com"
        >>> 
        >>> # 连接信号
        >>> service.data_updated.connect(handle_data)
        >>> service.metadata_error.connect(handle_error)
        >>> 
        >>> # 获取热门歌曲
        >>> service.get_hot_songs()
        >>> 
        >>> # 查询歌曲元数据
        >>> metadata = service.query_song_metadata("song.mp3")
    """
    data_updated = pyqtSignal(dict)  # type: ignore
    metadata_found = pyqtSignal(dict)  # type: ignore
    login_success = pyqtSignal()  # type: ignore
    login_failed = pyqtSignal(str)  # type: ignore
    cover_downloaded = pyqtSignal(str)  # type: ignore
    metadata_error = pyqtSignal(str)  # type: ignore
    
    def __init__(self):
        super().__init__()
        self.base_url = ""  # 留空表示禁用云服务，或填入有效API地址
        self.token = None
        self.session = requests.Session()  # 复用会话
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            max_retries=3,  # 最大重试次数
            pool_connections=10,  # 连接池大小
            pool_maxsize=50
        ))
        self._request_lock = threading.Lock()  # 请求锁
        self._cache = {}  # 内存缓存
        self._cache_lock = threading.Lock()  # 缓存锁
        self._last_request_time = 0  # 最后请求时间
        self._min_request_interval = 0.5  # 最小请求间隔(秒)
        self.mock_data = {
            "hot": [{
                "id": "mock1",
                "name": "示例热门歌曲1",
                "artist": "示例歌手"
            }, {
                "id": "mock2", 
                "name": "示例热门歌曲2",
                "artist": "示例歌手"
            }],
            "recommend": [{
                "id": "mock_playlist1",
                "name": "推荐歌单1",
                "cover": "default_cover.png"
            }],
            "personal": [{
                "id": "mock_personal1",
                "name": "个性化推荐1",
                "type": "daily"
            }]
        }
        
    @property
    def is_logged_in(self):
        """判断用户是否已登录"""
        return self.token is not None
        
    def _get_cache_key(self, endpoint, params):
        """生成缓存键"""
        param_str = str(sorted(params.items())) if params else ''
        return f"{endpoint}:{param_str}"

    def _get_from_cache(self, key, max_age=300):
        """从缓存获取数据"""
        with self._cache_lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                if time.time() - timestamp <= max_age:
                    return data
                del self._cache[key]
        return None

    def _set_to_cache(self, key, data):
        """设置缓存数据"""
        with self._cache_lock:
            self._cache[key] = (data, time.time())

    def _clear_cache(self):
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()

    def _rate_limit(self):
        """请求速率限制"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _make_request(self, endpoint, params=None, method='GET', retry=3, use_cache=True):
        """统一的请求方法
        Args:
            endpoint: API端点
            params: 请求参数
            method: HTTP方法
            retry: 重试次数
            use_cache: 是否使用缓存
        Returns:
            验证后的响应数据
        Raises:
            NetworkError: 网络相关错误
            APIError: API业务错误
        """
        if not self.base_url:
            raise ValueError("云服务未配置")

        # 检查缓存
        cache_key = self._get_cache_key(endpoint, params)
        if use_cache and method == 'GET':
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                print(f"[CACHE] 命中缓存: {cache_key}")
                return cached_data

        url = f"{self.base_url}/{endpoint}"
        last_error = None

        # 应用速率限制
        self._rate_limit()
        
        for attempt in range(1, retry + 1):
            try:
                start_time = time.time()
                with self._request_lock:
                    response = self.session.request(
                        method,
                        url,
                        params=params,
                        timeout=(3.05, 10)
                    )
                    response_time = time.time() - start_time
                    
                    print(f"[DEBUG] 请求 {url} 耗时 {response_time:.2f}s")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # 验证响应数据
                    self._validate_response(data)
                    
                    # 更新缓存
                    if use_cache and method == 'GET' and data:
                        try:
                            self._set_to_cache(cache_key, data)
                            print(f"[CACHE] 更新缓存: {cache_key}")
                        except Exception as e:
                            print(f"[CACHE] 缓存更新失败: {str(e)}")
                    
                    return data
                    
            except requests.exceptions.RequestException as e:
                last_error = NetworkError(
                    f"请求失败(尝试 {attempt}/{retry}): {str(e)}",
                    code=getattr(e.response, 'status_code', None),
                    details={
                        'url': url,
                        'params': params,
                        'attempt': attempt
                    }
                )
                if attempt < retry:
                    wait_time = min(2 ** attempt, 5)  # 指数退避
                    time.sleep(wait_time)
                continue
                
            except (ValueError, KeyError) as e:
                last_error = APIError(
                    f"响应数据格式错误: {str(e)}",
                    code='INVALID_RESPONSE',
                    details={
                        'url': url,
                        'response': response.text[:200] if response else None
                    }
                )
                break
                
        raise last_error

    def _validate_response(self, data):
        """验证API响应数据
        Args:
            data: 要验证的响应数据
        Raises:
            APIError: 当数据不符合预期时
        """
        if not isinstance(data, dict):
            raise APIError("响应必须是JSON对象", code='INVALID_FORMAT')
            
        if 'code' in data and data['code'] != 200:
            raise APIError(
                data.get('message', 'API返回错误'),
                code=data.get('code'),
                details=data
            )

    def get_hot_songs(self) -> None:
        """获取当前热门歌曲列表
        
        从云服务API获取热门歌曲数据并通过data_updated信号发送。
        如果云服务禁用或请求失败，则使用模拟数据。
        
        信号参数:
            data_updated(dict): 包含以下键值:
                - type (str): 数据类型，固定为'hot_songs'
                - data (List[Dict]): 歌曲列表，每个歌曲包含id、name等字段
                - timestamp (int): 数据获取时间戳
                - is_mock (bool, 可选): 是否为模拟数据
        
        异常:
            无显式抛出异常，错误通过metadata_error信号发送
        
        示例:
            >>> service.get_hot_songs()
            >>> # 连接信号处理返回数据
            >>> service.data_updated.connect(lambda data: print(data['type']))
        """
        try:
            if not self.base_url:
                raise CloudServiceError("云服务已禁用")
            
            data = self._make_request('hot')
            self.data_updated.emit({
                'type': 'hot_songs',
                'data': data.get('songs', []),
                'timestamp': int(time.time())
            })
        except CloudServiceError as e:
            self.metadata_error.emit(str(e))
            print(f"[WARN] 使用模拟数据: {str(e)}")
            self.data_updated.emit({
                'type': 'hot_songs',
                'data': self.mock_data["hot"],
                'is_mock': True
            })
    
    def get_recommend_playlists(self) -> None:
        """获取推荐歌单列表
        
        从云服务API获取推荐歌单数据并通过data_updated信号发送。
        如果云服务禁用或请求失败，则使用模拟数据。
        
        信号参数:
            data_updated(dict): 包含以下键值:
                - type (str): 数据类型，固定为'recommend_playlists'
                - data (List[Dict]): 歌单列表，每个歌单包含id、name等字段
                - timestamp (int): 数据获取时间戳
                - is_mock (bool, 可选): 是否为模拟数据
        
        异常:
            无显式抛出异常，错误通过metadata_error信号发送
            
        示例:
            >>> service.get_recommend_playlists()
            >>> # 连接信号处理返回数据
            >>> service.data_updated.connect(lambda data: print(len(data['data'])))
        """
        try:
            if not self.base_url:
                raise CloudServiceError("云服务已禁用")
            
            data = self._make_request('recommend')
            self.data_updated.emit({
                'type': 'recommend_playlists',
                'data': data.get('playlists', []),
                'timestamp': int(time.time())
            })
        except CloudServiceError as e:
            self.metadata_error.emit(str(e))
            print(f"[WARN] 使用模拟数据: {str(e)}")
            self.data_updated.emit({
                'type': 'recommend_playlists',
                'data': self.mock_data["recommend"],
                'is_mock': True
            })
    
    def get_personal_recommend(self) -> None:
        """获取个性化推荐内容
        
        从云服务API获取个性化推荐数据并通过data_updated信号发送。
        需要有效的token认证，如果云服务禁用或请求失败，则使用模拟数据。
        
        信号参数:
            data_updated(dict): 包含以下键值:
                - type (str): 数据类型，固定为'personal_recommend'
                - data (List[Dict]): 推荐歌曲列表，每首歌曲包含id、name等字段
                - timestamp (int): 数据获取时间戳
                - is_mock (bool, 可选): 是否为模拟数据
        
        异常:
            无显式抛出异常，错误通过metadata_error信号发送
            
        示例:
            >>> service.token = "valid_token"
            >>> service.get_personal_recommend()
            >>> # 连接信号处理返回数据
            >>> service.data_updated.connect(lambda data: print(data['type']))
        """
        try:
            if not self.base_url:
                raise CloudServiceError("云服务已禁用")
            if not self.token:
                raise CloudServiceError("需要认证token")
            
            data = self._make_request(
                'personal',
                headers={'Authorization': f'Bearer {self.token}'}
            )
            self.data_updated.emit({
                'type': 'personal_recommend',
                'data': data.get('recommends', []),
                'timestamp': int(time.time())
            })
        except CloudServiceError as e:
            self.metadata_error.emit(str(e))
            print(f"[WARN] 使用模拟数据: {str(e)}")
            self.data_updated.emit({
                'type': 'personal_recommend',
                'data': self.mock_data["personal"],
                'is_mock': True
            })
            
    def query_song_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        """查询歌曲元数据
        
        通过文件名查询云端歌曲元数据，结果通过metadata_found信号发送。
        
        参数:
            file_path: 音频文件路径
            
        返回:
            包含以下键的字典或None:
                - title (str): 歌曲标题
                - artist (str): 艺术家名称
                - album (str): 专辑名称
                - duration (float): 时长(秒)
                - source (str): 数据来源('cloud'或'mock')
                
        信号:
            metadata_found(dict): 当查询成功时触发，参数为元数据字典
            metadata_error(str): 当查询失败时触发，参数为错误信息
            
        示例:
            >>> metadata = service.query_song_metadata("song.mp3")
            >>> # 连接信号处理返回数据
            >>> service.metadata_found.connect(lambda data: print(data['title']))
        """
        if not self.base_url:
            self.metadata_error.emit("云服务已禁用")
            return None
            
        try:
            # 提取文件名作为查询条件
            filename = os.path.basename(file_path)
            song_name = os.path.splitext(filename)[0]
            
            # 使用统一请求方法(带缓存)
            params = {'q': song_name, 'limit': 1}
            data = self._make_request('search', params=params)
            
            if data.get('songs'):
                song = data['songs'][0]
                metadata = {
                    'title': song.get('name', song_name),
                    'artist': song.get('artists', [{'name': '未知艺术家'}])[0]['name'],
                    'album': song.get('album', {'name': '未知专辑'})['name'],
                    'duration': song.get('duration', 240000) / 1000,
                    'source': 'cloud'
                }
                self.metadata_found.emit(metadata)
                return metadata
                
        except CloudServiceError as e:
            self.metadata_error.emit(str(e))
            print(f"云服务查询元数据失败: {e}")
            
        return None