import cv2
import numpy as np
import os

class GestureDetector:
    def __init__(self, mode="mediapipe", model_path=None):
        """
        Initializes the GestureDetector.
        By default, uses MediaPipe Hands to do rule-based gesture tracking.
        This provides 30 FPS, zero-training, and high-accuracy palm detection.
        """
        self.mode = "mediapipe"
        print("[INFO] GestureDetector initialized using MEDIAPIPE rule-based engine.")
        
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

    def detect(self, frame, conf_threshold=0.55):
        """
        Runs gesture detection using MediaPipe.
        Returns a list of detections:
        [
            {
                "box": (x1, y1, x2, y2),
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence
            }
        ]
        """
        if self.hands is None:
            return []
            
        img_h, img_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        detections = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw landmarks on frame for feedback
                self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Extract coordinates
                landmarks = hand_landmarks.landmark
                
                # Get bounding box coordinates
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]
                
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                padding = 0.05
                x1 = int(max(0.0, x_min - padding) * img_w)
                y1 = int(max(0.0, y_min - padding) * img_h)
                x2 = int(min(1.0, x_max + padding) * img_w)
                y2 = int(min(1.0, y_max + padding) * img_h)
                
                bbox = (x1, y1, x2, y2)
                
                # --- RULE-BASED GESTURE CLASSIFIER ---
                # Check if index, middle, ring, and pinky are extended
                # Finger tips: Index (8), Middle (12), Ring (16), Pinky (20)
                # PIP Joints: Index (6), Middle (10), Ring (14), Pinky (18)
                # In image coordinates, y=0 is at the top, so tip.y < pip.y means extended.
                
                index_extended = landmarks[8].y < landmarks[6].y
                middle_extended = landmarks[12].y < landmarks[10].y
                ring_extended = landmarks[16].y < landmarks[14].y
                pinky_extended = landmarks[20].y < landmarks[18].y
                
                # Thumb logic: Thumb is extended if the distance between Thumb Tip (4) and Index Knuckle (5) is wide
                # Calculate Euclidean distance in 2D
                thumb_tip = np.array([landmarks[4].x, landmarks[4].y])
                index_knuckle = np.array([landmarks[5].x, landmarks[5].y])
                thumb_dist = np.linalg.norm(thumb_tip - index_knuckle)
                thumb_extended = thumb_dist > 0.08
                
                gesture = "unknown"
                class_id = -1
                
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
                    
                if class_id != -1:
                    detections.append({
                        "box": bbox,
                        "class_id": class_id,
                        "class_name": gesture,
                        "confidence": 1.0  # Rule-based is highly deterministic
                    })
                break  # Process only the first hand detected
                
        return detections
