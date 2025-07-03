import logging
import requests
import base64
import os
import secrets
from time import time
from urllib.parse import urlencode

class SpotifyAuth:
    """处理Spotify OAuth2授权流程"""
    
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv("SPOTIFY_REDIRECT_URI")
        self.token_url = "https://accounts.spotify.com/api/token"
        self.auth_url = "https://accounts.spotify.com/authorize"
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
        self.state = None
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("缺少必要的OAuth配置参数")
    
    def get_auth_url(self, scopes=None):
        """生成授权URL"""
        self.state = secrets.token_urlsafe(16)
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "state": self.state,
            "scope": " ".join(scopes) if scopes else "user-library-read user-modify-playback-state",
            "show_dialog": "true"
        }
        
        return f"{self.auth_url}?{urlencode(params)}"
    
    def exchange_code(self, code, state):
        """用授权码交换令牌"""
        if state != self.state:
            raise ValueError("无效的state参数")
            
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(self.token_url, data=data, headers=headers)
        response.raise_for_status()
        
        token_data = response.json()
        self._update_tokens(token_data)
        return token_data
    
    def refresh_access_token(self):
        """刷新访问令牌"""
        if not self.refresh_token:
            raise ValueError("缺少refresh_token")
            
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(self.token_url, data=data, headers=headers)
        response.raise_for_status()
        
        token_data = response.json()
        self._update_tokens(token_data)
        return token_data
    
    def _update_tokens(self, token_data):
        """更新令牌信息"""
        self.access_token = token_data["access_token"]
        self.token_expires = time() + token_data["expires_in"]
        if "refresh_token" in token_data:
            self.refresh_token = token_data["refresh_token"]

class SpotifyAPI:
    """Spotify API客户端(支持两种认证模式)"""
    
    def __init__(self, use_oauth=False):
        self.base_url = "https://api.spotify.com/v1"
        self.use_oauth = use_oauth
        
        if use_oauth:
            self.auth = SpotifyAuth()
            if not self.auth.access_token:
                raise ValueError("请先完成OAuth授权流程")
        else:
            self.token_url = "https://accounts.spotify.com/api/token"
            self.access_token = None
            self.token_expires = 0
            # 从环境变量获取Spotify API凭证
            self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
            self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
            
            if not self.client_id or not self.client_secret:
                raise ValueError(
                    "请设置Spotify API凭证:\n"
                    "1. 访问 https://developer.spotify.com/dashboard\n"
                    "2. 创建或选择你的应用\n"
                    "3. 设置以下环境变量:\n"
                    "   - SPOTIFY_CLIENT_ID=你的客户端ID\n"
                    "   - SPOTIFY_CLIENT_SECRET=你的客户端密钥\n"
                    "4. 或者直接在代码中传入client_id和client_secret参数"
                )
                
            self._refresh_token()
        
    def _get_auth_header(self):
        """生成Base64认证头(仅客户端凭证流使用)"""
        if self.use_oauth:
            return None
        auth_str = f"{self.client_id}:{self.client_secret}"
        return base64.b64encode(auth_str.encode()).decode()
        
    def _refresh_token(self):
        """刷新访问令牌"""
        try:
            if self.use_oauth:
                # OAuth模式刷新
                token_data = self.auth.refresh_access_token()
                self.access_token = token_data["access_token"]
                self.token_expires = time() + token_data["expires_in"]
            else:
                # 客户端凭证流刷新
                headers = {
                    "Authorization": f"Basic {self._get_auth_header()}"
                }
                data = {
                    "grant_type": "client_credentials"
                }
                
                response = requests.post(
                    self.token_url,
                    headers=headers,
                    data=data
                )
                response.raise_for_status()
                
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.token_expires = time() + token_data["expires_in"]
            
            logging.info("Spotify访问令牌获取成功")
            
        except Exception as e:
            logging.error(f"刷新Spotify令牌失败: {str(e)}")
            raise
            
    def _check_token(self):
        """检查并刷新令牌"""
        if self.use_oauth:
            # OAuth模式检查
            if time() > self.auth.token_expires - 60:  # 提前60秒刷新
                self._refresh_token()
            self.access_token = self.auth.access_token
        else:
            # 客户端凭证流检查
            if time() > self.token_expires - 60:  # 提前60秒刷新
                self._refresh_token()
            
    def _make_request(self, method, endpoint, params=None, data=None, retry=True):
        """统一请求方法(支持两种认证模式)"""
        self._check_token()
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=params,
                json=data
            )
            
            # 处理令牌过期(两种模式)
            if response.status_code == 401 and retry:
                self._refresh_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=data
                )
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"Spotify API请求失败: {str(e)}"
            if response.status_code == 403 and self.use_oauth:
                error_msg += "\n可能需要重新授权: 权限不足或用户已撤销授权"
            logging.error(error_msg)
            raise
        except Exception as e:
            logging.error(f"Spotify请求异常: {str(e)}")
            raise
            
    def search_tracks(self, query, limit=5):
        """搜索歌曲(支持两种认证模式)
        
        参数:
            query: 搜索关键词
            limit: 返回结果数量(默认5)
            
        返回:
            歌曲列表或空列表(出错时)
        """
        try:
            data = self._make_request(
                "GET",
                "/search",
                params={
                    "q": query,
                    "type": "track",
                    "limit": limit
                }
            )
            
            tracks = []
            for item in data["tracks"]["items"]:
                track = {
                    "title": item["name"],
                    "artist": ", ".join(
                        artist["name"] for artist in item["artists"]
                    ),
                    "album": item["album"]["name"],
                    "duration": item["duration_ms"] // 1000,
                    "cover_url": item["album"]["images"][0]["url"] if item["album"]["images"] else None,
                    "id": item["id"],
                    "uri": item["uri"]
                }
                tracks.append(track)
                
            return tracks
        except Exception as e:
            logging.error(f"搜索歌曲失败: {str(e)}")
            return []
            
    def get_track(self, track_id):
        """获取歌曲详情(支持两种认证模式)
        
        参数:
            track_id: Spotify曲目ID
            
        返回:
            曲目详情字典或None(出错时)
        """
        try:
            data = self._make_request(
                "GET",
                f"/tracks/{track_id}"
            )
            
            return {
                "title": data["name"],
                "artist": ", ".join(
                    artist["name"] for artist in data["artists"]
                ),
                "album": data["album"]["name"],
                "duration": data["duration_ms"] // 1000,
                "cover_url": data["album"]["images"][0]["url"] if data["album"]["images"] else None,
                "id": data["id"],
                "uri": data["uri"],
                "preview_url": data.get("preview_url"),
                "external_url": data.get("external_urls", {}).get("spotify")
            }
        except Exception as e:
            logging.error(f"获取曲目详情失败: {str(e)}")
            return None