from textual.message import Message
from textual.widgets import Label
from textual import events

class EventItem(Label):
    """個別の予定を表すフォーカス可能なウィジェット"""

    class EditRequested(Message):
        """予定の編集が要求されたときのメッセージ"""
        def __init__(self, event_data: dict) -> None:
            self.event_data = event_data
            super().__init__()

    def __init__(self, text: str, event_data: dict, **kwargs):
        super().__init__(text, **kwargs)
        self.event_data = event_data
        self.can_focus = True
        self.add_class("event-item")

    def on_key(self, event: events.Key) -> None:
        """キー操作で編集・削除リクエストを飛ばす"""
        if event.key == "e":
            self.post_message(self.EditRequested(self.event_data))
            event.stop()
        elif event.key == "delete":
            # 削除も編集画面経由で行うか、直接削除リクエストを飛ばすか
            # ここではEditRequestedを使い、便宜的にFormを開く (Form内にDeleteボタンがあるため)
            # または専用の DeleteRequested(Message) を作っても良い
            self.post_message(self.EditRequested(self.event_data))
            event.stop()
