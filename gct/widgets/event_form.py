from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label, Button, Input, Checkbox
from textual.containers import Vertical, Horizontal
from textual.validation import Function
from datetime import datetime, date, timedelta

class EventFormScreen(ModalScreen[dict]):
    """予定の作成・編集用モーダル画面"""
    
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "save", "Save"),
        ("ctrl+d", "delete_event", "Delete"),
    ]
    
    CSS = """
    EventFormScreen {
        align: center middle;
    }
    
    #form-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: #1f2335;
        border: solid #7aa2f7;
    }
    
    .form-title {
        text-align: center;
        text-style: bold;
        color: #bb9af7;
        margin-bottom: 1;
    }
    
    .input-row {
        height: 3;
        margin-bottom: 1;
    }
    
    .input-label {
        width: 15;
        content-align: right middle;
        padding-right: 1;
        color: #9aa5ce;
    }
    
    Input {
        width: 1fr;
    }
    
    #button-row {
        height: 3;
        align: right middle;
        margin-top: 1;
    }
    
    Button {
        margin-left: 2;
    }
    
    #btn-delete {
        background: #f7768e;
        color: #1a1b26;
        display: none; /* 初期は非表示、編集時のみ表示 */
    }
    """

    def __init__(self, target_date: date = None, event_data: dict = None, **kwargs):
        super().__init__(**kwargs)
        self.target_date = target_date or date.today()
        self.event_data = event_data # 編集モードの場合はここに既存データが入る
        self.is_edit_mode = bool(event_data)

    def compose(self) -> ComposeResult:
        title = "Edit Event" if self.is_edit_mode else "New Event"
        
        # 初期値の決定
        summary_val = ""
        start_val = f"{self.target_date.strftime('%Y-%m-%d')} 10:00"
        end_val = f"{self.target_date.strftime('%Y-%m-%d')} 11:00"
        all_day_val = False
        
        if self.is_edit_mode:
            summary_val = self.event_data.get('summary', '')
            start_dict = self.event_data.get('start', {})
            end_dict = self.event_data.get('end', {})
            
            if 'date' in start_dict:
                # 終日予定
                all_day_val = True
                start_val = start_dict['date']
                end_val = end_dict.get('date', start_val)
            else:
                # 時間指定
                s_dt = datetime.fromisoformat(start_dict.get('dateTime', '').replace('Z', '+00:00'))
                e_dt = datetime.fromisoformat(end_dict.get('dateTime', '').replace('Z', '+00:00'))
                # タイムゾーン変換を簡略化してローカルぽく表示
                start_val = s_dt.strftime('%Y-%m-%d %H:%M')
                end_val = e_dt.strftime('%Y-%m-%d %H:%M')

        with Vertical(id="form-container"):
            yield Label(title, classes="form-title")
            
            with Horizontal(classes="input-row"):
                yield Label("Title:", classes="input-label")
                yield Input(value=summary_val, placeholder="Event Title", id="input-summary")
                
            with Horizontal(classes="input-row"):
                yield Label("All Day:", classes="input-label")
                yield Checkbox(value=all_day_val, id="input-allday")
                
            with Horizontal(classes="input-row"):
                yield Label("Start:", classes="input-label")
                yield Input(value=start_val, placeholder="YYYY-MM-DD HH:MM", id="input-start")
                
            with Horizontal(classes="input-row"):
                yield Label("End:", classes="input-label")
                yield Input(value=end_val, placeholder="YYYY-MM-DD HH:MM", id="input-end")
                
            with Horizontal(id="button-row"):
                yield Button("Cancel (Esc)", id="btn-cancel", variant="default")
                if self.is_edit_mode:
                    btn_del = Button("Delete (Ctrl+D)", id="btn-delete")
                    btn_del.styles.display = "block"
                    yield btn_del
                yield Button("Save (Ctrl+S)", id="btn-save", variant="primary")

    def validate_date_input(self, text: str, is_all_day: bool) -> datetime:
        """入力文字列をパースしてdatetimeを返す"""
        try:
            if is_all_day:
                # ユーザーが YYYY-MM-DD HH:MM と入力していても、先頭の YYYY-MM-DD だけ取り出してパースする
                dt = datetime.strptime(text.strip()[:10], "%Y-%m-%d")
                return dt
            else:
                dt = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")
                return dt
        except ValueError:
            return None

    def action_cancel(self) -> None:
        self.dismiss(None) # キャンセル
        
    def action_delete_event(self) -> None:
        if self.is_edit_mode:
            self.dismiss({"action": "delete", "event_id": self.event_data.get('id')})

    def action_save(self) -> None:
        summary = self.query_one("#input-summary", Input).value.strip()
        if not summary:
            self.app.notify("Title is required", severity="error")
            return
            
        is_all_day = self.query_one("#input-allday", Checkbox).value
        start_str = self.query_one("#input-start", Input).value
        end_str = self.query_one("#input-end", Input).value
        
        start_dt = self.validate_date_input(start_str, is_all_day)
        end_dt = self.validate_date_input(end_str, is_all_day)
        
        if not start_dt or not end_dt:
            self.app.notify("Invalid date/time format", severity="error")
            return
            
        if start_dt > end_dt:
            self.app.notify("Start must be before End", severity="error")
            return

        result = {
            "action": "update" if self.is_edit_mode else "create",
            "summary": summary,
            "is_all_day": is_all_day,
            "start": start_dt,
            "end": end_dt
        }
        if self.is_edit_mode:
            result["event_id"] = self.event_data.get('id')

        self.dismiss(result)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.action_cancel()
        elif event.button.id == "btn-delete":
            self.action_delete_event()
        elif event.button.id == "btn-save":
            self.action_save()
