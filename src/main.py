import cv2
import os
import time
from detect_gesture import GestureDetector
from attendance import mark_attendance
from utils import draw_premium_hud, draw_corner_rect, play_beep_sound

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
    print("  👍 Thumbs Up   -> 'CONFIRM' and save to CSV")
    print("  ✊ Fist        -> 'CANCEL' pending state")
    print("="*50 + "\n")
    return name

def main():
    # Prompts user to input name
    student_name = get_student_name()
    
    # Initialize detector
    detector = GestureDetector()
    
    # Start webcam capture
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam.")
        return
        
    cv2.namedWindow("Gesture Attendance System", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Gesture Attendance System", 1000, 750)
    
    # State tracking variables
    active_gesture = None
    consecutive_frames = 0
    REQUIRED_FRAMES = 30  # Approx. 1 second at 30 FPS
    
    pending_status = None  # Can be "PRESENT" or "ABSENT"
    last_log_message = "Show Open Palm (Present) or Peace Sign (Absent) to begin."
    
    print("Webcam started. Focus on the window. Press 'Q' to quit, 'ESC' to switch student.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera feed disconnected.")
            break
            
        # Flip frame horizontally for natural mirror effect
        frame = cv2.flip(frame, 1)
        
        # Run detection
        # Set a slightly lower threshold for convenience, e.g. 0.55
        detections = detector.detect(frame, conf_threshold=0.55)
        
        # Identify the most confident gesture detection
        current_gesture = None
        current_bbox = None
        current_conf = 0.0
        
        if detections:
            # Sort by confidence descending and pick the top detection
            detections.sort(key=lambda x: x["confidence"], reverse=True)
            top_detect = detections[0]
            current_gesture = top_detect["class_name"]
            current_bbox = top_detect["box"]
            current_conf = top_detect["confidence"]
            
        # 1. State Machine for Gesture hold-to-confirm
        hold_ratio = 0.0
        
        if current_gesture is not None:
            # Draw cornered bounding box on frame
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
                        last_log_message = "Selected: PRESENT. Show Thumbs Up (Confirm) or Fist (Cancel)."
                        play_beep_sound(success=True)
                    elif current_gesture == "peace":
                        pending_status = "ABSENT"
                        last_log_message = "Selected: ABSENT. Show Thumbs Up (Confirm) or Fist (Cancel)."
                        play_beep_sound(success=True)
                    elif current_gesture == "fist":
                        pending_status = None
                        last_log_message = "Action cancelled. Show Open Palm or Peace to restart."
                        play_beep_sound(success=False)
                    elif current_gesture == "thumbs_up" and pending_status is not None:
                        # Log to CSV
                        success, message = mark_attendance(student_name, pending_status)
                        last_log_message = message
                        play_beep_sound(success=success)
                        pending_status = None  # Clear state after completion
                        
                    # Reset hold state
                    active_gesture = None
                    consecutive_frames = 0
            else:
                # Gesture is detected but not applicable in current state (e.g. thumbs up without state)
                active_gesture = None
                consecutive_frames = 0
                if current_gesture == "thumbs_up":
                    last_log_message = "Please select status first: Palm (Present) or Peace (Absent)."
        else:
            # No gestures detected, reset hold progress
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