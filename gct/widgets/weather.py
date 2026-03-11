from textual.app import ComposeResult
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal

class WeatherWidget(Vertical):
    """天気情報を表示するパネル"""

    def compose(self) -> ComposeResult:
        yield Label("Weather Forecast", classes="panel-title")
        with Horizontal(id="weather-content"):
            yield Label("󰖙", id="weather-icon")
            with Vertical():
                yield Label("Loading weather...", id="weather-temp")
                yield Label("", id="weather-desc")
        
        yield Static("", id="weather-hourly")

    def update_hourly(self, hourly_data):
        hourly = hourly_data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        
        text = "Hourly: "
        for i in range(0, len(times), 4):
            time_str = times[i].split('T')[1]
            text += f"\n[bold]{time_str}[/bold]: {temps[i]}° \n "
        
        self.query_one("#weather-hourly", Static).update(text)

    def update_weather(self, current_data):
        temp = current_data.get("temperature", "--")
        self.query_one("#weather-temp", Label).update(f"{temp}°C")
        self.notify("Weather updated")
