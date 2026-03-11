from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Label, Input, Button
from textual.containers import Vertical, Center
from textual.message import Message
from textual.binding import Binding

class SetupScreen(Screen):
    """初回起動時のセットアップ画面 (ClientID / Secret / Weather)"""

    BINDINGS = [
        Binding("ctrl+q", "app.quit", "Quit", show=True),
        Binding("q", "app.quit", "Quit", show=False),
    ]

    CSS = """
    SetupScreen {
        align: center middle;
    }

    #setup-container {
        width: 60;
        height: auto;
        background: #24283b;
        border: thick #7aa2f7;
        padding: 2;
    }

    Label {
        margin-top: 1;
        color: #9aa5ce;
    }

    Input {
        margin-bottom: 1;
        border: solid #414868;
    }

    #submit-btn {
        margin-top: 2;
        background: #7aa2f7;
        color: white;
        width: 100%;
    }
    """

    class Completed(Message):
        """セットアップ完了を通知するメッセージ"""
        def __init__(self, client_id, client_secret, location):
            super().__init__()
            self.client_id = client_id
            self.client_secret = client_secret
            self.location = location

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="setup-container"):
                yield Label("Welcome to GCT Setup", id="setup-title")
                yield Label("Google API Client ID:")
                yield Input(placeholder="Enter Client ID...", id="client-id")
                yield Label("Google API Client Secret:")
                yield Input(placeholder="Enter Client Secret...", password=True, id="client-secret")
                yield Label("Weather Location (e.g., Tokyo):")
                yield Input(placeholder="Enter city name...", id="location")
                yield Button("Start Setup", id="submit-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-btn":
            client_id = self.query_one("#client-id", Input).value
            client_secret = self.query_one("#client-secret", Input).value
            location = self.query_one("#location", Input).value
            
            if client_id and client_secret and location:
                # 辞書形式で結果を返して画面を閉じる
                self.dismiss({
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "location": location
                })
            else:
                self.notify("Please fill in all fields", severity="error")
