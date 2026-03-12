from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label, Button, ContentSwitcher
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding
from textual.command import Provider, Hit, Hits
from pathlib import Path
from datetime import datetime, timedelta, date
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
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
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
        self.weather_cache = {} # 日付(isoformat) -> hourly_data
        self.selected_date = date.today()
        self.all_events = [] # 取得済みの全予定

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
            def log_auth(msg):
                self.notify(msg)

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
            calendars = await asyncio.to_thread(self.calendar_api.get_calendar_list)
            cal_list_label = self.query_one("#calendar-list", Label)
            cal_text = ""
            for cal in calendars[:5]:
                indicator = "● " if cal.get('selected') else "○ "
                cal_text += f"{indicator}{cal['summary']}\n"
            cal_list_label.update(cal_text)

            # 3. カレンダー予定取得 (前後1ヶ月分取得)
            now = datetime.now()
            start_fetch = (now - timedelta(days=32)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_fetch = (now + timedelta(days=60)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            self.all_events = await asyncio.to_thread(
                self.calendar_api.get_events,
                time_min=start_fetch.isoformat() + 'Z',
                time_max=end_fetch.isoformat() + 'Z'
            )
            
            # 4. サイドバーの「Upcoming」更新
            upcoming = self.query_one("#sidebar-upcoming", Label)
            if self.all_events:
                now_utc = datetime.now() # 簡易的に現在時刻と比較
                upcoming_list = []
                for ev in self.all_events:
                    start_str = ev['start'].get('dateTime', ev['start'].get('date'))
                    # タイムゾーンを考慮した比較のための変換 (簡易版)
                    dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    # dt が現在(tzなし)に近くなるよう tzinfo を消去して比較
                    if dt.replace(tzinfo=None) >= now_utc:
                        time_part = dt.strftime('%H:%M') if 'T' in start_str else "AllDay"
                        upcoming_list.append(f"[bold]{dt.strftime('%m/%d')} {time_part}[/bold] {ev['summary']}")
                    if len(upcoming_list) >= 3:
                        break
                
                upcoming.update("\n".join(upcoming_list) if upcoming_list else "No future events")
            else:
                upcoming.update("No upcoming events")

            # 5. 月間表示用に分類 (今月分)
            events_by_day = {}
            for event in self.all_events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if dt.year == now.year and dt.month == now.month:
                    events_by_day.setdefault(dt.day, []).append(event)
            
            # 6. ウィジェット更新
            calendar_widget = self.query_one(CalendarWidget)
            await calendar_widget.update_events(events_by_day)
            
            # 週・日ビューも同期更新
            self.sync_sub_views(self.selected_date)
            
            header_info = self.query_one("#header-info", Label)
            header_info.update(f"{now.strftime('%B %Y')}")
            
            # 7. 今日または選択日にフォーカス
            days = calendar_widget.query(CalendarDay)
            for day_widget in days:
                if day_widget.date_obj == self.selected_date:
                    day_widget.focus()
                    break
            
        except Exception as e:
            self.notify(f"Refresh Error: {str(e)}", severity="error")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-month":
            self.action_switch_view("month")
        elif btn_id == "btn-week":
            self.action_switch_view("week")
        elif btn_id == "btn-day":
            self.action_switch_view("day")

    async def on_calendar_widget_day_selected(self, message: CalendarWidget.DaySelected) -> None:
        self.run_worker(self.handle_day_selection(message), exclusive=True, group="selection_update")

    async def handle_day_selection(self, message: CalendarWidget.DaySelected) -> None:
        await asyncio.sleep(0.05)
        if not message.date_obj: return
        
        self.selected_date = message.date_obj
        self.sync_sub_views(self.selected_date)

        date_key = self.selected_date.isoformat()
        if date_key in self.weather_cache:
            self.query_one(WeatherWidget).update_hourly(self.weather_cache[date_key])
            return

        try:
            lat = self.config["weather"]["latitude"]
            lon = self.config["weather"]["longitude"]
            hourly_data = await self.weather_api.get_hourly_weather(lat, lon, date_key)
            self.weather_cache[date_key] = hourly_data
            self.query_one(WeatherWidget).update_hourly(hourly_data)
        except Exception as e:
            self.log(f"Weather error: {e}")

    def sync_sub_views(self, target_date: date) -> None:
        """週・日ビューの表示内容を同期"""
        events_by_day = {}
        day_events = []
        for ev in self.all_events:
            start = ev['start'].get('dateTime', ev['start'].get('date'))
            dt = datetime.fromisoformat(start.replace('Z', '+00:00')).date()
            events_by_day.setdefault(dt.isoformat(), []).append(ev)
            if dt == target_date:
                day_events.append(ev)
        
        try:
            self.query_one(WeekWidget).update_view(target_date, events_by_day)
            self.query_one(DayWidget).update_view(target_date, day_events)
        except Exception:
            pass # まだ構築されていない場合はスキップ

    def compose(self) -> ComposeResult:
        now = datetime.now()
        yield Header()
        with Horizontal(id="app-body"):
            yield Sidebar(id="sidebar")
            with Vertical(id="main-content"):
                yield Label(f"{now.strftime('%B %Y')}", id="header-info")
                with ContentSwitcher(initial="view-month", id="view-switcher"):
                    yield CalendarWidget(now.year, now.month, id="view-month")
                    yield WeekWidget(id="view-week")
                    yield DayWidget(id="view-day")
        yield Footer()

    def action_switch_view(self, view: str) -> None:
        switcher = self.query_one("#view-switcher", ContentSwitcher)
        switcher.current = f"view-{view}"
        
        for btn in self.query("#sidebar Button"):
            btn.remove_class("-active")
        try:
            target_btn = self.query_one(f"#btn-{view}", Button)
            target_btn.add_class("-active")
        except Exception: pass
        self.notify(f"Switched to {view} view")

class GCTCommandProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        commands = [
            ("Exit / Quit App", self.app.action_quit, "Exit the application"),
            ("Switch to Month View", lambda: self.app.action_switch_view("month"), "Show monthly calendar"),
            ("Switch to Week View", lambda: self.app.action_switch_view("week"), "Show weekly calendar"),
            ("Switch to Day View", lambda: self.app.action_switch_view("day"), "Show daily schedule"),
            ("Refresh Data", self.app.refresh_data, "Fetch latest events and weather"),
        ]
        for name, action, help_text in commands:
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), action, help=help_text)

GCTApp.COMMANDS = GCTApp.COMMANDS | {GCTCommandProvider}

if __name__ == "__main__":
    app = GCTApp()
    app.run()
