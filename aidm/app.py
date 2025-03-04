import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from datetime import datetime
from .graph.game_master import GameMasterGraph, create_game_state
from .storage.save_manager import SaveManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

try:
    logger.info("Initializing Flask app...")
    app = Flask(__name__)
    
    logger.info("Setting up GameMaster...")
    game_master = GameMasterGraph()
    
    logger.info("Setting up SaveManager...")
    save_manager = SaveManager()
except Exception as e:
    logger.error(f"Initialization error: {str(e)}", exc_info=True)
    raise

@app.route('/')
def home():
    logger.debug("Handling home route request")
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering home template: {str(e)}", exc_info=True)
        return "Error loading page", 500

@app.route('/interact', methods=['POST'])
def interact():
    logger.debug("Handling interact request")
    try:
        player_input = request.json.get('message', '')
        save_name = request.json.get('save_name', 'default')
        
        logger.debug(f"Processing input for save: {save_name}")
        # Load current state
        state = save_manager.load_checkpoint(save_name)
        
        # Add player message to state
        state['messages'].append({
            "text": player_input,
            "is_player": True,
            "timestamp": datetime.now().isoformat()
        })
        state['context'] = player_input
        
        # Run the graph
        final_state = game_master.invoke(state)
        
        # Save to both current save and autosave
        save_manager.save_checkpoint(final_state, save_name)
        save_manager.save_checkpoint(final_state, "autosave")
        
        # Get the last message (AI's response)
        response = final_state['messages'][-1]['text']
        
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error in interact: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/saves', methods=['GET'])
def get_saves_route():
    saves = save_manager.get_all_saves()
    return jsonify({"saves": saves})

@app.route('/load', methods=['POST'])
def load_save():
    save_name = request.json.get('save_name')
    state = save_manager.load_checkpoint(save_name)
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
        save_manager.save_checkpoint(state, save_name)
        save_manager.save_checkpoint(state, "autosave")
        return jsonify({
            "message": f"Game saved as {save_name}",
            "messages": [
                {"text": msg["text"], "isPlayer": msg["is_player"]}
                for msg in messages
            ]
        })
    except Exception as e:
        return jsonify({"message": f"Error saving game: {str(e)}"}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 error: {error}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({"error": "An unexpected error occurred"}), 500

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 