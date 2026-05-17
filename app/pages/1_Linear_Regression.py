import streamlit as st
import pandas as pd
import numpy as np
import time
import random

from sqlalchemy import create_engine, text
import os
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from dotenv import load_dotenv 

# --- 1. CONFIGURATION & SECRETS ---
load_dotenv()
SECRET_GAME_PWD = os.getenv("GAME_PASSWORD", "ML10X").strip()
SECRET_ADMIN_PWD = os.getenv("ADMIN_PWD", "gem").strip()

st.set_page_config(page_title="ML Prediction Game", layout="wide", initial_sidebar_state="collapsed")

# --- 2. DATABASE SETUP ---
DB_URL = os.getenv("DATABASE_URL", "sqlite:///game_database.db")
@st.cache_resource
def get_engine():
    return create_engine(DB_URL)

engine = get_engine()

def init_db():
    with engine.connect() as conn:
        # Players table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS players (
                name VARCHAR(50) PRIMARY KEY,
                location VARCHAR(100) DEFAULT 'Unknown',
                total_score FLOAT DEFAULT 0,
                current_guess FLOAT DEFAULT -1,
                has_guessed BOOLEAN DEFAULT FALSE
            )
        """))
        # Game State table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS game_state (
                id INT PRIMARY KEY,
                status VARCHAR(20) DEFAULT 'setup', 
                current_round INT DEFAULT 1,
                total_rounds INT DEFAULT 5,
                expected_students INT DEFAULT 2, 
                min_hour FLOAT DEFAULT 1.0,
                max_hour FLOAT DEFAULT 10.0,
                join_wait_time INT DEFAULT 40,
                round_wait_time INT DEFAULT 40,
                target_hour FLOAT DEFAULT 5.0,
                actual_answer FLOAT DEFAULT 0.0,
                timer_ends_at FLOAT DEFAULT 0
            )
        """))
        
        # Safe Alters for new columns if DB already exists
        alters = [
            "ALTER TABLE players ADD COLUMN location VARCHAR(100) DEFAULT 'Unknown'",
            "ALTER TABLE game_state ADD COLUMN status VARCHAR(20) DEFAULT 'setup'",
            "ALTER TABLE game_state ADD COLUMN min_hour FLOAT DEFAULT 1.0",
            "ALTER TABLE game_state ADD COLUMN max_hour FLOAT DEFAULT 10.0",
            "ALTER TABLE game_state ADD COLUMN join_wait_time INT DEFAULT 40",
            "ALTER TABLE game_state ADD COLUMN round_wait_time INT DEFAULT 40",
            "ALTER TABLE game_state ADD COLUMN timer_ends_at FLOAT DEFAULT 0"
        ]
        for query in alters:
            try: conn.execute(text(query))
            except: pass
            
        try: conn.execute(text("INSERT INTO game_state (id) VALUES (1)"))
        except: pass
        conn.commit()

init_db()

# --- 3. GAME LOGIC & STATE MACHINE ---
# This ensures that ANY connected device can push the game forward when time runs out!
def check_and_transition_state():
    with engine.connect() as conn:
        state = pd.read_sql("SELECT * FROM game_state WHERE id = 1", conn).iloc[0]
        now = time.time()
        
        # If timer is running and time is up
        if state['timer_ends_at'] > 0 and now >= state['timer_ends_at']:
            if state['status'] == 'joining':
                # NEW LOGIC: Check if anyone actually joined
                player_count = conn.execute(text("SELECT COUNT(*) FROM players")).scalar()
                if player_count == 0:
                    # Abort and reset to setup
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
    # target = round(np.random.uniform(state['min_hour'], state['max_hour']), 1)
    # CHANGED: Now uses the standard 'random' library so the frozen graph seed doesn't break it
    target = round(random.uniform(state['min_hour'], state['max_hour']), 1)
    # AI logic: Marks = (Target * 4.5) + 12
    ai_answer = (target * 4.5) + 12 
    ends_at = time.time() + state['round_wait_time']
    
    conn.execute(text(f"""
        UPDATE game_state 
        SET status='playing', current_round={round_num}, target_hour={target}, 
            actual_answer={ai_answer}, timer_ends_at={ends_at} 
        WHERE id=1
    """))
    conn.execute(text("UPDATE players SET has_guessed=FALSE, current_guess=-1"))

def score_current_round(conn, state):
    # More forgiving scoring: 100 points max. Deduct 1 point for every 1 mark they are off.
    # We use has_guessed = 1 to guarantee it works on both SQLite and MySQL.
    conn.execute(text(f"""
        UPDATE players 
        SET total_score = total_score + CASE 
            WHEN has_guessed = 1 AND (100 - ABS(current_guess - {state['actual_answer']})) > 0 
            THEN ROUND(100 - ABS(current_guess - {state['actual_answer']}), 1)
            ELSE 0 
        END
    """))

