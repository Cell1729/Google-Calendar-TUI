import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# スコープの定義（読み書き権限）
SCOPES = ['https://www.googleapis.com/auth/calendar']

class AuthManager:
    """Google Calendar API の認証とトークン管理"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.token_path = config_dir / "token.json"
        self.secrets_path = config_dir / "secrets.json"

    def get_credentials(self, log_callback=None):
        creds = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.secrets_path.exists():
                    raise FileNotFoundError("secrets.json not found. Run setup first.")
                
                with open(self.secrets_path, "r") as f:
                    secrets = json.load(f)
                
                client_config = {
                    "installed": {
                        "client_id": secrets["client_id"],
                        "client_secret": secrets["client_secret"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"]
                    }
                }
                
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                
                # ブラウザが自動で開かない場合のために、URLをコールバック経由で通知
                if log_callback:
                    log_callback("Opening browser for OAuth2...")
                
                # Windowsでブラウザ起動が不安定な場合があるため、ポートを指定して実行
                creds = flow.run_local_server(
                    port=0, 
                    prompt='consent',
                    authorization_prompt_message='Please visit this URL: {url}'
                )
            
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
        
        return creds
