from typing import Any


class PlantingAdvisor:

    def __init__(self, crop, weather_data) -> None:

        self.crop: Any = crop
        self.weather_data: Any = weather_data

    def format_weather_data(self) -> str:

        temperature = self.weather_data.get("temperature", "Not provided")
        rainfall = self.weather_data.get("rainfall", "Not provided")
        soil_moisture = self.weather_data.get("soil_moisture", "Not provided")

        weather_summary: str = f"""
        WEATHER INFORMATION
        -------------------
        Crop: {self.crop.name}
        Temperature: {temperature}°C
        Rainfall: {rainfall} mm
        Soil Moisture: {soil_moisture}%
        """

        return weather_summary

    def analyze_temperature(self) -> str:

        temperature = self.weather_data.get("temperature")

        if temperature is None:
            return "Temperature information is missing."

        ideal_range = self.crop.ideal_conditions["temperature"]

        minimum, maximum = ideal_range.replace("°C", "").split("-")

        minimum = int(minimum)
        maximum = int(maximum)

        if minimum <= temperature <= maximum:
            return "Temperature is suitable for this crop."

        else:
            return "Temperature is not suitable for this crop."

    def analyze_rainfall(self) -> str:

        rainfall = self.weather_data.get("rainfall")

        if rainfall is None:
            return "Rainfall information is missing."

        minimum = self.crop.ideal_conditions["rainfall_min"]
        maximum = self.crop.ideal_conditions["rainfall_max"]

        if minimum <= rainfall <= maximum:
            return "Rainfall is suitable for this crop."

        else:
            return "Rainfall is not suitable for this crop."

    def analyze_soil_moisture(self) -> str:

        soil_moisture = self.weather_data.get("soil_moisture")

        if soil_moisture is None:
            return "Soil moisture information is missing."

        minimum = self.crop.ideal_conditions["soil_moisture_min"]
        maximum = self.crop.ideal_conditions["soil_moisture_max"]

        if minimum <= soil_moisture <= maximum:
            return "Soil moisture is suitable for this crop."

        else:
            return "Soil moisture is not suitable for this crop." 

    def analyze_overall_conditions(self) -> str:

        temperature_result: str = self.analyze_temperature()
        rainfall_result: str = self.analyze_rainfall()
        moisture_result: str = self.analyze_soil_moisture()

        if (
            temperature_result == "Temperature is suitable for this crop."
            and rainfall_result == "Rainfall is suitable for this crop."
            and moisture_result == "Soil moisture is suitable for this crop."
        ):

            return "All three sample growing conditions are suitable."

        else:

            return "Not all sample growing conditions are suitable or available."    
               