import cv2
import os
import json
from config import FACE_MODEL_PATH, FACES_DIR

class FaceRecognizer:
    def __init__(self):
        """
        Face verification class using OpenCV's Haar Cascade Face Detector 
        and Local Binary Patterns Histograms (LBPH) Face Recognizer.
        """
        # Load the built-in Haar Cascade classifier for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        self.model_loaded = False
        self.labels_map = {}
        
        # Create LBPH Face Recognizer
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
            
            # Load trained model if it exists
            labels_json_path = FACE_MODEL_PATH.replace(".yml", "_labels.json")
            if os.path.exists(FACE_MODEL_PATH) and os.path.exists(labels_json_path):
                self.recognizer.read(FACE_MODEL_PATH)
                with open(labels_json_path, "r") as jf:
                    # JSON keys are always strings, convert back to int labels
                    self.labels_map = {int(k): v for k, v in json.load(jf).items()}
                self.model_loaded = True
                print(f"[INFO] Face recognition model loaded successfully from {FACE_MODEL_PATH}")
                print(f"[INFO] Loaded faces database: {list(self.labels_map.values())}")
            else:
                print("[WARNING] Face recognition model weights or labels map not found.")
                print("[WARNING] Run train/train_faces.py after placing face images under data/faces/")
        except Exception as e:
            print(f"[ERROR] Failed to initialize LBPH Face Recognizer: {e}")

    def detect_face(self, frame):
        """
        Detects faces in a frame.
        Returns (bbox, gray_face_crop) for the largest face detected.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Equalize histogram to improve face detection under variable lighting
        gray = cv2.equalizeHist(gray)
        
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.2, 
            minNeighbors=5, 
            minSize=(80, 80)
        )
        
        if len(faces) == 0:
            return None, None
            
        # Select the largest face by area
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face
        
        # Crop the face from the grayscale frame
        gray_face_crop = gray[y:y+h, x:x+w]
        # Resize to a standard size for consistency (e.g. 150x150)
        gray_face_crop = cv2.resize(gray_face_crop, (150, 150))
        
        return (x, y, x + w, y + h), gray_face_crop

    def verify_face(self, frame, expected_name):
        """
        Verifies if the face detected in the frame matches the expected_name.
        Returns: (success_bool, message_str)
        """
        if not self.model_loaded:
            return True, "Face Verification Disabled (Model not trained yet)"
            
        bbox, gray_face = self.detect_face(frame)
        if gray_face is None:
            return False, "Face not detected. Look straight at the camera."
            
        try:
            # Predict the identity of the face
            # label_id: the matched class index
            # confidence: distance metric (lower is better, 0.0 is perfect match)
            label_id, confidence = self.recognizer.predict(gray_face)
            
            matched_name = self.labels_map.get(label_id, "Unknown")
            print(f"[FACE_REC] Expected: {expected_name}, Matched: {matched_name}, Confidence: {confidence:.2f}")
            
            # LBPH confidence threshold: values below 75-80 indicate a reliable match
            THRESHOLD = 75.0
            
            if matched_name.strip().lower() == expected_name.strip().lower():
                if confidence <= THRESHOLD:
                    return True, f"Face Verified ({matched_name.upper()}, score: {confidence:.1f})"
                else:
                    return False, f"Face match weak (score: {confidence:.1f}). Hold face steady."
            else:
                return False, "Access Denied: Face does not match registered employee!"
                
        except Exception as e:
            return False, f"Face verification error: {str(e)}"
