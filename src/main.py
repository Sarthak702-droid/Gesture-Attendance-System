import cv2
import os
import time
import pickle
from detect_gesture import GestureDetector
from attendance import mark_attendance
from utils import draw_premium_hud, draw_corner_rect, play_beep_sound, CameraStream
from gps_server import start_gps_server, get_local_ip
import gps_server
import config

def get_student_name():
    print("\n" + "="*50)
    print("      AI GESTURE ATTENDANCE SYSTEM - LOGIN")
    print("="*50)
    name = input("Enter Employee Name or ID (Press ENTER for Guest): ").strip()
    if not name:
        name = "Guest_Employee"
    print(f"[INFO] System initialized for employee: {name.upper()}")
    print("[INFO] Instructions:")
    print("  👍 Thumbs Up   -> Select 'IN' (Check-In)")
    print("  ✌️ Peace Sign  -> Select 'OUT' (Check-Out)")
    print("  ☝️ Index Up    -> Select 'URGENT EXIT' (Break Out)")
    print("  🖖 3-Fingers   -> Select 'URGENT RETURN' (Break In)")
    print("  ✋ Open Palm  -> 'CONFIRM' (Logs to Excel and Closes)")
    print("  ✊ Fist        -> 'CANCEL' pending state")
    print("="*50 + "\n")
    return name

