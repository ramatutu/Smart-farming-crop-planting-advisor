# Smart Farming Crop Recommendation Module

CROP_DATABASE = {
    "Maize": {
        "soil": ["Loamy", "Sandy"],
        "description": "Suitable for food and animal feed.",
        "water": "Moderate"
    },

    "Rice": {
        "soil": ["Clay", "Loamy"],
        "description": "Requires adequate water supply.",
        "water": "High"
    },

    "Tomato": {
        "soil": ["Loamy", "Sandy"],
        "description": "Suitable for vegetable production.",
        "water": "Moderate"
    },

    "Cassava": {
        "soil": ["Sandy", "Loamy"],
        "description": "A drought-tolerant root crop.",
        "water": "Low"
    },

    "Beans": {
        "soil": ["Loamy", "Sandy"],
        "description": "A good source of plant protein.",
        "water": "Moderate"
    }
}


def recommend_crops(soil_type):

    recommendations = []

    for crop, details in CROP_DATABASE.items():

        if soil_type in details["soil"]:

            recommendations.append({
                "crop": crop,
                "description": details["description"],
                "water": details["water"]
            })

    return recommendations


def get_crop_details(crop_name):

    return CROP_DATABASE.get(crop_name)
