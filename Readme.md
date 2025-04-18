# Basic usage with speech enabled (system TTS)
python main.py --speech

# Use ElevenLabs TTS (requires API key in .env)
python main.py --speech --tts-engine elevenlabs

# Use OpenAI TTS (requires API key in .env)
python main.py --speech --tts-engine openai

# Specify custom model paths
python main.py --speech --stt-model /path/to/model.pbmm --stt-scorer /path/to/scorer
