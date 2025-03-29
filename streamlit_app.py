__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
from crewai import Agent, Task, Crew
from langchain_groq import ChatGroq
import xlsxwriter
from io import BytesIO
import os

# Set page configuration
st.set_page_config(
    page_title="Fitness & Nutrition Planner 💪",
    page_icon="🥗",
    layout="wide"
)

# Apply custom CSS for background and card styling
st.markdown("""
    <style>
    /* Set background color similar to the uploaded design */
    body {
        background-color: #FDF4EE;  /* Light Peach Background */
    }
    
    /* Header container similar to the design */
    .header-container {
        background: white;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .header-container h1 {
        font-size: 3em;
        color: #000000;  /* Red for emphasis */
        margin-bottom: 10px;
    }
    .header-container p {
        font-size: 1.5em;
        color: #333333;  /* Dark Gray Text */
    }

    /* Button Styling */
    .stButton > button {
        background-color: #FF4B4B; /* Orange CTA Button */
        color: white;
        font-size: 1.2em;
        border-radius: 10px;
        padding: 12px 24px;
        border: none;
    }
    .stButton > button:hover {
        background-color: #FF4B4B;
    }
    
    /* Centered Section with Card Style */
    .content-container {
        background: white;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0px 6px 15px rgba(0, 0, 0, 0.1);
        text-align: center;
        max-width: 800px;
        margin: auto;
    }

    /* Feature List */
    .feature-list {
        font-size: 1.3em;
        text-align: left;
        padding-left: 20px;
        color: #34495E;
    }
    .feature-list li {
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# Create header similar to the uploaded design
st.markdown("""
    <div class="header-container">
        <h1>🥗  Personalized Diet & Workout Planner 🏋️‍♂️</h1>
        <p>Transform Your Lifestyle with Custom-Made Plans</p>
    </div>
""", unsafe_allow_html=True)

# Initialize Groq and Agents
os.environ["GROQ_API_KEY"] = st.secrets.GROQ_API_KEY
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
llm = ChatGroq(temperature=0, groq_api_key=GROQ_API_KEY, model_name="groq/llama-3.3-70b-versatile")

diet_agent = Agent(
    role='Nutrition Expert',
    goal='Generate personalized diet plans based on user inputs',
    backstory='Expert in nutrition science and meal planning with focus on Indian cuisine',
    verbose=True,
    llm=llm
)

workout_agent = Agent(
    role='Fitness Trainer',
    goal='Create effective workout plans tailored to user goals',
    backstory='Experienced fitness coach specializing in home workouts',
    verbose=True,
    llm=llm
)

# Session State Initialization
if 'app_state' not in st.session_state:
    st.session_state.app_state = {
        'maintenance': None,
        'target_calories': None,
        'diet_plan': None,
        'workout_plan': None,
        'show_goal_selector': False
    }

# Create tabs for better organization
tabs = st.tabs(["Personal Info", "Diet Planning", "Workout Planning"])

with tabs[0]:
    st.markdown("### 📝 Personal Information")
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown("##### Basic Information")
        age = st.number_input("Age", min_value=10, step=1)
        gender = st.selectbox("Gender", ["Male", "Female"])
        weight = st.number_input("Weight (kg)", min_value=10.0)
    
    with col2:
        st.markdown("##### Height")
        height_feet = st.number_input("Height (Feet)", min_value=3, max_value=8)
        height_inches = st.number_input("Height (Inches)", min_value=0, max_value=11)
    
    with col3:
        st.markdown("##### Preferences")
        diet_type = st.selectbox("Diet Type", ["Vegetarian", "Vegan", "Non-Vegetarian"])
        budget = st.selectbox("Budget", ["Low", "Medium", "High"])

    st.markdown("##### Activity Level")
    activity_level = st.selectbox("Select your activity level", [
        "Sedentary (little/no exercise)",
        "Lightly Active (light exercise 1-3 days/week)",
        "Moderately Active (moderate exercise 3-5 days/week)",
        "Very Active (hard exercise 6-7 days/week)",
        "Extra Active (physical job & daily exercise)"
    ])

    dislikes = st.text_area("Food dislikes/allergies (comma separated)")

    if st.button("Calculate Maintenance Calories", key="calc_calories"):
        with st.spinner("🔄 Calculating your maintenance calories..."):
            height_cm = (height_feet * 12 + height_inches) * 2.54
            
            if gender == "Male":
                bmr = 88.362 + (13.397 * weight) + (4.799 * height_cm) - (5.677 * age)
            else:
                bmr = 447.593 + (9.247 * weight) + (3.098 * height_cm) - (4.330 * age)
            
            activity_factors = {
                "Sedentary": 1.2,
                "Lightly": 1.375,
                "Moderately": 1.55,
                "Very": 1.725,
                "Extra": 1.9
            }
            activity_level_key = activity_level.split()[0]
            tdee = bmr * activity_factors[activity_level_key]
            
            st.session_state.app_state['maintenance'] = tdee
            st.session_state.app_state['target_calories'] = tdee
            st.session_state.app_state['show_goal_selector'] = True
            
            st.markdown(f"""
                <div class="success-message">
                    <h4>🎯 Your Daily Calorie Needs</h4>
                    <p>Maintenance calories: {tdee:.0f} kcal/day</p>
                </div>
            """, unsafe_allow_html=True)

with tabs[1]:
    st.markdown("### 🍽️ Diet Planning")
    
    if st.session_state.app_state.get('show_goal_selector'):
        st.markdown("##### Select Your Goal")
        calorie_delta = 250
        goal_options = [
            f"Lose 0.25kg/week: {int(st.session_state.app_state['maintenance'] - calorie_delta)} kcal",
            f"Lose 0.5kg/week: {int(st.session_state.app_state['maintenance'] - 2 * calorie_delta)} kcal",
            f"Maintain: {int(st.session_state.app_state['maintenance'])} kcal",
            f"Gain 0.25kg/week: {int(st.session_state.app_state['maintenance'] + calorie_delta)} kcal",
            f"Gain 0.5kg/week: {int(st.session_state.app_state['maintenance'] + 2 * calorie_delta)} kcal"
        ]
        
        selected_goal = st.selectbox("Select your goal:", goal_options)
        target = int(selected_goal.split()[2])
        st.session_state.app_state['target_calories'] = target

        if st.button("Generate Diet Plan", key="gen_diet"):
            with st.spinner("🔄 Creating your personalized diet plan..."):
                diet_prompt = f"""
                Create a 7-day {st.session_state.app_state['target_calories']} kcal {diet_type} meal plan for a {age}-year-old {gender}.
                StrictRequirements:
                - Indian cuisine with their quantity
                - Budget: {budget}
                - Avoid: {dislikes}
                - The selected calorie goal exactly among Breakfast, Lunch, Dinner, and Snacks
                - 4 meals/day (Breakfast, Lunch, Dinner, Snack) with detailed calories and nutrients
                - YouTube Recipe Video links for each meal in this format:"https://www.youtube.com/results?search_query="
                - Format: Markdown table with columns: | Day | Meal | Description | Calories | Nutrients | Recipe Link |
                  - List day number only once before Breakfast row for each day
                  - Use empty Day column for subsequent meals (Lunch, Snack, Dinner)
                  - Example:
                    | Day | Meal | Description | Calories | Nutrients | Recipe Link |
                    |-----|------|-------------|----------|-----------|-------------|
                    | 1   | Breakfast | ... | ... | ... | ... |
                    |     | Lunch | ... | ... | ... | ... |
                    |     | Snack | ... | ... | ... | ... |
                    |     | Dinner | ... | ... | ... | ... |
                """
                
                diet_task = Task(
                    description=diet_prompt,
                    expected_output="Markdown table with meal plan",
                    agent=diet_agent
                )
                
                diet_crew = Crew(
                    agents=[diet_agent],
                    tasks=[diet_task],
                    verbose=True
                )
                
                try:
                    diet_result = diet_crew.kickoff()
                    st.markdown("#### 📋 Your Personalized Diet Plan")
                    st.markdown(diet_result)
                    st.session_state.app_state['diet_plan'] = diet_result
                except Exception as e:
                    st.error(f"Error generating diet plan: {str(e)}")
    else:
        st.info("👆 Please calculate your maintenance calories first in the Personal Info tab.")

with tabs[2]:
    st.markdown("### 💪 Workout Planning")
    
    if st.session_state.app_state.get('diet_plan'):
        col1, col2 = st.columns(2)
        with col1:
            workout_days = st.number_input("Training days/week", min_value=1, max_value=7, value=3)
        with col2:
            workout_goal = st.selectbox("Workout Goal", ["Weight Loss", "Muscle Gain", "General Fitness"])
        
        if st.button("Generate Workout Plan", key="gen_workout"):
            with st.spinner("🔄 Creating your personalized workout plan..."):
                workout_prompt = f"""
                Create a {workout_days}-day/week {workout_goal} workout plan for a {age}-year-old {gender}.
                Requirements:
                - Home workout preferred
                - Include sets/reps and YouTube links in this format:"https://www.youtube.com/results?search_query="
                - Add 4-week progression plan
                - Format: Markdown table with columns: | Day | Exercise | Duration/Reps | Target Area | Video Link |
                  - List day number only once at the start of each day's workout
                  - Use empty Day column for subsequent exercises on the same day
                  - Example:
                    | Day | Exercise | Duration/Reps | Target Area | Video Link |
                    |-----|----------|---------------|-------------|------------|
                    | 1   | Push-ups | 3x15          | Chest       | ...        |
                    |     | Plank    | 3x1min        | Core        | ...        |
                """
                
                workout_task = Task(
                    description=workout_prompt,
                    expected_output="Markdown table with workout plan",
                    agent=workout_agent
                )
                
                workout_crew = Crew(
                    agents=[workout_agent],
                    tasks=[workout_task],
                    verbose=True
                )
                
                try:
                    workout_result = workout_crew.kickoff()
                    st.markdown("#### 📋 Your Personalized Workout Plan")
                    st.markdown(workout_result)
                    st.session_state.app_state['workout_plan'] = workout_result
                except Exception as e:
                    st.error(f"Error generating workout plan: {str(e)}")
    else:
        st.info("👆 Please generate your diet plan first in the Diet Planning tab.")

# Excel Generation Function
def generate_excel(content, sheet_name):
    try:
        content_str = str(content)
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet(sheet_name)
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#C6EFCE',
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'border': 1,
            'text_wrap': True
        })
        
        row = 0
        max_col_widths = {}
        lines = content_str.split('\n')
        
        for line in lines:
            if '|' in line:
                if '-|-' in line:
                    continue
                
                cells = [cell.strip() for cell in line.strip('|').split('|')]
                
                for col, cell in enumerate(cells):
                    max_col_widths[col] = max(
                        max_col_widths.get(col, 0),
                        len(cell)
                    )
                    current_format = header_format if row == 0 else cell_format
                    worksheet.write(row, col, cell, current_format)
                
                row += 1
        
        for col, width in max_col_widths.items():
            worksheet.set_column(col, col, min(width + 2, 50))
            
        workbook.close()
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Error generating Excel file: {str(e)}")
        return None

# Download Section
if st.session_state.app_state.get('diet_plan') or st.session_state.app_state.get('workout_plan'):
    st.markdown("### 📥 Download Your Plans")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.session_state.app_state.get('diet_plan'):
            diet_excel = generate_excel(st.session_state.app_state['diet_plan'], "Diet Plan")
            if diet_excel:
                st.download_button(
                    label="📊 Download Diet Plan Excel",
                    data=diet_excel,
                    file_name="diet_plan.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="diet_plan_excel"
                )
    
    with col2:
        if st.session_state.app_state.get('workout_plan'):
            workout_excel = generate_excel(st.session_state.app_state['workout_plan'], "Workout Plan")
            if workout_excel:
                st.download_button(
                    label="📊 Download Workout Plan Excel",
                    data=workout_excel,
                    file_name="workout_plan.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="workout_plan_excel"
                )
