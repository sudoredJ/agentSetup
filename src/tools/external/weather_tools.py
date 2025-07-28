"""Weather tools for fetching weather data from Open-Meteo API and sunrise/sunset times."""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from smolagents import tool

# Default location: Cambridge, MA
DEFAULT_LATITUDE = 42.3736
DEFAULT_LONGITUDE = -71.1097
DEFAULT_LOCATION = "Cambridge, MA"


def geocode_location(location: str) -> tuple[float, float, str]:
    """Geocode a location name to coordinates.
    
    Returns:
        Tuple of (latitude, longitude, formatted_name)
    """
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location, "count": 1}
    response = requests.get(geocode_url, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("results"):
            result = data["results"][0]
            return (
                result["latitude"],
                result["longitude"],
                f"{result.get('name', '')}, {result.get('country', '')}"
            )
    raise ValueError(f"Could not find location: {location}")


@tool
def get_weather_forecast(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    days: int = 7
) -> str:
    """Get weather forecast for a location using Open-Meteo API.
    
    Args:
        location: City name or address (will be geocoded). Defaults to Cambridge, MA if not specified.
        latitude: Latitude coordinate (used if location not provided)
        longitude: Longitude coordinate (used if location not provided)
        days: Number of days to forecast (default: 7, max: 16)
    
    Returns:
        Formatted weather forecast string
    
    Example:
        get_weather_forecast()  # Uses Cambridge, MA default
        get_weather_forecast(location="Berlin, Germany")
        get_weather_forecast(latitude=52.52, longitude=13.41)
    """
    try:
        location_name = None
        
        # If no location info provided, use default (Cambridge, MA)
        if not location and not (latitude and longitude):
            latitude = DEFAULT_LATITUDE
            longitude = DEFAULT_LONGITUDE
            location_name = DEFAULT_LOCATION
        # If location provided, geocode it
        elif location:
            try:
                latitude, longitude, location_name = geocode_location(location)
            except ValueError as e:
                return str(e)
        
        if not (latitude and longitude):
            return "Unable to determine location coordinates"
        
        # Fetch weather data
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone": "auto",
            "forecast_days": min(days, 16)
        }
        
        response = requests.get(weather_url, params=params, timeout=10)
        
        if response.status_code != 200:
            return f"Error fetching weather data: {response.status_code}"
        
        data = response.json()
        daily = data.get("daily", {})
        
        # Format the response
        formatted = f"**Weather Forecast"
        if location_name:
            formatted += f" for {location_name}"
        elif location:
            formatted += f" for {location}"
        formatted += f"** (Lat: {latitude:.2f}, Lon: {longitude:.2f})\n\n"
        
        # Weather codes mapping
        weather_codes = {
            0: "☀️ Clear sky",
            1: "🌤️ Mainly clear", 
            2: "⛅ Partly cloudy",
            3: "☁️ Overcast",
            45: "🌫️ Foggy",
            48: "🌫️ Rime fog",
            51: "🌦️ Light drizzle",
            61: "🌧️ Slight rain",
            63: "🌧️ Moderate rain",
            65: "🌧️ Heavy rain",
            71: "🌨️ Slight snow",
            73: "🌨️ Moderate snow",
            75: "❄️ Heavy snow",
            95: "⛈️ Thunderstorm",
            96: "⛈️ Thunderstorm with hail"
        }
        
        times = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precipitation = daily.get("precipitation_sum", [])
        weather_codes_data = daily.get("weathercode", [])
        
        for i in range(len(times)):
            date = datetime.fromisoformat(times[i])
            day_name = date.strftime("%A, %B %d")
            
            # Get weather description
            code = weather_codes_data[i] if i < len(weather_codes_data) else 0
            weather_desc = weather_codes.get(int(code), "Unknown")
            
            formatted += f"**{day_name}**\n"
            formatted += f"  {weather_desc}\n"
            formatted += f"  🌡️ High: {max_temps[i]:.1f}°C / {(max_temps[i] * 9/5 + 32):.1f}°F\n"
            formatted += f"  🌡️ Low: {min_temps[i]:.1f}°C / {(min_temps[i] * 9/5 + 32):.1f}°F\n"
            
            if precipitation[i] > 0:
                formatted += f"  💧 Precipitation: {precipitation[i]:.1f}mm\n"
            
            formatted += "\n"
        
        return formatted.strip()
        
    except Exception as e:
        return f"Error getting weather forecast: {str(e)}"


