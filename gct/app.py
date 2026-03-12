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
from .widgets.event_form import EventFormScreen
from .widgets.confirm_delete import ConfirmDeleteScreen
from .widgets.event_item import EventItem
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
        Binding("b", "navigate(-1)", "Prev", show=True),
        Binding("n", "navigate(1)", "Next", show=True),
        Binding("a", "add_event", "Add Event", show=True),
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
        self.view_date = date.today() # 表示基準日
        self.all_events = [] # 取得済みの全予定
        self.fetched_range = None # APIによる取得済みのデータ範囲 (start_date, end_date)

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

    async def refresh_data(self, target_date: date = None, fetch_api: bool = True) -> None:
        """データの取得と画面反映"""
        if not self.creds or not self.calendar_api: return
        
        if target_date:
            self.view_date = target_date
        else:
            target_date = self.view_date

        # キャッシュの範囲チェック
        need_fetch = fetch_api
        if not need_fetch and self.fetched_range:
            min_d, max_d = self.fetched_range
            # 表示期間が取得済み範囲の端に近づいた場合は裏で再フェッチ
            if target_date < min_d + timedelta(days=15) or target_date > max_d - timedelta(days=15):
                need_fetch = True
        elif not self.fetched_range:
            need_fetch = True

        try:
            if need_fetch:
                lat = self.config["weather"]["latitude"]
                lon = self.config["weather"]["longitude"]
                
                # 取得範囲を長めに設定 (前後3ヶ月〜半年) してキャッシュヒット率を上げる
                start_fetch = datetime.combine(target_date, datetime.min.time()) - timedelta(days=90)
                end_fetch = datetime.combine(target_date, datetime.min.time()) + timedelta(days=180)

                # 1〜3 を並行フェッチして超高速化しつつ、Google API のスレッド競合(SSLエラー)を回避
                weather_task = self.weather_api.get_weather(lat, lon)
                
                def fetch_calendar_data():
                    """Google APIはスレッドセーフではないため、1つのスレッドで直列に処理する"""
                    cals = self.calendar_api.get_calendar_list()
                    evs = self.calendar_api.get_events(
                        time_min=start_fetch.isoformat() + 'Z',
                        time_max=end_fetch.isoformat() + 'Z'
                    )
                    return cals, evs
                    
                cal_data_task = asyncio.to_thread(fetch_calendar_data)
                
                weather_data, (calendars, self.all_events) = await asyncio.gather(
                    weather_task, cal_data_task
                )
                
                # 取得した範囲を記録
                self.fetched_range = (start_fetch.date(), end_fetch.date())
                
                # 取得結果のUI反映
                self.query_one(WeatherWidget).update_weather(weather_data["current_weather"])
                
                cal_list_label = self.query_one("#calendar-list", Label)
                cal_text = ""
                for cal in calendars[:5]:
                    indicator = "● " if cal.get('selected') else "○ "
                    cal_text += f"{indicator}{cal['summary']}\n"
                cal_list_label.update(cal_text)

            # 4. サイドバーの「Upcoming」更新 (ここは常に「今日」基準)
            upcoming = self.query_one("#sidebar-upcoming", Label)
            if self.all_events:
                now_sys = datetime.now()
                upcoming_list = []
                # 未来の予定を抽出
                future_events = [ev for ev in self.all_events if datetime.fromisoformat(ev['start'].get('dateTime', ev['start'].get('date')).replace('Z', '+00:00')).replace(tzinfo=None) >= now_sys]
                for ev in future_events[:3]:
                    start_str = ev['start'].get('dateTime', ev['start'].get('date'))
                    dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    time_part = dt.strftime('%H:%M') if 'T' in start_str else "AllDay"
                    upcoming_list.append(f"[bold]{dt.strftime('%m/%d')} {time_part}[/bold] {ev['summary']}")
                
                upcoming.update("\n".join(upcoming_list) if upcoming_list else "No future events")
            else:
                upcoming.update("No upcoming events")

            # 5. 月間表示用に分類 (基準日の月分)
            events_by_day = {}
            for event in self.all_events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                if dt.year == target_date.year and dt.month == target_date.month:
                    events_by_day.setdefault(dt.day, []).append(event)
            
            # 6. ウィジェット更新
            # Month Widget の再構築 (年月が変わる可能性があるため)
            view_switcher = self.query_one("#view-switcher", ContentSwitcher)
            # 現在が月表示なら、CalendarWidget を作り直すか中身を入れ替える
            # 今回は CalendarWidget に update_calendar メソッドを追加して再描画を避けるのがスマート
            calendar_widget = self.query_one(CalendarWidget)
            if calendar_widget.year != target_date.year or calendar_widget.month != target_date.month:
                # 年月が変わる場合は recompose 的な処理が必要だが、CalendarWidget 側で対応させる
                await calendar_widget.update_calendar(target_date.year, target_date.month, events_by_day)
            else:
                await calendar_widget.update_events(events_by_day)
            
            # 週・日ビューも同期更新
            await self.sync_sub_views(target_date)
            
            header_info = self.query_one("#header-info", Label)
            header_info.update(f"{target_date.strftime('%B %Y')}")
            
            # 選択日にフォーカス
            days = calendar_widget.query(CalendarDay)
            for day_widget in days:
                if day_widget.date_obj == target_date:
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

    async def on_event_item_edit_requested(self, message: EventItem.EditRequested) -> None:
        """EventItemから編集リクエストが来たときの処理"""
        # EventItemから送信されたイベントデータを使ってEdit画面を開く
        await self.edit_event(message.event_data)

    async def on_calendar_widget_day_selected(self, message: CalendarWidget.DaySelected) -> None:
        self.run_worker(self.handle_day_selection(message), exclusive=True, group="selection_update")

    async def handle_day_selection(self, message: CalendarWidget.DaySelected) -> None:
        await asyncio.sleep(0.05)
        if not message.date_obj: return
        
        self.selected_date = message.date_obj
        await self.sync_sub_views(self.selected_date)

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

    async def sync_sub_views(self, target_date: date) -> None:
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
            await self.query_one(WeekWidget).update_view(target_date, events_by_day)
            await self.query_one(DayWidget).update_view(target_date, day_events)
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
        # 表示中の日付に基づいて再描画をかける (API通信はスキップ)
        self.run_worker(self.refresh_data(self.view_date, fetch_api=False))

    async def action_navigate(self, direction: str) -> None:
        """表示期間を前後させる (b/n キー)"""
        try:
            dir_val = int(direction)
        except ValueError:
            return

        switcher = self.query_one("#view-switcher", ContentSwitcher)
        current_view = switcher.current
        
        new_date = self.view_date
        if current_view == "view-month":
            # 1ヶ月前後 (安全な年月計算)
            y, m = new_date.year, new_date.month
            if dir_val > 0:
                y = y + (m // 12)
                m = (m % 12) + 1
            else:
                y = y - (1 if m == 1 else 0)
                m = 12 if m == 1 else m - 1
            new_date = date(y, m, 1)
        elif current_view == "view-week":
            # 1週間前後
            new_date += timedelta(weeks=dir_val)
        elif current_view == "view-day":
            # 1日前後
            new_date += timedelta(days=dir_val)
            
        self.selected_date = new_date
        # 画面の移動だけなので API通信はスキップ (データ不足時のみ自動取得)
        await self.refresh_data(new_date, fetch_api=False)
        
        # 動作確認用の通知
        view_name = current_view.split("-")[1].capitalize()
        self.notify(f"Navigated {view_name}: {new_date.strftime('%Y-%m-%d')}")

    async def action_add_event(self) -> None:
        """新規予定追加画面を開く"""
        self.push_screen(
            EventFormScreen(target_date=self.selected_date),
            self._handle_event_form_result
        )

    async def edit_event(self, event_data: dict) -> None:
        """既存の予定の編集画面を開く"""
        self.push_screen(
            EventFormScreen(target_date=self.selected_date, event_data=event_data),
            self._handle_event_form_result
        )

    async def _handle_event_form_result(self, result: dict) -> None:
        """フォームでの入力結果を受け取り、APIと通信する"""
        if not result:
            return # キャンセル時
        
        self.notify("Syncing with Google Calendar...")
        
        try:
            # 実際のAPIコールは同期的なため、スレッドに投げる
            if result["action"] == "create":
                await asyncio.to_thread(
                    self.calendar_api.create_event,
                    calendar_id="primary",
                    summary=result["summary"],
                    start_time=result["start"],
                    end_time=result["end"],
                    is_all_day=result["is_all_day"]
                )
                self.notify(f"Created event: {result['summary']}", severity="information")
                
            elif result["action"] == "update":
                update_params = {
                    "summary": result["summary"]
                }
                
                # 日時情報の組み上げ
                if result["is_all_day"]:
                    update_params["start"] = {"date": result["start"].strftime("%Y-%m-%d")}
                    update_params["end"] = {"date": result["end"].strftime("%Y-%m-%d")}
                else:
                    update_params["start"] = {"dateTime": result["start"].isoformat(), "timeZone": "UTC"}
                    update_params["end"] = {"dateTime": result["end"].isoformat(), "timeZone": "UTC"}
                
                await asyncio.to_thread(
                    self.calendar_api.update_event,
                    calendar_id="primary",
                    event_id=result["event_id"],
                    **update_params
                )
                self.notify(f"Updated event: {result['summary']}", severity="information")
                
            elif result["action"] == "delete":
                # 削除確認ダイアログ
                def check_delete(confirmed: bool):
                    if confirmed:
                        self.run_worker(self._delete_event_task(result["event_id"]))
                        
                self.push_screen(ConfirmDeleteScreen(), check_delete)
                return
                
            # 完了後、表示期間のデータを最新化
            self.run_worker(self.refresh_data(self.view_date, fetch_api=True))
            
        except Exception as e:
            self.notify(f"API Error: {str(e)}", severity="error")

    async def _delete_event_task(self, event_id: str):
        """スレッドワーカーとして削除を実行"""
        try:
            await asyncio.to_thread(
                self.calendar_api.delete_event,
                calendar_id="primary",
                event_id=event_id
            )
            self.notify("Deleted event.", severity="information")
            self.run_worker(self.refresh_data(self.view_date, fetch_api=True))
        except Exception as e:
            self.notify(f"Delete Error: {str(e)}", severity="error")

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
