import pandas as pd
import numpy as np
import os
import pickle
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report

def main():
    dataset_path = os.path.join("data", "landmark_dataset.csv")
    model_dir = "models"
    model_path = os.path.join(model_dir, "gesture_classifier.pkl")
    
    if not os.path.exists(dataset_path):
        print(f"[ERROR] Dataset not found at {dataset_path}")
        print("Please run train/collect_landmark_data.py first to collect training data.")
        return
        
    print("[INFO] Loading landmark dataset...")
    df = pd.read_csv(dataset_path)
    
    # Split features and labels
    # Column 0: label, Columns 1+: coordinates
    X = df.iloc[:, 1:].values
    y = df.iloc[:, 0].values
    
    # Split into train/test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"[INFO] Dataset loaded: {X_train.shape[0]} train samples, {X_test.shape[0]} test samples.")
    print("[INFO] Training Support Vector Machine (SVM) Classifier...")
    
    # Initialize and train linear SVM classifier
    # Linear kernel is extremely fast and generalizes well for normalized coordinates
    clf = SVC(kernel="linear", C=1.0, probability=True, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print("\n" + "="*50)
    print(f"      EVALUATION RESULTS (Test Accuracy: {accuracy*100:.2f}%)")
    print("="*50)
    print(classification_report(y_test, y_pred, target_names=["Open Palm", "Thumbs Up", "Peace", "Fist"]))
    print("="*50 + "\n")
    
    # Save the model
    os.makedirs(model_dir, exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump(clf, f)
        
    print(f"[SUCCESS] Trained machine learning classifier saved to: {model_path}")
    print("[SUCCESS] Size of trained model: {:.1f} KB".format(os.path.getsize(model_path) / 1024.0))

if __name__ == "__main__":
    main()
