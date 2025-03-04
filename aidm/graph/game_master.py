from typing import TypedDict, Dict, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langgraph.graph import StateGraph, END
import yaml
from pathlib import Path

class GameState(TypedDict):
    messages: List[Dict]
    current_save: str
    context: str
    next_action: str
    session_started: bool  # Track if session start prompt has been sent

class GameMasterGraph:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.llm = self._init_llm()
        self.workflow = self._create_graph()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _init_llm(self) -> ChatOpenAI:
        model_config = self.config['model']
        return ChatOpenAI(
            model=model_config['name'],
            temperature=model_config['temperature'],
            max_tokens=model_config['max_tokens'],
        )

    def _get_system_prompt(self, state: GameState) -> str:
        prompts = self.config['game_master']['system_prompts']
        
        # If this is the first message of the session, include the session start prompt
        if not state.get('session_started', False):
            return f"{prompts['initial']}\n\n{prompts['session_start']}"
        
        return prompts['initial']

    def _game_master_node(self, state: GameState) -> GameState:
        try:
            system_prompt = self._get_system_prompt(state)
            
            # If this is a new session, don't use player input
            if not state.get('session_started', False):
                prompt = PromptTemplate(
                    input_variables=["system"],
                    template="""
                    {system}

                    Begin the game session:
                    """
                )
                chain = prompt | self.llm
                response = chain.invoke({
                    "system": system_prompt
                })
            else:
                prompt = PromptTemplate(
                    input_variables=["system", "player_input", "game_state"],
                    template="""
                    {system}

                    Current game state:
                    {game_state}

                    Player input: {player_input}

                    Respond as the game master:
                    """
                )
                chain = prompt | self.llm
                
                max_context = self.config['game_master']['settings']['default_context_length']
                context = "\n".join([
                    f"{'Player' if msg['is_player'] else 'Game Master'}: {msg['text']}" 
                    for msg in state['messages'][-max_context:]
                ])
                
                response = chain.invoke({
                    "system": system_prompt,
                    "player_input": state['context'],
                    "game_state": context
                })
            
            # Mark session as started after first response
            if not state.get('session_started', False):
                state['session_started'] = True
            
            state['messages'].append({
                "text": response.content,
                "is_player": False,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            error_msg = "An unexpected error occurred. Please try again."
            state['messages'].append({
                "text": error_msg,
                "is_player": False,
                "timestamp": datetime.now().isoformat(),
                "is_error": True
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
        next_action="process_input",
        session_started=False
    ) 