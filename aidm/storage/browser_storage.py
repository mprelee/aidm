from typing import Dict, List, Optional
from datetime import datetime
import json

class BrowserStorage:
    """
    Client-side storage implementation using browser's localStorage.
    This is just the Python interface - the actual storage happens in JavaScript.
    """
    
    @staticmethod
    def save_game(name: str, messages: List[Dict], timestamp: Optional[str] = None) -> Dict:
        """Format game data for browser storage"""
        return {
            'messages': messages,
            'timestamp': timestamp or datetime.now().isoformat()
        }

    @staticmethod
    def format_message(text: str, is_player: bool, timestamp: Optional[str] = None) -> Dict:
        """Format a message for storage"""
        return {
            'text': text,
            'isPlayer': is_player,
            'timestamp': timestamp or datetime.now().isoformat()
        } 