from ultralytics import YOLO
import os
import cv2
import numpy as np

class GestureDetector:
    def __init__(self, mode="detect", model_path=None):
        """
        Initializes the GestureDetector.
        Modes:
        - "detect": One-stage YOLOv8 custom object detector (gesture_yolov8.pt).
        - "classify": Two-stage pipeline. MediaPipe Hands detects/crops hand, 
                      YOLOv8-classify model (gesture_yolov8_cls.pt) predicts gesture class.
        """
        self.mode = mode.lower()
        self.custom_model_loaded = False
        
        # Gesture classes matching dataset
        self.class_names = {
            0: "open_palm",
            1: "thumbs_up",
            2: "peace",
            3: "fist"
        }
        
        if self.mode == "classify":
            print("[INFO] GestureDetector set to CLASSIFICATION mode.")
            # Initialize MediaPipe Hands for localization
            try:
                import mediapipe as mp
                self.mp_hands = mp.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            except Exception as e:
                print(f"[ERROR] Failed to load MediaPipe for classification mode: {e}")
                self.hands = None
                
            # Load custom classifier
            if model_path is None:
                model_path = os.path.join("models", "gesture_yolov8_cls.pt")
                
            if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
                print(f"[INFO] Loading custom gesture classifier from {model_path}...")
                self.model = YOLO(model_path)
                self.custom_model_loaded = True
            else:
                print(f"[WARNING] Classifier model not found or empty at {model_path}!")
                print("[WARNING] Falling back to pretrained yolov8n-cls.pt for placeholder classification.")
                self.model = YOLO("yolov8n-cls.pt")
                
        else:  # Default to "detect"
            print("[INFO] GestureDetector set to DETECTION mode.")
            if model_path is None:
                model_path = os.path.join("models", "gesture_yolov8.pt")
                
            if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
                print(f"[INFO] Loading custom gesture detector from {model_path}...")
                self.model = YOLO(model_path)
                self.custom_model_loaded = True
            else:
                print(f"[WARNING] Custom detector model not found or empty at {model_path}!")
                print("[WARNING] Falling back to pretrained yolov8n.pt for placeholder detection.")
                self.model = YOLO("yolov8n.pt")

    def detect(self, frame, conf_threshold=0.5):
        """
        Runs gesture inference on the frame.
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
        if self.mode == "classify":
            return self._detect_classify_mode(frame, conf_threshold)
        else:
            return self._detect_detection_mode(frame, conf_threshold)

    def _detect_detection_mode(self, frame, conf_threshold):
        """Standard YOLOv8 Object Detection Mode."""
        results = self.model(frame, verbose=False)
        detections = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf < conf_threshold:
                    continue
                    
                cls_id = int(box.cls[0])
                x1, y1, x2, y2 = box.xyxy[0]
                box_coords = (int(x1), int(y1), int(x2), int(y2))
                
                if self.custom_model_loaded:
                    class_name = self.class_names.get(cls_id, f"unknown_{cls_id}")
                else:
                    # Fallback COCO classes mapping
                    coco_class_name = self.model.names.get(cls_id, "unknown")
                    class_name = coco_class_name
                    
                detections.append({
                    "box": box_coords,
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf
                })
                
        return detections

    def _detect_classify_mode(self, frame, conf_threshold):
        """Two-stage mode: MediaPipe Hands for cropping, YOLOv8-classify for gesture."""
        if self.hands is None:
            return []
            
        img_h, img_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)
        detections = []
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Extract landmark coordinates
                x_coords = [lm.x for lm in hand_landmarks.landmark]
                y_coords = [lm.y for lm in hand_landmarks.landmark]
                
                # Compute bounding box with padding
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                
                padding = 0.06
                x_min_p = max(0.0, x_min - padding)
                x_max_p = min(1.0, x_max + padding)
                y_min_p = max(0.0, y_min - padding)
                y_max_p = min(1.0, y_max + padding)
                
                # Convert to pixel coordinates
                x1 = int(x_min_p * img_w)
                y1 = int(y_min_p * img_h)
                x2 = int(x_max_p * img_w)
                y2 = int(y_max_p * img_h)
                
                box_coords = (x1, y1, x2, y2)
                
                # Crop hand from frame
                cropped_hand = frame[max(0, y1):min(img_h, y2), max(0, x1):min(img_w, x2)]
                
                if cropped_hand.size == 0:
                    continue
                    
                # Run YOLO classification model on the cropped hand
                cls_results = self.model(cropped_hand, verbose=False)
                
                for r in cls_results:
                    if r.probs is not None:
                        # Get highest probability index
                        top_cls_id = int(r.probs.top1)
                        conf = float(r.probs.top1conf)
                        
                        if conf < conf_threshold:
                            continue
                            
                        if self.custom_model_loaded:
                            class_name = self.class_names.get(top_cls_id, f"unknown_{top_cls_id}")
                        else:
                            # Fallback classification class names
                            class_name = self.model.names.get(top_cls_id, "unknown")
                            
                        detections.append({
                            "box": box_coords,
                            "class_id": top_cls_id,
                            "class_name": class_name,
                            "confidence": conf
                        })
                        
                break  # Process only the first detected hand
                
        return detections
