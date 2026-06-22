# Global Configurations for Gesture Attendance & Security System

# Camera stream source. 
# Set to:
# - An integer (e.g., 0, 1) for local USB webcams.
# - A string URL (e.g., "rtsp://username:password@ip_address:554/h264") for IP security cameras.
# - A string path to a video file for testing.
CAMERA_SOURCE = 0

# Security Features Toggles
FACE_RECOGNITION_ENABLED = True
SURVEILLANCE_ENABLED = True

# Intrusion Detection Night Surveillance Hours (24-hour format "HH:MM")
# Active period starts at LOCK_HOURS_START and runs until LOCK_HOURS_END.
LOCK_HOURS_START = "22:00"  # 10:00 PM
LOCK_HOURS_END = "06:00"    # 06:00 AM

# Notification Settings (Optional)
# If enabled, the system will send alert messages and snapshots to your Telegram channel.
TELEGRAM_ALERTS_ENABLED = False
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Paths
ALERT_DIR = "data/alerts"
FACES_DIR = "data/faces"
FACE_MODEL_PATH = "models/face_recognizer.yml"
