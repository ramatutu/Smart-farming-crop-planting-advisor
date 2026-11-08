"""
====================================================================
SMART FARMING & CROP PLANTING ADVISOR
SAEED'S PART OF THE PROJECT
WeatherClient – Open-Meteo Weather Data Integration
====================================================================

Purpose:
    Connects the Smart Farming application to the Open-Meteo API
    and retrieves temperature, precipitation (rainfall), and
    soil-moisture information for a farm's location.

Responsibilities:
    1. Send weather requests to Open-Meteo.
    2. Extract the requested weather information.
    3. Return the information in a Python dictionary.
    4. Handle network errors, timeouts, and invalid API responses.

Dependency:
    Install Requests with: pip install requests
"""

import requests


class WeatherClient:
    """Fetch weather information from the Open-Meteo forecast API."""

    def __init__(self):
        """Set the Open-Meteo API address."""
        self.url = "https://api.open-meteo.com/v1/forecast"

    def get_weather(self, latitude, longitude):
        """
        Fetch weather data for the supplied farm coordinates.

        Args:
            latitude (float): Farm latitude.
            longitude (float): Farm longitude.

        Returns:
            dict: Temperature, precipitation, soil moisture, and time.

        Raises:
            ValueError: If coordinates or returned data are invalid.
            RuntimeError: If the API request fails.
        """

        # Basic coordinate validation
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            raise ValueError("Latitude and longitude must be numbers.")

        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90.")

        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180.")

        # Tell Open-Meteo which location and weather variables we need.
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,precipitation",
            "hourly": "soil_moisture_0_to_1cm",
            "forecast_days": 1,
            "timezone": "auto"
        }

        try:
            # Send the request. Stop waiting after 15 seconds.
            response = requests.get(
                self.url,
                params=params,
                timeout=15
            )

            # Raise an error if the server returns an unsuccessful status.
            response.raise_for_status()

            # Convert the API's JSON response into Python data.
            data = response.json()

            # Safely get the current and hourly weather sections.
            current = data.get("current", {})
            hourly = data.get("hourly", {})

            temperature = current.get("temperature_2m")
            rainfall = current.get("precipitation")
            moisture_values = hourly.get("soil_moisture_0_to_1cm", [])

            if temperature is None:
                raise ValueError("Temperature data is missing.")

            if rainfall is None:
                raise ValueError("Precipitation data is missing.")

            # Use the first available non-empty hourly soil-moisture value.
            soil_moisture = next(
                (value for value in moisture_values if value is not None),
                None
            )

            if soil_moisture is None:
                raise ValueError("Soil moisture data is unavailable.")

            # Return the information in a format other modules can use.
            weather_data = {
                "temperature": temperature,
                "rainfall": rainfall,
                "soil_moisture": soil_moisture,
                "time": current.get("time")
            }

            return weather_data

        except requests.exceptions.Timeout as error:
            raise RuntimeError(
                "The weather request timed out. Please try again."
            ) from error

        except requests.exceptions.ConnectionError as error:
            raise RuntimeError(
                "Could not connect to Open-Meteo. Check your internet connection."
            ) from error

        except requests.exceptions.HTTPError as error:
            raise RuntimeError(
                f"Open-Meteo returned an HTTP error: {error}"
            ) from error

        except requests.exceptions.RequestException as error:
            raise RuntimeError(
                f"A network error occurred: {error}"
            ) from error

        except (ValueError, KeyError, TypeError) as error:
            raise RuntimeError(
                f"The weather response was invalid: {error}"
            ) from error


# --------------------------------------------------------------------
# SIMPLE TEST
# Run this file directly to test the WeatherClient connection.
# The coordinates below are an example location in Abuja, Nigeria.
# --------------------------------------------------------------------
if __name__ == "__main__":
    client = WeatherClient()

    try:
        weather = client.get_weather(9.0765, 7.3986)

        print("\nSMART FARMING - WEATHER INFORMATION")
        print("-----------------------------------")
        print(f"Temperature:   {weather['temperature']} °C")
        print(f"Precipitation: {weather['rainfall']} mm")
        print(f"Soil moisture: {weather['soil_moisture']} m³/m³")
        print(f"Time:          {weather['time']}")

    except (RuntimeError, ValueError) as error:
        print(f"Could not retrieve weather data: {error}")
