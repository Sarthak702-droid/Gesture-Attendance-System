import cv2
import numpy as np
import os
import pickle

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

class GestureDetector:
    def __init__(self, model_path=None):
        """
        Gesture detector that uses MediaPipe Hands for tracking
        and a trained Support Vector Machine (SVM) ML classifier for gesture prediction.
        Falls back to rule-based mathematical detection if the ML model is not trained.
        """
        # 1. Initialize MediaPipe
        try:
            import mediapipe as mp
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6
            )
            self.mp_draw = mp.solutions.drawing_utils
        except Exception as e:
            print(f"[ERROR] Failed to load MediaPipe: {e}")
            self.hands = None

        # 2. Load ML Classifier
        if model_path is None:
            model_path = os.path.join("models", "gesture_classifier.pkl")
            
        self.ml_model_loaded = False
        self.classifier = None
        
        if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
            try:
                with open(model_path, "rb") as f:
                    self.classifier = pickle.load(f)
                self.ml_model_loaded = True
                print(f"[INFO] Loaded hand landmark ML classifier from {model_path}")
            except Exception as e:
                print(f"[WARNING] Failed to load ML model: {e}. Using mathematical rules fallback.")
        else:
            print("[WARNING] ML classifier model not found or empty.")
            print("[WARNING] System will run in rule-based fallback mode. Train model using train/train_landmark_classifier.py")
            
        # Class names map
        self.class_names = {
            0: "open_palm",
            1: "thumbs_up",
            2: "peace",
            3: "fist"
        }

    def detect(self, frame, conf_threshold=0.55):
        """
        Detects hand and predicts gesture class using either ML model or mathematical rules.
        """
        if self.hands is None:
            return []
            
        img_h, img_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        detections = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw landmarks for visual feedback
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Bounding box
                x_coords = [lm.x for lm in hand_landmarks.landmark]
                y_coords = [lm.y for lm in hand_landmarks.landmark]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                padding = 0.05
                x1 = int(max(0.0, x_min - padding) * img_w)
                y1 = int(max(0.0, y_min - padding) * img_h)
                x2 = int(min(1.0, x_max + padding) * img_w)
                y2 = int(min(1.0, y_max + padding) * img_h)
                bbox = (x1, y1, x2, y2)
                
                gesture = "unknown"
                class_id = -1
                confidence = 0.0
                
                # Mode A: ML Model Inference
                if self.ml_model_loaded and self.classifier is not None:
                    try:
                        coords = get_normalized_landmarks(hand_landmarks.landmark)
                        
                        # Get class probabilities
                        probs = self.classifier.predict_proba([coords])[0]
                        pred_class = int(np.argmax(probs))
                        pred_conf = float(probs[pred_class])
                        
                        if pred_conf >= conf_threshold:
                            class_id = pred_class
                            gesture = self.class_names.get(class_id, "unknown")
                            confidence = pred_conf
                    except Exception as e:
                        print(f"[WARNING] ML inference error: {e}. Retrying with mathematical rules.")
                        
                # Mode B: Rule-based fallback if ML fails or is not loaded
                if class_id == -1:
                    landmarks = hand_landmarks.landmark
                    index_extended = landmarks[8].y < landmarks[6].y
                    middle_extended = landmarks[12].y < landmarks[10].y
                    ring_extended = landmarks[16].y < landmarks[14].y
                    pinky_extended = landmarks[20].y < landmarks[18].y
                    
                    # Thumb logic: Thumb tip distance to Index knuckle
                    thumb_tip = np.array([landmarks[4].x, landmarks[4].y])
                    index_knuckle = np.array([landmarks[5].x, landmarks[5].y])
                    thumb_dist = np.linalg.norm(thumb_tip - index_knuckle)
                    thumb_extended = thumb_dist > 0.08
                    
                    # ✋ Open Palm: All 4 major fingers open
                    if index_extended and middle_extended and ring_extended and pinky_extended:
                        gesture = "open_palm"
                        class_id = 0
                        
                    # ✌️ Peace Sign: Only Index and Middle open, Ring and Pinky closed
                    elif index_extended and middle_extended and not ring_extended and not pinky_extended:
                        gesture = "peace"
                        class_id = 2
                        
                    # 👍 Thumbs Up: Only Thumb extended, other 4 closed, and thumb tip above wrist
                    elif thumb_extended and not index_extended and not middle_extended and not ring_extended and not pinky_extended:
                        if landmarks[4].y < landmarks[0].y: # thumb pointing up relative to wrist
                            gesture = "thumbs_up"
                            class_id = 1
                            
                    # ✊ Fist: All 4 major fingers folded, and thumb folded/close
                    elif not index_extended and not middle_extended and not ring_extended and not pinky_extended and not thumb_extended:
                        gesture = "fist"
                        class_id = 3
                        
                    confidence = 1.0  # Rule-based is highly deterministic
                    
                if class_id != -1:
                    detections.append({
                        "box": bbox,
                        "class_id": class_id,
                        "class_name": gesture,
                        "confidence": confidence
                    })
                break  # Process only the first hand detected
                
        return detections
