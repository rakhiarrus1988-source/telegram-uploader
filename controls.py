import asyncio
import os

async def get_user_action(prompt_msg="Press Enter to continue, or type 's' to skip, 'b' to go back, 'q' to quit: "):
    """
    Get user action via input (runs in thread to not block event loop).
    Returns: 'continue', 'skip', 'back', 'quit'
    """
    try:
        # Run input in a thread to avoid blocking the async loop
        action = await asyncio.to_thread(input, prompt_msg)
        action = action.strip().lower()
        if action == 's':
            return 'skip'
        elif action == 'b':
            return 'back'
        elif action == 'q':
            return 'quit'
        else:
            return 'continue'
    except Exception:
        return 'continue'

def save_control_state(state_file='control_state.json', data=None):
    """Save current state for resume (file index, etc.)"""
    import json
    try:
        with open(state_file, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def load_control_state(state_file='control_state.json'):
    import json
    try:
        with open(state_file, 'r') as f:
            return json.load(f)
    except:
        return None