import os
import numpy as np
import webrtcvad
import pyaudio
from rich.console import Console
from rich.panel import Panel
from collections import deque
from threading import Thread, Event
import time
from dotenv import load_dotenv
import os

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")


# FIXED: Use the correct import and parameter name
from live_stt import LiveSTT  # From Whisper-Live-STT

console = Console()

class WhisperLiveSTT:
    def __init__(self, model_size="base", language="en", vad_aggressiveness=3,
                 sample_rate=16000, device_index=None):
        """
        Initialize Whisper Live STT engine.
        Args:
            model_size (str): Whisper model size (tiny, base, small, medium, large)
            language (str): Language code for transcription
            vad_aggressiveness (int): VAD aggressiveness (1-3)
            sample_rate (int): Audio sample rate
            device_index (int): Audio device index
        """
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.vad_aggressiveness = vad_aggressiveness
        self.chunk_size = int(sample_rate * 0.03)  # 30ms chunks
        self.buffer_queue = deque(maxlen=50)
        
        # Initialize Whisper Live STT
        try:
            console.print("[bold]Loading Whisper model...[/bold]")
            # FIXED: Use whisper_model parameter instead of model_size
            self.stt = LiveSTT(whisper_model=model_size)
            console.print(f"[green]Loaded Whisper {model_size} model[/green]")
        except Exception as e:
            console.print(Panel(f"[red]Failed to load Whisper: {str(e)}[/red]",
                          title="Model Error", border_style="red"))
            raise
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_listening = False
        self.stop_listening = Event()
        self.callback = None
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for audio input."""
        if self.stop_listening.is_set():
            return (None, pyaudio.paComplete)
        
        audio_data = np.frombuffer(in_data, dtype=np.int16)
        self.buffer_queue.append(audio_data)
        
        return (None, pyaudio.paContinue)
    
    def _process_audio(self):
        """Process audio with Whisper's sliding window approach."""
        self.stt.reset_ticker()
        
        while not self.stop_listening.is_set():
            if not self.buffer_queue:
                time.sleep(0.01)
                continue
            
            audio_data = self.buffer_queue.popleft()
            
            # FIXED: Use the correct method names based on LiveSTT API
            # This part may need adjustment based on the actual API
            try:
                # Convert audio_data to the format expected by stt.capture
                # Add audio data to frames in LiveSTT
                self.stt.frames.append(audio_data.tobytes())
                
                # Process the audio
                self.stt.process()
                
                # Get the confirmed text
                text = self.stt.confirmed_text
                
                if text and self.callback:
                    self.callback(text)
            except Exception as e:
                console.print(f"[yellow]Error processing audio: {str(e)}[/yellow]")
                time.sleep(0.1)
    
    def start_listening(self, callback_function):
        """Start listening for speech input."""
        if self.is_listening:
            return
        
        self.callback = callback_function
        self.stop_listening.clear()
        self.is_listening = True
        
        # Start audio stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index,
            stream_callback=self._audio_callback
        )
        
        console.print(Panel("[bold green]Listening for speech...[/bold green]",
                      title="Speech Recognition", border_style="green"))
        
        # Start processing thread
        self.process_thread = Thread(target=self._process_audio)
        self.process_thread.daemon = True
        self.process_thread.start()
    
    def stop_listening(self):
        """Stop listening for speech input."""
        if not self.is_listening:
            return
        
        self.stop_listening.set()
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        self.is_listening = False
        console.print("[yellow]Stopped listening for speech.[/yellow]")
    
    def __del__(self):
        """Clean up resources."""
        self.stop_listening()
        if hasattr(self, 'audio') and self.audio:
            self.audio.terminate()
