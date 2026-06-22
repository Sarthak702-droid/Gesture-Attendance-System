import cv2
import mediapipe as mp
import os
import time
import random

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)
mp_draw = mp.solutions.drawing_utils

# Create dataset directories
base_dir = "dataset"
splits = ["train", "val"]
types = ["images", "labels"]

for split in splits:
    for t in types:
        os.makedirs(os.path.join(base_dir, t, split), exist_ok=True)

# Gesture classes mapping
classes = {
    0: "open_palm",
    1: "thumbs_up",
    2: "peace",
    3: "fist"
}

# Number of images to capture per class
IMAGES_PER_CLASS = 60
VAL_SPLIT_RATIO = 0.2  # 20% validation, 80% training

cap = cv2.VideoCapture(0)

print("="*60)
# Set window parameters
cv2.namedWindow("Dataset Collector", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Dataset Collector", 800, 600)

for class_idx, class_name in classes.items():
    print(f"\n[INFO] Preparing to collect data for class {class_idx}: '{class_name}'")
    print("Press SPACE to start capturing, or 'q' to quit.")
    
    # Wait for user input to start capturing this class
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera feed not available.")
            break
            
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # Display instructions
        cv2.putText(frame, f"Next: {class_name.upper()}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame, "Press SPACE to start capturing...", (20, h - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow("Dataset Collector", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            break
        elif key == ord('q'):
            print("[INFO] Exiting dataset collection.")
            cap.release()
            cv2.destroyAllWindows()
            exit(0)
            
    print(f"[INFO] Starting capture for {class_name}... Please show the gesture.")
    
    # Wait 3 seconds before capturing to let user position hand
    for i in range(3, 0, -1):
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        cv2.putText(frame, f"Starting in {i}...", (w // 2 - 100, h // 2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
        cv2.imshow("Dataset Collector", frame)
        cv2.waitKey(1000)

    count = 0
    while count < IMAGES_PER_CLASS:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Camera feed lost.")
            break
            
        frame = cv2.flip(frame, 1)
        img_h, img_w, _ = frame.shape
        
        # Save a clean copy of the frame before drawing landmarks/boxes
        clean_frame = frame.copy()
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)
        
        hand_detected = False
        bbox_yolo = None
        bbox_pixel = None
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Extract landmark coordinates
                x_coords = [lm.x for lm in hand_landmarks.landmark]
                y_coords = [lm.y for lm in hand_landmarks.landmark]
                
                # Compute bounding box
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                # Add padding
                padding = 0.06
                x_min = max(0.0, x_min - padding)
                x_max = min(1.0, x_max + padding)
                y_min = max(0.0, y_min - padding)
                y_max = min(1.0, y_max + padding)
                
                # Convert to YOLO format (x_center, y_center, width, height) in normalized coords
                box_w = x_max - x_min
                box_h = y_max - y_min
                x_center = x_min + box_w / 2.0
                y_center = y_min + box_h / 2.0
                
                bbox_yolo = (x_center, y_center, box_w, box_h)
                
                # Pixel coordinates for display
                bbox_pixel = (
                    int(x_min * img_w), 
                    int(y_min * img_h), 
                    int(x_max * img_w), 
                    int(y_max * img_h)
                )
                
                # Draw hand landmarks for feedback
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                hand_detected = True
                break  # Just process one hand
                
        # Handle saving data
        if hand_detected and bbox_yolo is not None:
            # Decide split (train or val)
            split = "val" if random.random() < VAL_SPLIT_RATIO else "train"
            
            # Generate unique filename using timestamp
            timestamp = int(time.time() * 1000)
            filename = f"{class_name}_{timestamp}"
            
            img_path = os.path.join(base_dir, "images", split, f"{filename}.jpg")
            label_path = os.path.join(base_dir, "labels", split, f"{filename}.txt")
            
            # Save Clean Image (without drawings)
            cv2.imwrite(img_path, clean_frame)
            
            # Write label file
            with open(label_path, "w") as lf:
                lf.write(f"{class_idx} {bbox_yolo[0]:.6f} {bbox_yolo[1]:.6f} {bbox_yolo[2]:.6f} {bbox_yolo[3]:.6f}\n")
                
            # Draw bounding box on the screen frame for feedback
            cv2.rectangle(frame, (bbox_pixel[0], bbox_pixel[1]), (bbox_pixel[2], bbox_pixel[3]), (0, 255, 0), 2)
            cv2.putText(frame, f"Saved: {count + 1}/{IMAGES_PER_CLASS}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            count += 1
            time.sleep(0.05) # Add a tiny delay to avoid identical successive frames
        else:
            cv2.putText(frame, "HAND NOT DETECTED", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
        cv2.imshow("Dataset Collector", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("[INFO] Exiting dataset collection.")
            cap.release()
            cv2.destroyAllWindows()
            exit(0)

# Clean up
cap.release()
cv2.destroyAllWindows()
print("\n" + "="*60)
print("[SUCCESS] Dataset collection completed!")
print(f"Images are saved in {base_dir}/images/train and {base_dir}/images/val")
print(f"Labels are saved in {base_dir}/labels/train and {base_dir}/labels/val")
print("="*60)
