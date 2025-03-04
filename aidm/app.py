from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os
from datetime import datetime
from .graph.game_master import GameMasterGraph, create_game_state
from .storage.save_manager import SaveManager

# Load environment variables
load_dotenv()

app = Flask(__name__)
game_master = GameMasterGraph()
save_manager = SaveManager()  # Will use SQLite locally, Postgres in production

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/interact', methods=['POST'])
def interact():
    player_input = request.json.get('message', '')
    save_name = request.json.get('save_name', 'default')
    
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

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 