@tool
def get_current_weather(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
) -> str:
    """Get current weather for a location.
    
    Args:
        location: City name or address (will be geocoded). Defaults to Cambridge, MA if not specified.
        latitude: Latitude coordinate (used if location not provided)
        longitude: Longitude coordinate (used if location not provided)
    
    Returns:
        Formatted current weather string
    """
    try:
        location_name = None
        
        # If no location info provided, use default (Cambridge, MA)
        if not location and not (latitude and longitude):
            latitude = DEFAULT_LATITUDE
            longitude = DEFAULT_LONGITUDE
            location_name = DEFAULT_LOCATION
        # If location provided, geocode it
        elif location:
            try:
                latitude, longitude, location_name = geocode_location(location)
            except ValueError as e:
                return str(e)
        
        if not (latitude and longitude):
            return "Unable to determine location coordinates"
        
        # Fetch current weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto"
        }
        
        response = requests.get(weather_url, params=params, timeout=10)
        
        if response.status_code != 200:
            return f"Error fetching weather data: {response.status_code}"
        
        data = response.json()
        current = data.get("current", {})
        
        # Format response
        formatted = f"**Current Weather"
        if location_name:
            formatted += f" in {location_name}"
        elif location:
            formatted += f" in {location}"
        formatted += f"**\n\n"
        
        temp = current.get("temperature_2m", 0)
        feels_like = current.get("apparent_temperature", temp)
        humidity = current.get("relative_humidity_2m", 0)
        wind_speed = current.get("wind_speed_10m", 0)
        precip = current.get("precipitation", 0)
        
        formatted += f"🌡️ Temperature: {temp:.1f}°C / {(temp * 9/5 + 32):.1f}°F\n"
        formatted += f"🤔 Feels like: {feels_like:.1f}°C / {(feels_like * 9/5 + 32):.1f}°F\n"
        formatted += f"💧 Humidity: {humidity}%\n"
        formatted += f"💨 Wind: {wind_speed:.1f} km/h / {(wind_speed * 0.621371):.1f} mph\n"
        
        if precip > 0:
            formatted += f"🌧️ Precipitation: {precip:.1f}mm\n"
        
        return formatted
        
    except Exception as e:
        return f"Error getting current weather: {str(e)}"


