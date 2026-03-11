from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label, Button, ContentSwitcher
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from pathlib import Path
from datetime import datetime, timedelta
import asyncio

from .utils.auth import AuthManager
from .utils.config import ConfigManager
from .widgets.setup_screen import SetupScreen
from .widgets.calendar import CalendarWidget, CalendarDay
from .widgets.sidebar import Sidebar
from .widgets.weather import WeatherWidget
from .widgets.week_view import WeekWidget
from .widgets.day_view import DayWidget
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
            
            # 2. カレンダー一覧の取得とサイドバー更新
            # asyncio.to_thread を使用してブロッキングを回避
            calendars = await asyncio.to_thread(self.calendar_api.get_calendar_list)
            cal_list_label = self.query_one("#calendar-list", Label)
            cal_text = ""
            for cal in calendars[:5]: # 上位5件
                indicator = "● " if cal.get('selected') else "○ "
                cal_text += f"{indicator}{cal['summary']}\n"
            cal_list_label.update(cal_text)

            # 3. カレンダー予定取得 (今月の全予定)
            now = datetime.now()
            first_day = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day = (first_day + timedelta(days=32)).replace(day=1)
            
            events = await asyncio.to_thread(
                self.calendar_api.get_events,
                time_min=first_day.isoformat() + 'Z',
                time_max=last_day.isoformat() + 'Z'
            )
            
            # 4. サイドバーの「Upcoming」更新
            upcoming = self.query_one("#sidebar-upcoming", Label)
            if events:
                upcoming_text = ""
                for ev in events[:3]: # 直近3件
                    start = ev['start'].get('dateTime', ev['start'].get('date'))
                    dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    upcoming_text += f"[bold]{dt.strftime('%m/%d')}[/bold] {ev['summary']}\n"
                upcoming.update(upcoming_text)
            else:
                upcoming.update("No upcoming events")

            # 5. 日付ごとに分類
            events_by_day = {}
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if dt.month == now.month:
                    events_by_day.setdefault(dt.day, []).append(event)
            
            # 6. ウィジェット更新
            calendar_widget = self.query_one(CalendarWidget)
            await calendar_widget.update_events(events_by_day)
            
            # 月名の更新
            header_info = self.query_one("#header-info", Label)
            header_info.update(f"{now.strftime('%B %Y')}")
            
            # 7. 今日の日付にフォーカスを当てる
            days = calendar_widget.query(CalendarDay)
            for day_widget in days:
                if day_widget.is_today:
                    day_widget.focus()
                    break
            
        except Exception as e:
            self.notify(f"Refresh Error: {str(e)}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """ボタン押下時のイベントハンドラ"""
        btn_id = event.button.id
        if btn_id == "btn-month":
            self.action_switch_view("month")
        elif btn_id == "btn-week":
            self.action_switch_view("week")
        elif btn_id == "btn-day":
            self.action_switch_view("day")

    async def on_calendar_widget_day_selected(self, message: CalendarWidget.DaySelected) -> None:
        """カレンダーの日付が選択された時の処理"""
        # 1. 予定詳細の更新
        event_list = self.query_one("#event-list", Label)
        if message.events:
            text = ""
            for ev in message.events:
                start = ev['start'].get('dateTime', ev['start'].get('date'))
                # 時間部分だけ抽出 (ISOフォーマット想定)
                time_str = start.split('T')[1][:5] if 'T' in start else "All Day"
                text += f"󰄱 {time_str} - {ev['summary']}\n"
            event_list.update(text)
        else:
            event_list.update("No events for this day")

        # 2. 天気詳細の更新 (1h予報)
        if message.date_obj:
            try:
                lat = self.config["weather"]["latitude"]
                lon = self.config["weather"]["longitude"]
                # 該当日付の1時間ごとの天気を取得
                hourly_data = await self.weather_api.get_hourly_weather(
                    lat, lon, message.date_obj.isoformat()
                )
                self.query_one(WeatherWidget).update_hourly(hourly_data)
            except Exception as e:
                self.log(f"Weather detail error: {e}")

    def compose(self) -> ComposeResult:
        now = datetime.now()
        yield Header()
        with Horizontal(id="app-body"):
            yield Sidebar(id="sidebar")

            with Vertical(id="main-content"):
                yield Label(f"{now.strftime('%B %Y')}", id="header-info")
                
                # ビューの切り替え用
                with ContentSwitcher(initial="view-month", id="view-switcher"):
                    yield CalendarWidget(now.year, now.month, id="view-month")
                    yield WeekWidget(id="view-week")
                    yield DayWidget(id="view-day")

                yield WeatherWidget(id="weather-panel")
                
                # 詳細パネル
                with Vertical(id="event-detail"):
                    yield Label("Event Details", classes="panel-title")
                    yield Label("Select a day to see events", id="event-list")

        yield Footer()

    def action_switch_view(self, view: str) -> None:
        """ビューの切り替え表示"""
        switcher = self.query_one("#view-switcher", ContentSwitcher)
        switcher.current = f"view-{view}"

        # ボタンのスタイル更新
        for btn in self.query("#sidebar Button"):
            btn.remove_class("-active")
        
        try:
            target_btn = self.query_one(f"#btn-{view}", Button)
            target_btn.add_class("-active")
        except Exception:
            pass
        
        self.notify(f"Switched to {view} view")

if __name__ == "__main__":
    app = GCTApp()
    app.run()
