import cv2
import os
import time
import requests
import threading
from datetime import datetime
from ultralytics import YOLO
import config
from utils import play_beep_sound

class SurveillanceSystem:
    def __init__(self):
        """
        Intrusion detection surveillance system.
        Detects humans during night lock hours and triggers alerts/snapshots.
        """
        # Load the default pretrained YOLOv8 model for person detection (Class 0: person)
        print("[INFO] Loading YOLOv8 model for person detection surveillance...")
        self.model = YOLO("yolov8n.pt")
        
        self.last_alert_time = 0
        self.ALERT_COOLDOWN = 15  # seconds between saving snapshots/sending notifications
        
        alert_dir = getattr(config, "ALERT_DIR", "data/alerts")
        os.makedirs(alert_dir, exist_ok=True)

    def is_lock_hours(self):
        """
        Checks if the current system time falls within the restricted night lock hours.
        Supports overnight intervals (e.g., 22:00 to 06:00).
        """
        now = datetime.now().time()
        
        lock_start = getattr(config, "LOCK_HOURS_START", "22:00")
        lock_end = getattr(config, "LOCK_HOURS_END", "06:00")
        
        try:
            start_time = datetime.strptime(lock_start, "%H:%M").time()
            end_time = datetime.strptime(lock_end, "%H:%M").time()
        except ValueError as e:
            print(f"[ERROR] Invalid lock hours format in config.py: {e}. Defaulting to lock active.")
            return True

        if start_time <= end_time:
            # Case 1: Same day lock (e.g. 09:00 to 18:00)
            return start_time <= now <= end_time
        else:
            # Case 2: Overnight lock (e.g. 22:00 to 06:00)
            return now >= start_time or now <= end_time

    def detect_person(self, frame):
        """
        Runs person detection on the frame using YOLOv8.
        Returns: (person_detected, person_bbox)
        """
        results = self.model(frame, verbose=False)
        person_detected = False
        person_bbox = None
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Class 0 in COCO dataset is 'person'
                if cls_id == 0 and conf >= 0.60:
                    person_detected = True
                    x1, y1, x2, y2 = box.xyxy[0]
                    person_bbox = (int(x1), int(y1), int(x2), int(y2))
                    break  # Stop at first detected person
            if person_detected:
                break
                
        return person_detected, person_bbox

    def trigger_alert(self, frame, person_bbox, owner_verified=False):
        """
        Triggers intrusion alert if a person is detected and NOT verified as owner.
        """
        if owner_verified:
            # Owner is present, do not sound alarm
            return
            
        current_time = time.time()
        if current_time - self.last_alert_time >= self.ALERT_COOLDOWN:
            self.last_alert_time = current_time
            
            # Play alert siren beep sound in a background thread to prevent camera lag
            threading.Thread(target=self._trigger_siren, daemon=True).start()
            
            # Save snapshot
            alert_dir = getattr(config, "ALERT_DIR", "data/alerts")
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_name = f"intrusion_{timestamp_str}.jpg"
            snapshot_path = os.path.join(alert_dir, snapshot_name)
            
            # Save a copy of the frame containing the bounding box
            cv2.imwrite(snapshot_path, frame)
            print(f"[SECURITY] Intruder alert! Snapshot saved to {snapshot_path}")
            
            # Log the security incident in security_logs.json
            try:
                import json
                logs_path = os.path.join("data", "security_logs.json")
                logs = []
                if os.path.exists(logs_path):
                    with open(logs_path, "r", encoding="utf-8") as lf:
                        try:
                            logs = json.load(lf)
                        except Exception:
                            logs = []
                
                new_log = {
                    "id": f"sec_{int(current_time)}",
                    "timestamp": datetime.now().isoformat() + "Z",
                    "snapshot_name": snapshot_name,
                    "status": "UNAUTHORIZED INTRUSION"
                }
                logs.append(new_log)
                
                with open(logs_path, "w", encoding="utf-8") as lf:
                    json.dump(logs, lf, indent=2)
                
                # Push the snapshot and log to GitHub
                from attendance import git_push_logs_async
                git_push_logs_async()
            except Exception as ex:
                print(f"[WARNING] Failed to write security logs: {ex}")
            
            # Send Telegram alert in a background thread
            telegram_enabled = getattr(config, "TELEGRAM_ALERTS_ENABLED", False)
            if telegram_enabled:
                threading.Thread(
                    target=self._send_telegram, 
                    args=(snapshot_path, timestamp_str), 
                    daemon=True
                ).start()

    def _trigger_siren(self):
        """Plays double security warning beep."""
        try:
            import winsound
            winsound.Beep(900, 300)
            time.sleep(0.1)
            winsound.Beep(900, 300)
        except Exception:
            pass

    def _send_telegram(self, photo_path, timestamp):
        """Sends alert message and photo snapshot to Telegram channel via Bot API."""
        bot_token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
        chat_id = getattr(config, "TELEGRAM_CHAT_ID", "")
        
        if not bot_token or not chat_id:
            print("[WARNING] Telegram credentials not configured. Skipping alert notification.")
            return
            
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        message = f"🚨 *SECURITY INTRUSION ALERT* 🚨\n\n⚠️ An unauthorized person was detected in the office restricted area.\n📅 Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            with open(photo_path, 'rb') as photo:
                payload = {
                    'chat_id': chat_id,
                    'caption': message,
                    'parse_mode': 'Markdown'
                }
                files = {
                    'photo': photo
                }
                response = requests.post(url, data=payload, files=files, timeout=10)
                if response.status_code == 200:
                    print("[SECURITY] Telegram alert notification sent successfully!")
                else:
                    print(f"[ERROR] Telegram alert failed with code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[ERROR] Failed to send Telegram alert: {e}")
