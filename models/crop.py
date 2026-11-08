from typing import Any


class Crop:
    """
    This class stores information about different crops,
    including their ideal growing conditions and growth stages.
    """

    def __init__(self, name, ideal_conditions, growth_stages) -> None:

        self.name: Any = name
        self.ideal_conditions: Any = ideal_conditions
        self.growth_stages: Any = growth_stages

    def display_info(self) -> None:

        print("\nCROP INFORMATION")
        print("----------------")

        print("Crop Name:", self.name)

        print("\nIdeal Growing Conditions:")

        for condition, value in self.ideal_conditions.items():
            print(condition, ":", value)

        print("\nGrowth Stages:")

        for stage in self.growth_stages:
            print("-", stage)

    def get_crop_data(self) -> dict[str, Any]:

        return {
            "name": self.name,
            "ideal_conditions": self.ideal_conditions,
            "growth_stages": self.growth_stages
        }