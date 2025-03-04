from pathlib import Path
import json
from typing import List
from ..graph.game_master import GameState, create_game_state

class SaveManager:
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def get_checkpoint_path(self, save_name: str) -> Path:
        return self.checkpoint_dir / f"{save_name}.json"

    def save_checkpoint(self, state: GameState, save_name: str):
        checkpoint_path = self.get_checkpoint_path(save_name)
        with open(checkpoint_path, 'w') as f:
            json.dump(state, f, indent=2)

    def load_checkpoint(self, save_name: str) -> GameState:
        checkpoint_path = self.get_checkpoint_path(save_name)
        if not checkpoint_path.exists():
            return create_game_state()
        
        try:
            with open(checkpoint_path, 'r') as f:
                state_dict = json.load(f)
                return GameState(**state_dict)
        except:
            return create_game_state()

    def get_all_saves(self) -> List[str]:
        saves = [f.stem for f in self.checkpoint_dir.glob("*.json") 
                if f.stem.lower() != "autosave"]
        return sorted(saves) 