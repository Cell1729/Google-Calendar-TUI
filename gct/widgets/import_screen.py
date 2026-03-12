from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input
from textual.containers import Vertical, Horizontal
import os

class ImportScreen(ModalScreen[str]):
    """JSONファイルパスを入力するインポート画面"""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "import_file", "Import"),
    ]
    
    CSS = """
    ImportScreen {
        align: center middle;
    }
    
    #import-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: #1f2335;
        border: solid #7aa2f7;
    }
    
    #import-title {
        text-align: center;
        text-style: bold;
        color: #bb9af7;
        margin-bottom: 1;
    }
    
    #import-input {
        margin-bottom: 1;
    }
    
    #import-buttons {
        height: 3;
        align: right middle;
    }
    
    Button {
        margin-left: 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="import-container"):
            yield Label("Import Events from JSON", id="import-title")
            yield Label("Absolute Path to JSON file:", classes="input-label")
            yield Input(placeholder="e.g. C:/Users/sabax/events.json", id="import-input")
            with Horizontal(id="import-buttons"):
                yield Button("Cancel (Esc)", id="btn-cancel", variant="default")
                yield Button("Import (Enter)", id="btn-import", variant="primary")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_import_file(self) -> None:
        path = self.query_one("#import-input", Input).value.strip()
        if not path:
            self.app.notify("File path is required.", severity="error")
            return
        if not os.path.exists(path):
            self.app.notify("File not found.", severity="error")
            return
        self.dismiss(path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-import":
            self.action_import_file()
