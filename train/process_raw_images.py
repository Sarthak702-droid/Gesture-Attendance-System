import cv2
import os
import shutil
import time
import random
import numpy as np
import mediapipe as mp
import sys

# Add src to system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import config
from train_face_model import main as retrain_model

# Initialize MediaPipe Face Detection
mp_face = mp.solutions.face_detection
face_detector = mp_face.FaceDetection(min_detection_confidence=0.6)

def crop_and_resize_face(image, bbox, target_size=(200, 200)):
    """
    Crops the face from the image using relative bounding box, converts to grayscale, and resizes.
    """
    h, w, _ = image.shape
    xmin, ymin, width, height = bbox
    
    # Convert relative coordinates to pixels
    x = int(xmin * w)
    y = int(ymin * h)
    box_w = int(width * w)
    box_h = int(height * h)
    
    # Add padding
    padding_w = int(box_w * 0.15)
    padding_h = int(box_h * 0.15)
    
    x1 = max(0, x - padding_w)
    y1 = max(0, y - padding_h)
    x2 = min(w, x + box_w + padding_w)
    y2 = min(h, y + box_h + padding_h)
    
    face_crop = image[y1:y2, x1:x2]
    if face_crop.size == 0:
        return None
        
    gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray_crop)
    resized_crop = cv2.resize(equalized, target_size, interpolation=cv2.INTER_AREA)
    return resized_crop

def augment_image(face_gray):
    """
    Generates an augmented version of a grayscale face image.
    Performs slight rotation, scaling, shifting, and brightness adjustments.
    """
    h, w = face_gray.shape
    
    # 1. Random rotation (-12 to +12 degrees)
    angle = random.uniform(-12, 12)
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(face_gray, rotation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    
    # 2. Random translation/shift (up to 5% of dimensions)
    tx = random.uniform(-0.05, 0.05) * w
    ty = random.uniform(-0.05, 0.05) * h
    translation_matrix = np.float32([[1, 0, tx], [0, 1, ty]])
    shifted = cv2.warpAffine(rotated, translation_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    
    # 3. Random scale/zoom (90% to 110%)
    scale = random.uniform(0.9, 1.1)
    scale_matrix = cv2.getRotationMatrix2D(center, 0, scale)
    scaled = cv2.warpAffine(shifted, scale_matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    
    # 4. Random brightness adjustment (multiply by 0.75 to 1.25)
    brightness_factor = random.uniform(0.75, 1.25)
    augmented = np.clip(scaled * brightness_factor, 0, 255).astype(np.uint8)
    
    # 5. Random horizontal flip (50% chance)
    if random.choice([True, False]):
        augmented = cv2.flip(augmented, 1)
        
    return augmented

def move_raw_images_from_root():
    """
    Scans the root directory for employee/owner images and moves them to data/raw_images.
    """
    root_dir = "."
    raw_dir = getattr(config, "RAW_IMAGES_DIR", "data/raw_images")
    os.makedirs(raw_dir, exist_ok=True)
    
    moved_count = 0
    for filename in os.listdir(root_dir):
        if not filename.lower().endswith((".jpg", ".png", ".jpeg")):
            continue
            
        lower_name = filename.lower()
        if lower_name.startswith("employee_") or lower_name.startswith("empolyee_") or lower_name.startswith("owner_"):
            src_path = os.path.join(root_dir, filename)
            dst_path = os.path.join(raw_dir, filename)
            
            try:
                shutil.move(src_path, dst_path)
                print(f"[INFO] Moved raw image to repository folder: {filename}")
                moved_count += 1
            except Exception as e:
                print(f"[WARNING] Failed to move {filename}: {e}")
                
    return moved_count

def process_raw_database():
    """
    Scans data/raw_images/, parses names, extracts faces, augments them,
    saves them to data/faces/<name_underscore>, and triggers retraining.
    """
    raw_dir = getattr(config, "RAW_IMAGES_DIR", "data/raw_images")
    faces_dir = "data/faces"
    
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(faces_dir, exist_ok=True)
    
    raw_files = [f for f in os.listdir(raw_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))]
    
    if not raw_files:
        print("[WARNING] No raw employee/owner images found in data/raw_images/.")
        print("Please place files like 'employee_Name.jpg' or 'owner_Name.jpg' there.")
        return
        
    total_processed = 0
    
    print("="*60)
    print("     PROCESSING RAW FACE IMAGES & GENERATING DATASET")
    print("="*60)
    
    for filename in raw_files:
        # Parse name: e.g. employee_Ranveer Singh.jpg -> Ranveer Singh
        name_part = filename
        for prefix in ["employee_", "empolyee_", "owner_"]:
            if name_part.lower().startswith(prefix):
                name_part = name_part[len(prefix):]
                
        # Strip extension
        name, _ = os.path.splitext(name_part)
        name = name.strip()
        
        # Directory name: Ranveer_Singh
        folder_name = name.replace(" ", "_")
        target_dir = os.path.join(faces_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        
        img_path = os.path.join(raw_dir, filename)
        image = cv2.imread(img_path)
        if image is None:
            print(f"[ERROR] Failed to read {filename}")
            continue
            
        # Detect Face
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = face_detector.process(rgb_image)
        
        if not results.detections:
            print(f"[WARNING] No face detected in {filename}. Skipping this file.")
            continue
            
        # Extract face bounding box
        detection = results.detections[0]
        bbox_data = detection.location_data.relative_bounding_box
        bbox = (bbox_data.xmin, bbox_data.ymin, bbox_data.width, bbox_data.height)
        
        face_gray = crop_and_resize_face(image, bbox)
        if face_gray is None:
            print(f"[ERROR] Failed to crop face from {filename}")
            continue
            
        # Save the original face crop
        orig_filename = f"processed_original_{int(time.time())}.jpg"
        cv2.imwrite(os.path.join(target_dir, orig_filename), face_gray)
        
        # Generate augmented images (60 copies)
        AUGMENTATION_COUNT = 60
        print(f"[INFO] Face detected for '{name.upper()}'. Generating {AUGMENTATION_COUNT} augmented samples...")
        
        for i in range(AUGMENTATION_COUNT):
            aug_face = augment_image(face_gray)
            aug_filename = f"augmented_{i}_{int(time.time() * 1000)}.jpg"
            cv2.imwrite(os.path.join(target_dir, aug_filename), aug_face)
            
        print(f"[SUCCESS] Dataset for {name} saved to: {target_dir}")
        total_processed += 1
        
    print("="*60)
    if total_processed > 0:
        print(f"[INFO] Processed {total_processed} raw image files.")
        print("[INFO] Triggering face recognition model retraining...")
        # Close face detector resource
        face_detector.close()
        # Retrain the model
        retrain_model()
    else:
        print("[INFO] No new face datasets were created.")
        face_detector.close()

if __name__ == "__main__":
    # 1. Move any raw images from root first
    move_raw_images_from_root()
    # 2. Process all raw images and train
    process_raw_database()