def main():
    # Prompt for employee name
    employee_name = get_student_name()
    
    # Start the local GPS web server in the background
    local_ip = get_local_ip()
    start_gps_server()
    
    # Initialize MediaPipe gesture detector
    detector = GestureDetector()
    
    # Load Face Recognizer if trained
    face_model_path = os.path.join("models", "face_recognizer.xml")
    face_labels_path = os.path.join("models", "face_labels.pkl")
    face_recognizer = None
    face_labels = {}
    face_detector = None
    
    if os.path.exists(face_model_path) and os.path.exists(face_labels_path):
        try:
            import mediapipe as mp
            mp_face = mp.solutions.face_detection
            face_detector = mp_face.FaceDetection(min_detection_confidence=0.6)
            face_recognizer = cv2.face.LBPHFaceRecognizer_create()
            face_recognizer.read(face_model_path)
            with open(face_labels_path, "rb") as f:
                face_labels = pickle.load(f)
            print("[INFO] Face recognition system initialized successfully.")
        except Exception as e:
            print(f"[WARNING] Failed to load face recognizer: {e}")
    else:
        print("[WARNING] Face recognition model or labels map not found. Running in gesture-only bypass mode.")
    
    # Start Camera Stream
    print(f"[INFO] Initializing camera stream from source: {config.CAMERA_SOURCE}")
    cap = CameraStream(config.CAMERA_SOURCE).start()
    
    # Check if camera opened successfully
    test_grabbed, _ = cap.read()
    if not test_grabbed:
        print("[ERROR] Could not open camera stream. Check camera connection in config.py")
        cap.release()
        return
        
    cv2.namedWindow("Gesture Attendance System", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Gesture Attendance System", 1000, 750)
    
    # Bounding box & tracking states
    active_gesture = None
    consecutive_frames = 0
    REQUIRED_FRAMES = 15  # 0.5 seconds at 30 FPS for fast response
    
    pending_status = None  # Can be "IN", "OUT", "URGENT_EXIT", "URGENT_RETURN"
    last_log_message = "Show Thumbs Up (👍) for IN, Peace (✌️) for OUT, Index Up (☝️) for Exit, or 3-Fingers for Return."
    
    print(f"[INFO] Attendance ready. Show a selection gesture to begin.")
    
    while True:
        grabbed, frame = cap.read()
        if not grabbed or frame is None:
            time.sleep(0.1)
            continue
            
        # Flip frame horizontally if using local USB/laptop webcam
        if isinstance(config.CAMERA_SOURCE, int):
            frame = cv2.flip(frame, 1)
            
        h, w, _ = frame.shape
        
        # 1. Run Face Detection & Recognition
        face_verified = False
        face_name_detected = "UNKNOWN"
        face_bbox = None
        
        if face_detector is not None and face_recognizer is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = face_detector.process(rgb_frame)
            
            if face_results.detections:
                detection = face_results.detections[0]
                bbox_data = detection.location_data.relative_bounding_box
                fx = int(bbox_data.xmin * w)
                fy = int(bbox_data.ymin * h)
                fwidth = int(bbox_data.width * w)
                fheight = int(bbox_data.height * h)
                
                # Clamp coordinates to frame boundary
                fx1 = max(0, fx)
                fy1 = max(0, fy)
                fx2 = min(w, fx + fwidth)
                fy2 = min(h, fy + fheight)
                
                face_bbox = (fx1, fy1, fx2, fy2)
                
                # Crop and predict
                face_crop = frame[fy1:fy2, fx1:fx2]
                if face_crop.size > 0:
                    gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                    resized_crop = cv2.resize(gray_crop, (200, 200), interpolation=cv2.INTER_AREA)
                    
                    label_id, confidence = face_recognizer.predict(resized_crop)
                    # For LBPH, confidence represents distance (lower distance means better match)
                    if confidence < 95.0:
                        face_name_detected = face_labels.get(label_id, "UNKNOWN")
                        
                        # Match login employee name against face name (case-insensitive substring check)
                        login_name_clean = employee_name.strip().lower()
                        detected_name_clean = face_name_detected.lower()
                        
                        if login_name_clean in detected_name_clean or detected_name_clean in login_name_clean:
                            face_verified = True
                            
        # Draw Face Overlay
        if face_bbox is not None:
            face_color = (0, 255, 0) if face_verified else (0, 0, 255)
            draw_corner_rect(frame, face_bbox, color=face_color, thickness=2)
            face_label_text = f"{face_name_detected.upper()} (VERIFIED)" if face_verified else "FACE UNVERIFIED / MISMATCH"
            cv2.putText(frame, face_label_text, (face_bbox[0], face_bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 2, cv2.LINE_AA)
        
        # 2. Run MediaPipe Hands detector
        detections = detector.detect(frame, conf_threshold=0.60)
        
        detected_gesture = None
        hand_bbox = None
        
        for d in detections:
            if d["class_name"] in ["open_palm", "peace", "thumbs_up", "fist", "pointing_up", "three_fingers"]:
                detected_gesture = d["class_name"]
                hand_bbox = d["box"]
                break
                
        # Draw hand bounding box if gesture detected
        if detected_gesture is not None and hand_bbox is not None:
            color_map = {
                "open_palm": (255, 255, 0),       # Cyan
                "peace": (255, 0, 255),           # Magenta
                "thumbs_up": (0, 255, 0),         # Neon Green
                "fist": (0, 0, 255),               # Red
                "pointing_up": (0, 165, 255),      # Orange
                "three_fingers": (255, 191, 0)     # Amber/Yellowish
            }
            box_color = color_map.get(detected_gesture, (255, 255, 255))
            draw_corner_rect(frame, hand_bbox, color=box_color, thickness=3)
            
            # Label overlay above the box
            label_text = f"{detected_gesture.upper()}"
            cv2.putText(frame, label_text, (hand_bbox[0], hand_bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2, cv2.LINE_AA)
            
        # 3. Check action validity based on current state and face verification
        face_required_gestures = ["thumbs_up", "peace", "open_palm", "pointing_up", "three_fingers"]
        face_ok = True
        if face_recognizer is not None and detected_gesture in face_required_gestures:
            face_ok = face_verified
            
        is_valid_action = False
        if face_ok:
            if detected_gesture in ["thumbs_up", "peace", "pointing_up", "three_fingers"] and pending_status is None:
                is_valid_action = True
            elif detected_gesture == "open_palm" and pending_status is not None:
                is_valid_action = True
            elif detected_gesture == "fist" and pending_status is not None:
                is_valid_action = True
        else:
            if detected_gesture in face_required_gestures:
                last_log_message = "Face verification required! Show your face clearly."
            
        if is_valid_action:
            if detected_gesture == active_gesture:
                consecutive_frames += 1
            else:
                active_gesture = detected_gesture
                consecutive_frames = 1
        else:
            active_gesture = None
            consecutive_frames = 0
            
        # Calculate hold progress ratio
        hold_ratio = min(1.0, consecutive_frames / REQUIRED_FRAMES)
        
        # Format Geolocation text for screen HUD
        gps_lat = gps_server.GPS_DATA["latitude"]
        gps_lon = gps_server.GPS_DATA["longitude"]
        
        if gps_lat is not None and gps_lon is not None:
            location_hud = f"GPS: CONNECTED ({gps_lat:.5f}, {gps_lon:.5f})"
        else:
            location_hud = f"GPS SCAN: Open http://{local_ip}:5000 on mobile"
            
        # Trigger Attendance on complete hold progress
        if consecutive_frames >= REQUIRED_FRAMES and active_gesture is not None:
            if active_gesture == "thumbs_up" and pending_status is None:
                pending_status = "IN"
                last_log_message = "Selected: IN. Hold Palm (✋) to Confirm or Fist (✊) to Cancel."
                play_beep_sound(success=True)
            elif active_gesture == "peace" and pending_status is None:
                pending_status = "OUT"
                last_log_message = "Selected: OUT. Hold Palm (✋) to Confirm or Fist (✊) to Cancel."
                play_beep_sound(success=True)
            elif active_gesture == "pointing_up" and pending_status is None:
                pending_status = "URGENT_EXIT"
                last_log_message = "Selected: URGENT EXIT. Hold Palm (✋) to Confirm or Fist (✊) to Cancel."
                play_beep_sound(success=True)
            elif active_gesture == "three_fingers" and pending_status is None:
                pending_status = "URGENT_RETURN"
                last_log_message = "Selected: URGENT RETURN. Hold Palm (✋) to Confirm or Fist (✊) to Cancel."
                play_beep_sound(success=True)
            elif active_gesture == "fist":
                pending_status = None
                last_log_message = "Cancelled. Show a gesture (👍/✌️/☝️/3-Fingers) to select status."
                play_beep_sound(success=False)
            elif active_gesture == "open_palm" and pending_status is not None:
                # CONFIRM & EXPORT PIPELINE
                play_beep_sound(success=True)
                
                # Save Evidence Snapshot
                os.makedirs(config.EVIDENCE_DIR, exist_ok=True)
                timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                evidence_filename = f"{employee_name.replace(' ', '_')}_{pending_status}_{timestamp_str}.jpg"
                evidence_path = os.path.join(config.EVIDENCE_DIR, evidence_filename)
                cv2.imwrite(evidence_path, frame)
                
                # Resolve GPS Coordinates
                if gps_lat is not None and gps_lon is not None:
                    final_location = f"{gps_lat:.5f}, {gps_lon:.5f}"
                else:
                    final_location = f"{config.DEFAULT_LATITUDE:.5f}, {config.DEFAULT_LONGITUDE:.5f} (Default)"
                    
                # Mark Attendance (IN / OUT / URGENT_EXIT / URGENT_RETURN)
                success, msg = mark_attendance(employee_name, pending_status, final_location, evidence_path)
                
                # Visual Confirmation Screen
                confirm_overlay = frame.copy()
                cv2.rectangle(confirm_overlay, (0, 0), (w, h), (20, 20, 20), -1)
                cv2.addWeighted(confirm_overlay, 0.8, frame, 0.2, 0, frame)
                
                cv2.putText(frame, "ATTENDANCE LOGGED!", (w // 2 - 250, h // 2 - 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA)
                cv2.putText(frame, f"Name: {employee_name.upper()}", (w // 2 - 250, h // 2 + 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Status: {pending_status.replace('_', ' ')}", (w // 2 - 250, h // 2 + 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, f"Loc: {final_location}", (w // 2 - 250, h // 2 + 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                cv2.putText(frame, "Closing camera feed...", (w // 2 - 250, h // 2 + 130),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1, cv2.LINE_AA)
                
                cv2.imshow("Gesture Attendance System", frame)
                cv2.waitKey(2500)
                
                print(f"[SUCCESS] Attendance {pending_status} logged for {employee_name} at {final_location}!")
                print(f"[SUCCESS] Evidence snapshot saved to: {evidence_path}")
                break  # Stop camera and exit program immediately
                
            # Reset hold state
            active_gesture = None
            consecutive_frames = 0
            
        # Draw HUD overlays on frame
        hud_active_gesture = active_gesture if active_gesture else "thumbs_up"
        draw_premium_hud(frame, hud_active_gesture, hold_ratio, employee_name, last_log_message)
        
        # Display current pending status if any
        if pending_status is not None:
            cv2.putText(frame, f"PENDING: {pending_status.replace('_', ' ')}", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)
            # Display GPS status in main loop HUD
            cv2.putText(frame, location_hud, (20, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255) if gps_lat else (0, 165, 255), 2, cv2.LINE_AA)
        else:
            # Display GPS status
            cv2.putText(frame, location_hud, (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255) if gps_lat else (0, 165, 255), 2, cv2.LINE_AA)
                        
        # Display face verification status on HUD
        if face_recognizer is not None:
            face_status_text = "FACE: VERIFIED" if face_verified else "FACE: UNVERIFIED"
            face_status_color = (0, 255, 0) if face_verified else (0, 0, 255)
            cv2.putText(frame, face_status_text, (20, 160 if pending_status else 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, face_status_color, 2, cv2.LINE_AA)
 
        # Show final frame
        cv2.imshow("Gesture Attendance System", frame)
        
        # Keyboard handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            print("[INFO] Exiting...")
            break
        elif key == 27:  # ESC key - switch student
            print("[INFO] Resetting student log...")
            cv2.destroyAllWindows()
            cap.release()
            
            # Rerun main to prompt name
            main()
            return
 
    cap.release()
    cv2.destroyAllWindows()
 
if __name__ == "__main__":
    main()