# Auto-check state on every page load
check_and_transition_state()

# Fetch latest state after potential transitions
with engine.connect() as conn:
    state = pd.read_sql("SELECT * FROM game_state WHERE id = 1", conn).iloc[0]

# --- 4. SHARED ML VISUALIZATION ---
def draw_ml_plot():
    # Generate static dummy data for the visual
    np.random.seed(42)
    x = np.linspace(0, 10, 50)
    y = 4.5 * x + 12 + (np.random.randn(50) * 5)
    model = LinearRegression().fit(x.reshape(-1, 1), y)
    y_pred = model.predict(x.reshape(-1, 1))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.scatter(x, y, color='blue', alpha=0.5, label='Historical Student Data')
    ax.plot(x, y_pred, color='red', linewidth=2, label='Regression Line')
    ax.set_xlabel("Study Hours")
    ax.set_ylabel("Marks")
    ax.legend()
    st.pyplot(fig)


# --- 5. ROUTING (Teacher vs Student Link) ---
# If URL has ?join=true, show student view directly.
is_student_link = st.query_params.get("join") == "true"

if not is_student_link:
    st.sidebar.title("👨‍🏫 Teacher Login")
    teacher_pwd = st.sidebar.text_input("Admin Password", type="password")
    if teacher_pwd.lower() != SECRET_ADMIN_PWD.lower():
        st.info("👈 Please log in as a teacher on the sidebar, or use the Student Link to join.")
        st.stop()
        
    # --- TEACHER DASHBOARD ---
    st.title("👨‍🏫 Game Control Center")
    # --- NEW: EMERGENCY STOP BUTTON ---
    if state['status'] in ['joining', 'playing']:
        if st.button("🛑 Stop Game & Return to Setup", type="primary"):
            with engine.connect() as conn:
                # Reset the game state back to setup and kill the timer
                conn.execute(text("UPDATE game_state SET status='setup', timer_ends_at=0 WHERE id=1"))
                # Optional but recommended: Kick everyone out of the lobby so it's clean for the next try
                conn.execute(text("DELETE FROM players"))
                conn.commit()
            st.rerun()
    # ----------------------------------
    
    if state['status'] == 'setup' or state['status'] == 'finished':
        st.header("⚙️ Game Setup")
        with st.form("setup_form"):
            col1, col2 = st.columns(2)
            with col1:
                exp_students = st.number_input("Number of Players", 1, 50, 2)
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

    elif state['status'] == 'joining':
        st.header("⏳ Waiting for Players...")
        # Generate the dynamic link based on where the app is hosted
        # If running locally, it shows localhost. On railway, it shows the railway URL.
        current_url = st.query_params.to_dict() # Clear params just in case
        join_link = "?join=true"
        st.success(f"**Share this exact link with students:** `YOUR_WEBSITE_URL/{join_link}`")
        
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
            draw_ml_plot()
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


# --- STUDENT DASHBOARD ---
else:
    st.title("🎓 Student Portal")
    
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
                            # NEW: Save the name in session memory!
                            st.session_state['student_name'] = name 
                            st.success("Joined! Waiting for game to start...")
                        except:
                            # If they rejoin after accidentally refreshing, save name anyway
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
            draw_ml_plot()
        with col2:
            remaining = max(int(state['timer_ends_at'] - time.time()), 0)
            st.metric("⏳ Time Remaining", f"{remaining} sec")
            st.info(f"🎯 Predict marks for: **{state['target_hour']} hours**")
            
            with st.form("guess_form"):
                # NEW: Auto-fill the name using the saved session state!
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

# --- FINISHED STATE (Both Teacher and Student see this) ---
if state['status'] == 'finished':
    st.empty()
    st.markdown("<h1 style='text-align: center; font-size: 50px;'>🏁 Final Results!</h1>", unsafe_allow_html=True)
    
    with engine.connect() as conn:
        leaderboard = pd.read_sql("SELECT name, location, total_score FROM players ORDER BY total_score DESC", conn)
    
    if len(leaderboard) > 0:
        st.balloons()
        leaderboard.index = leaderboard.index + 1
        st.dataframe(leaderboard, use_container_width=True)
        
    if not is_student_link and st.button("🔄 Reset Server for New Game"):
        with engine.connect() as conn:
            conn.execute(text("UPDATE game_state SET status='setup' WHERE id=1"))
            conn.commit()
        st.rerun()