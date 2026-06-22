import cv2
import os
import numpy as np
import json
import sys

# Add src to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from config import FACE_MODEL_PATH, FACES_DIR

def train_face_classifier():
    if not os.path.exists(FACES_DIR):
        print(f"[ERROR] Faces directory not found at {FACES_DIR}")
        print("Please create the folder structure: data/faces/<employee_name>/ and put face images there.")
        return

    # Load Haar cascade face detector
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    
    # Initialize recognizer
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    faces_data = []
    labels_data = []
    labels_map = {}
    
    label_counter = 0
    
    print("[INFO] Scanning face database...")
    
    # Walk through each directory in data/faces/
    for folder_name in os.listdir(FACES_DIR):
        folder_path = os.path.join(FACES_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue
            
        print(f"[INFO] Processing class {label_counter}: '{folder_name}'")
        labels_map[label_counter] = folder_name
        
        # Read all images in this folder
        for file in os.listdir(folder_path):
            if not file.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            img_path = os.path.join(folder_path, file)
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            
            # Detect face
            faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
            
            for (x, y, w, h) in faces:
                # Crop and resize to standard 150x150
                face_crop = gray[y:y+h, x:x+w]
                face_crop = cv2.resize(face_crop, (150, 150))
                
                faces_data.append(face_crop)
                labels_data.append(label_counter)
                break  # Take only one face per image
                
        label_counter += 1

    if len(faces_data) == 0:
        print("[ERROR] No face images found for training.")
        print("Ensure you have placed face images in folders: data/faces/<employee_name>/*.jpg")
        return

    print(f"[INFO] Found {len(faces_data)} faces across {len(labels_map)} classes.")
    print("[INFO] Training LBPH Face Recognizer...")
    
    try:
        recognizer.train(faces_data, np.array(labels_data))
        
        # Save model and labels map
        os.makedirs(os.path.dirname(FACE_MODEL_PATH), exist_ok=True)
        recognizer.save(FACE_MODEL_PATH)
        
        labels_json_path = FACE_MODEL_PATH.replace(".yml", "_labels.json")
        with open(labels_json_path, "w") as jf:
            json.dump(labels_map, jf, indent=4)
            
        print(f"[SUCCESS] Trained face recognizer model weights saved to {FACE_MODEL_PATH}")
        print(f"[SUCCESS] Face labels mapping JSON saved to {labels_json_path}")
        
    except Exception as e:
        print(f"[ERROR] Failed to train LBPH Face Recognizer: {e}")

if __name__ == "__main__":
    train_face_classifier()
