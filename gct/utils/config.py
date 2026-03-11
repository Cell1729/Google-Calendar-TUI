import json
from pathlib import Path

class ConfigManager:
    """gct の設定ファイルを管理するクラス"""
    
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_path = config_dir / "config.json"
        self.secrets_path = config_dir / "secrets.json"
        self.defaults = {
            "general": {
                "default_view": "month",
                "theme": "dark"
            },
            "weather": {
                "enabled": True,
                "latitude": 35.6895,
                "longitude": 139.6917,
                "location_name": "Tokyo"
            },
            "keybindings": {
                "move_up": "k",
                "move_down": "j",
                "move_left": "h",
                "move_right": "l",
                "refresh": "r"
            }
        }

    def load_config(self):
        if not self.config_path.exists():
            return self.defaults
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return self.defaults

    def save_config(self, config_data):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

    def load_secrets(self):
        if not self.secrets_path.exists():
            return None
        try:
            with open(self.secrets_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def save_secrets(self, client_id, client_secret):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        secrets = {
            "client_id": client_id,
            "client_secret": client_secret
        }
        with open(self.secrets_path, "w", encoding="utf-8") as f:
            json.dump(secrets, f, indent=2)
