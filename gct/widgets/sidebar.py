from textual.app import ComposeResult
from textual.widgets import Label, Button, Static
from textual.containers import Vertical

class Sidebar(Vertical):
    """サイドバーメニューとサマリー表示"""

    def compose(self) -> ComposeResult:
        yield Label("Views", classes="sidebar-title")
        yield Button("  Month", id="btn-month", classes="-active")
        yield Button("󱑆  Week", id="btn-week")
        yield Button("󰃭  Day", id="btn-day")
        
        yield Static("\n")
        
        yield Label("Calendars", classes="sidebar-title")
        with Vertical(id="calendar-container"):
            yield Label("Loading...", id="calendar-list")

        yield Static("\n")
        
        yield Label("Upcoming", classes="sidebar-title")
        with Vertical(id="upcoming-container"):
            yield Label("No upcoming events", id="sidebar-upcoming")
