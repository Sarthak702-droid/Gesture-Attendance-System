import cv2
import os
import time
import requests
import threading
from datetime import datetime
from ultralytics import YOLO
from config import (
    LOCK_HOURS_START, LOCK_HOURS_END, 
    TELEGRAM_ALERTS_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    ALERT_DIR
)
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
        
        os.makedirs(ALERT_DIR, exist_ok=True)

    def is_lock_hours(self):
        """
        Checks if the current system time falls within the restricted night lock hours.
        Supports overnight intervals (e.g., 22:00 to 06:00).
        """
        now = datetime.now().time()
        
        try:
            start_time = datetime.strptime(LOCK_HOURS_START, "%H:%M").time()
            end_time = datetime.strptime(LOCK_HOURS_END, "%H:%M").time()
        except ValueError as e:
            print(f"[ERROR] Invalid lock hours format in config.py: {e}. Defaulting to lock active.")
            return True

        if start_time <= end_time:
            # Case 1: Same day lock (e.g. 09:00 to 18:00)
            return start_time <= now <= end_time
        else:
            # Case 2: Overnight lock (e.g. 22:00 to 06:00)
            return now >= start_time or now <= end_time

    def process_frame(self, frame):
        """
        Runs person detection on the frame.
        If an intrusion is detected during lock hours, triggers alert and saves snapshot.
        Returns: (is_intrusion, modified_frame)
        """
        if not self.is_lock_hours():
            return False, frame
            
        results = self.model(frame, verbose=False)
        intrusion_detected = False
        person_bbox = None
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # Class 0 in COCO dataset is 'person'
                if cls_id == 0 and conf >= 0.60:
                    intrusion_detected = True
                    x1, y1, x2, y2 = box.xyxy[0]
                    person_bbox = (int(x1), int(y1), int(x2), int(y2))
                    break  # Stop at first detected intruder
            if intrusion_detected:
                break
                
        if intrusion_detected and person_bbox is not None:
            # Draw red warning box and text on the frame
            x1, y1, x2, y2 = person_bbox
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            cv2.putText(frame, "WARNING: INTRUDER DETECTED", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
            
            # Draw full screen blinking red alert border
            cv2.rectangle(frame, (0, 0), (frame.shape[1], frame.shape[2]), (0, 0, 255), 10)
            
            current_time = time.time()
            if current_time - self.last_alert_time >= self.ALERT_COOLDOWN:
                self.last_alert_time = current_time
                
                # Play alert siren beep sound in a background thread to prevent lag
                threading.Thread(target=self._trigger_siren, daemon=True).start()
                
                # Save snapshot
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                snapshot_name = f"intrusion_{timestamp_str}.jpg"
                snapshot_path = os.path.join(ALERT_DIR, snapshot_name)
                
                # Save a copy of the frame containing the bounding box
                cv2.imwrite(snapshot_path, frame)
                print(f"[SECURITY] Intruder alert! Snapshot saved to {snapshot_path}")
                
                # Send Telegram alert in a background thread
                if TELEGRAM_ALERTS_ENABLED:
                    threading.Thread(
                        target=self._send_telegram, 
                        args=(snapshot_path, timestamp_str), 
                        daemon=True
                    ).start()
                    
        return intrusion_detected, frame

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
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("[WARNING] Telegram credentials not configured. Skipping alert notification.")
            return
            
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        message = f"🚨 *SECURITY INTRUSION ALERT* 🚨\n\n⚠️ An unauthorized person was detected in the office restricted area.\n📅 Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            with open(photo_path, 'rb') as photo:
                payload = {
                    'chat_id': TELEGRAM_CHAT_ID,
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
