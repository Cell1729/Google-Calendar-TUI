from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal

class WeekWidget(Vertical):
    """週間表示ウィジェット"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = {}

    def compose(self) -> ComposeResult:
        yield Label("Week View (Work in Progress)", classes="view-header")
        with Horizontal(id="week-grid"):
            for i in range(7):
                with Vertical(classes="week-col"):
                    yield Label(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][i])
                    yield Static("", classes="week-events")

    def update_events(self, events):
        self.events = events
