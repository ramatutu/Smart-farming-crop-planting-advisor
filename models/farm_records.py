"""Plain data records saved by FarmLogStore.

Kept separate from models/crop.py (Yung parly's file) so the two branches
never touch the same file.
"""
from dataclasses import dataclass, asdict, fields
from typing import Optional

ACTIVITY_TYPES = (
    "planting", "weeding", "irrigation", "fertilizing",
    "spraying", "pruning", "harvesting", "other",
)


class _Record:
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        known = {f.name for f in fields(cls)}  # ignore unknown keys -> forward compatible
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class FarmPlot(_Record):
    plot_id: str
    name: str
    location: str
    latitude: float
    longitude: float
    crop: str
    planting_date: Optional[str] = None      # ISO date
    area_hectares: Optional[float] = None
    created_at: str = ""


@dataclass
class ActivityLog(_Record):
    log_id: str
    plot_id: str
    activity_type: str
    date: str                                 # ISO date
    notes: str = ""
    created_at: str = ""


@dataclass
class CalendarEvent(_Record):
    event_id: str
    plot_id: str
    title: str
    date: str                                 # ISO date
    event_type: str = "task"
    reminder: bool = True
    done: bool = False
