import httpx
from datetime import datetime

class WeatherAPI:
    """Open-Meteo API を使用して天気情報を取得するクラス"""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    async def get_weather(self, lat, lon):
        """現在の天気と1日単位の予報を取得"""
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_probability_mean", "weathercode"],
            "timezone": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()

    async def get_hourly_weather(self, lat, lon, date_str):
        """指定した日の1時間ごとの予報を取得"""
        # Open-Meteo は過去〜未来7日分程度を一度に返すため、フィルタリングが必要
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ["temperature_2m", "precipitation_probability", "weathercode"],
            "start_date": date_str,
            "end_date": date_str,
            "timezone": "auto"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def get_weather_desc(code):
        """WMO Weather interpretation codes を文字列に変換"""
        codes = {
            0: "☀️ Clear sky",
            1: "🌤️ Mainly clear",
            2: "⛅ Partly cloudy",
            3: "☁️ Overcast",
            45: "🌫️ Fog",
            48: "🌫️ Depositing rime fog",
            51: "🌦️ Light drizzle",
            61: "🌧️ Slight rain",
            71: "🌨️ Slight snow",
            95: "⛈️ Thunderstorm",
        }
        return codes.get(code, "❓ Unknown")
