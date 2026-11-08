"""Smart Farming & Crop Planting Advisor - Streamlit UI.

Integrated version: wires the UI to
    FarmLogStore - plots, logs, season calendar, validation
    WeatherClient - Open-Meteo weather
    Crop / PlantingAdvisor / GeminiClient - crop rules + AI advice

Run with:  streamlit run app.py
"""
import os
from datetime import date
from pathlib import Path

import streamlit as st

from models.crop import CROP_DATABASE, get_crop, list_crop_names, recommend_crops
from models.farm_records import ACTIVITY_TYPES
from services.farm_log_store import FarmLogStore, StorageError
from services.planting_advisor import PlantingAdvisor
from services.risk_alerts import weather_warnings
from services.weather_client import WeatherClient
from utils.validators import ValidationError

DATA_FILE = os.getenv("FARM_DATA_FILE") or str(Path(__file__).parent / "data" / "farm_data.json")

# ---------------------------------------------------------------- page setup
st.set_page_config(page_title="Smart Farming Advisor", page_icon="🌱", layout="wide")


# ------------------------------------------------------------------- helpers
def get_store() -> FarmLogStore:
    """One FarmLogStore per browser session (loads data/farm_data.json)."""
    if "store" not in st.session_state:
        st.session_state.store = FarmLogStore(DATA_FILE)
    return st.session_state.store


def get_weather_client() -> WeatherClient:
    if "weather_client" not in st.session_state:
        st.session_state.weather_client = WeatherClient()
    return st.session_state.weather_client


def get_gemini():
    """Return (GeminiClient or None, message). The app works without Gemini."""
    if "gemini" not in st.session_state:
        try:
            from services.gemini_client import GeminiClient
            st.session_state.gemini = (GeminiClient(), "")
        except ValueError:
            st.session_state.gemini = (None, "Add GEMINI_API_KEY to your .env file to enable AI advice.")
        except ImportError:
            st.session_state.gemini = (None, "Install the AI packages: pip install google-genai python-dotenv")
    return st.session_state.gemini


def select_plot(key: str):
    """Plot dropdown shared by several pages. Returns a FarmPlot or None."""
    plots = get_store().list_plots()
    if not plots:
        st.info("No farm plots yet. Add one under **Farm Details** first.")
        return None
    labels = {p.plot_id: f"{p.name}  ({p.crop.title()}, {p.location})" for p in plots}
    plot_id = st.selectbox("Select a plot", list(labels), format_func=labels.get, key=key)
    return get_store().get_plot(plot_id)


def fetch_weather(plot, force: bool = False):
    """Fetch (and remember) the weather for a plot. Returns dict or None."""
    cache = st.session_state.setdefault("weather", {})
    if plot.plot_id in cache and not force:
        return cache[plot.plot_id]
    try:
        with st.spinner("Fetching live weather..."):
            cache[plot.plot_id] = get_weather_client().get_weather(plot.latitude, plot.longitude)
    except (ValueError, RuntimeError) as exc:
        st.error(f"Could not get weather: {exc}")
        return None
    return cache[plot.plot_id]


def show_weather_metrics(weather):
    c1, c2, c3 = st.columns(3)
    c1.metric("Temperature", f"{weather['temperature']} °C")
    c2.metric("Rainfall (now)", f"{weather['rainfall']} mm")
    c3.metric("Soil moisture", f"{weather['soil_moisture']} m³/m³")
    st.caption(f"Reading time: {weather.get('time') or 'unknown'}")


def show_alert(level: str, message: str):
    {"error": st.error, "warning": st.warning}.get(level, st.info)(message)


def csv_download(label: str, writer, filename: str):
    """`writer(path)` writes a CSV; offer the file as a browser download."""
    path = Path(DATA_FILE).parent / filename
    try:
        writer(path)
        st.download_button(label, path.read_bytes(), file_name=filename, mime="text/csv")
    except StorageError as exc:
        st.error(str(exc))


# ------------------------------------------------------------------ title
st.title("🌱 Smart Farming & Crop Planting Advisor")
st.write(
    "Welcome to your intelligent farming assistant. "
    "Get crop information, planting advice and farm management support."
)
st.divider()

st.sidebar.title("Farm Navigation")
menu = st.sidebar.selectbox(
    "Select a Section",
    [
        "Dashboard",
        "Farm Details",
        "Crop Selection",
        "Weather Information",
        "Planting Calendar",
        "AI Farming Advisor",
        "Pest & Weather Warnings",
        "Farm Logs",
    ],
)

try:
    store = get_store()
except StorageError as exc:
    st.error(f"Could not open the farm data file: {exc}")
    st.stop()

