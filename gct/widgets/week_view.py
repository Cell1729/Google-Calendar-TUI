from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal, Container
from datetime import datetime, timedelta, date

class WeekDay(Vertical):
    """週間表示内の1日分カラム"""
    def __init__(self, date_obj: date, events: list = None, **kwargs):
        super().__init__(**kwargs)
        self.date_obj = date_obj
        self.events = events or []

    def compose(self) -> ComposeResult:
        is_today = self.date_obj == date.today()
        day_name = self.date_obj.strftime("%a")
        day_str = f"{self.date_obj.day} ({day_name})"
        
        yield Label(day_str, classes="week-day-header" + (" today" if is_today else ""))
        yield Label("", id="week-cell-events")
        self.call_after_refresh(self.update_content)

    def update_content(self) -> None:
        """予定のリストを更新"""
        list_widget = self.query_one("#week-cell-events", Label)
        if self.events:
            event_titles = []
            # 週間表示は縦長なので少し多めに表示
            for ev in self.events[:8]:
                summary = ev.get('summary', '(No Title)')
                start = ev['start'].get('dateTime', ev['start'].get('date', ''))
                time_str = start.split('T')[1][:5] if 'T' in start else "--"
                
                # 文字数制限
                if len(summary) > 12:
                    summary = summary[:11] + "…"
                event_titles.append(f"{time_str} {summary}")
            
            list_widget.update("\n".join(event_titles))
        else:
            list_widget.update("")

class WeekWidget(Vertical):
    """週間表示ウィジェット (日曜開始)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_date = date.today()
        self.events_by_day = {} # { "YYYY-MM-DD": [events] }

    def compose(self) -> ComposeResult:
        yield Label("Weekly Schedule", classes="view-header", id="week-view-title")
        
        # 日曜開始の計算
        start_of_week = self.current_date - timedelta(days=(self.current_date.weekday() + 1) % 7)
        
        with Horizontal(id="week-grid"):
            for i in range(7):
                day_date = start_of_week + timedelta(days=i)
                date_str = day_date.isoformat()
                events = self.events_by_day.get(date_str, [])
                yield WeekDay(day_date, events=events, classes="week-col")

    def update_view(self, target_date: date, events_by_day: dict):
        """外部からデータを流し込んで更新"""
        self.current_date = target_date
        self.events_by_day = events_by_day
        
        # タイトル更新
        start_of_week = self.current_date - timedelta(days=(self.current_date.weekday() + 1) % 7)
        end_of_week = start_of_week + timedelta(days=6)
        title = self.query_one("#week-view-title", Label)
        title.update(f"Week of {start_of_week.strftime('%b %d')} - {end_of_week.strftime('%b %d, %Y')}")

        # 各カラムを更新 (recompose を回避s)
        columns = self.query(WeekDay)
        if len(columns) == 7:
            for i, col in enumerate(columns):
                day_date = start_of_week + timedelta(days=i)
                col.date_obj = day_date
                col.events = self.events_by_day.get(day_date.isoformat(), [])
                # re-update header
                header = col.query_one(".week-day-header", Label)
                header.update(f"{day_date.day} ({day_date.strftime('%a')})")
                col.update_content()
        else:
            # 万が一構成が違ったら再構築
            self.recompose()
