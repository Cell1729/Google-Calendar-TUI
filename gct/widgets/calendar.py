from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual import events
from datetime import datetime, date
import calendar

class CalendarDay(Static):
    """1日分のセル"""
    can_focus = True

    def __init__(self, day: int, is_today: bool = False, events: list = None, date_obj: date = None, **kwargs):
        super().__init__(**kwargs)
        self.day = day
        self.is_today = is_today
        self.events = events or []
        self.date_obj = date_obj

    def compose(self) -> ComposeResult:
        if self.is_today:
            self.add_class("today")
        # プレースホルダを作成
        yield Label(str(self.day) if self.day > 0 else "", id="day-num")
        yield Label("", id="cell-event-list")
        self.call_after_refresh(self.update_content)

    def update_content(self) -> None:
        """中身を更新 (予定のタイトルを表示)"""
        list_widget = self.query_one("#cell-event-list", Label)
        if self.events:
            event_titles = []
            for ev in self.events[:3]: # 最大3件
                summary = ev.get('summary', '(No Title)')
                # 文字数制限 (セルからはみ出さないよう)
                if len(summary) > 10:
                    summary = summary[:9] + "…"
                event_titles.append(f"•{summary}")
            
            list_widget.update("\n".join(event_titles))
        else:
            list_widget.update("")

    def on_focus(self) -> None:
        """フォーカスされたときに親に通知"""
        if self.day > 0:
            self.post_message(CalendarWidget.DaySelected(self.day, self.events, self.date_obj))

class CalendarWidget(Vertical):
    """カレンダー本体のウィジェット"""

    class DaySelected(Message):
        """日付が選択（フォーカス）された時のメッセージ"""
        def __init__(self, day: int, events: list, date_obj: date):
            super().__init__()
            self.day = day
            self.events = events
            self.date_obj = date_obj

    def __init__(self, year: int, month: int, **kwargs):
        super().__init__(**kwargs)
        self.year = year
        self.month = month
        self.events_cache = {}

    def on_key(self, event: events.Key) -> None:
        """キーボードによるカレンダー移動 (矢印 / hjkl)"""
        focused_widget = self.app.focused
        if not isinstance(focused_widget, CalendarDay):
            return

        days = list(self.query(CalendarDay))
        try:
            curr_idx = days.index(focused_widget)
        except ValueError:
            return

        new_idx = curr_idx
        if event.key in ("up", "k"):
            new_idx = curr_idx - 7
        elif event.key in ("down", "j"):
            new_idx = curr_idx + 7
        elif event.key in ("left", "h"):
            new_idx = curr_idx - 1
        elif event.key in ("right", "l"):
            new_idx = curr_idx + 1
        
        if new_idx != curr_idx and 0 <= new_idx < len(days):
            days[new_idx].focus()
            event.prevent_default()
            event.stop()

    def compose(self) -> ComposeResult:
        # 七曜ヘッダー
        with Horizontal(id="day-names"):
            for day_name in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
                yield Label(day_name, classes="day-name")

        # カレンダーグリッド
        with Container(classes="calendar-grid"):
            cal = calendar.monthcalendar(self.year, self.month)
            today = date.today()
            
            for week in cal:
                for day in week:
                    is_today = (self.year == today.year and self.month == today.month and day == today.day)
                    events = self.events_cache.get(day, [])
                    date_obj = date(self.year, self.month, day) if day > 0 else None
                    yield CalendarDay(day, is_today=is_today, events=events, date_obj=date_obj)

    async def update_events(self, events_by_day):
        """現在のウィジェットを更新 (再構築しない)"""
        self.events_cache = events_by_day
        days = self.query(CalendarDay)
        for day_widget in days:
            if day_widget.day > 0:
                day_widget.events = self.events_cache.get(day_widget.day, [])
                day_widget.update_content()
