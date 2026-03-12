from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Checkbox, ListItem, ListView
from textual.containers import Vertical, Horizontal

class CalendarSelectionScreen(ModalScreen[list]):
    """表示するカレンダーを選択するモーダル画面"""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
    ]
    
    CSS = """
    CalendarSelectionScreen {
        align: center middle;
    }
    
    #cal-select-container {
        width: 60;
        height: 70%;
        padding: 1 2;
        background: #1f2335;
        border: solid #7aa2f7;
    }
    
    #cal-select-title {
        text-align: center;
        text-style: bold;
        color: #bb9af7;
        margin-bottom: 1;
    }
    
    #cal-list-view {
        height: 1fr;
        border: solid #414868;
        margin-bottom: 1;
    }
    
    .cal-item {
        padding: 1;
    }
    
    #cal-buttons {
        height: 3;
        align: right middle;
    }
    
    Button {
        margin-left: 2;
    }
    """

    def __init__(self, calendars: list, active_ids: list, **kwargs):
        super().__init__(**kwargs)
        self.calendars = calendars
        self.active_ids = active_ids

    def compose(self) -> ComposeResult:
        with Vertical(id="cal-select-container"):
            yield Label("Select Calendars to Display", id="cal-select-title")
            
            with Vertical(id="cal-list-view"):
                for cal in self.calendars:
                    is_checked = cal['id'] in self.active_ids
                    # カレンダー名を表示するチェックボックス
                    cb = Checkbox(cal.get('summary', 'Unknown'), value=is_checked)
                    cb.calendar_id = cal['id'] # カスタムプロパティにIDを保持
                    yield cb
            
            with Horizontal(id="cal-buttons"):
                yield Button("Cancel (Esc)", id="btn-cancel", variant="default")
                yield Button("Save (Ctrl+S)", id="btn-save", variant="primary")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_save(self) -> None:
        selected_ids = []
        for cb in self.query(Checkbox):
            if cb.value:
                selected_ids.append(cb.calendar_id)
                
        if not selected_ids:
            self.app.notify("Please select at least one calendar.", severity="warning")
            return
            
        self.dismiss(selected_ids)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-save":
            self.action_save()
