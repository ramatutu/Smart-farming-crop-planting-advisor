"""Cross-module tests: Crop <-> PlantingAdvisor <-> WeatherClient <-> FarmLogStore <-> UI."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from models.crop import CROP_DATABASE, get_crop, list_crop_names, recommend_crops
from services.farm_log_store import FarmLogStore
from services.planting_advisor import PlantingAdvisor
from services.risk_alerts import weather_warnings
from services.weather_client import WeatherClient

GOOD_WEATHER = {"temperature": 25.0, "rainfall": 1.0, "soil_moisture": 0.30, "time": "2026-11-08T10:00"}


class FakeGemini:
    def __init__(self):
        self.prompts = []

    def generate_response(self, prompt):
        self.prompts.append(prompt)
        return "FAKE ADVICE"


class TestCrop(unittest.TestCase):
    def test_lookup_is_case_insensitive(self):
        self.assertEqual(get_crop("maize").name, "Maize")   # store saves lowercase
        self.assertEqual(get_crop("  RICE ").name, "Rice")
        self.assertIsNone(get_crop("unobtainium"))

    def test_every_crop_has_what_the_advisor_needs(self):
        for name in list_crop_names():
            crop = get_crop(name)
            ic = crop.ideal_conditions
            for key in ("temperature", "rainfall_min", "rainfall_max",
                        "soil_moisture_min", "soil_moisture_max"):
                self.assertIn(key, ic, f"{name} missing {key}")
            self.assertLess(ic["soil_moisture_max"], 1.0, "soil moisture is m3/m3, not percent")
            for title, day in crop.schedule_stages():
                self.assertIsInstance(day, int)
                self.assertGreaterEqual(day, 0)
            self.assertEqual(crop.schedule_stages()[-1][0], "Harvest")

    def test_recommend_crops_original_and_new_signature(self):
        self.assertTrue(recommend_crops("Clay"))
        self.assertEqual([r["crop"] for r in recommend_crops("Clay")],
                         [r["crop"] for r in recommend_crops("clay", "Rainy", "Low")])
        self.assertEqual(recommend_crops("Silty"), [])


class TestAdvisorWithCrop(unittest.TestCase):
    def test_conditions_and_prompt(self):
        fake = FakeGemini()
        advisor = PlantingAdvisor(get_crop("maize"), GOOD_WEATHER, fake)
        self.assertEqual(advisor.analyze_temperature(), "Temperature is suitable for this crop.")
        self.assertEqual(advisor.analyze_rainfall(), "Rainfall is suitable for this crop.")
        self.assertEqual(advisor.analyze_soil_moisture(), "Soil moisture is suitable for this crop.")
        self.assertIn("All three", advisor.analyze_overall_conditions())
        self.assertEqual(advisor.generate_ai_recommendation(), "FAKE ADVICE")
        self.assertIn("Maize", fake.prompts[0])
        self.assertIn("m³/m³", advisor.format_weather_data())

    def test_unsuitable_and_pest_risk(self):
        wet = {"temperature": 40, "rainfall": 20, "soil_moisture": 0.48}
        advisor = PlantingAdvisor(get_crop("maize"), wet)
        self.assertIn("not suitable", advisor.analyze_temperature())
        self.assertIn("High", advisor.analyze_pest_and_disease_risk())

    def test_without_gemini(self):
        self.assertEqual(PlantingAdvisor(get_crop("rice"), GOOD_WEATHER).generate_ai_recommendation(),
                         "Gemini client is not available.")

    def test_every_crop_runs_through_advisor(self):
        for name in list_crop_names():
            text = PlantingAdvisor(get_crop(name), GOOD_WEATHER).analyze_pest_and_disease_risk()
            self.assertIn(name, text)


class TestStoreWithCrop(unittest.TestCase):
    def test_crop_stages_feed_season_schedule(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FarmLogStore(Path(tmp) / "farm.json")
            plot = store.add_plot("North Field", "Lafia", "8.49, 8.52", "maize", "2026-03-15")
            crop = get_crop(plot.crop)
            events = store.generate_season_schedule(plot.plot_id, crop.schedule_stages())
            self.assertEqual(events[-1].title, "Harvest")
            self.assertEqual(events[-1].date, "2026-06-23")   # 15 Mar + 100 days

    def test_store_coordinates_work_with_weather_client(self):
        with tempfile.TemporaryDirectory() as tmp:
            plot = FarmLogStore(Path(tmp) / "f.json").add_plot("P1", "Abuja", "9.0765, 7.3986", "rice")
        with mock.patch("services.weather_client.requests.get") as get:
            get.return_value.json.return_value = {
                "current": {"temperature_2m": 28.1, "precipitation": 0.0, "time": "t"},
                "hourly": {"soil_moisture_0_to_1cm": [None, 0.31]},
            }
            weather = WeatherClient().get_weather(plot.latitude, plot.longitude)
        self.assertEqual(weather["soil_moisture"], 0.31)


class TestWeatherClient(unittest.TestCase):
    def _fake(self, payload):
        resp = mock.Mock()
        resp.json.return_value = payload
        return mock.patch("services.weather_client.requests.get", return_value=resp)

    def test_ok(self):
        payload = {"current": {"temperature_2m": 30, "precipitation": 0.2, "time": "t"},
                   "hourly": {"soil_moisture_0_to_1cm": [0.25]}}
        with self._fake(payload):
            self.assertEqual(WeatherClient().get_weather(9, 7)["temperature"], 30)

    def test_bad_coordinates(self):
        for lat, lon in (("x", 1), (95, 1), (1, 200)):
            with self.assertRaises(ValueError):
                WeatherClient().get_weather(lat, lon)

    def test_network_failures_become_runtime_errors(self):
        for exc in (requests.exceptions.Timeout(), requests.exceptions.ConnectionError()):
            with mock.patch("services.weather_client.requests.get", side_effect=exc):
                with self.assertRaises(RuntimeError):
                    WeatherClient().get_weather(9, 7)

    def test_missing_data_becomes_runtime_error(self):
        with self._fake({"current": {}, "hourly": {}}):
            with self.assertRaises(RuntimeError):
                WeatherClient().get_weather(9, 7)


class TestRiskAlerts(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(weather_warnings(GOOD_WEATHER)[0][0], "info")
        levels = dict(weather_warnings({"temperature": 38, "rainfall": 9, "soil_moisture": 0.05}))
        self.assertIn("error", levels)
        self.assertEqual(weather_warnings(None), [])


class TestGeminiClientSetup(unittest.TestCase):
    def test_missing_key_raises_value_error(self):
        from services.gemini_client import GeminiClient
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GEMINI_API_KEY", None)
            with mock.patch("services.gemini_client.os.getenv", return_value=None):
                with self.assertRaises(ValueError):
                    GeminiClient()


try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover
    AppTest = None

APP = str(Path(__file__).resolve().parent.parent / "app.py")
SECTIONS = ["Dashboard", "Farm Details", "Crop Selection", "Weather Information",
            "Planting Calendar", "AI Farming Advisor", "Pest & Weather Warnings", "Farm Logs"]


@unittest.skipIf(AppTest is None, "streamlit not installed")
class TestApp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["FARM_DATA_FILE"] = str(Path(self._tmp.name) / "farm.json")
        os.environ.pop("GEMINI_API_KEY", None)

    def tearDown(self):
        os.environ.pop("FARM_DATA_FILE", None)
        self._tmp.cleanup()

    def _app(self):
        at = AppTest.from_file(APP, default_timeout=30)
        at.run()
        return at

    def test_every_section_renders_empty(self):
        at = self._app()
        for section in SECTIONS:
            at.sidebar.selectbox[0].select(section).run()
            self.assertEqual(len(at.exception), 0, f"{section}: {[e.value for e in at.exception]}")

    def test_register_plot_then_all_sections(self):
        at = self._app()
        at.sidebar.selectbox[0].select("Farm Details").run()
        at.text_input[0].set_value("North Field")
        at.text_input[1].set_value("Lafia")
        at.text_input[2].set_value("8.49, 8.52")
        at.text_input[3].set_value("15/03/2026")
        at.button[0].click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("Saved plot" in s.value for s in at.success), [e.value for e in at.error])

        for section in SECTIONS:
            at.sidebar.selectbox[0].select(section).run()
            self.assertEqual(len(at.exception), 0, f"{section}: {[e.value for e in at.exception]}")

    def test_bad_coordinates_show_friendly_error(self):
        at = self._app()
        at.sidebar.selectbox[0].select("Farm Details").run()
        at.text_input[0].set_value("North Field")
        at.text_input[1].set_value("Lafia")
        at.text_input[2].set_value("999, 8.5")
        at.button[0].click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("latitude" in e.value.lower() for e in at.error))

    def test_calendar_generation(self):
        at = self._app()
        at.sidebar.selectbox[0].select("Farm Details").run()
        for i, v in enumerate(["North Field", "Lafia", "8.49, 8.52", "15/03/2026"]):
            at.text_input[i].set_value(v)
        at.button[0].click().run()
        at.sidebar.selectbox[0].select("Planting Calendar").run()
        gen = [b for b in at.button if b.label == "Generate season schedule"]
        self.assertTrue(gen, "generate button missing")
        gen[0].click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("Harvest" in c.label for c in at.checkbox))

    def test_weather_failure_is_handled(self):
        at = self._app()
        at.sidebar.selectbox[0].select("Farm Details").run()
        for i, v in enumerate(["North Field", "Lafia", "8.49, 8.52"]):
            at.text_input[i].set_value(v)
        at.button[0].click().run()
        with mock.patch("services.weather_client.requests.get",
                        side_effect=requests.exceptions.ConnectionError()):
            at.sidebar.selectbox[0].select("Weather Information").run()
            at.button[0].click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("Could not get weather" in e.value for e in at.error))


if __name__ == "__main__":
    unittest.main()
