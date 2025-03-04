from typing import Any, Optional, Protocol
import logging
from .models import SessionLocal, GameState

logger = logging.getLogger(__name__)

class Checkpointer(Protocol):
    def get(self, thread_id: str) -> Optional[dict]: ...
    def put(self, thread_id: str, state: dict) -> None: ...
    def delete(self, thread_id: str) -> None: ...

class DatabaseCheckpointer:
    def get(self, thread_id: str) -> Optional[dict]:
        logger.debug(f"Getting state for thread {thread_id}")
        db = SessionLocal()
        try:
            state = db.query(GameState).filter_by(thread_id=thread_id).first()
            if state:
                logger.debug(f"Found state: {state.state_data}")
                return state.state_data
            logger.debug("No state found")
            return None
        except Exception as e:
            logger.error(f"Error getting state: {str(e)}", exc_info=True)
            return None
        finally:
            db.close()

    def put(self, thread_id: str, state: dict) -> None:
        logger.debug(f"Saving state for thread {thread_id}")
        db = SessionLocal()
        try:
            db_state = db.query(GameState).filter_by(thread_id=thread_id).first()
            if db_state is None:
                db_state = GameState(thread_id=thread_id, state_data=state)
                db.add(db_state)
            else:
                db_state.state_data = state
            db.commit()
            logger.debug("State saved successfully")
        except Exception as e:
            logger.error(f"Error saving state: {str(e)}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def delete(self, thread_id: str) -> None:
        db = SessionLocal()
        try:
            db.query(GameState).filter_by(thread_id=thread_id).delete()
            db.commit()
        finally:
            db.close() 