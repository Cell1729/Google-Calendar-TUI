from textual.app import ComposeResult
from textual.widgets import Static, Label, Button
from textual.containers import Vertical

class Sidebar(Static):
    """サイドバーメニューとサマリー表示"""

    def compose(self) -> ComposeResult:
        with Vertical(id="sidebar"):
            yield Label("Views", classes="sidebar-title")
            yield Button("  Month", id="btn-month", classes="-active")
            yield Button("󱑆  Week", id="btn-week")
            yield Button("󰃭  Day", id="btn-day")
            
            yield Static("\n")
            
            yield Label("Calendars", classes="sidebar-title")
            # ここにカレンダー一覧が並ぶ予定
            yield Label("Loading...", id="calendar-list")

            yield Static("\n")
            
            yield Label("Upcoming", classes="sidebar-title")
            yield Label("No upcoming events", id="sidebar-upcoming")
