from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label, Button
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from .utils.auth import AuthManager
from .utils.config import ConfigManager
from .widgets.setup_screen import SetupScreen
from .widgets.calendar import CalendarWidget
from .widgets.sidebar import Sidebar
from .widgets.weather import WeatherWidget
from .api.calendar import CalendarAPI
from .api.weather import WeatherAPI

# 設定ディレクトリ
CONFIG_DIR = Path.home() / ".config" / "gct"

class GCTApp(App):
    """Google Calendar TUI Main Application"""
    
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("ctrl+q", "quit", "Quit", show=False),
        Binding("m", "switch_view('month')", "Month", show=True),
        Binding("w", "switch_view('week')", "Week", show=True),
        Binding("d", "switch_view('day')", "Day", show=True),
        Binding("r", "refresh", "Refresh", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager(CONFIG_DIR)
        self.auth_manager = AuthManager(CONFIG_DIR)
        self.calendar_api = None
        self.weather_api = WeatherAPI()
        self.creds = None
        self.config = self.config_manager.load_config()

    async def on_mount(self) -> None:
        """起動時の処理"""
        secrets = self.config_manager.load_secrets()
        if not secrets:
            self.push_screen(SetupScreen(), self.handle_setup_completed)
        else:
            await self.authenticate()

    async def handle_setup_completed(self, result: dict) -> None:
        """セットアップ画面からの情報を保存して認証へ"""
        if result:
            self.config_manager.save_secrets(result["client_id"], result["client_secret"])
            config = self.config_manager.load_config()
            config["weather"]["location_name"] = result["location"]
            self.config_manager.save_config(config)
            await self.authenticate()

    async def authenticate(self) -> None:
        """Google API 認証の実行 (非ブロッキング)"""
        try:
            # 認証プロセスからのログを通知として表示するコールバック
            def log_auth(msg):
                self.notify(msg)

            # 認証処理はブラウザの起動を伴うため、別スレッドで実行
            # self.run_in_thread の代わりに asyncio.to_thread を使用
            self.creds = await asyncio.to_thread(
                self.auth_manager.get_credentials, 
                log_callback=log_auth
            )
            self.calendar_api = CalendarAPI(self.creds)
            self.notify("Authentication successful!", severity="information")
            await self.refresh_data()
        except Exception as e:
            self.notify(f"Auth Error: {str(e)}", severity="error")

    async def refresh_data(self) -> None:
        """データの取得と画面反映"""
        if not self.creds or not self.calendar_api: return

        try:
            # 1. 天気取得
            lat = self.config["weather"]["latitude"]
            lon = self.config["weather"]["longitude"]
            weather_data = await self.weather_api.get_weather(lat, lon)
            self.query_one(WeatherWidget).update_weather(weather_data["current_weather"])
            
            # 2. カレンダー予定取得 (今月の全予定)
            now = datetime.now()
            first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day = (first_day + timedelta(days=32)).replace(day=1)
            
            events = self.calendar_api.get_events(
                time_min=first_day.isoformat() + 'Z',
                time_max=last_day.isoformat() + 'Z'
            )
            
            # 3. 日付ごとに分類
            events_by_day = {}
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if dt.month == now.month:
                    events_by_day.setdefault(dt.day, []).append(event)
            
            # 4. ウィジェット更新
            self.query_one(CalendarWidget).update_events(events_by_day)
            
        except Exception as e:
            self.notify(f"Refresh Error: {str(e)}", severity="error")

    def compose(self) -> ComposeResult:
        now = datetime.now()
        yield Header()
        with Horizontal():
            yield Sidebar()

            with Vertical(id="main-content"):
                yield Label(f"{now.strftime('%B %Y')}", id="header-info")
                
                # 分割したウィジェットを配置
                yield CalendarWidget(now.year, now.month)
                yield WeatherWidget()
                
                # 詳細パネル
                with Vertical(id="event-detail"):
                    yield Label("Event Details", classes="panel-title")
                    yield Label("Select a day to see events", id="event-list")

        yield Footer()

    def action_switch_view(self, view: str) -> None:
        self.notify(f"Switching to {view} view")

if __name__ == "__main__":
    app = GCTApp()
    app.run()
