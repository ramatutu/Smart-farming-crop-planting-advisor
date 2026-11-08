"""Crop model and crop database (Yung parly's module).

The original CROP_DATABASE / recommend_crops / get_crop_details are kept as
they were. Added during integration:

* ideal_conditions, growth_stages, care_tasks and days_to_harvest for each crop
* a Crop class, which PlantingAdvisor needs (crop.name, crop.ideal_conditions,
  crop.growth_stages)
* get_crop(), list_crop_names()

UNITS (must match WeatherClient / Open-Meteo):
    temperature        degrees C, written as a "min-max" string, e.g. "20-30°C"
    rainfall_*         mm, compared with the CURRENT precipitation reading
    soil_moisture_*    m3/m3 (volumetric, usually 0.0 - 0.5), NOT percent

NOTE: the numeric ranges below are reasonable starting values, not
agronomy-verified figures. Yung parly / the team should review them.
"""
from dataclasses import dataclass, field
from typing import Optional

CROP_DATABASE = {
    "Maize": {
        "soil": ["Loamy", "Sandy"],
        "description": "Suitable for food and animal feed.",
        "water": "Moderate",
        "ideal_conditions": {
            "temperature": "20-30°C",
            "rainfall_min": 0.0, "rainfall_max": 5.0,
            "soil_moisture_min": 0.20, "soil_moisture_max": 0.40,
        },
        "growth_stages": {
            "Germination": (0, 10), "Vegetative growth": (11, 55),
            "Flowering": (56, 75), "Grain filling": (76, 100),
        },
        "care_tasks": [("First weeding", 21), ("Fertilizer top-dressing", 28),
                       ("Second weeding", 42), ("Scout for fall armyworm", 14)],
        "days_to_harvest": 100,
    },
    "Rice": {
        "soil": ["Clay", "Loamy"],
        "description": "Requires adequate water supply.",
        "water": "High",
        "ideal_conditions": {
            "temperature": "22-32°C",
            "rainfall_min": 0.0, "rainfall_max": 10.0,
            "soil_moisture_min": 0.35, "soil_moisture_max": 0.50,
        },
        "growth_stages": {
            "Seedling": (0, 20), "Tillering": (21, 55),
            "Flowering": (56, 90), "Grain filling": (91, 120),
        },
        "care_tasks": [("Transplant seedlings", 21), ("Weeding", 30),
                       ("Fertilizer top-dressing", 45), ("Drain the field", 105)],
        "days_to_harvest": 120,
    },
    "Tomato": {
        "soil": ["Loamy", "Sandy"],
        "description": "Suitable for vegetable production.",
        "water": "Moderate",
        "ideal_conditions": {
            "temperature": "18-29°C",
            "rainfall_min": 0.0, "rainfall_max": 4.0,
            "soil_moisture_min": 0.20, "soil_moisture_max": 0.35,
        },
        "growth_stages": {
            "Seedling": (0, 21), "Vegetative growth": (22, 45),
            "Flowering": (46, 65), "Fruiting": (66, 90),
        },
        "care_tasks": [("Stake the plants", 25), ("Fertilizer application", 30),
                       ("Inspect for blight and pests", 40)],
        "days_to_harvest": 90,
    },
    "Cassava": {
        "soil": ["Sandy", "Loamy"],
        "description": "A drought-tolerant root crop.",
        "water": "Low",
        "ideal_conditions": {
            "temperature": "22-32°C",
            "rainfall_min": 0.0, "rainfall_max": 6.0,
            "soil_moisture_min": 0.15, "soil_moisture_max": 0.35,
        },
        "growth_stages": {
            "Establishment": (0, 60), "Canopy growth": (61, 150),
            "Root bulking": (151, 300),
        },
        "care_tasks": [("First weeding", 30), ("Second weeding", 60),
                       ("Fertilizer application", 60), ("Third weeding", 90)],
        "days_to_harvest": 300,
    },
    "Beans": {
        "soil": ["Loamy", "Sandy"],
        "description": "A good source of plant protein.",
        "water": "Moderate",
        "ideal_conditions": {
            "temperature": "18-28°C",
            "rainfall_min": 0.0, "rainfall_max": 4.0,
            "soil_moisture_min": 0.20, "soil_moisture_max": 0.35,
        },
        "growth_stages": {
            "Germination": (0, 8), "Vegetative growth": (9, 30),
            "Flowering": (31, 45), "Pod filling": (46, 70),
        },
        "care_tasks": [("First weeding", 14), ("Second weeding", 28),
                       ("Inspect for pests and rust", 35)],
        "days_to_harvest": 70,
    },
}


@dataclass(frozen=True)
class Crop:
    """One crop's rules. Satisfies the CropProfile protocol PlantingAdvisor expects."""
    name: str
    soil_types: tuple
    description: str
    water_need: str
    ideal_conditions: dict
    growth_stages: dict          # stage name -> (first_day, last_day) after planting
    care_tasks: list = field(default_factory=list)   # [(title, days_after_planting)]
    days_to_harvest: int = 0

    def schedule_stages(self) -> list:
        """(title, days_after_planting) pairs, ready for
        FarmLogStore.generate_season_schedule()."""
        stages = list(self.care_tasks)
        if self.days_to_harvest:
            stages.append(("Harvest", self.days_to_harvest))
        return sorted(stages, key=lambda item: item[1])


def list_crop_names() -> list:
    return list(CROP_DATABASE)


def get_crop(crop_name) -> Optional[Crop]:
    """Case-insensitive lookup (the store saves crop names in lowercase)."""
    wanted = str(crop_name or "").strip().lower()
    for name, d in CROP_DATABASE.items():
        if name.lower() == wanted:
            return Crop(
                name=name,
                soil_types=tuple(d["soil"]),
                description=d["description"],
                water_need=d["water"],
                ideal_conditions=dict(d["ideal_conditions"]),
                growth_stages=dict(d["growth_stages"]),
                care_tasks=list(d["care_tasks"]),
                days_to_harvest=d["days_to_harvest"],
            )
    return None


def recommend_crops(soil_type, season=None, budget=None):
    """Crops that suit the soil type. `season` and `budget` are accepted so the
    UI can pass them, but they are not used for filtering yet."""
    wanted = str(soil_type or "").strip().lower()
    recommendations = []
    for crop, details in CROP_DATABASE.items():
        if wanted in [s.lower() for s in details["soil"]]:
            recommendations.append({
                "crop": crop,
                "description": details["description"],
                "water": details["water"],
            })
    return recommendations


def get_crop_details(crop_name):
    return CROP_DATABASE.get(crop_name)
