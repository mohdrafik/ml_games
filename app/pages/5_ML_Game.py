import streamlit as st
import pandas as pd
import time
import random
from sqlalchemy import text
import os

from dotenv import load_dotenv 

# --- NEW: IMPORT FROM MODULAR UTILS ---
from utils.db import engine
from utils.ml_models import draw_ml_plot, get_linear_regression_prediction

# --- 1. CONFIGURATION & SECRETS ---
load_dotenv()
SECRET_GAME_PWD = os.getenv("GAME_PASSWORD").strip()
SECRET_ADMIN_PWD = os.getenv("ADMIN_PWD").strip()

st.set_page_config(page_title="ML Prediction Game", layout="wide", initial_sidebar_state="collapsed")

# --- 2. GAME LOGIC & STATE MACHINE ---
def check_and_transition_state():
    with engine.connect() as conn:
        state = pd.read_sql("SELECT * FROM game_state WHERE id = 1", conn).iloc[0]
        now = time.time()
        
        if state['timer_ends_at'] > 0 and now >= state['timer_ends_at'] and state['status'] != 'processing':
            lock_query = text(f"UPDATE game_state SET status = 'processing' WHERE id = 1 AND status = '{state['status']}'")
            result = conn.execute(lock_query)
            
            if result.rowcount > 0:
                if state['status'] == 'joining':
                    player_count = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
                    if player_count == 0:
                        conn.execute(text("UPDATE game_state SET status='setup', timer_ends_at=0 WHERE id=1"))
                    else:
                        start_next_round(conn, state, 1)
                
                elif state['status'] == 'playing':
                    score_current_round(conn, state)
                    if state['current_round'] >= state['total_rounds']:
                        conn.execute(text("UPDATE game_state SET status='finished', timer_ends_at=0 WHERE id=1"))
                    else:
                        start_next_round(conn, state, int(state['current_round']) + 1)
                
                conn.commit()
                return True
    return False

def start_next_round(conn, state, round_num):
    target = round(random.uniform(state['min_hour'], state['max_hour']), 1)
    
    # --- NEW: USES IMPORTED ML LOGIC ---
    ai_answer = get_linear_regression_prediction(target)
    ends_at = time.time() + state['round_wait_time']
    
    conn.execute(text(f"""
        UPDATE game_state 
        SET status='playing', current_round={round_num}, target_hour={target}, 
            actual_answer={ai_answer}, timer_ends_at={ends_at} 
        WHERE id=1
    """))
    conn.execute(text("UPDATE players SET has_guessed=FALSE, current_guess=-1"))

def score_current_round(conn, state):
    conn.execute(text(f"""
        UPDATE players 
        SET total_score = total_score + CASE 
            WHEN has_guessed = 1 AND (100 - ABS(current_guess - {state['actual_answer']})) > 0 
            THEN ROUND(100 - ABS(current_guess - {state['actual_answer']}), 1)
            ELSE 0 
        END
    """))

check_and_transition_state()

with engine.connect() as conn:
    state = pd.read_sql("SELECT * FROM game_state WHERE id = 1", conn).iloc[0]

## --- 3. ROUTING (Teacher vs Student Link) ---
# --- 3. ROUTING (Role Selection) ---
st.title("🏆 Machine Learning Prediction Arena")
role = st.radio("Select Your Role to Enter:", ["🎓 I am a Student", "👨‍🏫 I am the Teacher (Admin)"], horizontal=True)
st.markdown("---")

