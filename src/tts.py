import os
import subprocess
import threading

def speak_text_async(phrase):
    """
    Helper to speak English text asynchronously using Windows PowerShell Speech Synthesizer.
    This runs entirely offline, requires zero external pip packages, and doesn't block.
    """
    def speak():
        try:
            safe_phrase = phrase.replace("'", "''")
            cmd = f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Speak('{safe_phrase}')"
            subprocess.run(["powershell", "-Command", cmd], capture_output=True)
        except Exception as e:
            print(f"[WARNING] Speech synthesis error: {e}")
            
    t = threading.Thread(target=speak, daemon=True)
    t.start()

def play_login_greeting_tts(name):
    """
    Plays a welcome voice greeting in English when the user logs in at the terminal.
    """
    display_name = name.replace("_", " ")
    
    # Check if owner or employee
    import config
    owner_name = getattr(config, "OWNER_NAME", "Sarthak Tripathy").strip().lower()
    
    if display_name.strip().lower() == owner_name:
        phrase = f"Welcome Owner, {display_name}"
    else:
        phrase = f"Welcome Employee, {display_name}"
        
    print(f"[INFO] Speaking login greeting: '{phrase}'")
    speak_text_async(phrase)

def play_attendance_tts(name, status):
    """
    Plays a confirmation voice greeting in English when attendance is logged.
    """
    display_name = name.replace("_", " ")
    
    if status.upper() in ["IN", "URGENT_RETURN"]:
        phrase = f"Welcome, {display_name}"
    elif status.upper() in ["OUT", "URGENT_EXIT"]:
        phrase = f"See you soon, {display_name}"
    else:
        phrase = f"Thank you, {display_name}"
        
    print(f"[INFO] Speaking attendance confirmation: '{phrase}'")
    speak_text_async(phrase)