@tool
def get_sunrise_sunset(
    location: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    date: Optional[str] = None,
    days_ahead: int = 0
) -> str:
    """Get sunrise and sunset times for a location.
    
    Args:
        location: City name or address (will be geocoded). Defaults to Cambridge, MA if not specified.
        latitude: Latitude coordinate (used if location not provided)
        longitude: Longitude coordinate (used if location not provided)
        date: Date in YYYY-MM-DD format, or "today", "tomorrow". Defaults to today.
        days_ahead: Number of days ahead to show (0 for just one day, up to 7 for a week)
    
    Returns:
        Formatted sunrise/sunset times
    
    Example:
        get_sunrise_sunset()  # Today in Cambridge, MA
        get_sunrise_sunset(location="Tokyo")  # Today in Tokyo
        get_sunrise_sunset(location="London", date="2024-12-25")  # Christmas in London
        get_sunrise_sunset(location="Oslo", days_ahead=7)  # Week in Oslo
    """
    try:
        location_name = None
        
        # If no location info provided, use default (Cambridge, MA)
        if not location and not (latitude and longitude):
            latitude = DEFAULT_LATITUDE
            longitude = DEFAULT_LONGITUDE
            location_name = DEFAULT_LOCATION
        # If location provided, geocode it
        elif location:
            try:
                latitude, longitude, location_name = geocode_location(location)
            except ValueError as e:
                return str(e)
        
        if not (latitude and longitude):
            return "Unable to determine location coordinates"
        
        # Format dates
        if date is None:
            date = "today"
        
        # Build API request
        api_url = "https://api.sunrisesunset.io/json"
        
        formatted = f"**Sunrise & Sunset Times"
        if location_name:
            formatted += f" for {location_name}"
        elif location:
            formatted += f" for {location}"
        formatted += f"**\n"
        formatted += f"📍 Coordinates: {latitude:.2f}°N, {longitude:.2f}°{'E' if longitude > 0 else 'W'}\n\n"
        
        if days_ahead > 0:
            # Multi-day request
            start_date = datetime.now()
            dates = []
            
            for i in range(min(days_ahead + 1, 8)):  # Max 8 days
                current_date = start_date + timedelta(days=i)
                dates.append(current_date.strftime("%Y-%m-%d"))
            
            for query_date in dates:
                params = {
                    "lat": latitude,
                    "lng": longitude,
                    "date": query_date,
                    "time_format": "24"
                }
                
                response = requests.get(api_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "OK":
                        results = data["results"]
                        date_obj = datetime.strptime(results["date"], "%Y-%m-%d")
                        day_name = date_obj.strftime("%A, %B %d, %Y")
                        
                        formatted += f"**{day_name}**\n"
                        formatted += f"🌅 Sunrise: {results['sunrise']}\n"
                        formatted += f"🌇 Sunset: {results['sunset']}\n"
                        formatted += f"☀️ Day length: {results['day_length']}\n"
                        formatted += f"🌞 Solar noon: {results['solar_noon']}\n"
                        formatted += f"🌄 Dawn: {results['dawn']}\n"
                        formatted += f"🌆 Dusk: {results['dusk']}\n"
                        formatted += f"✨ Golden hour: {results['golden_hour']}\n\n"
        else:
            # Single day request
            params = {
                "lat": latitude,
                "lng": longitude,
                "date": date,
                "time_format": "24"
            }
            
            response = requests.get(api_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return f"Error fetching sunrise/sunset data: {response.status_code}"
            
            data = response.json()
            if data.get("status") != "OK":
                return f"Error: {data.get('status', 'Unknown error')}"
            
            results = data["results"]
            
            # Format date nicely
            if results["date"]:
                date_obj = datetime.strptime(results["date"], "%Y-%m-%d")
                formatted += f"📅 {date_obj.strftime('%A, %B %d, %Y')}\n\n"
            
            formatted += f"🌅 **Sunrise**: {results['sunrise']}\n"
            formatted += f"🌇 **Sunset**: {results['sunset']}\n"
            formatted += f"☀️ **Day length**: {results['day_length']}\n\n"
            
            formatted += f"**Additional Details:**\n"
            formatted += f"🌞 Solar noon: {results['solar_noon']}\n"
            formatted += f"🌄 Dawn: {results['dawn']} (civil twilight begins)\n"
            formatted += f"🌆 Dusk: {results['dusk']} (civil twilight ends)\n"
            formatted += f"🌌 First light: {results['first_light']} (astronomical twilight)\n"
            formatted += f"🌃 Last light: {results['last_light']} (astronomical twilight)\n"
            formatted += f"✨ Golden hour: {results['golden_hour']}\n"
            
            # Add timezone info
            formatted += f"\n⏰ Timezone: {results['timezone']} (UTC{results['utc_offset']/60:+.0f})"
        
        return formatted.strip()
        
    except Exception as e:
        return f"Error getting sunrise/sunset times: {str(e)}"