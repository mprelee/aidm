import logging
from flask import Flask, render_template, request, jsonify, make_response, session
from dotenv import load_dotenv
import os
from datetime import datetime
from datetime import timedelta  # Import timedelta separately
from .graph.game_master import GameMasterGraph, create_game_state
from .models import init_db
import uuid

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    logger.info("Initializing Flask app...")
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev')
    # Configure session to be permanent and last 30 days
    app.permanent_session_lifetime = timedelta(days=30)
    
    logger.info("Initializing database...")
    init_db()
    
    logger.info("Setting up GameMaster...")
    game_master = GameMasterGraph()
except Exception as e:
    logger.error(f"Initialization error: {str(e)}", exc_info=True)
    raise

@app.route('/')
def home():
    logger.debug("Handling home route request")
    try:
        response = make_response(render_template('index.html'))
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
            session.permanent = True
        return response
    except Exception as e:
        logger.error(f"Error rendering home template: {str(e)}", exc_info=True)
        return "Error loading page", 500

@app.route('/interact', methods=['POST'])
def interact():
    logger.debug("Handling interact request")
    try:
        player_input = request.json.get('message', '')
        
        thread_id = session['session_id']
        
        # Get existing state from checkpointer or create new one
        state = game_master.checkpointer.get(thread_id) or create_game_state()
        
        if player_input:
            state['messages'].append({
                "text": player_input,
                "is_player": True,
                "timestamp": datetime.now().isoformat()
            })
        
        # Get AI response with thread config
        final_state = game_master.invoke(state, {
            "configurable": {
                "thread_id": thread_id,
                "session": {
                    "id": thread_id
                }
            }
        })
        
        # Store state in checkpointer
        game_master.checkpointer.put(thread_id, final_state)
        
        response = final_state['messages'][-1]['text']
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error in interact: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_game():
    try:
        thread_id = session['session_id']
        game_master.checkpointer.delete(thread_id)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error resetting game: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/state', methods=['GET'])
def get_state():
    try:
        thread_id = session['session_id']
        state = game_master.checkpointer.get(thread_id)
        if state:
            return jsonify({
                "messages": [
                    {"text": msg["text"], "isPlayer": msg["is_player"]}
                    for msg in state['messages']
                ]
            })
        return jsonify({"messages": []})
    except Exception as e:
        logger.error(f"Error getting state: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 