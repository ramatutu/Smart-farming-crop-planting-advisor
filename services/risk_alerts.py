"""Simple weather-risk alerts built from WeatherClient output.

WeatherClient currently returns the CURRENT reading only (no forecast), so
these are "conditions right now" alerts, not forecasts of approaching weather.
Thresholds are named constants so the team can tune them.
"""
HEAT_WARNING_C = 32.0
HEAT_DANGER_C = 35.0
HEAVY_RAIN_MM = 7.5       # roughly "heavy rain" per hour
MODERATE_RAIN_MM = 2.5
DRY_SOIL_M3M3 = 0.10      # very dry topsoil
SATURATED_SOIL_M3M3 = 0.45


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def weather_warnings(weather) -> list:
    """Return a list of (level, message); level is 'error', 'warning' or 'info'."""
    if not weather:
        return []
    alerts = []
    temp = _num(weather.get("temperature"))
    rain = _num(weather.get("rainfall"))
    moisture = _num(weather.get("soil_moisture"))

    if temp is not None:
        if temp >= HEAT_DANGER_C:
            alerts.append(("error", f"Extreme heat ({temp:.1f} °C). Protect seedlings and irrigate early or late in the day."))
        elif temp >= HEAT_WARNING_C:
            alerts.append(("warning", f"Hot conditions ({temp:.1f} °C). Watch for heat stress."))
    if rain is not None:
        if rain >= HEAVY_RAIN_MM:
            alerts.append(("error", f"Heavy rain ({rain:.1f} mm). Risk of waterlogging and erosion; delay planting and spraying."))
        elif rain >= MODERATE_RAIN_MM:
            alerts.append(("warning", f"Moderate rain ({rain:.1f} mm). Hold off on fertilizer or spraying."))
    if moisture is not None:
        if moisture <= DRY_SOIL_M3M3:
            alerts.append(("warning", f"Very dry topsoil ({moisture:.2f} m³/m³). Consider irrigating."))
        elif moisture >= SATURATED_SOIL_M3M3:
            alerts.append(("warning", f"Soil is close to saturated ({moisture:.2f} m³/m³). Check drainage."))
    if not alerts:
        alerts.append(("info", "No extreme weather detected in the current reading."))
    return alerts
