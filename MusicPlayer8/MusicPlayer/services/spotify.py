import os
import requests
import logging
from typing import Optional, Dict, List

class SpotifyAPI:
    """Spotify API封装类"""
    
    BASE_URL = "https://api.spotify.com/v1"
    
    def __init__(self):
        # 使用提供的认证信息
        self.client_id = "8508ad9faadd47c5b095563bf7e08bfc"
        self.client_secret = "42007995c9684c418ac6c92a06b93801"
        self.redirect_uri = "http://localhost:8888/callback"
        self.access_token = None
        self.refresh_token = None
        self._authenticate()
        
    def get_auth_url(self):
        """获取用户授权URL"""
        auth_url = "https://accounts.spotify.com/authorize"
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": "user-read-private user-read-email user-library-read playlist-read-private"
        }
        return f"{auth_url}?{'&'.join(f'{k}={v}' for k,v in params.items())}"
        
    def get_user_token(self, code: str):
        """使用授权码获取用户令牌"""
        token_url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            return True
        return False
        
    def refresh_access_token(self):
        """使用刷新令牌获取新的访问令牌"""
        if not self.refresh_token:
            return False
            
        token_url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            return True
        return False
        
    def _authenticate(self):
        """获取访问令牌"""
        auth_url = "https://accounts.spotify.com/api/token"
        auth_response = requests.post(
            auth_url,
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret)
        )
        
        if auth_response.status_code == 200:
            self.access_token = auth_response.json().get("access_token")
        else:
            logging.error(f"Spotify认证失败: {auth_response.text}")
            raise Exception("无法获取Spotify访问令牌")
    
    def search_tracks(self, query: str, limit: int = 10) -> Optional[List[Dict]]:
        """搜索音乐曲目"""
        if not self.access_token:
            return None
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        params = {
            "q": query,
            "type": "track",
            "limit": limit
        }
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/search",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                return self._parse_tracks(response.json().get("tracks", {}).get("items", []))
            else:
                logging.error(f"Spotify搜索失败: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Spotify API调用异常: {str(e)}")
            return None
    
    def _parse_tracks(self, tracks: List[Dict]) -> List[Dict]:
        """解析曲目数据为统一格式"""
        return [{
            "id": track.get("id"),
            "title": track.get("name"),
            "artist": ", ".join(a["name"] for a in track.get("artists", [])),
            "album": track.get("album", {}).get("name"),
            "duration": track.get("duration_ms", 0) // 1000,
            "cover_url": track.get("album", {}).get("images", [{}])[0].get("url"),
            "source": "spotify"
        } for track in tracks]

    def get_track(self, track_id: str) -> Optional[Dict]:
        """获取特定曲目详情"""
        if not self.access_token:
            return None
            
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/tracks/{track_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return self._parse_tracks([response.json()])[0]
            else:
                logging.error(f"获取Spotify曲目失败: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Spotify API调用异常: {str(e)}")
            return None

    def get_playback_url(self, track_id: str) -> Optional[str]:
        """获取播放URL(返回预览URL)"""
        track = self.get_track(track_id)
        if not track:
            return None
            
        # 返回30秒预览URL(Spotify API限制)
        preview_url = track.get("preview_url")
        if preview_url:
            return preview_url
            
        # 回退方案：返回外部播放URL
        return f"https://open.spotify.com/track/{track_id}"