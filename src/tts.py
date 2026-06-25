import os
import requests
import winsound
import threading

API_KEY = "sk_fa2jy613_Zv4AKJOpp1ysNd8pXCbRBaIH"
API_URL = "https://api.sarvam.ai/text-to-speech/stream"

def play_login_greeting_tts(name):
    """
    Plays a welcome voice greeting in Odia (female Pooja voice) when the user logs in at the terminal.
    Runs asynchronously in a background thread.
    """
    display_name = name.replace("_", " ")
    
    # Check if owner or employee
    import config
    owner_name = getattr(config, "OWNER_NAME", "Sarthak Tripathy").strip().lower()
    
    if display_name.strip().lower() == owner_name:
        text = f"ସ୍ୱାଗତ ମାଲିକ, {display_name}।"  # "Welcome Owner, Sarthak Tripathy"
    else:
        text = f"ସ୍ୱାଗତ କର୍ମଚାରୀ, {display_name}।"  # "Welcome Employee, <Name>"
        
    def run_greeting():
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
                "output_audio_codec": "wav",
                "enable_preprocessing": True
            }
            
            response = requests.post(API_URL, headers=headers, json=payload, timeout=5.0)
            if response.status_code == 200:
                os.makedirs("data", exist_ok=True)
                temp_wav = os.path.join("data", "temp_login_tts.wav")
                with open(temp_wav, "wb") as f:
                    f.write(response.content)
                winsound.PlaySound(temp_wav, winsound.SND_FILENAME)
        except Exception as e:
            print(f"[WARNING] Login greeting voice error: {e}")
            
    threading.Thread(target=run_greeting, daemon=True).start()


def play_attendance_tts(name, status):
    """
    Calls Sarvam AI's streaming Text-to-Speech API to generate and play Odia female voice feedback
    when attendance is logged.
    """
    # Normalize name to human readable (replace underscores with spaces)
    display_name = name.replace("_", " ")
    
    # Formulate Odia speech text:
    # "Welcome, <Name>" -> "<Name>, ଆପଣଙ୍କୁ ସ୍ୱାଗତ।"
    # "See you soon, <Name>" -> "<Name>, ପୁଣି ଦେଖାହେବା।"
    if status.upper() in ["IN", "URGENT_RETURN"]:
        text = f"{display_name}, ଆପଣଙ୍କୁ ସ୍ୱାଗତ।"
    elif status.upper() in ["OUT", "URGENT_EXIT"]:
        text = f"{display_name}, ପୁଣି ଦେଖାହେବା।"
    else:
        text = f"{display_name}, ଧନ୍ୟବାଦ।"
        
    try:
        headers = {
            "api-subscription-key": API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "target_language_code": "od-IN",
            "speaker": "pooja",  # Pooja is the standard female Odia voice
            "model": "bulbul:v3",
            "pace": 1,
            "speech_sample_rate": 22050,
            "output_audio_codec": "wav",  # winsound requires wav format
            "enable_preprocessing": True
        }
        
        print(f"[INFO] Requesting Odia female voice (Pooja) TTS for {display_name} ({status})...")
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
