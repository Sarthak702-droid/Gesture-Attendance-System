import cv2
import os
import time
import pickle
from detect_gesture import GestureDetector
from attendance import mark_attendance
from utils import draw_premium_hud, draw_corner_rect, play_beep_sound, CameraStream, check_liveness
from gps_server import start_gps_server, get_local_ip
from security import SurveillanceSystem
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
    
    # Play login voice greeting in Odia (runs asynchronously in a thread)
    try:
        from tts import play_login_greeting_tts
        play_login_greeting_tts(employee_name)
    except Exception as e:
        print(f"[WARNING] Login greeting error: {e}")
        
    # Start the local GPS web server in the background
    local_ip = get_local_ip()
    start_gps_server()
    
    # Initialize MediaPipe gesture detector
    detector = GestureDetector()
    
    # Initialize Security Surveillance System
    surveillance = SurveillanceSystem()
    
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

        # Check if Surveillance System night lock is active
        if getattr(config, "SURVEILLANCE_ENABLED", False) and surveillance.is_lock_hours():
            # 1. Run Person Detection
            person_detected, person_bbox = surveillance.detect_person(frame)
            
            owner_verified = False
            face_name_detected = "UNKNOWN"
            face_bbox = None
            face_confidence = None
            multi_face_active_surv = False
            liveness_ok_surv = True
            liveness_score_surv = 0.0
            
            # 2. Run Face Recognition ONLY if a person is in the frame
            if person_detected and face_detector is not None and face_recognizer is not None:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                face_results = face_detector.process(rgb_frame)
                
                if face_results.detections:
                    num_faces = len(face_results.detections)
                    if num_faces > 1:
                        multi_face_active_surv = True
                        owner_verified = False  # Block verification for security
                    else:
                        detection = face_results.detections[0]
                        bbox_data = detection.location_data.relative_bounding_box
                        fx = int(bbox_data.xmin * w)
                        fy = int(bbox_data.ymin * h)
                        fwidth = int(bbox_data.width * w)
                        fheight = int(bbox_data.height * h)
                        
                        # Clamp and pad coordinates by 15% to match training database padding
                        padding_w = int(fwidth * 0.15)
                        padding_h = int(fheight * 0.15)
                        
                        fx1_pad = max(0, fx - padding_w)
                        fy1_pad = max(0, fy - padding_h)
                        fx2_pad = min(w, fx + fwidth + padding_w)
                        fy2_pad = min(h, fy + fheight + padding_h)
                        
                        face_bbox = (fx1_pad, fy1_pad, fx2_pad, fy2_pad)
                        
                        face_crop = frame[fy1_pad:fy2_pad, fx1_pad:fx2_pad]
                        if face_crop.size > 0:
                            liveness_ok_surv, liveness_score_surv = check_liveness(face_crop)
                            if not liveness_ok_surv:
                                owner_verified = False  # Spoof detected
                            else:
                                gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                                equalized = cv2.equalizeHist(gray_crop)
                                resized_crop = cv2.resize(equalized, (200, 200), interpolation=cv2.INTER_AREA)
                                
                                label_id, confidence = face_recognizer.predict(resized_crop)
                                face_confidence = confidence
                                
                                threshold = getattr(config, "FACE_CONFIDENCE_THRESHOLD", 70.0)
                                if confidence < threshold:
                                    face_name_detected = face_labels.get(label_id, "UNKNOWN")
                                    
                                    owner_name = getattr(config, "OWNER_NAME", "Sarthak Tripathy").strip().lower()
                                    if owner_name in face_name_detected.lower() or face_name_detected.lower() in owner_name:
                                        owner_verified = True
            
            # 3. Trigger Alert/Alarm based on results
            if person_detected:
                surveillance.trigger_alert(frame, person_bbox, owner_verified)
                
            # 4. Security Overlay / Display
            overlay = frame.copy()
            # Draw red banner at the top
            cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 150), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            cv2.putText(frame, "SECURITY LOCKDOWN ACTIVE: SURVEILLANCE MODE", (20, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Q: QUIT SURVEILLANCE", (w - 240, 38),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
            
            if person_detected:
                if owner_verified:
                    # Draw green box for verified owner
                    if face_bbox is not None:
                        draw_corner_rect(frame, face_bbox, color=(0, 255, 0), thickness=2)
                        cv2.putText(frame, f"OWNER DETECTED ({face_name_detected.upper()})", 
                                    (face_bbox[0], face_bbox[1] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
                    cv2.putText(frame, "ACCESS GRANTED: OWNER DETECTED", (20, h - 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                else:
                    # Draw red box around intruder
                    if person_bbox is not None:
                        cv2.rectangle(frame, (person_bbox[0], person_bbox[1]), 
                                      (person_bbox[2], person_bbox[3]), (0, 0, 255), 3)
                    
                    # Draw face box if detected but not verified
                    if face_bbox is not None:
                        draw_corner_rect(frame, face_bbox, color=(0, 0, 255), thickness=2)
                        conf_str = f" (Dist: {face_confidence:.1f})" if face_confidence is not None else ""
                        cv2.putText(frame, f"UNVERIFIED{conf_str}", (face_bbox[0], face_bbox[1] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2, cv2.LINE_AA)
                                    
                    # Draw full screen blinking red alert border
                    cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10)
                    cv2.putText(frame, "🚨 INTRUDER ALERT! SIREN ACTIVE 🚨", (20, h - 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "STATUS: SECURE (NO INTRUSION DETECTED)", (20, h - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
            
            cv2.imshow("Gesture Attendance System", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("[INFO] Exiting surveillance mode...")
                break
            continue
        
        # 1. Run Face Detection & Recognition
        face_verified = False
        face_name_detected = "UNKNOWN"
        face_bbox = None
        face_confidence = None
        multi_face_active = False
        liveness_ok = True
        liveness_score = 0.0
        
        if face_detector is not None and face_recognizer is not None:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_results = face_detector.process(rgb_frame)
            
            if face_results.detections:
                num_faces = len(face_results.detections)
                if num_faces > 1:
                    multi_face_active = True
                else:
                    detection = face_results.detections[0]
                    bbox_data = detection.location_data.relative_bounding_box
                    fx = int(bbox_data.xmin * w)
                    fy = int(bbox_data.ymin * h)
                    fwidth = int(bbox_data.width * w)
                    fheight = int(bbox_data.height * h)
                    
                    # Clamp and pad coordinates by 15% to match training database padding
                    padding_w = int(fwidth * 0.15)
                    padding_h = int(fheight * 0.15)
                    
                    fx1_pad = max(0, fx - padding_w)
                    fy1_pad = max(0, fy - padding_h)
                    fx2_pad = min(w, fx + fwidth + padding_w)
                    fy2_pad = min(h, fy + fheight + padding_h)
                    
                    face_bbox = (fx1_pad, fy1_pad, fx2_pad, fy2_pad)
                    
                    # Crop and predict
                    face_crop = frame[fy1_pad:fy2_pad, fx1_pad:fx2_pad]
                    if face_crop.size > 0:
                        liveness_ok, liveness_score = check_liveness(face_crop)
                        
                        gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                        equalized = cv2.equalizeHist(gray_crop)
                        resized_crop = cv2.resize(equalized, (200, 200), interpolation=cv2.INTER_AREA)
                        
                        label_id, confidence = face_recognizer.predict(resized_crop)
                        face_confidence = confidence
                        
                        # For LBPH, confidence represents distance (lower distance means better match)
                        threshold = getattr(config, "FACE_CONFIDENCE_THRESHOLD", 70.0)
                        if confidence < threshold:
                            face_name_detected = face_labels.get(label_id, "UNKNOWN")
                            
                            # Match login employee name against face name (case-insensitive substring check)
                            login_name_clean = employee_name.strip().lower()
                            detected_name_clean = face_name_detected.lower()
                            
                            if login_name_clean in detected_name_clean or detected_name_clean in login_name_clean:
                                face_verified = True
                            
        # Draw Face Overlay
        if face_bbox is not None:
            if not liveness_ok:
                face_color = (0, 0, 255)  # Red for spoof
                draw_corner_rect(frame, face_bbox, color=face_color, thickness=2)
                face_label_text = f"SPOOF DETECTED! (Conf: {liveness_score:.1f})"
                cv2.putText(frame, face_label_text, (face_bbox[0], face_bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 2, cv2.LINE_AA)
            else:
                face_color = (0, 255, 0) if face_verified else (0, 0, 255)
                draw_corner_rect(frame, face_bbox, color=face_color, thickness=2)
                
                conf_str = f" (Dist: {face_confidence:.1f})" if face_confidence is not None else ""
                liveness_str = f" | Live Score: {liveness_score:.1f}"
                if face_verified:
                    face_label_text = f"{face_name_detected.upper()}{conf_str}{liveness_str} (VERIFIED)"
                else:
                    face_label_text = f"UNVERIFIED{conf_str}{liveness_str}"
                cv2.putText(frame, face_label_text, (face_bbox[0], face_bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, face_color, 2, cv2.LINE_AA)
                            
        # Render Blinking Warning for Multi-Face Detection
        if multi_face_active:
            if int(time.time() * 2) % 2 == 0:
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 255), 10)
                cv2.rectangle(overlay, (w // 2 - 300, h // 2 - 40), (w // 2 + 300, h // 2 + 40), (0, 0, 150), -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
                cv2.putText(frame, "🚨 MULTI-FACE DETECTED 🚨", (w // 2 - 250, h // 2 + 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3, cv2.LINE_AA)
        
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
            
        # 3. Check action validity based on current state, face verification, liveness, and multi-face
        face_required_gestures = ["thumbs_up", "peace", "open_palm", "pointing_up", "three_fingers"]
        face_ok = True
        if face_recognizer is not None and detected_gesture in face_required_gestures:
            face_ok = face_verified and liveness_ok and not multi_face_active
            
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
                if multi_face_active:
                    last_log_message = "Multi-face detected! Blocked for security."
                elif not liveness_ok:
                    last_log_message = "Spoof detected! Liveness verification failed."
                else:
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
                cv2.waitKey(100)
                
                # Check for Kiosk Broadcasts
                broadcast_message_to_speak = None
                try:
                    import json
                    json_path = os.path.join("data", "broadcasts.json")
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as f:
                            broadcasts = json.load(f)
                            
                        updated = False
                        for b in broadcasts:
                            if b.get("active", True):
                                target = b.get("target", "all").strip().lower()
                                read_by = b.get("read_by", [])
                                emp_name_clean = employee_name.strip().lower()
                                
                                # Match target: either 'all' or substring match
                                matches_target = (target == "all") or (target in emp_name_clean) or (emp_name_clean in target)
                                is_unread = employee_name not in read_by
                                
                                if matches_target and is_unread:
                                    broadcast_message_to_speak = b.get("message")
                                    read_by.append(employee_name)
                                    b["read_by"] = read_by
                                    updated = True
                                    break  # Only handle one broadcast per check-in
                                    
                        if updated:
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump(broadcasts, f, indent=2)
                            # Push updated broadcasts database to github
                            from attendance import git_push_logs_async
                            git_push_logs_async()
                except Exception as ex:
                    print(f"[WARNING] Broadcasts lookup error: {ex}")

                # Play TTS voice feedback
                try:
                    from tts import play_attendance_tts
                    play_attendance_tts(employee_name, pending_status)
                except Exception as e:
                    print(f"[WARNING] TTS error: {e}")
                    
                cv2.waitKey(1000)
                
                # If there's an active announcement, display the banner and speak it synchronously
                if broadcast_message_to_speak:
                    # Draw a nice dark orange announcement popup box
                    ann_overlay = frame.copy()
                    cv2.rectangle(ann_overlay, (0, 0), (w, h), (30, 20, 10), -1)
                    cv2.rectangle(ann_overlay, (20, 20), (w - 20, h - 20), (0, 165, 255), 2)
                    cv2.addWeighted(ann_overlay, 0.85, frame, 0.15, 0, frame)
                    
                    cv2.putText(frame, "ANNOUNCEMENT FOR YOU:", (50, 80),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2, cv2.LINE_AA)
                    
                    # Wrap message text to fit screen
                    msg_text = broadcast_message_to_speak
                    words = msg_text.split()
                    lines = []
                    current_line = []
                    for word in words:
                        current_line.append(word)
                        test_str = " ".join(current_line)
                        (tw, th), _ = cv2.getTextSize(test_str, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 1)
                        if tw > w - 100:
                            current_line.pop()
                            lines.append(" ".join(current_line))
                            current_line = [word]
                    if current_line:
                        lines.append(" ".join(current_line))
                        
                    y_offset = 140
                    for line in lines:
                        cv2.putText(frame, line, (50, y_offset),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
                        y_offset += 35
                        
                    cv2.putText(frame, "Closing camera feed after announcement...", (50, h - 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
                    
                    cv2.imshow("Gesture Attendance System", frame)
                    cv2.waitKey(200)
                    
                    try:
                        from tts import play_broadcast_tts
                        play_broadcast_tts(broadcast_message_to_speak)
                    except Exception as ex:
                        print(f"[WARNING] Broadcast speech error: {ex}")
                        cv2.waitKey(3000) # Fallback if TTS fails
                
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