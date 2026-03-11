from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal

class DayWidget(Vertical):
    """日間表示ウィジェット"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = []

    def compose(self) -> ComposeResult:
        yield Label("Day View (Work in Progress)", classes="view-header")
        with Horizontal():
            with Vertical(id="time-axis"):
                for h in range(24):
                    yield Label(f"{h:02}:00")
            with Vertical(id="day-events"):
                yield Label("Select a day from month view to see details here.")

    def update_events(self, events):
        self.events = events
