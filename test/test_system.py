import os
import sys
import unittest
import numpy as np

# Add src to python path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

class TestGestureAttendanceSystem(unittest.TestCase):
    def setUp(self):
        # We will use a separate test CSV file to avoid messing up production logs
        import attendance
        self.original_csv_path = attendance.CSV_PATH
        attendance.CSV_PATH = os.path.join("data", "test_attendance.csv")
        self.test_csv_path = attendance.CSV_PATH
        
        # Clean up any leftover test CSV files
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)

    def tearDown(self):
        # Restore original CSV path and clean up
        import attendance
        attendance.CSV_PATH = self.original_csv_path
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)

    def test_imports(self):
        """Verify all custom modules can be imported without syntax errors."""
        try:
            import attendance
            import detect_gesture
            import utils
            import main
            print("[TEST] All modules imported successfully!")
        except Exception as e:
            self.fail(f"Module import failed: {e}")

    def test_attendance_logging_and_cooldown(self):
        """Verify attendance logs correctly and cooldown duplicate checking works."""
        from attendance import mark_attendance
        
        # First log - should succeed
        success, msg = mark_attendance("John Doe", "PRESENT")
        self.assertTrue(success)
        self.assertIn("Successfully logged", msg)
        
        # Verify file exists and has content
        self.assertTrue(os.path.exists(self.test_csv_path))
        with open(self.test_csv_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Header + 1 record
            self.assertIn("John Doe,PRESENT", lines[1])

        # Second log (immediate duplicate) - should fail due to cooldown
        success2, msg2 = mark_attendance("John Doe", "PRESENT")
        self.assertFalse(success2)
        self.assertIn("Already logged", msg2)
        self.assertIn("Cooldown", msg2)
        
        # Verify no duplicate row was added
        with open(self.test_csv_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Still only 2 lines
            
        # Different student or status should work
        success3, msg3 = mark_attendance("Jane Smith", "PRESENT")
        self.assertTrue(success3)
        
        success4, msg4 = mark_attendance("John Doe", "ABSENT")
        self.assertTrue(success4)

    def test_gesture_detector_init(self):
        """Verify detector initializes (even with fallback to yolov8n.pt)."""
        from detect_gesture import GestureDetector
        
        try:
            # Should load fallback yolov8n.pt if gesture_yolov8.pt isn't trained yet
            detector = GestureDetector()
            self.assertIsNotNone(detector.model)
            print("[TEST] GestureDetector initialized successfully!")
            
            # Run inference on a blank dummy image
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = detector.detect(dummy_frame)
            self.assertIsInstance(detections, list)
            print(f"[TEST] Run mock detection. Number of detections found: {len(detections)}")
        except Exception as e:
            self.fail(f"Gesture detector test failed: {e}")

if __name__ == "__main__":
    unittest.main()
