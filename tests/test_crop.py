from models.crop import Crop


def create_crops() -> dict[str, Crop]:

    maize: Crop = Crop(
        name="Maize",
        ideal_conditions={
            "temperature": "20-30°C",
            "rainfall": "Moderate rainfall",
            "soil_type": "Well-drained soil"
        },
        growth_stages=[
            "Germination",
            "Seedling",
            "Vegetative",
            "Flowering",
            "Grain Filling",
            "Maturity"
        ]
    )

    cassava: Crop = Crop(
        name="Cassava",
        ideal_conditions={
            "temperature": "25-29°C",
            "rainfall": "Adequate rainfall",
            "soil_type": "Well-drained soil"
        },
        growth_stages=[
            "Planting",
            "Sprouting",
            "Root Development",
            "Bulking",
            "Maturity"
        ]
    )

    rice: Crop = Crop(
        name="Rice",
        ideal_conditions={
            "temperature": "20-35°C",
            "rainfall": "Adequate water supply",
            "soil_type": "Suitable rice-growing soil"
        },
        growth_stages=[
            "Germination",
            "Seedling",
            "Tillering",
            "Flowering",
            "Grain Filling",
            "Maturity"
        ]
    )

    tomato: Crop = Crop(
        name="Tomato",
        ideal_conditions={
            "temperature": "18-30°C",
            "rainfall": "Moderate water supply",
            "soil_type": "Well-drained fertile soil"
        },
        growth_stages=[
            "Germination",
            "Seedling",
            "Vegetative",
            "Flowering",
            "Fruiting",
            "Maturity"
        ]
    )

    return {
        "maize": maize,
        "cassava": cassava,
        "rice": rice,
        "tomato": tomato
    }


def test_crop_creation() -> None:

    crops: dict[str, Crop] = create_crops()

    assert len(crops) == 4


def test_crop_names() -> None:

    crops: dict[str, Crop] = create_crops()

    assert crops["maize"].name == "Maize"
    assert crops["cassava"].name == "Cassava"
    assert crops["rice"].name == "Rice"
    assert crops["tomato"].name == "Tomato"


def test_crop_growth_stages() -> None:

    crops: dict[str, Crop] = create_crops()

    assert "Germination" in crops["maize"].growth_stages
    assert "Root Development" in crops["cassava"].growth_stages
    assert "Tillering" in crops["rice"].growth_stages
    assert "Fruiting" in crops["tomato"].growth_stages


def test_crop_ideal_conditions() -> None:

    crops: dict[str, Crop] = create_crops()

    assert crops["maize"].ideal_conditions["temperature"] == "20-30°C"
    assert crops["cassava"].ideal_conditions["temperature"] == "25-29°C"
    assert crops["rice"].ideal_conditions["temperature"] == "20-35°C"
    assert crops["tomato"].ideal_conditions["temperature"] == "18-30°C"