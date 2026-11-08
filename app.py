import streamlit as st
from datetime import date

# Page configuration
st.set_page_config(
    page_title="Smart Farming Advisor",
    page_icon="🌱",
    layout="wide"
)

# Application title
st.title("🌱 Smart Farming & Crop Planting Advisor")

st.write(
    "Welcome to your intelligent farming assistant. "
    "Get crop information, planting advice and farm management support."
)

st.divider()

# Sidebar navigation
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
        "Farm Logs"
    ]
)

# Dashboard
if menu == "Dashboard":

    st.header("Farm Dashboard")

    col1, col2, col3 = st.columns(3)

    col1.metric("Farm Status", "Active")
    col2.metric("Available Crops", "5")
    col3.metric("System Status", "Online")

    st.subheader("Welcome to Smart Farming")

    st.info(
        "Use the navigation menu to manage your farm "
        "and receive farming recommendations."
    )

# Farm Details
elif menu == "Farm Details":

    st.header("🌾 Farm Registration")

    if "farm_details" not in st.session_state:
        st.session_state.farm_details = {}

    with st.form("farm_form"):

        farm_name = st.text_input("Farm Name")

        location = st.text_input("Farm Location")

        farm_size = st.number_input(
            "Farm Size (hectares)",
            min_value=0.1,
            value=1.0
        )

        soil_type = st.selectbox(
            "Soil Type",
            ["Loamy", "Clay", "Sandy", "Silty"]
        )

        submitted = st.form_submit_button(
            "Save Farm Details"
        )

        if submitted:

            if farm_name and location:

                st.session_state.farm_details = {
                    "Farm Name": farm_name,
                    "Location": location,
                    "Farm Size": farm_size,
                    "Soil Type": soil_type
                }

                st.success("Farm details saved successfully!")

            else:
                st.warning("Please enter your farm name and location.")

    if st.session_state.farm_details:

        st.subheader("Saved Farm Information")

        for key, value in st.session_state.farm_details.items():

            st.write(f"**{key}:** {value}")
# Crop Selection
elif menu == "Crop Selection"
    st.header("🌱 Crop Recommendation")
    from crop import recommend_crops

    soil_type = st.selectbox(
        "Select your soil type",
        ["Loamy", "Sandy", "Clay", "Silty"]
    )

    season = st.selectbox(
        "Select season",
        ["Rainy", "Dry", "Harmattan"]
    )

    budget = st.selectbox(
        "Your budget",
        ["Low", "Medium", "High"]
    )

    if st.button("Recommend Crops"):
        recommendations = recommend_crops(soil_type, season, budget)
        st.success("Recommended crops for you:")
        for crop in recommendations:
            st.write(f"✅ {crop}")
# Planting Calendar
elif menu == "Planting Calendar":

    st.header("Planting Calendar")

    planting_date = st.date_input(
        "Select your planned planting date",
        value=date.today()
    )

    st.write("Planned planting date:", planting_date)

# AI Farming Advisor
elif menu == "AI Farming Advisor":

    st.header("AI Farming Recommendations")

    question = st.text_area(
        "Ask your farming question"
    )

    if st.button("Get Farming Advice"):
        if question:
            st.info(
                "Your question will be processed "
                "by the AI farming advisor module."
            )
        else:
            st.warning("Please enter a question.")

# Warnings
elif menu == "Pest & Weather Warnings":

    st.header("Farm Alerts")

    st.warning(
        "Weather and pest alerts will appear here "
        "when connected to the relevant modules."
    )

# Farm Logs
elif menu == "Farm Logs":

    st.header("Farm Activity Logs")

    activity = st.text_area(
        "Enter your farming activity"
    )

    if st.button("Save Activity"):
        if activity:
            st.success("Farm activity recorded!")
        else:
            st.warning("Please enter an activity.")

# Footer
st.divider()

st.caption(
    "Smart Farming & Crop Planting Advisor | "
    "Developed by the UI & Frontend Team"
)
