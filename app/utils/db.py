import os
import streamlit as st
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Connect to Railway MySQL (falls back to local SQLite for testing)
DB_URL = os.getenv("DATABASE_URL", "sqlite:///game_database.db")

# @st.cache_resource
# def get_engine():
#     return create_engine(DB_URL)

@st.cache_resource
def get_engine():
    # pool_pre_ping=True checks if the connection is dead and reconnects automatically!
    # pool_recycle=300 forces the app to refresh the connection every 5 minutes.
    return create_engine(DB_URL, pool_pre_ping=True, pool_recycle=300)


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

# Run initialization immediately upon import
init_db()