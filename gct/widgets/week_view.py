from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal, Container
from datetime import datetime, timedelta, date
from .event_item import EventItem

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
        yield Vertical(id="week-cell-events")
        # 非同期になったため、初期化時は親から update_view 経由で呼ばれるのを待つか、
        # あるいは GCTApp 側での描画時に処理される

    async def update_content(self) -> None:
        """予定のリストを更新"""
        list_widget = self.query_one("#week-cell-events", Vertical)
        
        # 既存のイベント要素をクリア
        for child in list(list_widget.children):
            await child.remove()
            
        if self.events:
            # 週間表示は縦長なので少し多めに表示
            for ev in self.events[:8]:
                summary = ev.get('summary', '(No Title)')
                start = ev['start'].get('dateTime', ev['start'].get('date', ''))
                time_str = start.split('T')[1][:5] if 'T' in start else "--"
                
                # 文字数制限
                if len(summary) > 12:
                    summary = summary[:11] + "…"
                    
                item = EventItem(f"{time_str} {summary}", event_data=ev)
                await list_widget.mount(item)

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

    async def update_view(self, target_date: date, events_by_day: dict):
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
                await col.update_content()
        else:
            # 万が一構成が違ったら再構築
            self.recompose()

        # 描画完了後に指定日付の予定へフォーカスを試みる
        self.call_after_refresh(self._focus_target_date, target_date)

    def _focus_target_date(self, target_date: date) -> None:
        """指定された日付のカラムを探し、予定があれば最初にフォーカスする"""
        try:
            from textual.widgets import ContentSwitcher
            switcher = self.app.query_one("#view-switcher", ContentSwitcher)
            if switcher.current != "view-week":
                return

            for col in self.query(WeekDay):
                if col.date_obj == target_date:
                    events = list(col.query(EventItem))
                    if events:
                        events[0].focus()
                    break
        except Exception:
            pass