# ---------------------------------------------------------------- Dashboard
if menu == "Dashboard":
    st.header("Farm Dashboard")
    plots = store.list_plots()
    reminders = store.due_reminders()

    col1, col2, col3 = st.columns(3)
    col1.metric("Farm Plots", len(plots))
    col2.metric("Available Crops", len(CROP_DATABASE))
    col3.metric("Tasks Due (next 3 days)", len(reminders))

    if reminders:
        st.subheader("Upcoming tasks")
        names = {p.plot_id: p.name for p in plots}
        for ev in reminders:
            st.warning(f"**{ev.date}** - {ev.title} ({names.get(ev.plot_id, '?')})")

    if plots:
        st.subheader("Your plots")
        st.dataframe(
            [{"Plot": p.name, "Crop": p.crop.title(), "Location": p.location,
              "Planting date": p.planting_date or "-", "Area (ha)": p.area_hectares or "-"}
             for p in plots],
            width="stretch", hide_index=True,
        )
    else:
        st.info("Use the navigation menu to add your first plot under **Farm Details**.")

# ------------------------------------------------------------- Farm Details
elif menu == "Farm Details":
    st.header("🌾 Farm Registration")

    with st.form("farm_form"):
        plot_name = st.text_input("Plot / Farm Name", placeholder="North Field")
        location = st.text_input("Farm Location (town or area)", placeholder="Lafia")
        coordinates = st.text_input(
            "Coordinates (latitude, longitude)", placeholder="8.49, 8.52",
            help="Used to fetch live weather for this plot.",
        )
        crop_name = st.selectbox("Crop", list_crop_names())
        planting_text = st.text_input(
            "Planting date (optional)", placeholder="15/03/2026 or 2026-03-15"
        )
        farm_size = st.number_input("Farm Size (hectares)", min_value=0.1, value=1.0)
        submitted = st.form_submit_button("Save Farm Details")

    if submitted:
        try:
            plot = store.add_plot(plot_name, location, coordinates, crop_name,
                                  planting_text or None, farm_size)
            st.success(f"Saved plot '{plot.name}'.")
        except ValidationError as exc:
            st.error(str(exc))
        except StorageError as exc:
            st.error(f"Could not save: {exc}")

    plots = store.list_plots()
    if plots:
        st.subheader("Saved Farm Information")
        for p in plots:
            st.write(
                f"**{p.name}** - {p.crop.title()} - {p.location} "
                f"({p.latitude}, {p.longitude}) - planted: {p.planting_date or 'not set'}"
            )
        with st.expander("Delete a plot"):
            doomed = select_plot("delete_plot")
            confirm = st.checkbox("Yes, delete this plot and all its logs and calendar events")
            if doomed and st.button("Delete plot") and confirm:
                try:
                    store.delete_plot(doomed.plot_id)
                    st.session_state.get("weather", {}).pop(doomed.plot_id, None)
                    st.rerun()
                except (KeyError, StorageError) as exc:
                    st.error(str(exc))

# ----------------------------------------------------------- Crop Selection
elif menu == "Crop Selection":
    st.header("🌱 Crop Recommendation")

    soil_type = st.selectbox("Select your soil type", ["Loamy", "Sandy", "Clay", "Silty"])
    season = st.selectbox("Select season", ["Rainy", "Dry", "Harmattan"])
    budget = st.selectbox("Your budget", ["Low", "Medium", "High"])
    st.caption("Season and budget are collected for future filtering; recommendations currently use soil type.")

    if st.button("Recommend Crops"):
        recommendations = recommend_crops(soil_type, season, budget)
        if recommendations:
            st.success("Recommended crops for you:")
            for rec in recommendations:
                st.write(f"✅ **{rec['crop']}** - {rec['description']} (Water need: {rec['water']})")
        else:
            st.warning(f"No crops in the database suit {soil_type} soil yet.")

# ------------------------------------------------------ Weather Information
elif menu == "Weather Information":
    st.header("🌦️ Weather Information")
    plot = select_plot("weather_plot")
    if plot:
        if st.button("Get Live Weather"):
            fetch_weather(plot, force=True)
        weather = st.session_state.get("weather", {}).get(plot.plot_id)
        if weather:
            show_weather_metrics(weather)
        else:
            st.info("Click **Get Live Weather** to load current conditions for this plot.")

