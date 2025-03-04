import logging
from flask import Flask, render_template, request, jsonify, make_response, session
from dotenv import load_dotenv
import os
from datetime import datetime
from .graph.game_master import GameMasterGraph, create_game_state
from .models import SessionLocal, Adventure, init_db
import uuid
from .storage import SaveManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    logger.info("Initializing Flask app...")
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev')
    
    logger.info("Setting up GameMaster...")
    game_master = GameMasterGraph()
    
    logger.info("Initializing database...")
    init_db()

    logger.info("Initializing SaveManager...")
    save_manager = SaveManager()
except Exception as e:
    logger.error(f"Initialization error: {str(e)}", exc_info=True)
    raise

def get_or_create_session():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    db = SessionLocal()
    try:
        adventure = db.query(Adventure).filter_by(session_id=session['session_id']).first()
        if not adventure:
            adventure = Adventure(session_id=session['session_id'], messages=[])
            db.add(adventure)
            db.commit()
        return adventure
    finally:
        db.close()

@app.route('/')
def home():
    logger.debug("Handling home route request")
    try:
        response = make_response(render_template('index.html'))
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        return response
    except Exception as e:
        logger.error(f"Error rendering home template: {str(e)}", exc_info=True)
        return "Error loading page", 500

@app.route('/interact', methods=['POST'])
def interact():
    logger.debug("Handling interact request")
    try:
        player_input = request.json.get('message', '')
        
        # Use session ID as thread ID for state persistence
        config = {
            "configurable": {
                "thread_id": session['session_id']
            }
        }
        
        # Load existing state or create new one
        state = save_manager.load_state(session['session_id'])
        
        if player_input:
            state['messages'].append({
                "text": player_input,
                "is_player": True,
                "timestamp": datetime.now().isoformat()
            })
        
        # Get AI response with thread config
        final_state = game_master.invoke(state, config)
        
        # Save updated state
        save_manager.save_state(final_state, session['session_id'])
        
        response = final_state['messages'][-1]['text']
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error in interact: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_game():
    try:
        save_manager.delete_state(session['session_id'])
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error resetting game: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 