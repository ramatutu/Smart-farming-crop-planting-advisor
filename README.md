# feature/data-store (Ramatu)

Files in this branch:
- `utils/validators.py`        regex validation (coordinates, location, plot/crop names, dates, number extraction)
- `models/farm_records.py`     FarmPlot, ActivityLog, CalendarEvent dataclasses
- `services/farm_log_store.py` FarmLogStore (JSON persistence, CSV export, season calendar)
- `tests/test_data_store.py`   15 unit tests

Run tests (PowerShell, from the repo root):
    python -m unittest discover -s tests -t . -v

Git (PowerShell):
    git checkout -b feature/data-store
    git add .
    git commit -m "Add FarmLogStore and regex validators"
    git push -u origin feature/data-store   # then open a PR into main

## How the other teammates use it
```python
from services.farm_log_store import FarmLogStore, StorageError
from utils.validators import ValidationError, parse_coordinates, extract_numbers

store = FarmLogStore()                        # loads data/farm_data.json
plot = store.add_plot("North Field", "Lafia", "8.49, 8.52", "Maize", "15/03/2026")
store.add_log(plot.plot_id, "weeding", "2026-04-05", "First weeding")

# Yung parly's Crop class can feed the schedule:
store.generate_season_schedule(plot.plot_id, [("Weeding", 21), ("Harvest", 100)])

# Malibigad (UI): catch ValidationError and show str(e) to the user
try:
    store.add_plot(name, location, coords_text, crop, date_text)
except ValidationError as e:
    show_error(str(e))

# Saeed (WeatherClient) needs lat/lon:  plot.latitude, plot.longitude
```
