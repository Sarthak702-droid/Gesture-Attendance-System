import os
import requests
import winsound

API_KEY = "sk_fa2jy613_Zv4AKJOpp1ysNd8pXCbRBaIH"
API_URL = "https://api.sarvam.ai/text-to-speech/stream"

def play_attendance_tts(name, status):
    """
    Calls Sarvam AI's streaming Text-to-Speech API to generate and play Odia voice feedback
    when attendance is logged.
    """
    # Formulate Odia speech text
    # Pooja voice speaking in od-IN (Odia)
    if status.upper() == "IN":
        text = f"{name}, ଆପଣଙ୍କର ଚେକ୍-ଇନ୍ ସଫଳ ହେଲା।"
    elif status.upper() == "OUT":
        text = f"{name}, ଆପଣଙ୍କର ଚେକ୍-ଆଉଟ୍ ସଫଳ ହେଲା।"
    elif status.upper() == "URGENT_EXIT":
        text = f"{name}, ଆପଣଙ୍କର ପ୍ରସ୍ଥାନ ସଫଳ ହେଲା।"
    elif status.upper() == "URGENT_RETURN":
        text = f"{name}, ଆପଣଙ୍କର ପ୍ରତ୍ୟାବର୍ତ୍ତନ ସଫଳ ହେଲା।"
    else:
        text = f"{name}, ଆପଣଙ୍କର ଅଟେଣ୍ଡାନ୍ସ ସଫଳ ହେଲା।"
        
    try:
        headers = {
            "api-subscription-key": API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "target_language_code": "od-IN",
            "speaker": "pooja",
            "model": "bulbul:v3",
            "pace": 1,
            "speech_sample_rate": 22050,
            "output_audio_codec": "wav",  # winsound requires wav format
            "enable_preprocessing": True
        }
        
        print(f"[INFO] Requesting Odia TTS for {name} ({status})...")
        response = requests.post(API_URL, headers=headers, json=payload, timeout=5.0)
        
        if response.status_code == 200:
            os.makedirs("data", exist_ok=True)
            temp_wav = os.path.join("data", "temp_tts.wav")
            
            with open(temp_wav, "wb") as f:
                f.write(response.content)
                
            print(f"[INFO] Playing Odia confirmation voice feedback...")
            # Play WAV synchronously so it doesn't get cut off before the main process exits
            winsound.PlaySound(temp_wav, winsound.SND_FILENAME)
        else:
            print(f"[WARNING] Sarvam AI API returned error status {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"[WARNING] Failed to fetch or play Odia TTS: {e}")
