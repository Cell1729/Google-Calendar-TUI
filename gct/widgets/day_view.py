from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal, ScrollableContainer
from datetime import datetime, date

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
                
                # 右側：予定スロット
                with Vertical(id="day-events"):
                    for h in range(24):
                        yield Label("", id=f"hour-{h}", classes="hour-slot")

    def update_view(self, target_date: date, events: list):
        """日付と予定リストで表示を更新"""
        self.current_date = target_date
        self.events = events
        
        # タイトル更新
        self.query_one("#day-view-title", Label).update(self.current_date.strftime("%A, %B %d, %Y"))
        
        # スロットをクリア
        for h in range(24):
            self.query_one(f"#hour-{h}", Label).update("")
        
        # 予定をスロットに流し込む
        for ev in self.events:
            start = ev['start'].get('dateTime', ev['start'].get('date', ''))
            summary = ev.get('summary', '(No Title)')
            
            if 'T' in start:
                # 時間指定あり
                hour = int(start.split('T')[1][:2])
                time_str = start.split('T')[1][:5]
                slot = self.query_one(f"#hour-{hour}", Label)
                current_text = slot.renderable
                new_text = f"󰄱 {time_str} {summary}"
                if current_text:
                    slot.update(str(current_text) + "\n" + new_text)
                else:
                    slot.update(new_text)
            else:
                # 終日予定などは 0時に
                slot = self.query_one("#hour-0", Label)
                current_text = slot.renderable
                new_text = f"󰄱 All Day: {summary}"
                if current_text:
                    slot.update(str(current_text) + "\n" + new_text)
                else:
                    slot.update(new_text)
