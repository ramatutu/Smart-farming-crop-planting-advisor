"""FarmLogStore - saves/loads farm plots, activity logs and season calendars.

Storage: one JSON file (default data/farm_data.json), written atomically so a
crash mid-save can never corrupt it. CSV export is provided for logs/plots/calendar.

Typical use (from the UI):
    store = FarmLogStore()
    plot = store.add_plot("North Field", "Lafia", "8.49, 8.52", "Maize", "15/03/2026")
    store.add_log(plot.plot_id, "weeding", "2026-04-05", "First weeding done")
    store.generate_season_schedule(plot.plot_id, [("Weeding", 21), ("Harvest", 100)])
"""
import csv
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from models.farm_records import ACTIVITY_TYPES, ActivityLog, CalendarEvent, FarmPlot
from utils.validators import (
    ValidationError,
    parse_coordinates,
    parse_date,
    validate_crop_name,
    validate_date,
    validate_location,
    validate_plot_name,
    validate_positive_number,
)

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1


class StorageError(Exception):
    """Raised when the data file cannot be read or written."""


class FarmLogStore:
    def __init__(self, data_file: str | os.PathLike = "data/farm_data.json"):
        self.data_file = Path(data_file)
        self._plots: dict[str, FarmPlot] = {}
        self._logs: dict[str, ActivityLog] = {}
        self._events: dict[str, CalendarEvent] = {}
        self.load()

    # ------------------------------------------------------------------ I/O
    def load(self) -> None:
        """Load from disk. A missing file means a fresh start; a corrupt file is
        moved aside (.corrupt) so the app keeps running and nothing is lost."""
        self._plots, self._logs, self._events = {}, {}, {}
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self._plots = {p["plot_id"]: FarmPlot.from_dict(p) for p in raw.get("plots", [])}
            self._logs = {l["log_id"]: ActivityLog.from_dict(l) for l in raw.get("logs", [])}
            self._events = {e["event_id"]: CalendarEvent.from_dict(e) for e in raw.get("calendar", [])}
        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
            backup = self.data_file.with_suffix(".corrupt")
            try:
                os.replace(self.data_file, backup)
            except OSError:
                pass
            self._plots, self._logs, self._events = {}, {}, {}
            log.warning("Data file was unreadable (%s). Moved to %s; starting fresh.", exc, backup)
        except OSError as exc:
            raise StorageError(f"Could not read {self.data_file}: {exc}") from exc

    def save(self) -> None:
        """Atomic write: dump to a temp file in the same folder, then replace."""
        payload = {
            "version": SCHEMA_VERSION,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "plots": [p.to_dict() for p in self._plots.values()],
            "logs": [l.to_dict() for l in self._logs.values()],
            "calendar": [e.to_dict() for e in self._events.values()],
        }
        tmp_path = None
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=self.data_file.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.data_file)
        except OSError as exc:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise StorageError(f"Could not save to {self.data_file}: {exc}") from exc

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex[:8]

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    # ---------------------------------------------------------------- plots
    def add_plot(self, name, location, coordinates, crop,
                 planting_date=None, area_hectares=None) -> FarmPlot:
        """`coordinates` may be 'lat, lon' text or a (lat, lon) tuple."""
        name = validate_plot_name(name)
        if any(p.name.lower() == name.lower() for p in self._plots.values()):
            raise ValidationError(f"A plot named '{name}' already exists.")
        lat, lon = (parse_coordinates(coordinates) if isinstance(coordinates, str)
                    else parse_coordinates(f"{coordinates[0]}, {coordinates[1]}"))
        plot = FarmPlot(
            plot_id=self._new_id(),
            name=name,
            location=validate_location(location),
            latitude=lat,
            longitude=lon,
            crop=validate_crop_name(crop),
            planting_date=validate_date(planting_date) if planting_date else None,
            area_hectares=(validate_positive_number(area_hectares, "Area")
                           if area_hectares not in (None, "") else None),
            created_at=self._now(),
        )
        self._plots[plot.plot_id] = plot
        self.save()
        return plot

    def get_plot(self, plot_id: str) -> FarmPlot:
        try:
            return self._plots[plot_id]
        except KeyError:
            raise KeyError(f"No plot with id '{plot_id}'.") from None

    def list_plots(self) -> list[FarmPlot]:
        return sorted(self._plots.values(), key=lambda p: p.created_at)

    def update_plot(self, plot_id: str, **changes) -> FarmPlot:
        """Update any of: name, location, coordinates, crop, planting_date, area_hectares."""
        plot = self.get_plot(plot_id)
        if "name" in changes:
            new_name = validate_plot_name(changes["name"])
            if any(p.name.lower() == new_name.lower() and p.plot_id != plot_id
                   for p in self._plots.values()):
                raise ValidationError(f"A plot named '{new_name}' already exists.")
            plot.name = new_name
        if "location" in changes:
            plot.location = validate_location(changes["location"])
        if "coordinates" in changes:
            plot.latitude, plot.longitude = parse_coordinates(changes["coordinates"])
        if "crop" in changes:
            plot.crop = validate_crop_name(changes["crop"])
        if "planting_date" in changes:
            value = changes["planting_date"]
            plot.planting_date = validate_date(value) if value else None
        if "area_hectares" in changes:
            value = changes["area_hectares"]
            plot.area_hectares = (validate_positive_number(value, "Area")
                                  if value not in (None, "") else None)
        self.save()
        return plot

    def delete_plot(self, plot_id: str) -> None:
        """Deletes the plot and everything attached to it (logs + calendar)."""
        self.get_plot(plot_id)
        del self._plots[plot_id]
        self._logs = {k: v for k, v in self._logs.items() if v.plot_id != plot_id}
        self._events = {k: v for k, v in self._events.items() if v.plot_id != plot_id}
        self.save()

    # ----------------------------------------------------------------- logs
    def add_log(self, plot_id: str, activity_type: str, date, notes: str = "") -> ActivityLog:
        self.get_plot(plot_id)
        activity = str(activity_type).strip().lower()
        if activity not in ACTIVITY_TYPES:
            raise ValidationError(f"Activity must be one of: {', '.join(ACTIVITY_TYPES)}.")
        entry = ActivityLog(
            log_id=self._new_id(),
            plot_id=plot_id,
            activity_type=activity,
            date=validate_date(date),
            notes=(notes or "").strip()[:1000],
            created_at=self._now(),
        )
        self._logs[entry.log_id] = entry
        # Logging a planting activity also records the plot's planting date.
        if activity == "planting":
            self._plots[plot_id].planting_date = entry.date
        self.save()
        return entry

    def list_logs(self, plot_id: Optional[str] = None,
                  activity_type: Optional[str] = None) -> list[ActivityLog]:
        logs = [l for l in self._logs.values()
                if (plot_id is None or l.plot_id == plot_id)
                and (activity_type is None or l.activity_type == activity_type)]
        return sorted(logs, key=lambda l: (l.date, l.created_at), reverse=True)

    def delete_log(self, log_id: str) -> None:
        if log_id not in self._logs:
            raise KeyError(f"No log with id '{log_id}'.")
        del self._logs[log_id]
        self.save()

    # ------------------------------------------------------------- calendar
    def add_event(self, plot_id: str, title: str, date,
                  event_type: str = "task", reminder: bool = True) -> CalendarEvent:
        self.get_plot(plot_id)
        title = (title or "").strip()
        if not title:
            raise ValidationError("Event title cannot be empty.")
        event = CalendarEvent(self._new_id(), plot_id, title[:120],
                              validate_date(date), event_type, bool(reminder))
        self._events[event.event_id] = event
        self.save()
        return event

    def generate_season_schedule(self, plot_id: str,
                                 stages: Iterable[tuple[str, int]]) -> list[CalendarEvent]:
        """Build a season calendar from the plot's planting date.

        `stages` is a list of (title, days_after_planting), e.g. taken from the
        Crop class: [("First weeding", 21), ("Fertilise", 35), ("Harvest", 100)].
        Re-running replaces earlier auto-generated events for that plot.
        """
        plot = self.get_plot(plot_id)
        if not plot.planting_date:
            raise ValidationError("Set a planting date for this plot before generating a schedule.")
        start = parse_date(plot.planting_date)
        self._events = {k: v for k, v in self._events.items()
                        if not (v.plot_id == plot_id and v.event_type == "scheduled")}
        created = []
        for title, offset in stages:
            if not isinstance(offset, int) or offset < 0:
                raise ValidationError(f"Day offset for '{title}' must be a whole number >= 0.")
            ev = CalendarEvent(self._new_id(), plot_id, str(title).strip(),
                               (start + timedelta(days=offset)).isoformat(),
                               event_type="scheduled", reminder=True)
            self._events[ev.event_id] = ev
            created.append(ev)
        self.save()
        return sorted(created, key=lambda e: e.date)

    def list_events(self, plot_id: Optional[str] = None,
                    from_date=None, include_done: bool = True) -> list[CalendarEvent]:
        cutoff = validate_date(from_date) if from_date else None
        events = [e for e in self._events.values()
                  if (plot_id is None or e.plot_id == plot_id)
                  and (cutoff is None or e.date >= cutoff)
                  and (include_done or not e.done)]
        return sorted(events, key=lambda e: e.date)

    def due_reminders(self, today=None, days_ahead: int = 3) -> list[CalendarEvent]:
        """Pending reminder events due from today up to `days_ahead` days out."""
        day = parse_date(today) if today else datetime.now().date()
        start, end = day.isoformat(), (day + timedelta(days=days_ahead)).isoformat()
        return [e for e in self.list_events(include_done=False)
                if e.reminder and start <= e.date <= end]

    def mark_event_done(self, event_id: str, done: bool = True) -> CalendarEvent:
        if event_id not in self._events:
            raise KeyError(f"No event with id '{event_id}'.")
        self._events[event_id].done = done
        self.save()
        return self._events[event_id]

    def delete_event(self, event_id: str) -> None:
        if event_id not in self._events:
            raise KeyError(f"No event with id '{event_id}'.")
        del self._events[event_id]
        self.save()

    # ------------------------------------------------------------ CSV export
    def _export_csv(self, path, rows: list[dict], columns: list[str]) -> Path:
        path = Path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as exc:
            raise StorageError(f"Could not write {path}: {exc}") from exc
        return path

    def export_logs_csv(self, path="data/activity_logs.csv", plot_id: Optional[str] = None) -> Path:
        names = {p.plot_id: p.name for p in self._plots.values()}
        rows = [{"date": l.date, "plot": names.get(l.plot_id, "?"), "activity": l.activity_type,
                 "notes": l.notes} for l in reversed(self.list_logs(plot_id))]
        return self._export_csv(path, rows, ["date", "plot", "activity", "notes"])

    def export_plots_csv(self, path="data/plots.csv") -> Path:
        cols = ["plot_id", "name", "location", "latitude", "longitude",
                "crop", "planting_date", "area_hectares"]
        rows = [{c: getattr(p, c) for c in cols} for p in self.list_plots()]
        return self._export_csv(path, rows, cols)

    def export_calendar_csv(self, path="data/season_calendar.csv",
                            plot_id: Optional[str] = None) -> Path:
        names = {p.plot_id: p.name for p in self._plots.values()}
        rows = [{"date": e.date, "plot": names.get(e.plot_id, "?"), "title": e.title,
                 "type": e.event_type, "done": e.done} for e in self.list_events(plot_id)]
        return self._export_csv(path, rows, ["date", "plot", "title", "type", "done"])
