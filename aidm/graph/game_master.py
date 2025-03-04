from typing import Annotated, TypedDict
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver
import yaml
import os

class GameState(TypedDict):
    # Use Annotated to specify how messages should be updated
    messages: Annotated[list, "add_messages"]
    session_started: bool

class GameMasterGraph:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.llm = self._init_llm()
        self.memory = MemorySaver()  # Add memory checkpointing
        self.workflow = self._create_graph()

    def _load_config(self, config_path: str) -> dict:
        # Try loading from current directory first
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        
        # Try loading from package directory
        package_config = os.path.join(os.path.dirname(__file__), '..', config_path)
        if os.path.exists(package_config):
            with open(package_config, 'r') as f:
                return yaml.safe_load(f)
            
        raise FileNotFoundError(f"Could not find config file at {config_path} or {package_config}")

    def _init_llm(self) -> ChatOpenAI:
        model_config = self.config['model']
        return ChatOpenAI(
            model=model_config['name'],
            temperature=model_config['temperature'],
            max_tokens=model_config['max_tokens']
        )

    def _get_system_prompt(self) -> str:
        prompts = self.config['game_master']['prompts']
        settings = self.config['game_master']['settings']
        rules = self.config['game_master']['rules']
        
        return prompts['initial'].format(
            genre=settings['genre'],
            rules_system=rules['system']
        )

    def _game_master_node(self, state: GameState) -> GameState:
        try:
            # Convert state messages to LangChain message format
            messages = []
            
            # Add conversation history
            max_context = self.config['game_master']['session']['max_context_messages']
            history = state['messages']
            context_messages = history[-max_context:] if len(history) > max_context else history
            
            # Add system prompt first
            messages.append({"role": "system", "content": self._get_system_prompt()})
            
            # Add conversation history
            for msg in context_messages:
                if msg['is_player']:
                    messages.append(HumanMessage(content=msg['text']))
                else:
                    messages.append(AIMessage(content=msg['text']))

            # Create prompt with message history
            prompt = ChatPromptTemplate.from_messages([
                ("system", self._get_system_prompt()),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}" if state.get('session_started', False) else self.config['game_master']['prompts']['session_start'])
            ])

            # Create chain
            chain = prompt | self.llm

            # Get response
            response = chain.invoke({
                "history": messages,
                "input": state['messages'][-1]['text'] if state['messages'] and state.get('session_started', False) else ""
            })

            if not state.get('session_started', False):
                state['session_started'] = True

            # Add response to state
            state['messages'].append({
                "text": response.content,
                "is_player": False,
                "timestamp": datetime.now().isoformat()
            })

            # Continue the conversation
            state['next'] = "game_master"

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
        
        # Add game master node
        workflow.add_node("game_master", self._game_master_node)
        
        # Set entry point
        workflow.add_edge(START, "game_master")
        
        # Add edges for continuing conversation
        workflow.add_conditional_edges(
            "game_master",
            lambda x: x.get("next", "game_master"),
            {
                "game_master": "game_master"  # Continue conversation
            }
        )
        
        # Compile with memory checkpointer
        return workflow.compile(checkpointer=self.memory)

    def invoke(self, state: GameState, config: dict) -> GameState:
        # Pass config to maintain conversation thread
        return self.workflow.invoke(state, config)

def create_game_state() -> GameState:
    return GameState(
        messages=[],
        session_started=False
    ) 