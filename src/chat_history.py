import json
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

console = Console()

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
                console.print(Panel(f"[red]Error loading chat history: {e}[/red]", title="Chat History Error", border_style="red"))
                return []
        return []
    
    def _save_history(self):
        """
        Save chat history to file.
        """
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            console.print(Panel(f"[red]Error saving chat history: {e}[/red]", title="Chat History Error", border_style="red"))
    
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
        formatted_history = "[bold]Previous conversation:[/bold]\n"
        
        for msg in self.history:
            role = msg["role"].capitalize()
            content = msg["content"]
            formatted_history += f"[cyan]{role}[/cyan]: {content}\n\n"
        
        return formatted_history
    
    def clear_history(self):
        """
        Clear the chat history.
        """
        self.history = []
        self._save_history()
        console.print(Panel("[yellow]Chat history cleared.[/yellow]", title="Chat History", border_style="yellow"))