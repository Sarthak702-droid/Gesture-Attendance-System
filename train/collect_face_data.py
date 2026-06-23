import cv2
import os
import time
import mediapipe as mp
import numpy as np

def crop_and_resize_face(frame, bbox, target_size=(200, 200)):
    """
    Crops the face from the frame using bounding box, converts to grayscale, and resizes.
    """
    h, w, _ = frame.shape
    x, y, width, height = bbox
    
    # Expand bounding box slightly for better facial feature capture
    padding_w = int(width * 0.1)
    padding_h = int(height * 0.1)
    
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

def process_static_images(detector, face_dir):
    """
    Scans test/test2.jpg and test/test3.jpg and extracts faces if found.
    """
    test_files = ["test/test2.jpg", "test/test3.jpg"]
    count = 0
    
    for fpath in test_files:
        if not os.path.exists(fpath):
            continue
            
        img = cv2.imread(fpath)
        if img is None:
            continue
            
        img_h, img_w, _ = img.shape
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = detector.process(rgb_img)
        
        if results.detections:
            for idx, detection in enumerate(results.detections):
                bbox_data = detection.location_data.relative_bounding_box
                x = int(bbox_data.xmin * img_w)
                y = int(bbox_data.ymin * img_h)
                width = int(bbox_data.width * img_w)
                height = int(bbox_data.height * img_h)
                
                face_img = crop_and_resize_face(img, (x, y, width, height))
                if face_img is not None:
                    count += 1
                    out_path = os.path.join(face_dir, f"static_face_{count}_{idx}.jpg")
                    cv2.imwrite(out_path, face_img)
                    
    if count > 0:
        print(f"[INFO] Successfully extracted {count} face samples from existing test images.")
    else:
        print("[INFO] No faces found in existing test images. Capturing via webcam is required.")

def main():
    print("="*60)
    print("      FACE DATA COLLECTOR FOR RECOGNITION")
    print("="*60)
    
    employee_name = input("Enter Employee Name (Default: Sarthak Tripathy): ").strip()
    if not employee_name:
        employee_name = "Sarthak Tripathy"
        
    # Format folder name: Sarthak_Tripathy
    folder_name = employee_name.replace(" ", "_")
    face_dir = os.path.join("data", "faces", folder_name)
    os.makedirs(face_dir, exist_ok=True)
    
    # Initialize MediaPipe Face Detection
    mp_face = mp.solutions.face_detection
    face_detector = mp_face.FaceDetection(min_detection_confidence=0.6)
    
    # 1. Process existing test images
    process_static_images(face_detector, face_dir)
    
    # 2. Capture from Webcam
    SAMPLES_TO_COLLECT = 100
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("[WARNING] Webcam not accessible. Using only static images for face data.")
        face_detector.close()
        return
        
    cv2.namedWindow("Face Data Collector", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Face Data Collector", 800, 600)
    
    print(f"\n[INFO] Starting webcam to collect {SAMPLES_TO_COLLECT} samples.")
    print("Hold position and turn your head slightly to capture different angles.")
    print("Press SPACE to start capturing, or 'q' to quit.")
    
    # Wait for space to start
    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        cv2.putText(frame, f"Ready for: {employee_name.upper()}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, "Press SPACE to start capturing...", (20, h - 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        
        cv2.imshow("Face Data Collector", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            break
        elif key == ord('q'):
            cap.release()
            cv2.destroyAllWindows()
            face_detector.close()
            return
            
    # Capture loop
    count = 0
    while count < SAMPLES_TO_COLLECT:
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detector.process(rgb_frame)
        
        face_detected = False
        
        if results.detections:
            # Take the first detected face
            detection = results.detections[0]
            bbox_data = detection.location_data.relative_bounding_box
            x = int(bbox_data.xmin * w)
            y = int(bbox_data.ymin * h)
            width = int(bbox_data.width * w)
            height = int(bbox_data.height * h)
            
            face_img = crop_and_resize_face(frame, (x, y, width, height))
            if face_img is not None:
                count += 1
                out_path = os.path.join(face_dir, f"webcam_face_{count}.jpg")
                cv2.imwrite(out_path, face_img)
                face_detected = True
                
                # Draw box on display frame
                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)
                
        # HUD info
        if face_detected:
            cv2.putText(frame, f"Capturing: {count}/{SAMPLES_TO_COLLECT}", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        else:
            cv2.putText(frame, "FACE NOT DETECTED", (20, 40), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
            
        cv2.imshow("Face Data Collector", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
            
        time.sleep(0.05) # Add a tiny delay
        
    cap.release()
    cv2.destroyAllWindows()
    face_detector.close()
    
    print("\n" + "="*60)
    print("[SUCCESS] Face samples collection completed!")
    print(f"[SUCCESS] Dataset saved to: {face_dir}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
