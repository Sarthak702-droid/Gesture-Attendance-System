from ultralytics import YOLO
import os
import shutil

def main():
    # Define paths
    yaml_path = os.path.abspath(os.path.join("dataset", "data.yaml"))
    
    if not os.path.exists(yaml_path):
        print(f"[ERROR] dataset/data.yaml not found at {yaml_path}")
        return

    # Load pretrained YOLOv8 nano model
    print("[INFO] Loading pretrained YOLOv8 nano model...")
    model = YOLO("yolov8n.pt")
    
    # Train the model
    # We set device='cpu' to prevent any cuda crashes if the drivers are not proper.
    # If the user has a GPU, they can change this to device=0 or just omit it to let ultralytics choose.
    print("[INFO] Starting training on custom dataset...")
    results = model.train(
        data=yaml_path,
        epochs=50,
        imgsz=640,
        project="models",
        name="gesture_train",
        exist_ok=True
    )
    
    # Copy trained weights to models/gesture_yolov8.pt
    src_best = os.path.join("models", "gesture_train", "weights", "best.pt")
    dest_best = os.path.join("models", "gesture_yolov8.pt")
    
    if os.path.exists(src_best):
        os.makedirs("models", exist_ok=True)
        shutil.copy(src_best, dest_best)
        print(f"[SUCCESS] Trained model saved and copied to: {dest_best}")
    else:
        print(f"[WARNING] Could not find the trained weights at {src_best}. Please check the training output.")

if __name__ == "__main__":
    main()
