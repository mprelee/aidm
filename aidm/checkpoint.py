from typing import Any, Optional, Protocol
from .models import SessionLocal, GameState

class Checkpointer(Protocol):
    def get(self, thread_id: str) -> Optional[dict]: ...
    def put(self, thread_id: str, state: dict) -> None: ...
    def delete(self, thread_id: str) -> None: ...

class DatabaseCheckpointer:
    def get(self, thread_id: str) -> Optional[dict]:
        db = SessionLocal()
        try:
            state = db.query(GameState).filter_by(thread_id=thread_id).first()
            if state:
                return state.state_data
            return None
        finally:
            db.close()

    def put(self, thread_id: str, state: dict) -> None:
        db = SessionLocal()
        try:
            db_state = db.query(GameState).filter_by(thread_id=thread_id).first()
            if db_state is None:
                db_state = GameState(thread_id=thread_id, state_data=state)
                db.add(db_state)
            else:
                db_state.state_data = state
            db.commit()
        finally:
            db.close()

    def delete(self, thread_id: str) -> None:
        db = SessionLocal()
        try:
            db.query(GameState).filter_by(thread_id=thread_id).delete()
            db.commit()
        finally:
            db.close() 