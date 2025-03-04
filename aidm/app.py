from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import sqlite3
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize the LLM
llm = ChatOpenAI(
    model="gpt-4-0125-preview",
    temperature=0.7,
)

# Create prompt template for the game master
game_master_prompt = PromptTemplate(
    input_variables=["player_input", "game_state"],
    template="""You are a Game Master for a role-playing game. 
    Current game state: {game_state}
    Player input: {player_input}
    
    Respond as a game master would, describing the situation and asking for the player's next action."""
)

game_master_chain = LLMChain(llm=llm, prompt=game_master_prompt)

def init_db():
    conn = sqlite3.connect('game_state.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS game_state
                 (id INTEGER PRIMARY KEY, state TEXT)''')
    # Initialize with empty game state if none exists
    c.execute('INSERT OR IGNORE INTO game_state (id, state) VALUES (1, "Game just started. No current state.")')
    conn.commit()
    conn.close()

def get_game_state():
    conn = sqlite3.connect('game_state.db')
    c = conn.cursor()
    state = c.execute('SELECT state FROM game_state WHERE id = 1').fetchone()
    conn.close()
    return state[0] if state else "No game state found."

def update_game_state(new_state):
    conn = sqlite3.connect('game_state.db')
    c = conn.cursor()
    c.execute('UPDATE game_state SET state = ? WHERE id = 1', (new_state,))
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/interact', methods=['POST'])
def interact():
    player_input = request.json.get('message', '')
    current_state = get_game_state()
    
    response = game_master_chain.invoke({
        "player_input": player_input,
        "game_state": current_state
    })
    
    # Update game state with the new response
    update_game_state(response['text'])
    
    return jsonify({"response": response['text']})

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 