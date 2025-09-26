import json
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StateManager:
    """
    Manages the persistent state of the bot, such as the watchlist.
    """
    def __init__(self, config: Dict[str, Any]):
        # Define the path for the state file inside the data directory
        self.state_filepath = os.path.join('data', 'bot_state.json')
        self.config = config
        self._ensure_state_file_exists()

    def _ensure_state_file_exists(self):
        """
        Ensures the state file exists. If not, it creates it with the
        watchlist from the initial configuration.
        """
        if not os.path.exists(self.state_filepath):
            logger.info("State file not found. Creating a new one from initial config.")
            # Get the initial watchlist from the main config file
            initial_watchlist = self.config.get('trading', {}).get('WATCHLIST', [])
            initial_state = {'watchlist': initial_watchlist}
            self.save_state(initial_state)

    def load_state(self) -> Dict[str, Any]:
        """
        Loads the entire state (including the watchlist) from the JSON file.
        """
        try:
            with open(self.state_filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Could not load state file: {e}. Returning default state.")
            # Fallback to initial config if file is corrupted or missing
            return {'watchlist': self.config.get('trading', {}).get('WATCHLIST', [])}

    def save_state(self, state: Dict[str, Any]):
        """
        Saves the entire state to the JSON file.
        """
        try:
            with open(self.state_filepath, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            logger.error(f"Could not save state to file: {e}")

    def get_watchlist(self) -> List[str]:
        """Convenience method to get just the watchlist from the state."""
        state = self.load_state()
        return state.get('watchlist', [])

    def update_watchlist(self, new_watchlist: List[str]):
        """Convenience method to update the watchlist in the state."""
        state = self.load_state()
        state['watchlist'] = sorted(list(set(new_watchlist))) # Ensure unique and sorted
        self.save_state(state)