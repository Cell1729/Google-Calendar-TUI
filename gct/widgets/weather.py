from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal

class WeatherWidget(Static):
    """天気情報を表示するパネル"""

    def compose(self) -> ComposeResult:
        with Vertical(id="weather-panel"):
            yield Label("Weather Forecast", classes="panel-title")
            with Horizontal(id="weather-content"):
                yield Label("󰖙", id="weather-icon")  # デフォルトアイコン
                with Vertical():
                    yield Label("Loading weather...", id="weather-temp")
                    yield Label("", id="weather-desc")
            
            # 1hごとの詳細表示エリア（初期は非表示にするなどの制御が可能）
            yield Static("", id="weather-hourly")

    def update_weather(self, current_data):
        """現在の天気を更新"""
        temp = current_data.get("temperature", "--")
        code = current_data.get("weathercode", 0)
        
        # 本来は api/weather.py の変換メソッドを使うが、簡易的にここで更新
        self.query_one("#weather-temp", Label).update(f"{temp}°C")
        self.notify("Weather updated")
