# Smart Farming & Crop Planting Advisor

Streamlit app that tracks farm plots, fetches live weather (Open-Meteo), checks
conditions against crop rules, and asks Gemini for planting advice.

## Run it (PowerShell)

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    copy .env.example .env        # then put your GEMINI_API_KEY in .env
    streamlit run app.py

The app works without a Gemini key (you just won't get the AI advice section).
Farm data is saved to `data/farm_data.json`.

## Run the tests

    python -m unittest discover -s tests -t . -v

## Layout

    app.py                       UI (Malibigad)
    models/crop.py               Crop class + crop database (Yung parly)
    models/farm_records.py       FarmPlot / ActivityLog / CalendarEvent (Ramatu)
    services/weather_client.py   Open-Meteo client (Saeed)
    services/planting_advisor.py Condition checks + Gemini prompt (Yung parly)
    services/gemini_client.py    Gemini wrapper (Yung parly)
    services/farm_log_store.py   JSON/CSV persistence (Ramatu)
    services/risk_alerts.py      Weather warnings (added during integration)
    utils/validators.py          Regex validation (Ramatu)
    tests/                       unit + integration + UI tests

## Known limits

- Weather is the current reading only (no forecast), so "alerts" describe
  conditions right now, not approaching storms.
- Crop temperature/rainfall/soil-moisture ranges in `models/crop.py` are
  starting values and should be reviewed by the team.
- Season and budget on the Crop Selection page are collected but not yet used.
