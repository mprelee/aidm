from sqlalchemy import Column, Integer, String, JSON, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class GameState(Base):
    __tablename__ = 'game_states'
    
    id = Column(Integer, primary_key=True)
    thread_id = Column(String, unique=True, nullable=False)
    state_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

def get_db_url():
    if os.environ.get('DATABASE_URL'):
        # Convert Railway's Postgres URL to SQLAlchemy format
        url = os.environ['DATABASE_URL']
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url
    return 'sqlite:///game_state.db'

engine = create_engine(get_db_url())
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine) 