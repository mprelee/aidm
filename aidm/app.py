from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Dict, List
import os
import json
from datetime import datetime
from pathlib import Path

# Load environment variables
load_dotenv()

# Create checkpoints directory if it doesn't exist
CHECKPOINT_DIR = Path("./checkpoints")
CHECKPOINT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-4-0125-preview",
    temperature=0.7,
)

class GameState(TypedDict):
    messages: List[Dict]
    current_save: str
    context: str
    next_action: str

def create_game_state() -> GameState:
    return GameState(
        messages=[],
        current_save="default",
        context="",
        next_action="process_input"
    )

# Define the game master node
def game_master(state: GameState) -> GameState:
    # Create or update prompt template
    prompt = PromptTemplate(
        input_variables=["player_input", "game_state"],
        template="""You are a Game Master for a role-playing game. 
        Current game state: {game_state}
        Player input: {player_input}
        
        Respond as a game master would, describing the situation and asking for the player's next action."""
    )
    
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # Get recent message history for context
    context = "\n".join([
        f"{'Player' if msg['is_player'] else 'Game Master'}: {msg['text']}" 
        for msg in state['messages'][-10:]  # Last 10 messages for context
    ])
    
    response = chain.invoke({
        "player_input": state['context'],
        "game_state": context
    })
    
    # Add AI response to messages
    state['messages'].append({
        "text": response['text'],
        "is_player": False,
        "timestamp": datetime.now().isoformat()
    })
    
    return state

# Create the graph
workflow = StateGraph(GameState)

# Add the game master node
workflow.add_node("game_master", game_master)

# Add edges - connect START to game_master, and game_master to END
workflow.set_entry_point("game_master")  # This replaces the need for explicit START edge
workflow.add_edge('game_master', END)

# Compile the graph
app_graph = workflow.compile()

def save_checkpoint(state: GameState, save_name: str):
    checkpoint_path = get_checkpoint_path(save_name)
    with open(checkpoint_path, 'w') as f:
        json.dump(state, f, indent=2)

def load_checkpoint(save_name: str) -> GameState:
    checkpoint_path = get_checkpoint_path(save_name)
    if not checkpoint_path.exists():
        return create_game_state()
    
    try:
        with open(checkpoint_path, 'r') as f:
            state_dict = json.load(f)
            return GameState(**state_dict)
    except:
        return create_game_state()

def get_checkpoint_path(save_name: str) -> Path:
    return CHECKPOINT_DIR / f"{save_name}.json"

def get_all_saves():
    saves = [f.stem for f in CHECKPOINT_DIR.glob("*.json") 
             if f.stem.lower() != "autosave"]
    return sorted(saves)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/interact', methods=['POST'])
def interact():
    player_input = request.json.get('message', '')
    save_name = request.json.get('save_name', 'default')
    
    # Load current state
    state = load_checkpoint(save_name)
    
    # Add player message to state
    state['messages'].append({
        "text": player_input,
        "is_player": True,
        "timestamp": datetime.now().isoformat()
    })
    state['context'] = player_input
    
    # Run the graph
    final_state = app_graph.invoke(state)
    
    # Save to both current save and autosave
    save_checkpoint(final_state, save_name)
    save_checkpoint(final_state, "autosave")
    
    # Get the last message (AI's response)
    response = final_state['messages'][-1]['text']
    
    return jsonify({"response": response})

@app.route('/saves', methods=['GET'])
def get_saves_route():
    saves = get_all_saves()
    return jsonify({"saves": saves})

@app.route('/load', methods=['POST'])
def load_save():
    save_name = request.json.get('save_name')
    state = load_checkpoint(save_name)
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
    state['messages'] = [
        {
            "text": msg['text'],
            "is_player": msg['isPlayer'],
            "timestamp": datetime.now().isoformat()
        }
        for msg in messages
    ]
    
    try:
        save_checkpoint(state, save_name)
        # After manual save, update autosave to match
        save_checkpoint(state, "autosave")
        return jsonify({"message": f"Game saved as {save_name}"})
    except Exception as e:
        return jsonify({"message": f"Error saving game: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True) 