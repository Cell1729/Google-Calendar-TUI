from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Container, Horizontal
from datetime import datetime, date
import calendar

class CalendarDay(Static):
    """1日分のセル"""
    def __init__(self, day: int, is_today: bool = False, events: list = None):
        super().__init__()
        self.day = day
        self.is_today = is_today
        self.events = events or []

    def compose(self) -> ComposeResult:
        yield Label(str(self.day) if self.day > 0 else "")
        if self.events:
            yield Static("•" * min(len(self.events), 3), classes="event-dots")

class CalendarWidget(Static):
    """カレンダー本体のウィジェット"""

    def __init__(self, year: int, month: int):
        super().__init__()
        self.year = year
        self.month = month
        self.events_cache = {}

    def compose(self) -> ComposeResult:
        # 七曜ヘッダー
        with Horizontal(id="day-names"):
            for day_name in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
                yield Label(day_name, expand=True, classes="day-name")

        # カレンダーグリッド
        with Container(classes="calendar-grid"):
            cal = calendar.monthcalendar(self.year, self.month)
            today = date.today()
            
            for week in cal:
                for day in week:
                    is_today = (self.year == today.year and self.month == today.month and day == today.day)
                    # 予定は外部から注入される想定
                    events = self.events_cache.get(day, [])
                    yield CalendarDay(day, is_today=is_today, events=events)

    async def update_events(self, events_by_day):
        """予定データを更新して再描画"""
        self.events_cache = events_by_day
        await self.recompose()
