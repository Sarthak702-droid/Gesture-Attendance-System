import cv2
import os
import mediapipe as mp
import numpy as np

def crop_and_resize_face(frame, bbox, target_size=(200, 200)):
    h, w, _ = frame.shape
    x, y, width, height = bbox
    
    # Add 15% padding
    padding_w = int(width * 0.15)
    padding_h = int(height * 0.15)
    
    x1 = max(0, x - padding_w)
    y1 = max(0, y - padding_h)
    x2 = min(w, x + width + padding_w)
    y2 = min(h, y + height + padding_h)
    
    face_crop = frame[y1:y2, x1:x2]
    if face_crop.size == 0:
        return None
        
    gray_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    resized_crop = cv2.resize(gray_crop, target_size, interpolation=cv2.INTER_AREA)
    return resized_crop

def main():
    employee_name = "Sarthak Tripathy"
    folder_name = employee_name.replace(" ", "_")
    face_dir = os.path.join("data", "faces", folder_name)
    os.makedirs(face_dir, exist_ok=True)
    
    # Initialize MediaPipe Face Detection
    mp_face = mp.solutions.face_detection
    face_detector = mp_face.FaceDetection(min_detection_confidence=0.55)
    
    print("="*60)
    print("      EXTRACTING FACES FROM EXISTING WORKSPACE IMAGES")
    print("="*60)
    
    # List of files/directories to scan
    scan_paths = [
        "test/test2.jpg",
        "test/test3.jpg"
    ]
    
    # Add all images from dataset
    dataset_dirs = [
        "dataset/images/train",
        "dataset/images/val"
    ]
    for d in dataset_dirs:
        if os.path.exists(d):
            for file in os.listdir(d):
                if file.endswith(".jpg"):
                    scan_paths.append(os.path.join(d, file))
                    
    print(f"[INFO] Found {len(scan_paths)} potential images to scan for faces.")
    
    count = 0
    scanned = 0
    
    for fpath in scan_paths:
        if not os.path.exists(fpath):
            continue
            
        img = cv2.imread(fpath)
        if img is None:
            continue
            
        scanned += 1
        img_h, img_w, _ = img.shape
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = face_detector.process(rgb_img)
        
        if results.detections:
            for idx, detection in enumerate(results.detections):
                bbox_data = detection.location_data.relative_bounding_box
                x = int(bbox_data.xmin * img_w)
                y = int(bbox_data.ymin * img_h)
                width = int(bbox_data.width * img_w)
                height = int(bbox_data.height * img_h)
                
                # Filter out extremely small face boxes (noise)
                if width < 30 or height < 30:
                    continue
                    
                face_img = crop_and_resize_face(img, (x, y, width, height))
                if face_img is not None:
                    count += 1
                    out_path = os.path.join(face_dir, f"extracted_face_{count}.jpg")
                    cv2.imwrite(out_path, face_img)
                    break # Only extract one face per image
                    
        if scanned % 50 == 0:
            print(f"Scanned {scanned}/{len(scan_paths)} images... Extracted {count} faces.")
            
    face_detector.close()
    
    print("\n" + "="*60)
    print("      EXTRACTION SUMMARY")
    print("="*60)
    print(f"Total Images Scanned: {scanned}")
    print(f"Faces Extracted and Saved: {count}")
    print(f"Output Directory: {face_dir}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
