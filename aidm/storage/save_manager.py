import json
import os
import sqlite3
import psycopg2
from typing import Optional
from ..graph.game_master import GameState, create_game_state

class SaveManager:
    def __init__(self, db_path: str = "game_state.db"):
        self.is_prod = bool(os.getenv('DATABASE_URL', '').strip())
        self.db_url = os.getenv('DATABASE_URL')
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS game_states (
                            session_id TEXT PRIMARY KEY,
                            state_data JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_states (
                        session_id TEXT PRIMARY KEY,
                        state_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()

    def save_state(self, state: GameState, session_id: str):
        state_json = json.dumps(state)
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO game_states (session_id, state_data)
                        VALUES (%s, %s)
                        ON CONFLICT (session_id) 
                        DO UPDATE SET 
                            state_data = %s,
                            updated_at = CURRENT_TIMESTAMP
                    """, (session_id, state_json, state_json))
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO game_states (session_id, state_data)
                    VALUES (?, ?)
                    ON CONFLICT(session_id) 
                    DO UPDATE SET 
                        state_data = ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (session_id, state_json, state_json))
                conn.commit()

    def load_state(self, session_id: str) -> GameState:
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT state_data FROM game_states WHERE session_id = %s", (session_id,))
                    result = cur.fetchone()
                    if result:
                        return GameState(**json.loads(result[0]))
        else:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("SELECT state_data FROM game_states WHERE session_id = ?", (session_id,))
                result = cur.fetchone()
                if result:
                    return GameState(**json.loads(result[0]))
        return create_game_state()

    def delete_state(self, session_id: str):
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM game_states WHERE session_id = %s", (session_id,))
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM game_states WHERE session_id = ?", (session_id,))
                conn.commit() 