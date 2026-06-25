# Configuration for Gesture Attendance System

# Camera source: 0 for webcam, "rtsp://..." for IP cameras
CAMERA_SOURCE = 0

# Directories
EVIDENCE_DIR = "data/evidence"
ALERT_DIR = "data/alerts"
RAW_IMAGES_DIR = "data/raw_images"

# Geolocation Fallbacks (used if mobile GPS is not captured)
DEFAULT_LATITUDE = 28.6139
DEFAULT_LONGITUDE = 77.2090

# Face Recognition Confidence Threshold (For LBPH, lower is more strict. Recommended range: 65.0 - 75.0)
FACE_CONFIDENCE_THRESHOLD = 70.0

# Security Surveillance Mode Toggles
SURVEILLANCE_ENABLED = True
LOCK_HOURS_START = "22:00"  # 10:00 PM (24-hour format)
LOCK_HOURS_END = "06:00"    # 06:00 AM (24-hour format)

# Owner Name for Security Bypass (Intruder detection will bypass for this name)
OWNER_NAME = "Sarthak Tripathy"

# Telegram Alerts Settings (Optional)
TELEGRAM_ALERTS_ENABLED = False
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""


