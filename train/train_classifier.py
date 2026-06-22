from ultralytics import YOLO
import os
import shutil

def main():
    data_dir = os.path.abspath("dataset_classify")
    
    if not os.path.exists(data_dir):
        print(f"[ERROR] Classification dataset not found at {data_dir}.")
        print("[ERROR] Please run train/prepare_classify_data.py first to create cropped images.")
        return

    # Load pretrained YOLOv8 nano classification model
    print("[INFO] Loading pretrained YOLOv8 nano classification model...")
    model = YOLO("yolov8n-cls.pt")
    
    # Train the model
    print("[INFO] Starting classification model training...")
    model.train(
        data=data_dir,
        epochs=50,
        imgsz=224,
        project="models",
        name="gesture_train_cls",
        exist_ok=True
    )
    
    # Copy trained weights to models/gesture_yolov8_cls.pt
    src_best = os.path.join("models", "gesture_train_cls", "weights", "best.pt")
    dest_best = os.path.join("models", "gesture_yolov8_cls.pt")
    
    if os.path.exists(src_best):
        os.makedirs("models", exist_ok=True)
        shutil.copy(src_best, dest_best)
        print(f"[SUCCESS] Trained classification model saved and copied to: {dest_best}")
    else:
        print(f"[WARNING] Could not find the trained weights at {src_best}. Check training output.")

if __name__ == "__main__":
    main()
