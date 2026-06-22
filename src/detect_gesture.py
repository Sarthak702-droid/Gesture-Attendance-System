from ultralytics import YOLO
import os

class GestureDetector:
    def __init__(self, model_path=None):
        """
        Initializes the YOLOv8 model for gesture detection.
        If custom model is not found, falls back to the pretrained yolov8n.pt.
        """
        if model_path is None:
            model_path = os.path.join("models", "gesture_yolov8.pt")
            
        self.custom_model_loaded = False
        
        if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
            print(f"[INFO] Loading custom gesture YOLO model from {model_path}...")
            self.model = YOLO(model_path)
            self.custom_model_loaded = True
        else:
            print(f"[WARNING] Custom model not found or empty at {model_path}!")
            print("[WARNING] Falling back to pretrained yolov8n.pt. Detection will serve as a placeholder.")
            self.model = YOLO("yolov8n.pt")
            
        # Class names mapping matching dataset/data.yaml
        self.class_names = {
            0: "open_palm",
            1: "thumbs_up",
            2: "peace",
            3: "fist"
        }

    def detect(self, frame, conf_threshold=0.5):
        """
        Runs model inference on a frame.
        Returns a list of detections:
        [
            {
                "box": (x1, y1, x2, y2),
                "class_id": class_id,
                "class_name": class_name,
                "confidence": confidence
            },
            ...
        ]
        """
        results = self.model(frame, verbose=False)
        detections = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf < conf_threshold:
                    continue
                    
                cls_id = int(box.cls[0])
                
                # Bounding box coordinates (xyxy format, floats)
                x1, y1, x2, y2 = box.xyxy[0]
                box_coords = (int(x1), int(y1), int(x2), int(y2))
                
                # Class name resolution
                if self.custom_model_loaded:
                    class_name = self.class_names.get(cls_id, f"unknown_{cls_id}")
                else:
                    # In pretrained yolov8n.pt, class names are different (COCO dataset)
                    # We will map whatever it detects to a placeholder name for testing purposes
                    coco_class_name = self.model.names.get(cls_id, "unknown")
                    class_name = coco_class_name
                    
                detections.append({
                    "box": box_coords,
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf
                })
                
        return detections
