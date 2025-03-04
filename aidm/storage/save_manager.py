import json
import os
import sqlite3
import psycopg2
from typing import List
from ..graph.game_master import GameState, create_game_state

class SaveManager:
    def __init__(self, db_path: str = "game_state.db"):
        # Only consider it production if DATABASE_URL is set AND not empty
        self.is_prod = bool(os.getenv('DATABASE_URL', '').strip())
        self.db_url = os.getenv('DATABASE_URL')
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS game_saves (
                            id SERIAL PRIMARY KEY,
                            session_id TEXT NOT NULL,
                            save_name TEXT NOT NULL,
                            state_data JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(session_id, save_name)
                        )
                    """)
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_saves (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        save_name TEXT NOT NULL,
                        state_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(session_id, save_name)
                    )
                """)
                conn.commit()

    def save_checkpoint(self, state: GameState, save_name: str, session_id: str):
        state_json = json.dumps(state)
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO game_saves (session_id, save_name, state_data)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (session_id, save_name) 
                        DO UPDATE SET 
                            state_data = %s,
                            updated_at = CURRENT_TIMESTAMP
                    """, (session_id, save_name, state_json, state_json))
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO game_saves (session_id, save_name, state_data)
                    VALUES (?, ?, ?)
                    ON CONFLICT(session_id, save_name) 
                    DO UPDATE SET 
                        state_data = ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (session_id, save_name, state_json, state_json))
                conn.commit()

    def load_checkpoint(self, save_name: str, session_id: str) -> GameState:
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT state_data FROM game_saves 
                        WHERE save_name = %s AND session_id = %s
                    """, (save_name, session_id))
                    result = cur.fetchone()
                    if result:
                        return GameState(**json.loads(result[0]))
        else:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    SELECT state_data FROM game_saves 
                    WHERE save_name = ? AND session_id = ?
                """, (save_name, session_id))
                result = cur.fetchone()
                if result:
                    return GameState(**json.loads(result[0]))
        return create_game_state()

    def get_all_saves(self, session_id: str) -> List[str]:
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT save_name FROM game_saves 
                        WHERE session_id = %s AND save_name != 'autosave' 
                        ORDER BY updated_at DESC
                    """, (session_id,))
                    return [row[0] for row in cur.fetchall()]
        else:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    SELECT save_name FROM game_saves 
                    WHERE session_id = ? AND save_name != 'autosave' 
                    ORDER BY updated_at DESC
                """, (session_id,))
                return [row[0] for row in cur.fetchall()] 