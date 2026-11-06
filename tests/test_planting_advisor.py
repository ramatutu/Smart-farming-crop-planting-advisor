from models.crop import Crop
from services.planting_advisor import PlantingAdvisor


def create_advisor() -> PlantingAdvisor:

    maize: Crop = Crop(
        name="Maize",
        ideal_conditions={
            "temperature": "20-30°C",
            "rainfall_min": 10,
            "rainfall_max": 20,
            "soil_moisture_min": 40,
            "soil_moisture_max": 80,
            "soil_type": "Well-drained soil"
        },
        growth_stages=[
            "Germination",
            "Seedling",
            "Vegetative",
            "Flowering",
            "Maturity"
        ]
    )

    weather_data: dict[str, int] = {
        "temperature": 27,
        "rainfall": 15,
        "soil_moisture": 65
    }

    return PlantingAdvisor(maize, weather_data)


def test_format_weather_data() -> None:

    advisor: PlantingAdvisor = create_advisor()

    result: str = advisor.format_weather_data()

    assert "Maize" in result
    assert "27" in result


def test_analyze_temperature() -> None:

    advisor: PlantingAdvisor = create_advisor()

    assert advisor.analyze_temperature() == "Temperature is suitable for this crop."


def test_analyze_rainfall() -> None:

    advisor: PlantingAdvisor = create_advisor()

    assert advisor.analyze_rainfall() == "Rainfall is suitable for this crop."


def test_analyze_soil_moisture() -> None:

    advisor: PlantingAdvisor = create_advisor()

    assert advisor.analyze_soil_moisture() == "Soil moisture is suitable for this crop."


def test_analyze_overall_conditions() -> None:

    advisor: PlantingAdvisor = create_advisor()

    assert advisor.analyze_overall_conditions() == "All three sample growing conditions are suitable."