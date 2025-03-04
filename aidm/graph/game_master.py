from typing import TypedDict, Dict, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END

class GameState(TypedDict):
    messages: List[Dict]
    current_save: str
    context: str
    next_action: str

class GameMasterGraph:
    def __init__(self, model="gpt-4-0125-preview", temperature=0.7):
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
        )
        self.workflow = self._create_graph()

    def _game_master_node(self, state: GameState) -> GameState:
        prompt = PromptTemplate(
            input_variables=["player_input", "game_state"],
            template="""You are a Game Master for a role-playing game. 
            Current game state: {game_state}
            Player input: {player_input}
            
            Respond as a game master would, describing the situation and asking for the player's next action."""
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
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

    def _create_graph(self) -> StateGraph:
        workflow = StateGraph(GameState)
        workflow.add_node("game_master", self._game_master_node)
        workflow.set_entry_point("game_master")
        workflow.add_edge('game_master', END)
        return workflow.compile()

    def invoke(self, state: GameState) -> GameState:
        return self.workflow.invoke(state)

def create_game_state() -> GameState:
    return GameState(
        messages=[],
        current_save="default",
        context="",
        next_action="process_input"
    ) 