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
                            save_name TEXT PRIMARY KEY,
                            state_data JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS game_saves (
                        save_name TEXT PRIMARY KEY,
                        state_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()

    def save_checkpoint(self, state: GameState, save_name: str):
        state_json = json.dumps(state)
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO game_saves (save_name, state_data)
                        VALUES (%s, %s)
                        ON CONFLICT (save_name) 
                        DO UPDATE SET 
                            state_data = %s,
                            updated_at = CURRENT_TIMESTAMP
                    """, (save_name, state_json, state_json))
                conn.commit()
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO game_saves (save_name, state_data)
                    VALUES (?, ?)
                    ON CONFLICT(save_name) 
                    DO UPDATE SET 
                        state_data = ?,
                        updated_at = CURRENT_TIMESTAMP
                """, (save_name, state_json, state_json))
                conn.commit()

    def load_checkpoint(self, save_name: str) -> GameState:
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT state_data FROM game_saves WHERE save_name = %s", (save_name,))
                    result = cur.fetchone()
                    if result:
                        return GameState(**json.loads(result[0]))
        else:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("SELECT state_data FROM game_saves WHERE save_name = ?", (save_name,))
                result = cur.fetchone()
                if result:
                    return GameState(**json.loads(result[0]))
        return create_game_state()

    def get_all_saves(self) -> List[str]:
        if self.is_prod:
            with psycopg2.connect(self.db_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT save_name FROM game_saves 
                        WHERE save_name != 'autosave' 
                        ORDER BY updated_at DESC
                    """)
                    return [row[0] for row in cur.fetchall()]
        else:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("""
                    SELECT save_name FROM game_saves 
                    WHERE save_name != 'autosave' 
                    ORDER BY updated_at DESC
                """)
                return [row[0] for row in cur.fetchall()] 