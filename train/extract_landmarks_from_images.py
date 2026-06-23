import os
import cv2
import csv
import mediapipe as mp
import numpy as np

def get_normalized_landmarks(landmarks):
    """
    Translates landmarks relative to the wrist (landmark 0) 
    and scales coordinates between -1.0 and 1.0.
    """
    x0, y0, z0 = landmarks[0].x, landmarks[0].y, landmarks[0].z
    coords = []
    
    for lm in landmarks:
        coords.extend([lm.x - x0, lm.y - y0, lm.z - z0])
        
    max_val = max(abs(c) for c in coords)
    if max_val > 0:
        coords = [c / max_val for c in coords]
        
    return coords

def main():
    # Initialize MediaPipe Hands
    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=True,
        max_num_hands=1,
        min_detection_confidence=0.5
    )
    
    base_dir = "dataset"
    dataset_dir = "data"
    os.makedirs(dataset_dir, exist_ok=True)
    dataset_path = os.path.join(dataset_dir, "landmark_dataset.csv")
    
    # Class name to index mapping
    class_mapping = {
        "open_palm": 0,
        "thumbs_up": 1,
        "peace": 2,
        "fist": 3
    }
    
    # Open CSV file for writing
    csv_file = open(dataset_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(csv_file)
    
    # Write headers: label, x0, y0, z0, ..., x20, y20, z20
    headers = ["label"]
    for i in range(21):
        headers.extend([f"x{i}", f"y{i}", f"z{i}"])
    writer.writerow(headers)
    
    splits = ["train", "val"]
    total_images = 0
    detected_hands = 0
    failed_hands = 0
    
    print("="*60)
    print("      EXTRACTING LANDMARKS FROM EXISTING IMAGES")
    print("="*60)
    
    for split in splits:
        img_dir = os.path.join(base_dir, "images", split)
        if not os.path.exists(img_dir):
            print(f"[WARNING] Image directory not found: {img_dir}")
            continue
            
        print(f"\n[INFO] Processing split: {split.upper()}")
        
        for file in os.listdir(img_dir):
            if not file.endswith(".jpg"):
                continue
                
            total_images += 1
            
            # Determine class index based on file prefix
            class_idx = -1
            for class_name, idx in class_mapping.items():
                if file.startswith(class_name):
                    class_idx = idx
                    break
                    
            if class_idx == -1:
                # Fallback: check label file if filename prefix doesn't match
                base_name = os.path.splitext(file)[0]
                lbl_path = os.path.join(base_dir, "labels", split, f"{base_name}.txt")
                if os.path.exists(lbl_path):
                    try:
                        with open(lbl_path, "r") as lf:
                            line = lf.readline().strip()
                            if line:
                                class_idx = int(line.split()[0])
                    except Exception:
                        pass
                        
            if class_idx == -1:
                print(f"[WARNING] Could not determine class for image: {file}")
                continue
                
            img_path = os.path.join(img_dir, file)
            img = cv2.imread(img_path)
            if img is None:
                print(f"[WARNING] Failed to load image: {img_path}")
                continue
                
            # Convert to RGB for MediaPipe
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(rgb_img)
            
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    normalized_coords = get_normalized_landmarks(hand_landmarks.landmark)
                    writer.writerow([class_idx] + normalized_coords)
                    detected_hands += 1
                    break # Process only the first hand
            else:
                failed_hands += 1
                
            if total_images % 50 == 0:
                print(f"Processed {total_images} images... Hands detected: {detected_hands}")
                
    csv_file.close()
    hands.close()
    
    print("\n" + "="*60)
    print("      EXTRACTION SUMMARY")
    print("="*60)
    print(f"Total Images Processed: {total_images}")
    print(f"Successful Hand Detections (Saved): {detected_hands}")
    print(f"Failed Detections: {failed_hands}")
    print(f"Dataset Saved to: {dataset_path}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