if role == "👨‍🏫 I am the Teacher (Admin)":
    st.sidebar.title("👨‍🏫 Teacher Login")
    
    # Initialize login state if it doesn't exist
    if 'teacher_logged_in' not in st.session_state:
        st.session_state['teacher_logged_in'] = False

    # The Login Check
    if not st.session_state['teacher_logged_in']:
        teacher_pwd = st.sidebar.text_input("Admin Password", type="password")
        if st.sidebar.button("Login"):
            if teacher_pwd.lower() == SECRET_ADMIN_PWD.lower():
                st.session_state['teacher_logged_in'] = True
                st.rerun()
            else:
                st.sidebar.error("Incorrect Password!")
        
        st.info("👈 Please log in on the sidebar to access the Control Center.")
        st.stop()
        
    # Optional: Add a logout button for security
    if st.sidebar.button("Logout"):
        st.session_state['teacher_logged_in'] = False
        st.rerun()
        
    # --- TEACHER DASHBOARD ---
    st.header("👨‍🏫 Game Control Center")

    if state['status'] in ['joining', 'playing']:
        if st.button("🛑 Stop Game & Return to Setup", type="primary"):
            with engine.connect() as conn:
                conn.execute(text("UPDATE game_state SET status='setup', timer_ends_at=0 WHERE id=1"))
                conn.execute(text("DELETE FROM players"))
                conn.commit()
            st.rerun()
    
    if state['status'] == 'setup' or state['status'] == 'finished':
        st.header("⚙️ Game Setup & Concept Explanation")
        st.subheader("📊 How the Game Works")
        st.markdown("""
        **Teacher Script:** "Look at the blue dots. These are past students. The red line is our AI's 'Line of Best Fit'. 
        When the game starts, the AI will pick a random Study Hour. Your goal is to guess exactly how many marks the red line predicts!"
        """)
        
        # --- NEW: DRAWS PLOT FROM UTILS ---
        st.pyplot(draw_ml_plot())
        st.markdown("---")

        with st.form("setup_form"):
            col1, col2 = st.columns(2)
            with col1:
                exp_students = st.number_input("Number of Players", 1, 50, int(state.get('expected_students', 2)))
                tot_rounds = st.number_input("Number of Rounds", 1, 20, 5)
                join_wait = st.number_input("Waiting time to join (sec)", 10, 300, 40)
            with col2:
                min_h = st.number_input("Min Study Hours", 1.0, 20.0, 1.0)
                max_h = st.number_input("Max Study Hours", 1.0, 20.0, 10.0)
                round_wait = st.number_input("Round Time Limit (sec)", 10, 120, 40)
            
            if st.form_submit_button("🚀 Start Game / Open Lobby"):
                ends_at = time.time() + join_wait
                with engine.connect() as conn:
                    conn.execute(text("DELETE FROM players"))
                    conn.execute(text(f"""
                        UPDATE game_state SET 
                        status='joining', expected_students={exp_students}, total_rounds={tot_rounds},
                        min_hour={min_h}, max_hour={max_h}, join_wait_time={join_wait}, 
                        round_wait_time={round_wait}, timer_ends_at={ends_at} WHERE id=1
                    """))
                    conn.commit()
                st.rerun()

    # elif state['status'] == 'joining':
    #     st.header("⏳ Waiting for Players...")
    #     join_link = "?join=true"
    #     st.success(f"**Share this exact link with students:** `YOUR_WEBSITE_URL/{join_link}`")
    elif state['status'] == 'joining':
        st.header("⏳ Waiting for Players...")
        st.success("**Tell students to go to the website and select 'I am a Student' to join!**")

        remaining = max(int(state['timer_ends_at'] - time.time()), 0)
        st.metric("Time until Game Starts", f"{remaining} sec")
        
        with engine.connect() as conn:
            players = pd.read_sql("SELECT name, location FROM players", conn)
        st.write(f"Joined: {len(players)} / {state['expected_students']}")
        st.dataframe(players, use_container_width=True)
        
        time.sleep(1)
        st.rerun()

    elif state['status'] == 'playing':
        col1, col2 = st.columns([2, 1])
        with col1:
            st.header(f"🎮 Round {state['current_round']} of {state['total_rounds']}")
            st.pyplot(draw_ml_plot())
        with col2:
            remaining = max(int(state['timer_ends_at'] - time.time()), 0)
            st.metric("⏳ Time Remaining", f"{remaining} sec")
            st.info(f"🎯 Target Study Hours: **{state['target_hour']}**")
            
            with engine.connect() as conn:
                players = pd.read_sql("SELECT name, has_guessed FROM players", conn)
            st.write(f"Guesses Locked: {len(players[players['has_guessed']==True])} / {len(players)}")
            st.dataframe(players, use_container_width=True)
            
        time.sleep(1)
        st.rerun()

# --- 4. STUDENT DASHBOARD ---
# else:
#     st.title("🎓 Student Portal")
# --- 4. STUDENT DASHBOARD ---
elif role == "🎓 I am a Student":
    st.header("🎓 Student Portal")
    
    if state['status'] == 'setup':
        st.info("The teacher has not started the game yet. Please wait.")
        time.sleep(2)
        st.rerun()

    elif state['status'] == 'joining':
        st.header("👋 Join the Game Lobby")
        remaining = max(int(state['timer_ends_at'] - time.time()), 0)
        st.metric("Game starts in:", f"{remaining} sec")
        
        with st.form("join_form"):
            name = st.text_input("Your Name (Mandatory)*")
            loc = st.text_input("Your Location (Optional)")
            if st.form_submit_button("Join Game"):
                if name:
                    with engine.connect() as conn:
                        try:
                            conn.execute(text(f"INSERT INTO players (name, location) VALUES ('{name}', '{loc}')"))
                            conn.commit()
                            st.session_state['student_name'] = name 
                            st.success("Joined! Waiting for game to start...")
                        except:
                            st.session_state['student_name'] = name
                            st.success("Welcome back! Waiting for game to start...")
                else:
                    st.error("Name is required!")
        time.sleep(1)
        st.rerun()

    elif state['status'] == 'playing':
        col1, col2 = st.columns([2, 1])
        with col1:
            st.header(f"Round {state['current_round']} / {state['total_rounds']}")
            st.pyplot(draw_ml_plot())
        with col2:
            remaining = max(int(state['timer_ends_at'] - time.time()), 0)
            st.metric("⏳ Time Remaining", f"{remaining} sec")
            st.info(f"🎯 Predict marks for: **{state['target_hour']} hours**")
            
            with st.form("guess_form"):
                saved_name = st.session_state.get('student_name', '')
                name = st.text_input("Verify Your Name:", value=saved_name)
                guess = st.number_input("Your Guess (Marks):", 0.0, 150.0, 50.0)
                
                if st.form_submit_button("Submit Guess"):
                    if name:
                        with engine.connect() as conn:
                            conn.execute(text(f"UPDATE players SET current_guess={guess}, has_guessed=TRUE WHERE name='{name}'"))
                            conn.commit()
                        st.success("Guess Locked!")
                    else:
                        st.error("Name is missing!")
        time.sleep(1)
        st.rerun()

# --- 5. FINISHED STATE ---
if state['status'] == 'finished':
    st.empty()
    st.markdown("<h1 style='text-align: center; font-size: 50px;'>🏁 Final Results!</h1>", unsafe_allow_html=True)
    
    with engine.connect() as conn:
        leaderboard = pd.read_sql("SELECT name, location, total_score FROM players ORDER BY total_score DESC", conn)
    
    if len(leaderboard) > 0:
        st.balloons()
        leaderboard.index = leaderboard.index + 1
        st.dataframe(leaderboard, use_container_width=True)
        
    # if not is_student_link and st.button("🔄 Reset Server for New Game"):
    if role == "👨‍🏫 I am the Teacher (Admin)" and st.button("🔄 Reset Server for New Game"):
        with engine.connect() as conn:
            conn.execute(text("UPDATE game_state SET status='setup' WHERE id=1"))
            conn.commit()
        st.rerun()