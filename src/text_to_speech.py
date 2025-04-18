import os
from RealtimeTTS import TextToAudioStream
from RealtimeTTS.engines import SystemEngine, ElevenlabsEngine, OpenAIEngine
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
import time

console = Console()
load_dotenv()

class RealtimeTTSHandler:
    def __init__(self, engine_type="system", voice=None):
        """
        Initialize the RealtimeTTS handler.
        
        Args:
            engine_type (str): TTS engine to use ('system', 'elevenlabs', 'openai')
            voice (str): Voice to use for TTS
        """
        self.engine_type = engine_type.lower()
        self.voice = voice
        # self.tts_config = TTSConfig()
        self.tts_engine = self._initialize_engine()
        self.stream = None
        self.speaker = None
        
    def _initialize_engine(self):
        """Initialize the selected TTS engine."""
        try:
            if self.engine_type == "elevenlabs":
                api_key = os.getenv("ELEVENLABS_API_KEY")
                if not api_key:
                    console.print(Panel("[yellow]No ElevenLabs API key found. Falling back to system TTS.[/yellow]", 
                                       title="TTS Warning", border_style="yellow"))
                    return SystemEngine()
                return ElevenlabsEngine(api_key=api_key, voice=self.voice or "Rachel")
                
            elif self.engine_type == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    console.print(Panel("[yellow]No OpenAI API key found. Falling back to system TTS.[/yellow]", 
                                       title="TTS Warning", border_style="yellow"))
                    return SystemEngine()
                return OpenAIEngine(api_key=api_key, voice=self.voice or "alloy")
                
            else:  # Default to system
                return SystemEngine()
                
        except Exception as e:
            console.print(Panel(f"[red]Failed to initialize TTS engine: {str(e)}. Falling back to system TTS.[/red]", 
                               title="TTS Error", border_style="red"))
            return SystemEngine()
            
    def initialize_stream(self):
        """Initialize the TTS stream."""
        try:
            self.stream = TextToAudioStream(self.tts_engine, self.tts_config)
            # self.speaker = TextToStreamSpeaker(self.stream)
            console.print("[green]TTS stream initialized successfully.[/green]")
            return True
        except Exception as e:
            console.print(Panel(f"[red]Failed to initialize TTS stream: {str(e)}[/red]", 
                               title="TTS Error", border_style="red"))
            return False
            
    def speak(self, text):
        """Convert text to speech.
        
        Args:
            text (str): Text to convert to speech
        """
        if not self.stream:
            if not self.initialize_stream():
                console.print("[yellow]Using print fallback since TTS failed to initialize.[/yellow]")
                console.print(Panel(text, title="Bot (Text Fallback)", border_style="blue"))
                return
                
        try:
            # Show the text that's being spoken
            console.print(Panel(text, title="Bot (Speaking)", border_style="cyan"))
            
            self.speaker.say(text)
            
            # Wait for speaking to finish
            while self.speaker.is_speaking():
                time.sleep(0.1)
                
            return True
        except Exception as e:
            console.print(Panel(f"[red]Failed to speak text: {str(e)}[/red]", 
                               title="TTS Error", border_style="red"))
            console.print(Panel(text, title="Bot (Text Fallback)", border_style="blue"))
            return False
            
    def set_engine(self, engine_type, voice=None):
        """Change the TTS engine.
        
        Args:
            engine_type (str): TTS engine to use ('system', 'elevenlabs', 'openai')
            voice (str): Voice to use for TTS
        """
        self.engine_type = engine_type.lower()
        self.voice = voice
        self.tts_engine = self._initialize_engine()
        
        # Re-initialize stream with new engine
        if self.stream:
            self.stream.close()
            self.stream = None
            self.speaker = None
            
        return self.initialize_stream()
        
    def set_config(self, rate=1.0, volume=1.0, pitch=1.0):
        """Set TTS configuration parameters.
        
        Args:
            rate (float): Speaking rate multiplier
            volume (float): Volume level
            pitch (float): Pitch multiplier
        """
        self.tts_config.rate = rate
        self.tts_config.volume = volume
        self.tts_config.pitch = pitch
        
        # Re-initialize stream with new config
        if self.stream:
            self.stream.close()
            self.stream = None
            self.speaker = None
            
        return self.initialize_stream()
        
    def close(self):
        """Close the TTS stream."""
        if self.stream:
            self.stream.close()
            self.stream = None
            self.speaker = None