# --------------------------------------------------------- Planting Calendar
elif menu == "Planting Calendar":
    st.header("Planting Calendar")
    plot = select_plot("calendar_plot")
    if plot:
        crop = get_crop(plot.crop)

        if not plot.planting_date:
            st.warning("This plot has no planting date yet.")
        planned = st.date_input(
            "Planned planting date",
            value=date.fromisoformat(plot.planting_date) if plot.planting_date else date.today(),
        )
        if st.button("Save planting date"):
            try:
                store.update_plot(plot.plot_id, planting_date=planned)
                st.success("Planting date saved.")
                st.rerun()
            except (ValidationError, StorageError) as exc:
                st.error(str(exc))

        if crop is None:
            st.warning(f"No schedule template for '{plot.crop}'.")
        elif plot.planting_date and st.button("Generate season schedule"):
            try:
                store.generate_season_schedule(plot.plot_id, crop.schedule_stages())
                st.success("Season schedule created.")
            except (ValidationError, StorageError) as exc:
                st.error(str(exc))

        events = store.list_events(plot.plot_id)
        if events:
            st.subheader("Season calendar")
            for ev in events:
                checked = st.checkbox(f"{ev.date} - {ev.title}", value=ev.done, key=f"ev_{ev.event_id}")
                if checked != ev.done:
                    try:
                        store.mark_event_done(ev.event_id, checked)
                        st.rerun()
                    except (KeyError, StorageError) as exc:
                        st.error(str(exc))
            csv_download("Download calendar (CSV)",
                         lambda path: store.export_calendar_csv(path, plot.plot_id),
                         "season_calendar.csv")

# -------------------------------------------------------- AI Farming Advisor
elif menu == "AI Farming Advisor":
    st.header("AI Farming Recommendations")
    plot = select_plot("advisor_plot")
    if plot:
        crop = get_crop(plot.crop)
        if crop is None:
            st.warning(f"No crop rules for '{plot.crop}' yet, so the advisor can't analyse it.")
        else:
            weather = fetch_weather(plot)
            if weather:
                show_weather_metrics(weather)
                gemini, gemini_msg = get_gemini()
                advisor = PlantingAdvisor(crop, weather, gemini)

                st.subheader("Condition check")
                st.write(f"- {advisor.analyze_temperature()}")
                st.write(f"- {advisor.analyze_rainfall()}")
                st.write(f"- {advisor.analyze_soil_moisture()}")
                st.write(f"- {advisor.analyze_overall_conditions()}")

                if gemini is None:
                    st.info(gemini_msg)
                elif st.button("Get AI Planting Advice"):
                    with st.spinner("Asking the AI advisor..."):
                        st.session_state[f"advice_{plot.plot_id}"] = advisor.generate_ai_recommendation()
                advice = st.session_state.get(f"advice_{plot.plot_id}")
                if advice:
                    st.subheader("AI advice")
                    st.write(advice)
                    if gemini is not None and gemini.last_error:
                        with st.expander("Technical details (for debugging)"):
                            st.code(gemini.last_error, language=None)

# -------------------------------------------------- Pest & Weather Warnings
elif menu == "Pest & Weather Warnings":
    st.header("Farm Alerts")
    plot = select_plot("warning_plot")
    if plot:
        weather = fetch_weather(plot)
        if weather:
            st.subheader("Weather warnings")
            for level, message in weather_warnings(weather):
                show_alert(level, message)

            crop = get_crop(plot.crop)
            st.subheader("Pest and disease risk")
            if crop is None:
                st.warning(f"No crop rules for '{plot.crop}' yet.")
            else:
                st.code(PlantingAdvisor(crop, weather).analyze_pest_and_disease_risk(), language=None)

# ---------------------------------------------------------------- Farm Logs
elif menu == "Farm Logs":
    st.header("Farm Activity Logs")
    plot = select_plot("logs_plot")
    if plot:
        with st.form("log_form"):
            activity = st.selectbox("Activity", ACTIVITY_TYPES)
            when = st.date_input("Date", value=date.today())
            notes = st.text_area("Notes (optional)")
            saved = st.form_submit_button("Save Activity")
        if saved:
            try:
                store.add_log(plot.plot_id, activity, when, notes)
                st.success("Farm activity recorded!")
            except (ValidationError, KeyError, StorageError) as exc:
                st.error(str(exc))

        logs = store.list_logs(plot.plot_id)
        if logs:
            st.subheader("History")
            st.dataframe(
                [{"Date": l.date, "Activity": l.activity_type, "Notes": l.notes} for l in logs],
                width="stretch", hide_index=True,
            )
            csv_download("Download logs (CSV)",
                         lambda path: store.export_logs_csv(path, plot.plot_id),
                         "activity_logs.csv")
        else:
            st.info("No activities logged for this plot yet.")

# ------------------------------------------------------------------ footer
st.divider()
st.caption("Smart Farming & Crop Planting Advisor | Developed by the UI & Frontend Team")
