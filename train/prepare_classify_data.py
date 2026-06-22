import os
import cv2
import shutil

def main():
    base_dir = "dataset"
    classify_dir = "dataset_classify"
    
    splits = ["train", "val"]
    
    classes = {
        0: "open_palm",
        1: "thumbs_up",
        2: "peace",
        3: "fist"
    }
    
    print("[INFO] Preparing classification dataset by cropping hands from labeled images...")
    
    # Create output directories
    for split in splits:
        for class_name in classes.values():
            os.makedirs(os.path.join(classify_dir, split, class_name), exist_ok=True)
            
    total_cropped = 0
    
    for split in splits:
        img_dir = os.path.join(base_dir, "images", split)
        lbl_dir = os.path.join(base_dir, "labels", split)
        
        if not os.path.exists(img_dir):
            continue
            
        for file in os.listdir(img_dir):
            if not file.endswith(".jpg"):
                continue
                
            base_name = os.path.splitext(file)[0]
            img_path = os.path.join(img_dir, file)
            lbl_path = os.path.join(lbl_dir, f"{base_name}.txt")
            
            if not os.path.exists(lbl_path):
                continue
                
            # Read image
            img = cv2.imread(img_path)
            if img is None:
                continue
                
            img_h, img_w, _ = img.shape
            
            # Read label annotations
            with open(lbl_path, "r") as lf:
                lines = lf.readlines()
                
            for idx, line in enumerate(lines):
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                    
                cls_idx = int(parts[0])
                x_center = float(parts[1])
                y_center = float(parts[2])
                box_w = float(parts[3])
                box_h = float(parts[4])
                
                # Convert normalized coordinates to pixel bounding box coordinates
                x1 = int((x_center - box_w / 2.0) * img_w)
                y1 = int((y_center - box_h / 2.0) * img_h)
                x2 = int((x_center + box_w / 2.0) * img_w)
                y2 = int((y_center + box_h / 2.0) * img_h)
                
                # Clamp coordinates to image dimensions
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(img_w, x2)
                y2 = min(img_h, y2)
                
                # Crop hand
                cropped_hand = img[y1:y2, x1:x2]
                
                if cropped_hand.size == 0:
                    continue
                    
                # Save cropped hand to class folder
                class_name = classes.get(cls_idx, "unknown")
                out_path = os.path.join(classify_dir, split, class_name, f"{base_name}_crop_{idx}.jpg")
                cv2.imwrite(out_path, cropped_hand)
                total_cropped += 1
                
    print(f"[SUCCESS] Classification dataset prepared! Cropped {total_cropped} hand images.")
    print(f"Dataset stored under '{classify_dir}/'")

if __name__ == "__main__":
    main()
