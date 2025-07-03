import os
import cloudmusic
import functools
import json
from typing import Optional, Dict
import requests
from difflib import SequenceMatcher
from mutagen import File
from mutagen.id3 import USLT, APIC
from tinytag import TinyTag
import sqlite3
import time
import logging

class MetadataManager:
    def __init__(self):
        self.cache_db = "metadata_cache.db"
        self._init_cache_db()
        logging.basicConfig(level=logging.INFO)
        
    def _init_cache_db(self):
        """初始化SQLite缓存数据库"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata_cache (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _get_local_metadata(self, file_path):
        """获取本地文件元数据"""
        try:
            tag = TinyTag.get(file_path)
            return {
                "title": tag.title or os.path.basename(file_path),
                "artist": tag.artist or "未知艺术家",
                "album": tag.album or "未知专辑",
                "duration": tag.duration or 0
            }
        except Exception as e:
            logging.error(f"读取本地元数据失败: {e}")
            return {
                "title": os.path.basename(file_path),
                "artist": "未知艺术家",
                "album": "未知专辑",
                "duration": 0
            }

    def _match_cloud_metadata(self, local_meta):
        """匹配网易云音乐数据"""
        try:
            # 尝试通过元数据匹配
            query = f"{local_meta['title']} {local_meta['artist']}"
            results = self._safe_cloud_request(
                lambda: cloudmusic.search(query))
            
            if results:
                # 使用模糊匹配找到最佳结果
                best_match = None
                best_score = 0
                
                for music in results:
                    # 比较歌曲名和艺术家名的相似度
                    title_score = SequenceMatcher(
                        None, local_meta['title'], music.name).ratio()
                    artist_score = SequenceMatcher(
                        None, local_meta['artist'], music.artist).ratio()
                    total_score = title_score * 0.6 + artist_score * 0.4
                    
                    if total_score > best_score:
                        best_score = total_score
                        best_match = music
                
                if best_score > 0.7:  # 相似度阈值
                    return best_match
        
        except Exception as e:
            logging.error(f"匹配云数据失败: {e}")
        
        return None

    def _safe_cloud_request(self, request_func):
        """安全的云API请求，带重试机制"""
        max_retries = 3
        for i in range(max_retries):
            try:
                return request_func()
            except Exception as e:
                if "429" in str(e) and i < max_retries - 1:
                    wait_time = 2 ** i  # 指数退避
                    time.sleep(wait_time)
                    continue
                raise

    @functools.lru_cache(maxsize=1024)
    def get_metadata(self, file_path: str, use_cloud: bool = True) -> Dict:
        """
        获取文件元数据(统一接口)
        
        参数:
            file_path: 文件路径
            use_cloud: 是否尝试获取云数据
            
        返回:
            包含元数据的字典，格式:
            {
                "title": str,
                "artist": str,
                "album": str,
                "duration": int,
                "lyrics": Optional[str],
                "cover_url": Optional[str],
                "source": str  # "local"或"cloud"
            }
        """
        # 首先尝试从缓存获取
        cache_key = f"{file_path}:{use_cloud}"
        cached = self._get_cached_metadata(cache_key)
        if cached:
            return cached
            
        # 获取本地元数据
        local_meta = self._get_local_metadata(file_path)
        meta = {
            **local_meta,
            "lyrics": None,
            "cover_url": None,
            "source": "local"
        }
        
        # 如果启用云数据且网络可用
        if use_cloud:
            try:
                cloud_meta = self._get_cloud_metadata(file_path, local_meta)
                if cloud_meta:
                    meta.update({
                        "title": cloud_meta.get("title", meta["title"]),
                        "artist": cloud_meta.get("artist", meta["artist"]),
                        "album": cloud_meta.get("album", meta["album"]),
                        "duration": cloud_meta.get("duration", meta["duration"]),
                        "lyrics": cloud_meta.get("lyrics"),
                        "cover_url": cloud_meta.get("cover_url"),
                        "source": "cloud"
                    })
            except Exception as e:
                logging.warning(f"获取云数据失败，使用本地数据: {str(e)}")
        
        # 更新缓存
        self._cache_metadata(cache_key, meta)
        return meta

    def _get_cached_metadata(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取元数据"""
        with sqlite3.connect(self.cache_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT data FROM metadata_cache WHERE key=?",
                (cache_key,))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

    def _cache_metadata(self, cache_key: str, metadata: Dict) -> None:
        """缓存元数据"""
        with sqlite3.connect(self.cache_db) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO metadata_cache 
                (key, data, last_updated) VALUES (?, ?, ?)""",
                (cache_key, json.dumps(metadata), int(time.time()))
            )

    def _get_cloud_metadata(self, file_path: str, local_meta: Dict) -> Optional[Dict]:
        """获取云端元数据"""
        music = self._match_cloud_metadata(local_meta)
        if not music:
            return None
            
        try:
            lyrics = self._safe_cloud_request(
                lambda: music.getLyrics()[0])
            cover_url = music.picUrl
            
            return {
                "title": music.name,
                "artist": music.artist,
                "album": music.album,
                "lyrics": lyrics,
                "cover_url": cover_url,
                "duration": music.duration
            }
        except Exception as e:
            logging.error(f"获取云数据详情失败: {e}")
            return None

    # 保持向后兼容的别名
    get_cloud_metadata = _get_cloud_metadata

    def update_local_metadata(self, file_path, metadata):
        """更新本地文件元数据"""
        try:
            audio = File(file_path)
            
            # 更新基本标签
            if metadata.get('title'):
                audio.tags["TIT2"] = metadata['title']
            if metadata.get('artist'):
                audio.tags["TPE1"] = metadata['artist']
            if metadata.get('album'):
                audio.tags["TALB"] = metadata['album']
            
            # 添加歌词
            if metadata.get('lyrics'):
                audio.tags["USLT"] = USLT(
                    encoding=3, 
                    text=metadata['lyrics']
                )
            
            # 添加封面
            if metadata.get('cover_url'):
                try:
                    cover_data = requests.get(
                        metadata['cover_url'], timeout=5).content
                    audio.tags.add(APIC(
                        encoding=3,
                        mime='image/jpeg',
                        type=3,  # 封面图片
                        desc='Cover',
                        data=cover_data
                    ))
                except Exception as e:
                    logging.error(f"下载封面失败: {e}")
            
            audio.save()
            return True
            
        except Exception as e:
            logging.error(f"更新本地元数据失败: {e}")
            return False

    def get_local_metadata(self, file_path):
        """获取本地文件元数据(包括已更新的)"""
        return self._get_local_metadata(file_path)