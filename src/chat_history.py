import json
import os
from datetime import datetime

class ChatHistoryManager:
    def __init__(self, history_file="chat_history.json", max_history=10):
        """
        Initialize the chat history manager.
        
        Args:
            history_file (str): File to store chat history
            max_history (int): Maximum number of messages to keep in history
        """
        self.history_file = history_file
        self.max_history = max_history
        self.history = self._load_history()

    def _load_history(self):
        """
        Load chat history from file if it exists.
        
        Returns:
            list: Chat history
        """
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading chat history: {e}")
                return []
        return []

    def _save_history(self):
        """
        Save chat history to file.
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.history_file)), exist_ok=True)
            
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"Error saving chat history: {e}")

    def add_to_history(self, role, content):
        """
        Add a message to chat history.
        
        Args:
            role (str): 'user' or 'assistant'
            content (str): Message content
        """
        # Create a new message
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to history
        self.history.append(message)
        
        # Trim history if needed
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
            
        # Save updated history
        self._save_history()

    def get_history(self):
        """
        Get the chat history.
        
        Returns:
            list: Chat history
        """
        return self.history

    def get_formatted_history(self):
        """
        Get a formatted string representation of the chat history.
        
        Returns:
            str: Formatted chat history
        """
        formatted_history = "Previous conversation:\n"
        for msg in self.history:
            role = msg["role"].capitalize()
            content = msg["content"]
            formatted_history += f"{role}: {content}\n\n"
        return formatted_history

    def clear_history(self):
        """
        Clear the chat history.
        """
        self.history = []
        self._save_history()
