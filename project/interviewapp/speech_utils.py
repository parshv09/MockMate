import whisper

model = whisper.load_model("base")  # small / base is fine

def transcribe_audio(audio_path):
    result = model.transcribe(audio_path)
    return result.get("text", "").strip()
