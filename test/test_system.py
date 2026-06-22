import os
import sys
import unittest
import numpy as np
from unittest.mock import MagicMock, patch

# Add src to python path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

class TestGestureAttendanceSystem(unittest.TestCase):
    def setUp(self):
        # We will use a separate test CSV and XLSX file to avoid messing up production logs
        import attendance
        self.original_csv_path = attendance.CSV_PATH
        self.original_xlsx_path = attendance.XLSX_PATH
        
        attendance.CSV_PATH = os.path.join("data", "test_attendance.csv")
        attendance.XLSX_PATH = os.path.join("data", "test_attendance.xlsx")
        
        self.test_csv_path = attendance.CSV_PATH
        self.test_xlsx_path = attendance.XLSX_PATH
        
        # Clean up any leftover test files
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)
        if os.path.exists(self.test_xlsx_path):
            os.remove(self.test_xlsx_path)

    def tearDown(self):
        # Restore original paths and clean up
        import attendance
        attendance.CSV_PATH = self.original_csv_path
        attendance.XLSX_PATH = self.original_xlsx_path
        
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)
        if os.path.exists(self.test_xlsx_path):
            os.remove(self.test_xlsx_path)

    def test_imports(self):
        """Verify all custom modules can be imported without syntax errors."""
        try:
            import config
            import attendance
            import detect_gesture
            import face_rec
            import security
            import utils
            import main
            import dashboard
            print("[TEST] All modules (including security and config) imported successfully!")
        except Exception as e:
            self.fail(f"Module import failed: {e}")

    def test_attendance_logging_and_cooldown(self):
        """Verify attendance logs correctly, cooldown duplicates works, and Excel syncs."""
        from attendance import mark_attendance
        
        # First log - should succeed
        success, msg = mark_attendance("John Doe", "PRESENT")
        self.assertTrue(success)
        self.assertIn("Successfully logged", msg)
        
        # Verify CSV file exists and has content
        self.assertTrue(os.path.exists(self.test_csv_path))
        with open(self.test_csv_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Header + 1 record
            self.assertIn("John Doe,PRESENT", lines[1])

        # Verify Excel file exists
        self.assertTrue(os.path.exists(self.test_xlsx_path))
        
        # Second log (immediate duplicate) - should fail due to cooldown
        success2, msg2 = mark_attendance("John Doe", "PRESENT")
        self.assertFalse(success2)
        self.assertIn("Already logged", msg2)

    def test_config_parameters(self):
        """Verify that configuration settings are accessible and correctly typed."""
        import config
        self.assertTrue(hasattr(config, "CAMERA_SOURCE"))
        self.assertTrue(hasattr(config, "FACE_RECOGNITION_ENABLED"))
        self.assertTrue(hasattr(config, "SURVEILLANCE_ENABLED"))
        self.assertIsInstance(config.LOCK_HOURS_START, str)
        self.assertIsInstance(config.LOCK_HOURS_END, str)

    def test_face_recognizer_init(self):
        """Verify FaceRecognizer class initializes and handles face detection on mock frame."""
        from face_rec import FaceRecognizer
        recognizer = FaceRecognizer()
        self.assertFalse(recognizer.model_loaded) # Initially false because models aren't trained
        
        # Test detection on empty black frame (should return None, None)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bbox, gray_crop = recognizer.detect_face(dummy_frame)
        self.assertIsNone(bbox)
        self.assertIsNone(gray_crop)
        
        # Test verification when model not loaded (should auto-bypass and return True)
        success, msg = recognizer.verify_face(dummy_frame, "John Doe")
        self.assertTrue(success)
        self.assertIn("Verification Disabled", msg)

    def test_surveillance_system(self):
        """Verify SurveillanceSystem checks lock hours and runs person detection."""
        from security import SurveillanceSystem
        system = SurveillanceSystem()
        
        # Check lock hours method returns boolean
        is_locked = system.is_lock_hours()
        self.assertIsInstance(is_locked, bool)
        
        # Test frame processing on mock frame (should not crash)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        is_intrusion, processed_frame = system.process_frame(dummy_frame)
        self.assertIsInstance(is_intrusion, bool)
        self.assertEqual(processed_frame.shape, dummy_frame.shape)

    @patch('cv2.VideoCapture')
    def test_threaded_camera_stream(self, mock_vc):
        """Verify threaded CameraStream starts and releases using mocked cv2.VideoCapture."""
        # Set up mock returns
        mock_instance = MagicMock()
        mock_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_vc.return_value = mock_instance
        
        from utils import CameraStream
        stream = CameraStream(0)
        self.assertFalse(stream.started)
        
        stream.start()
        self.assertTrue(stream.started)
        
        grabbed, frame = stream.read()
        self.assertTrue(grabbed)
        self.assertIsNotNone(frame)
        
        stream.release()
        self.assertFalse(stream.started)

if __name__ == "__main__":
    unittest.main()
