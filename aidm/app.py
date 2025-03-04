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
        
        # Get adventure from database
        db = SessionLocal()
        try:
            adventure = get_or_create_session()
            
            # Create new state with history from database
            state = create_game_state()
            state['messages'] = adventure.messages
            
            if player_input:
                state['messages'].append({
                    "text": player_input,
                    "is_player": True,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Get AI response with thread config
            final_state = game_master.invoke(state, config)
            
            # Save updated state to database
            adventure.messages = final_state['messages']
            db.commit()
            
            response = final_state['messages'][-1]['text']
            return jsonify({"response": response})
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error in interact: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_game():
    try:
        db = SessionLocal()
        adventure = get_or_create_session()
        adventure.messages = []
        db.commit()
        db.close()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error resetting game: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/saves', methods=['GET'])
def get_saves_route():
    saves = save_manager.get_all_saves(session['session_id'])
    return jsonify({"saves": saves})

@app.route('/load', methods=['POST'])
def load_save():
    save_name = request.json.get('save_name')
    state = save_manager.load_checkpoint(save_name, session['session_id'])
    return jsonify({
        "messages": [
            {"text": msg["text"], "isPlayer": msg["is_player"]}
            for msg in state['messages']
        ]
    })

@app.route('/save', methods=['POST'])
def create_save():
    save_name = request.json.get('save_name')
    messages = request.json.get('messages', [])
    
    if save_name.lower() == 'autosave':
        return jsonify({"message": "Cannot manually overwrite autosave"}), 400
    
    if save_name.lower() == 'new':
        return jsonify({"message": "Cannot use reserved name 'new'"}), 400
    
    # Create new state
    state = create_game_state()
    
    # If this is a new game with no messages, get the initial response
    if not messages:
        state = game_master.invoke(state)
        messages = state['messages']
    else:
        state['messages'] = [
            {
                "text": msg['text'],
                "is_player": msg['isPlayer'],
                "timestamp": datetime.now().isoformat()
            }
            for msg in messages
        ]
    
    try:
        save_manager.save_checkpoint(state, save_name, session['session_id'])
        save_manager.save_checkpoint(state, "autosave", session['session_id'])
        return jsonify({
            "message": f"Game saved as {save_name}",
            "messages": [
                {"text": msg["text"], "isPlayer": msg["is_player"]}
                for msg in messages
            ]
        })
    except Exception as e:
        logger.error(f"Error saving game: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 