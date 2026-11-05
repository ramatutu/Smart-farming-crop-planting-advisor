import json
import tempfile
import unittest
from pathlib import Path

from services.farm_log_store import FarmLogStore
from utils.validators import (ValidationError, extract_numbers, parse_coordinates,
                              validate_date, validate_latitude, validate_longitude,
                              validate_location)


class TestValidators(unittest.TestCase):
    def test_latitude_longitude(self):
        self.assertEqual(validate_latitude("8.49"), 8.49)
        self.assertEqual(validate_latitude("-90"), -90.0)
        self.assertEqual(validate_longitude("180"), 180.0)
        self.assertEqual(validate_longitude("-122.4"), -122.4)
        for bad in ("91", "90.5", "abc", "", "8.", "--5"):
            with self.assertRaises(ValidationError):
                validate_latitude(bad)
        for bad in ("181", "180.1", "x", "1e5"):
            with self.assertRaises(ValidationError):
                validate_longitude(bad)

    def test_coordinate_pair(self):
        self.assertEqual(parse_coordinates("8.5, 7.1"), (8.5, 7.1))
        self.assertEqual(parse_coordinates("8.5 7.1"), (8.5, 7.1))
        self.assertEqual(parse_coordinates("-33.9;18.4"), (-33.9, 18.4))
        for bad in ("8.5", "95, 7", "8.5, 200", "hello"):
            with self.assertRaises(ValidationError):
                parse_coordinates(bad)

    def test_location(self):
        self.assertEqual(validate_location("  Lafia,   Nasarawa "), "Lafia, Nasarawa")
        for bad in ("", "1234", "L", "<script>"):
            with self.assertRaises(ValidationError):
                validate_location(bad)

    def test_dates(self):
        self.assertEqual(validate_date("2026-03-15"), "2026-03-15")
        self.assertEqual(validate_date("15/03/2026"), "2026-03-15")
        for bad in ("2026-02-30", "31/02/2026", "March 5", "2026/03/15", ""):
            with self.assertRaises(ValidationError):
                validate_date(bad)

    def test_extract_numbers(self):
        self.assertEqual(extract_numbers("Irrigate 25 mm, temp 31.5C, low -2"), [25.0, 31.5, -2.0])
        self.assertEqual(extract_numbers(""), [])


class TestFarmLogStore(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "farm.json"
        self.store = FarmLogStore(self.path)
        self.plot = self.store.add_plot("North Field", "Lafia", "8.49, 8.52", "Maize", "15/03/2026", "2.5")

    def tearDown(self):
        self._tmp.cleanup()

    def test_persistence_roundtrip(self):
        self.store.add_log(self.plot.plot_id, "weeding", "2026-04-05", "first pass")
        reloaded = FarmLogStore(self.path)
        self.assertEqual(len(reloaded.list_plots()), 1)
        p = reloaded.list_plots()[0]
        self.assertEqual((p.crop, p.planting_date, p.area_hectares), ("maize", "2026-03-15", 2.5))
        self.assertEqual(reloaded.list_logs()[0].notes, "first pass")

    def test_duplicate_and_invalid_plot(self):
        with self.assertRaises(ValidationError):
            self.store.add_plot("north field", "Lafia", "8.5, 8.5", "rice")
        with self.assertRaises(ValidationError):
            self.store.add_plot("Other", "Lafia", "999, 8.5", "rice")
        self.assertEqual(len(self.store.list_plots()), 1)

    def test_invalid_activity(self):
        with self.assertRaises(ValidationError):
            self.store.add_log(self.plot.plot_id, "dancing", "2026-04-05")
        with self.assertRaises(KeyError):
            self.store.add_log("nope", "weeding", "2026-04-05")

    def test_planting_log_sets_planting_date(self):
        self.store.add_log(self.plot.plot_id, "planting", "2026-05-01")
        self.assertEqual(self.store.get_plot(self.plot.plot_id).planting_date, "2026-05-01")

    def test_schedule_and_reminders(self):
        events = self.store.generate_season_schedule(
            self.plot.plot_id, [("Weeding", 21), ("Fertilise", 35), ("Harvest", 100)])
        self.assertEqual([e.date for e in events], ["2026-04-05", "2026-04-19", "2026-06-23"])
        # regenerating replaces, not duplicates
        self.store.generate_season_schedule(self.plot.plot_id, [("Weeding", 21)])
        self.assertEqual(len(self.store.list_events(self.plot.plot_id)), 1)
        due = self.store.due_reminders(today="2026-04-03", days_ahead=3)
        self.assertEqual([e.title for e in due], ["Weeding"])
        self.store.mark_event_done(due[0].event_id)
        self.assertEqual(self.store.due_reminders(today="2026-04-03"), [])

    def test_schedule_requires_planting_date(self):
        p = self.store.add_plot("South", "Lafia", "8.4, 8.5", "cassava")
        with self.assertRaises(ValidationError):
            self.store.generate_season_schedule(p.plot_id, [("Harvest", 90)])

    def test_delete_plot_cascades(self):
        self.store.add_log(self.plot.plot_id, "weeding", "2026-04-05")
        self.store.add_event(self.plot.plot_id, "Spray", "2026-04-10")
        self.store.delete_plot(self.plot.plot_id)
        reloaded = FarmLogStore(self.path)
        self.assertEqual((reloaded.list_plots(), reloaded.list_logs(), reloaded.list_events()), ([], [], []))

    def test_corrupt_file_recovers(self):
        self.path.write_text("{ not valid json", encoding="utf-8")
        store = FarmLogStore(self.path)
        self.assertEqual(store.list_plots(), [])
        self.assertTrue(self.path.with_suffix(".corrupt").exists())
        store.add_plot("Fresh", "Lafia", "8.4, 8.5", "rice")  # still usable
        self.assertEqual(len(FarmLogStore(self.path).list_plots()), 1)

    def test_update_plot(self):
        self.store.update_plot(self.plot.plot_id, crop="Rice", coordinates="9.0, 8.0")
        p = FarmLogStore(self.path).get_plot(self.plot.plot_id)
        self.assertEqual((p.crop, p.latitude, p.longitude), ("rice", 9.0, 8.0))

    def test_csv_export(self):
        self.store.add_log(self.plot.plot_id, "weeding", "2026-04-05", "note, with comma")
        out = self.store.export_logs_csv(Path(self._tmp.name) / "logs.csv")
        text = out.read_text(encoding="utf-8")
        self.assertIn("date,plot,activity,notes", text)
        self.assertIn('"note, with comma"', text)


if __name__ == "__main__":
    unittest.main()
