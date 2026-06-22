import cv2
import os
import time
from detect_gesture import GestureDetector
from attendance import mark_attendance
from utils import draw_premium_hud, draw_corner_rect, play_beep_sound, CameraStream
from face_rec import FaceRecognizer
from security import SurveillanceSystem
import config

def get_student_name():
    print("\n" + "="*50)
    print("      AI GESTURE ATTENDANCE SYSTEM - LOGIN")
    print("="*50)
    name = input("Enter Student Name or ID (Press ENTER for Guest): ").strip()
    if not name:
        name = "Guest_Student"
    print(f"[INFO] System initialized for student: {name.upper()}")
    print("[INFO] Instructions:")
    print("  ✋ Open Palm  -> Select 'PRESENT'")
    print("  ✌️ Peace Sign  -> Select 'ABSENT'")
    print("  👍 Thumbs Up   -> 'CONFIRM' (requires Face Scan)")
    print("  ✊ Fist        -> 'CANCEL' pending state")
    print("="*50 + "\n")
    return name

def main():
    # Prompt user to input name
    student_name = get_student_name()
    
    # Initialize components
    detector = GestureDetector()
    face_verifier = FaceRecognizer()
    surveillance = SurveillanceSystem()
    
    # Start threaded camera stream (handles webcams, IP cameras/RTSP streams lag-free)
    print(f"[INFO] Starting camera stream from source: {config.CAMERA_SOURCE}")
    cap = CameraStream(config.CAMERA_SOURCE).start()
    
    # Check if stream opened successfully
    test_grabbed, _ = cap.read()
    if not test_grabbed:
        print("[ERROR] Could not start camera stream. Check connection/source settings in config.py")
        cap.release()
        return
        
    cv2.namedWindow("Gesture Attendance System", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Gesture Attendance System", 1000, 750)
    
    # State tracking variables
    active_gesture = None
    consecutive_frames = 0
    REQUIRED_FRAMES = 30  # Approx. 1 second at 30 FPS
    
    pending_status = None
    last_log_message = "Show Open Palm (Present) or Peace Sign (Absent) to begin."
    
    print("Camera running. Focus on the window. Press 'Q' to quit, 'ESC' to switch student.")
    
    while True:
        grabbed, frame = cap.read()
        if not grabbed or frame is None:
            print("[ERROR] Camera feed lost or disconnected.")
            time.sleep(0.1)
            continue
            
        # Flip frame horizontally if it's a local webcam (makes framing more natural)
        # We assume integer camera sources are local webcams
        if isinstance(config.CAMERA_SOURCE, int):
            frame = cv2.flip(frame, 1)
            
        # 1. NIGHT SURVEILLANCE STATE
        # If lock hours are active, run theft protection and skip attendance logic
        if config.SURVEILLANCE_ENABLED and surveillance.is_lock_hours():
            is_intrusion, frame = surveillance.process_frame(frame)
            
            # Security HUD Overlay
            h, w, _ = frame.shape
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 50), (0, 0, 150), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
            
            cv2.putText(frame, "SECURITY LOCKDOWN ACTIVE: SURVEILLANCE MODE", (20, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Q: QUIT SURVEILLANCE", (w - 250, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
            
            cv2.imshow("Gesture Attendance System", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == ord('Q'):
                print("[INFO] Exiting surveillance mode...")
                break
            continue

        # 2. STANDARD WORKPLACE ATTENDANCE STATE
        # Run gesture detection
        detections = detector.detect(frame, conf_threshold=0.55)
        
        current_gesture = None
        current_bbox = None
        current_conf = 0.0
        
        if detections:
            detections.sort(key=lambda x: x["confidence"], reverse=True)
            top_detect = detections[0]
            current_gesture = top_detect["class_name"]
            current_bbox = top_detect["box"]
            current_conf = top_detect["confidence"]
            
        hold_ratio = 0.0
        
        # If face recognition is enabled, draw face bounding box if detected
        if config.FACE_RECOGNITION_ENABLED:
            face_bbox, _ = face_verifier.detect_face(frame)
            if face_bbox is not None:
                # Draw neon cyan corners around the face
                draw_corner_rect(frame, face_bbox, color=(255, 255, 0), thickness=2, length=12)
                cv2.putText(frame, "FACE DETECTED", (face_bbox[0], face_bbox[1] - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1, cv2.LINE_AA)
        
        if current_gesture is not None:
            # Color map based on gesture
            color_map = {
                "open_palm": (255, 255, 0),    # Cyan
                "peace": (255, 0, 255),        # Magenta
                "thumbs_up": (0, 255, 0),      # Neon Green
                "fist": (0, 0, 255)            # Red
            }
            box_color = color_map.get(current_gesture, (255, 255, 255))
            draw_corner_rect(frame, current_bbox, color=box_color, thickness=3)
            
            # Label overlay above the box
            label_text = f"{current_gesture.upper()} ({current_conf:.2f})"
            cv2.putText(frame, label_text, (current_bbox[0], current_bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2, cv2.LINE_AA)
            
            # Check gesture action validity
            is_valid_action = False
            if current_gesture in ["open_palm", "peace"]:
                is_valid_action = True
            elif current_gesture == "thumbs_up" and pending_status is not None:
                is_valid_action = True
            elif current_gesture == "fist" and pending_status is not None:
                is_valid_action = True
                
            if is_valid_action:
                if current_gesture == active_gesture:
                    consecutive_frames += 1
                else:
                    active_gesture = current_gesture
                    consecutive_frames = 1
                    
                hold_ratio = min(1.0, consecutive_frames / REQUIRED_FRAMES)
                
                # If gesture held long enough, execute action
                if consecutive_frames >= REQUIRED_FRAMES:
                    if current_gesture == "open_palm":
                        pending_status = "PRESENT"
                        last_log_message = "Selected: PRESENT. Hold Thumbs Up to Verify Face & Log."
                        play_beep_sound(success=True)
                    elif current_gesture == "peace":
                        pending_status = "ABSENT"
                        last_log_message = "Selected: ABSENT. Hold Thumbs Up to Verify Face & Log."
                        play_beep_sound(success=True)
                    elif current_gesture == "fist":
                        pending_status = None
                        last_log_message = "Action cancelled. Show Open Palm or Peace to restart."
                        play_beep_sound(success=False)
                    elif current_gesture == "thumbs_up" and pending_status is not None:
                        # 3. FACE VERIFICATION PHASE (ANTI-PROXY)
                        if config.FACE_RECOGNITION_ENABLED:
                            last_log_message = "Verifying face..."
                            # Draw face check HUD on frame
                            face_ok, face_msg = face_verifier.verify_face(frame, student_name)
                            if face_ok:
                                # Proceed to log attendance to CSV/Excel
                                success, message = mark_attendance(student_name, pending_status)
                                last_log_message = f"{face_msg} | {message}"
                                play_beep_sound(success=success)
                                pending_status = None  # Clear state
                            else:
                                last_log_message = face_msg
                                play_beep_sound(success=False)
                                pending_status = None  # Reset state on failure to verify
                        else:
                            # Direct check-in without face recognition
                            success, message = mark_attendance(student_name, pending_status)
                            last_log_message = message
                            play_beep_sound(success=success)
                            pending_status = None
                            
                    # Reset hold state
                    active_gesture = None
                    consecutive_frames = 0
            else:
                active_gesture = None
                consecutive_frames = 0
                if current_gesture == "thumbs_up":
                    last_log_message = "Select status first: Palm (Present) or Peace (Absent)."
        else:
            active_gesture = None
            consecutive_frames = 0

        # Draw HUD overlays on frame
        draw_premium_hud(frame, active_gesture, hold_ratio, student_name, last_log_message)
        
        # Display current pending status if any
        if pending_status is not None:
            cv2.putText(frame, f"PENDING: {pending_status}", (20, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2, cv2.LINE_AA)

        # Show final frame
        cv2.imshow("Gesture Attendance System", frame)
        
        # Keyboard handling
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == ord('Q'):
            print("[INFO] Shutting down...")
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