import cv2
import mediapipe as mp
import os
import csv
import time
import numpy as np

def get_normalized_landmarks(landmarks):
    """
    Normalizes coordinates by:
    1. Translating the wrist (landmark 0) to (0,0,0) by subtracting it from all points.
    2. Scaling the coordinates so the maximum absolute value is 1.0 (scale-invariance).
    """
    x0, y0, z0 = landmarks[0].x, landmarks[0].y, landmarks[0].z
    coords = []
    
    # Translate relative to wrist
    for lm in landmarks:
        coords.extend([lm.x - x0, lm.y - y0, lm.z - z0])
        
    # Scale normalization
    max_val = max(abs(c) for c in coords)
    if max_val > 0:
        coords = [c / max_val for c in coords]
        
    return coords

def main():
    # Initialize MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    mp_draw = mp.solutions.drawing_utils
    
    # Output path
    dataset_dir = "data"
    os.makedirs(dataset_dir, exist_ok=True)
    dataset_path = os.path.join(dataset_dir, "landmark_dataset.csv")
    
    # Classes mapping
    classes = {
        0: "open_palm",
        1: "thumbs_up",
        2: "peace",
        3: "fist"
    }
    
    # Open CSV file
    file_exists = os.path.exists(dataset_path)
    csv_file = open(dataset_path, "a", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    
    if not file_exists or os.stat(dataset_path).st_size == 0:
        # Write headers: label, x0, y0, z0, ..., x20, y20, z20
        headers = ["label"]
        for i in range(21):
            headers.extend([f"x{i}", f"y{i}", f"z{i}"])
        writer.writerow(headers)
        
    # Capture settings
    SAMPLES_PER_CLASS = 150  # Number of frames to capture per gesture
    cap = cv2.VideoCapture(0)
    
    cv2.namedWindow("Landmark Collector", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Landmark Collector", 800, 600)
    
    print("="*60)
    print("      HAND GESTURE LANDMARK COLLECTOR")
    print("="*60)
    
    for class_idx, class_name in classes.items():
        print(f"\n[INFO] Prepare to collect data for: {class_name.upper()}")
        print("Press SPACE to start capturing, or 'q' to quit.")
        
        # 1. Wait for Space input
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            cv2.putText(frame, f"Next: {class_name.upper()}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "Press SPACE to start...", (20, h - 20), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
            cv2.imshow("Landmark Collector", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                break
            elif key == ord('q'):
                print("[INFO] Exiting collector.")
                csv_file.close()
                cap.release()
                cv2.destroyAllWindows()
                return
                
        # 2. Countdown
        for i in range(3, 0, -1):
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            cv2.putText(frame, f"Starting in {i}...", (w // 2 - 100, h // 2), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3, cv2.LINE_AA)
            cv2.imshow("Landmark Collector", frame)
            cv2.waitKey(1000)
            
        # 3. Capture Loop
        count = 0
        while count < SAMPLES_PER_CLASS:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_frame)
            
            hand_detected = False
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw landmarks for feedback
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    
                    # Get normalized coordinates list
                    normalized_coords = get_normalized_landmarks(hand_landmarks.landmark)
                    
                    # Write to CSV
                    writer.writerow([class_idx] + normalized_coords)
                    
                    count += 1
                    hand_detected = True
                    break
                    
            # Feedback text
            if hand_detected:
                cv2.putText(frame, f"Capturing {class_name.upper()}: {count}/{SAMPLES_PER_CLASS}", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "HAND NOT DETECTED", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
                
            cv2.imshow("Landmark Collector", frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("[INFO] Exiting collector.")
                csv_file.close()
                cap.release()
                cv2.destroyAllWindows()
                return
                
            time.sleep(0.02) # Slower capture to prevent redundant identical frames
            
    print("\n[SUCCESS] Landmark data collection completed!")
    print(f"[SUCCESS] Dataset saved to: {dataset_path}")
    
    csv_file.close()
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
