from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal, ScrollableContainer
from datetime import datetime, date
from .event_item import EventItem

class DayWidget(Vertical):
    """日間表示ウィジェット (時間軸付き詳細表示)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_date = date.today()
        self.events = []

    def compose(self) -> ComposeResult:
        yield Label(self.current_date.strftime("%A, %B %d, %Y"), id="day-view-title", classes="view-header")
        
        with ScrollableContainer(id="day-scroll"):
            with Horizontal(id="day-content"):
                # 左側：時間軸
                with Vertical(id="time-axis"):
                    for h in range(24):
                        yield Label(f"{h:02}:00", classes="time-label")
                
                # 右側：予定スロット (EventItem を追加するためのコンテナ)
                with Vertical(id="day-events"):
                    for h in range(24):
                        yield Vertical(id=f"hour-{h}", classes="hour-slot")

    async def update_view(self, target_date: date, events: list):
        """日付と予定リストで表示を更新"""
        self.current_date = target_date
        self.events = events
        
        # タイトル更新
        self.query_one("#day-view-title", Label).update(self.current_date.strftime("%A, %B %d, %Y"))
        
        # スロットの中身を全クリア
        for h in range(24):
            slot = self.query_one(f"#hour-{h}", Vertical)
            for child in list(slot.children):
                await child.remove()
        
        # 予定をEventItemとしてスロットにマウント
        for ev in self.events:
            start = ev['start'].get('dateTime', ev['start'].get('date', ''))
            summary = ev.get('summary', '(No Title)')
            
            if 'T' in start:
                # 時間指定あり
                hour = int(start.split('T')[1][:2])
                time_str = start.split('T')[1][:5]
                slot = self.query_one(f"#hour-{hour}", Vertical)
                item = EventItem(f"󰄱 {time_str} {summary}", event_data=ev)
                await slot.mount(item)
            else:
                # 終日予定などは 0時に
                slot = self.query_one("#hour-0", Vertical)
                item = EventItem(f"󰄱 All Day: {summary}", event_data=ev)
                await slot.mount(item)
