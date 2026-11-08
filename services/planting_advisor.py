from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class CropProfile(Protocol):
    name: str
    ideal_conditions: Mapping[str, object]
    growth_stages: Mapping[str, object]


class GeminiClient(Protocol):
    def generate_response(self, prompt: str) -> str:
        ...


class PlantingAdvisor:

    def __init__(
        self,
        crop: CropProfile,
        weather_data: Mapping[str, float | int | str | None],
        gemini_client: GeminiClient | None = None,
    ) -> None:
        self.crop: CropProfile = crop
        self.weather_data: Mapping[str, float | int | str | None] = weather_data
        self.gemini_client: GeminiClient | None = gemini_client

    def format_weather_data(self) -> str:
        temperature: float | int | str | None = self.weather_data.get("temperature", "Not provided")
        rainfall: float | int | str | None = self.weather_data.get("rainfall", "Not provided")
        soil_moisture: float | int | str | None = self.weather_data.get("soil_moisture", "Not provided")

        weather_summary: str = f"""
        WEATHER INFORMATION
        -------------------
        Crop: {self.crop.name}
        Temperature: {temperature}°C
        Rainfall: {rainfall} mm
        Soil Moisture: {soil_moisture}%
        """

        return weather_summary

    def _to_float(self, value: object) -> float | None:
        if value is None:
            return None

        if not isinstance(value, (float, int, str)):
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def analyze_temperature(self) -> str:
        temperature: float | int | str | None = self.weather_data.get("temperature")

        if temperature is None:
            return "Temperature information is missing."

        temperature_value: float | None = self._to_float(temperature)
        if temperature_value is None:
            return "Temperature information is missing."

        ideal_range: object = self.crop.ideal_conditions["temperature"]
        range_text: str = str(ideal_range).replace("°C", "").replace(" ", "")

        if "-" not in range_text:
            return "Temperature is not suitable for this crop."

        minimum_text, maximum_text = range_text.split("-", 1)

        try:
            minimum = float(minimum_text)
            maximum = float(maximum_text)
        except ValueError:
            return "Temperature information is missing."

        if minimum <= temperature_value <= maximum:
            return "Temperature is suitable for this crop."

        return "Temperature is not suitable for this crop."

    def analyze_rainfall(self) -> str:
        rainfall: float | int | str | None = self.weather_data.get("rainfall")

        if rainfall is None:
            return "Rainfall information is missing."

        rainfall_value: float | None = self._to_float(rainfall)
        if rainfall_value is None:
            return "Rainfall information is missing."

        minimum: float | None = self._to_float(self.crop.ideal_conditions["rainfall_min"])
        maximum: float | None = self._to_float(self.crop.ideal_conditions["rainfall_max"])

        if minimum is None or maximum is None:
            return "Rainfall information is missing."

        if minimum <= rainfall_value <= maximum:
            return "Rainfall is suitable for this crop."

        return "Rainfall is not suitable for this crop."

    def analyze_soil_moisture(self) -> str:
        soil_moisture: float | int | str | None = self.weather_data.get("soil_moisture")

        if soil_moisture is None:
            return "Soil moisture information is missing."

        moisture_value: float | None = self._to_float(soil_moisture)
        if moisture_value is None:
            return "Soil moisture information is missing."

        minimum: float | None = self._to_float(self.crop.ideal_conditions["soil_moisture_min"])
        maximum: float | None = self._to_float(self.crop.ideal_conditions["soil_moisture_max"])

        if minimum is None or maximum is None:
            return "Soil moisture information is missing."

        if minimum <= moisture_value <= maximum:
            return "Soil moisture is suitable for this crop."

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

        return "Not all sample growing conditions are suitable or available."

    def analyze_pest_and_disease_risk(self) -> str:
        crop_name: str = self.crop.name.lower()

        rainfall: float | None = self._to_float(
            self.weather_data.get("rainfall")
        )

        soil_moisture: float | None = self._to_float(
            self.weather_data.get("soil_moisture")
        )

        if rainfall is None or soil_moisture is None:
            return (
                "Pest and disease risk cannot be fully assessed "
                "because weather information is missing."
            )

        rainfall_max: float | None = self._to_float(
            self.crop.ideal_conditions.get("rainfall_max")
        )

        moisture_max: float | None = self._to_float(
            self.crop.ideal_conditions.get("soil_moisture_max")
        )

        if rainfall_max is None or moisture_max is None:
            return "Ideal conditions are insufficient for risk analysis."

        if rainfall > rainfall_max and soil_moisture > moisture_max:
            risk_level = "High"
            risk_message = (
                "Excessive wetness may increase the risk of "
                "fungal diseases. Monitor crops closely."
            )

        elif rainfall > rainfall_max or soil_moisture > moisture_max:
            risk_level = "Moderate"
            risk_message = (
                "Some wetness conditions may favor disease development. "
                "Regular crop inspection is recommended."
            )

        else:
            risk_level = "No elevated wetness signal"
            risk_message = (
                "The supplied measurements do not indicate "
                "excessive wetness. Continue monitoring crops."
            )

        if crop_name == "maize":
            threats = (
                "Fall armyworm, stem borers, and maize leaf diseases."
            )

        elif crop_name == "rice":
            threats = (
                "Rice stem borers, rice blast, and bacterial leaf blight."
            )

        else:
            threats = (
                "Monitor for common pests and diseases affecting "
                "this crop."
            )

        return f"""
PEST AND DISEASE RISK ANALYSIS
------------------------------
Crop: {self.crop.name}
Risk Level: {risk_level}
Possible Threats: {threats}
Assessment: {risk_message}
"""

    def generate_ai_recommendation(self) -> str:
        if self.gemini_client is None:
            return "Gemini client is not available."

        prompt: str = f"""
        You are an expert agricultural planting advisor.

        IMPORTANT INSTRUCTIONS:
        - Analyze ONLY the crop specified below.
        - Do not confuse this crop with another crop.
        - Use the exact crop name provided.
        - Use the weather information provided.
        - Do not invent weather measurements.
        - Make all recommendations specific to this crop.
        - If information is missing, clearly state that it is missing.

        CROP INFORMATION:
        Crop Name: {self.crop.name}
        Ideal Conditions: {self.crop.ideal_conditions}
        Growth Stages: {self.crop.growth_stages}

        WEATHER INFORMATION:
        {self.format_weather_data()}

        SUITABILITY ANALYSIS:
        {self.analyze_temperature()}
        {self.analyze_rainfall()}
        {self.analyze_soil_moisture()}
        {self.analyze_overall_conditions()}
        {self.analyze_pest_and_disease_risk()}

        Provide the following in a concise format:

        1. Planting recommendations (maximum 3 bullet points).
        2. Weather suitability assessment (brief explanation).
        3. Possible pests and diseases (maximum 3).
        4. Ways to improve growing conditions (maximum 3 bullet points).

        Keep your response below 250 words.
        Avoid unnecessary explanations.

        Make your response practical and specific to {self.crop.name}.
        """

        return self.gemini_client.generate_response(prompt)
