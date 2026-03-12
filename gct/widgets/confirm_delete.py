from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button
from textual.containers import Vertical, Horizontal

class ConfirmDeleteScreen(ModalScreen[bool]):
    """削除確認用モーダルダイアログ"""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "confirm", "Confirm"),
    ]

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    
    #confirm-container {
        width: 40;
        height: auto;
        padding: 1 2;
        background: #1f2335;
        border: solid #f7768e;
    }
    
    #confirm-message {
        text-align: center;
        text-style: bold;
        color: #c0caf5;
        margin-bottom: 2;
    }
    
    #confirm-buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 2;
    }
    
    #btn-yes {
        background: #f7768e;
        color: #1a1b26;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Label("Are you sure you want to delete this event?", id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel (Esc)", id="btn-no", variant="default")
                yield Button("Delete (Enter)", id="btn-yes", variant="error")

    def action_cancel(self) -> None:
        self.dismiss(False)

    def action_confirm(self) -> None:
        self.dismiss(True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.action_confirm()
        else:
            self.action_cancel()
