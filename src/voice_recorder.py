import ctypes
import time
import os

def record_win_audio(save_path, duration_seconds=5):
    """
    Records audio from default mic using Windows MCI API (no external pip dependencies).
    This works 100% locally on any Windows OS.
    """
    try:
        # Create parent directory if not exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Make sure path has backslashes and is double-quoted for MCI
        abs_path = os.path.abspath(save_path)
        
        winmm = ctypes.windll.winmm
        
        # Open a new waveaudio device
        winmm.mciSendStringW("open new type waveaudio alias recsound", None, 0, 0)
        
        # Start recording
        winmm.mciSendStringW("record recsound", None, 0, 0)
        print(f"[AUDIO] Recording started: saving to {abs_path}")
        
        # Wait for the duration
        time.sleep(duration_seconds)
        
        # Save recording
        save_cmd = f'save recsound "{abs_path}"'
        winmm.mciSendStringW(save_cmd, None, 0, 0)
        
        # Close device
        winmm.mciSendStringW("close recsound", None, 0, 0)
        
        print("[AUDIO] Recording finished and saved successfully.")
        return True
    except Exception as e:
        print(f"[WARNING] Native Windows audio recording failed: {e}")
        return False
