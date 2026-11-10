"""Regex-based input validation (Ramatu's module).

Every validator returns a cleaned/normalised value or raises ValidationError
with a message that is safe to show directly in the UI.
"""
import re
from datetime import date, datetime


class ValidationError(ValueError):
    """Raised when user input fails validation."""


# --- Compiled patterns -------------------------------------------------------
# Latitude: -90..90, Longitude: -180..180, optional decimals.
LAT_RE = re.compile(r"^[+-]?(?:90(?:\.0+)?|[1-8]?\d(?:\.\d+)?)$")
LON_RE = re.compile(r"^[+-]?(?:180(?:\.0+)?|1[0-7]\d(?:\.\d+)?|[1-9]?\d(?:\.\d+)?)$")
# "8.5, 7.1"  /  "8.5 7.1"  /  "8.5;7.1"
COORD_PAIR_RE = re.compile(
    r"^\s*([+-]?\d{1,3}(?:\.\d+)?)\s*(?:,|;|\s)\s*([+-]?\d{1,3}(?:\.\d+)?)\s*$"
)
# Place names: start with a letter, then letters/spaces/. , ' -  (2-100 chars)
LOCATION_RE = re.compile(r"^(?=.{2,100}$)[^\W\d_](?:[^\W\d_]|[\s.,'\-])*$")
# Plot names may contain digits and '#': "Plot #3 - North Field"
PLOT_NAME_RE = re.compile(r"^(?=.{2,60}$)\w(?:[\w\s.,'#\-])*$")
CROP_RE = re.compile(r"^(?=.{2,40}$)[^\W\d_](?:[^\W\d_]|[\s'\-])*$")
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
DAY_FIRST_DATE_RE = re.compile(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})$")
NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _clean(value) -> str:
    return "" if value is None else str(value).strip()


def validate_latitude(value) -> float:
    text = _clean(value)
    if not LAT_RE.match(text):
        raise ValidationError(f"Invalid latitude '{text}'. Use a number from -90 to 90.")
    return float(text)


def validate_longitude(value) -> float:
    text = _clean(value)
    if not LON_RE.match(text):
        raise ValidationError(f"Invalid longitude '{text}'. Use a number from -180 to 180.")
    return float(text)


def parse_coordinates(text) -> tuple[float, float]:
    """Parse 'lat, lon' typed into a single box -> (lat, lon)."""
    match = COORD_PAIR_RE.match(_clean(text))
    if not match:
        raise ValidationError("Coordinates must look like '8.5, 7.1' (latitude, longitude).")
    return validate_latitude(match.group(1)), validate_longitude(match.group(2))


def validate_location(value) -> str:
    text = re.sub(r"\s+", " ", _clean(value))
    if not LOCATION_RE.match(text):
        raise ValidationError(
            "Location must be 2-100 characters, start with a letter, and contain "
            "only letters, spaces, and . , ' -"
        )
    return text


def validate_plot_name(value) -> str:
    text = re.sub(r"\s+", " ", _clean(value))
    if not PLOT_NAME_RE.match(text):
        raise ValidationError("Plot name must be 2-60 characters (letters, digits, spaces, . , ' # -).")
    return text


def validate_crop_name(value) -> str:
    text = re.sub(r"\s+", " ", _clean(value))
    if not CROP_RE.match(text):
        raise ValidationError("Crop name must be 2-40 letters (e.g. 'maize', 'cassava').")
    return text.lower()


def parse_date(value) -> date:
    """Accept YYYY-MM-DD or DD/MM/YYYY (also - or .). Rejects impossible dates."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _clean(value)
    iso = ISO_DATE_RE.match(text)
    dfirst = DAY_FIRST_DATE_RE.match(text)
    if not (iso or dfirst):
        raise ValidationError("Date must look like 2026-03-15 or 15/03/2026.")
    try:
        if iso:
            y, m, d = map(int, iso.groups())
        else:
            d, m, y = map(int, dfirst.groups())
        return date(y, m, d)
    except ValueError:  # e.g. 31/02/2026
        raise ValidationError(f"'{text}' is not a real calendar date.") from None


def validate_date(value) -> str:
    """Return the date normalised to ISO format (YYYY-MM-DD)."""
    return parse_date(value).isoformat()


def validate_positive_number(value, field: str = "Value") -> float:
    text = _clean(value)
    if not re.fullmatch(r"\d+(?:\.\d+)?", text) or float(text) <= 0:
        raise ValidationError(f"{field} must be a positive number.")
    return float(text)


def extract_numbers(text: str) -> list[float]:
    """Pull raw numbers out of unstructured text, e.g. AI output like
    'Irrigate 25 mm, temp 31.5C' -> [25.0, 31.5]."""
    return [float(n) for n in NUMBER_RE.findall(text or "")]
