import cv2
import os
import time
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
    consecutive_palm_frames = 0
    REQUIRED_PALM_FRAMES = 15  # 0.5 seconds at 30 FPS for fast response
    
    print(f"[INFO] Attendance ready. Show Palm sign (✋) to log check-in.")
    
    while True:
        grabbed, frame = cap.read()
        if not grabbed or frame is None:
            time.sleep(0.1)
            continue
            
        # Flip frame horizontally if using local USB/laptop webcam
        if isinstance(config.CAMERA_SOURCE, int):
            frame = cv2.flip(frame, 1)
            
        h, w, _ = frame.shape
        
        # Run MediaPipe Hands detector
        detections = detector.detect(frame, conf_threshold=0.60)
        
        palm_active = False
        hand_bbox = None
        
        for d in detections:
            if d["class_name"] == "open_palm":
                palm_active = True
                hand_bbox = d["box"]
                break
                
        # Draw hand bounding box if Palm detected
        if palm_active and hand_bbox is not None:
            draw_corner_rect(frame, hand_bbox, color=(255, 255, 0), thickness=3) # Neon Cyan
            cv2.putText(frame, "PALM DETECTED", (hand_bbox[0], hand_bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2, cv2.LINE_AA)
            
            consecutive_palm_frames += 1
        else:
            consecutive_palm_frames = 0
            
        # Calculate hold progress ratio
        hold_ratio = min(1.0, consecutive_palm_frames / REQUIRED_PALM_FRAMES)
        
        # Format Geolocation text for screen HUD
        gps_lat = gps_server.GPS_DATA["latitude"]
        gps_lon = gps_server.GPS_DATA["longitude"]
        
        if gps_lat is not None and gps_lon is not None:
            location_hud = f"GPS: CONNECTED ({gps_lat:.5f}, {gps_lon:.5f})"
            status_color = (0, 255, 0) # Green
        else:
            location_hud = f"GPS SCAN: Open http://{local_ip}:5000 on mobile"
            status_color = (0, 165, 255) # Orange/Amber
            
        # 1. Trigger Attendance on complete hold progress
        if consecutive_palm_frames >= REQUIRED_PALM_FRAMES:
            # Play beep sound
            play_beep_sound(success=True)
            
            # Save Evidence Snapshot
            os.makedirs(config.EVIDENCE_DIR, exist_ok=True)
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            evidence_filename = f"{employee_name.replace(' ', '_')}_{timestamp_str}.jpg"
            evidence_path = os.path.join(config.EVIDENCE_DIR, evidence_filename)
            
            # Save clean frame before UI elements or landmarks are drawn
            # (MediaPipe draws on 'frame' so we copy the original read if needed, 
            # but standard BGR frame is okay since landmarks show the actual palm position as proof!)
            cv2.imwrite(evidence_path, frame)
            
            # Resolve GPS Coordinates
            if gps_lat is not None and gps_lon is not None:
                final_location = f"{gps_lat:.5f}, {gps_lon:.5f}"
            else:
                final_location = f"{config.DEFAULT_LATITUDE:.5f}, {config.DEFAULT_LONGITUDE:.5f} (Default)"
                
            # Log to CSV/Excel
            success, msg = mark_attendance(employee_name, "PRESENT", final_location, evidence_path)
            
            # Show visual confirmation on screen for 2.5 seconds
            confirm_overlay = frame.copy()
            cv2.rectangle(confirm_overlay, (0, 0), (w, h), (20, 20, 20), -1)
            cv2.addWeighted(confirm_overlay, 0.8, frame, 0.2, 0, frame)
            
            cv2.putText(frame, "ATTENDANCE LOGGED!", (w // 2 - 250, h // 2 - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, f"Name: {employee_name.upper()}", (w // 2 - 250, h // 2 + 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, f"Loc: {final_location}", (w // 2 - 250, h // 2 + 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Closing camera feed...", (w // 2 - 250, h // 2 + 100),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1, cv2.LINE_AA)
            
            cv2.imshow("Gesture Attendance System", frame)
            cv2.waitKey(2500)
            
            print(f"[SUCCESS] Attendance logged for {employee_name} at {final_location}!")
            print(f"[SUCCESS] Evidence snapshot saved to: {evidence_path}")
            break  # Stop camera and exit program immediately
            
        # Draw HUD overlays on frame
        draw_premium_hud(frame, "open_palm", hold_ratio, employee_name, location_hud)
        
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