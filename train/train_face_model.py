import cv2
import os
import numpy as np
import pickle

def main():
    face_dir = os.path.join("data", "faces")
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    
    face_model_path = os.path.join(model_dir, "face_recognizer.xml")
    face_labels_path = os.path.join(model_dir, "face_labels.pkl")
    
    if not os.path.exists(face_dir):
        print(f"[ERROR] Face data directory not found at {face_dir}")
        print("Please run train/collect_face_data.py first.")
        return
        
    subfolders = [d for d in os.listdir(face_dir) if os.path.isdir(os.path.join(face_dir, d))]
    
    if not subfolders:
        print("[ERROR] No face folders found in data/faces/")
        print("Please run train/collect_face_data.py first.")
        return
        
    faces_data = []
    labels = []
    label_map = {} # Maps ID -> Name
    
    print("="*60)
    print("      TRAINING FACE RECOGNIZER MODEL")
    print("="*60)
    
    for idx, folder_name in enumerate(subfolders):
        name = folder_name.replace("_", " ")
        label_map[idx] = name
        
        folder_path = os.path.join(face_dir, folder_name)
        print(f"[INFO] Reading face images for: {name.upper()}")
        
        img_count = 0
        for fname in os.listdir(folder_path):
            if not (fname.endswith(".jpg") or fname.endswith(".png")):
                continue
                
            img_path = os.path.join(folder_path, fname)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
                
            # Apply histogram equalization and enforce 200x200 size consistency
            equalized = cv2.equalizeHist(img)
            resized = cv2.resize(equalized, (200, 200), interpolation=cv2.INTER_AREA)
            
            faces_data.append(resized)
            labels.append(idx)
            img_count += 1
            
        print(f"[INFO] Found {img_count} images for {name}.")
        
    if not faces_data:
        print("[ERROR] No face images found to train.")
        return
        
    # Convert labels to numpy array
    labels = np.array(labels, dtype=np.int32)
    
    # Initialize LBPH Face Recognizer
    print("\n[INFO] Initializing LBPH Face Recognizer...")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    # Train
    print("[INFO] Training model (this will be quick)...")
    recognizer.train(faces_data, labels)
    
    # Save the model and labels map
    recognizer.write(face_model_path)
    with open(face_labels_path, "wb") as f:
        pickle.dump(label_map, f)
        
    print("\n" + "="*60)
    print("[SUCCESS] Face recognizer model trained successfully!")
    print(f"[SUCCESS] Weights saved to: {face_model_path}")
    print(f"[SUCCESS] Label lookup saved to: {face_labels_path}")
    print(f"[SUCCESS] Classes trained: {list(label_map.values())}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
