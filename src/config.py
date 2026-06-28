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

# Liveness (Anti-Spoofing) Detection Threshold
# Laplacian variance of face crop. Blurry print photos have low variance (< 60),
# screens have very high variance due to screen glare/pixel-grids.
LIVENESS_THRESHOLD = 60.0

# HR Payroll & Cost Center Settings
OFFICE_START_TIME = "09:00"  # Expected check-in time (24-hour format)
OFFICE_END_TIME = "17:00"    # Expected check-out time (24-hour format)
HOURLY_RATE = 500.0          # Employee hourly pay rate
LATE_PENALTY_RATE = 100.0    # Deducted amount per late arrival

# Network & Challenge Verification
VALIDATE_OFFICE_NETWORK = True
ALLOWED_LOCAL_SUBNET = "192.168"
LIVENESS_CHALLENGE_ENABLED = True

# Load dynamic configurations at startup
import json
import os
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "config.json")
if not os.path.exists(config_path):
    config_path = os.path.join("data", "config.json")

OWNER_EXEMPT_LATE = True

def reload_config():
    global OWNER_NAME, OWNER_EXEMPT_LATE, OFFICE_START_TIME, OFFICE_END_TIME
    global LIVENESS_CHALLENGE_ENABLED, VALIDATE_OFFICE_NETWORK, ALLOWED_LOCAL_SUBNET
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as _f:
                _dyn_config = json.load(_f)
                OWNER_NAME = _dyn_config.get("owner_name", OWNER_NAME)
                OWNER_EXEMPT_LATE = _dyn_config.get("owner_exempt_late", OWNER_EXEMPT_LATE)
                OFFICE_START_TIME = _dyn_config.get("office_start_time", OFFICE_START_TIME)
                OFFICE_END_TIME = _dyn_config.get("office_end_time", OFFICE_END_TIME)
                LIVENESS_CHALLENGE_ENABLED = _dyn_config.get("liveness_challenge_enabled", LIVENESS_CHALLENGE_ENABLED)
                VALIDATE_OFFICE_NETWORK = _dyn_config.get("validate_office_network", VALIDATE_OFFICE_NETWORK)
                ALLOWED_LOCAL_SUBNET = _dyn_config.get("allowed_local_subnet", ALLOWED_LOCAL_SUBNET)
        except Exception as _e:
            print(f"[WARNING] Failed to load dynamic config from config.json: {_e}")

reload_config()


