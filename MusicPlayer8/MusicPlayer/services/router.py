import logging
from typing import Dict, List, Optional, Any
from difflib import SequenceMatcher
from .cloud_music import CloudMusicService
from .spotify import SpotifyAPI

class MusicRouter:
    """音乐服务智能路由器"""
    
    def __init__(self):
        self.netease = CloudMusicService()
        self.spotify = SpotifyAPI()
        
    def search(self, keyword: str, limit: int = 10) -> Dict[str, Any]:
        """统一搜索接口"""
        if self.netease.logged_in:
            results = self.netease.search(keyword, limit)
            return self._format_response(results, "netease")
        else:
            results = self.spotify.search_tracks(keyword, limit)
            return self._format_response(results, "spotify")
    
    def get_playback_url(self, track_id: str, source: str) -> Optional[str]:
        """获取播放URL(支持智能切换)"""
        if source == "netease":
            if self.netease.logged_in:
                return self.netease.get_song_url(track_id)
            else:
                # 智能切换到Spotify
                spotify_track = self._find_spotify_equivalent(track_id)
                return spotify_track["preview_url"] if spotify_track else None
        else:
            return self.spotify.get_playback_url(track_id)
    
    def _find_spotify_equivalent(self, netease_track_id: str) -> Optional[Dict]:
        """查找Spotify等效曲目"""
        netease_track = self.netease.get_track_metadata(netease_track_id)
        if not netease_track:
            return None
            
        query = f"{netease_track['name']} artist:{netease_track['artist']}"
        spotify_results = self.spotify.search_tracks(query, limit=3)
        
        best_match = None
        best_score = 0
        for track in spotify_results["tracks"]:
            score = self._calculate_similarity(netease_track, track)
            if score > 0.85 and score > best_score:
                best_match = track
                best_score = score
                
        return best_match
    
    @staticmethod
    def _calculate_similarity(
        netease_track: Dict, 
        spotify_track: Dict
    ) -> float:
        """计算曲目相似度(0-1范围)"""
        # 标题相似度
        title_sim = SequenceMatcher(
            None, 
            netease_track["name"].lower(), 
            spotify_track["name"].lower()
        ).ratio()
        
        # 艺术家相似度
        artist_sim = SequenceMatcher(
            None,
            netease_track["artist"].lower(),
            spotify_track["artists"][0]["name"].lower()
        ).ratio()
        
        # 时长相似度(允许±10秒差异)
        duration_diff = abs(
            netease_track["duration"] - spotify_track["duration_ms"] / 1000
        )
        duration_sim = 1 - min(duration_diff / 10, 1)
        
        # 加权综合评分
        return (
            0.4 * title_sim + 
            0.3 * artist_sim + 
            0.2 * duration_sim +
            0.1 * (1 if netease_track["album"] == spotify_track["album"]["name"] else 0)
        )
    
    @staticmethod
    def _format_response(
        results: List[Dict], 
        source: str
    ) -> Dict[str, Any]:
        """统一响应格式"""
        return {
            "result": {
                "tracks": results,
                "metadata": {
                    "service_used": source,
                    "service_switched": False,
                    "netease_logged_in": source == "netease"
                }
            }
        }