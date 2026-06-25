import os
import sys
import unittest
import numpy as np
from datetime import datetime
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
            import utils
            import main
            import dashboard
            import gps_server
            print("[TEST] All modules imported successfully!")
        except Exception as e:
            self.fail(f"Module import failed: {e}")

    def test_attendance_logging_and_cooldown(self):
        """Verify attendance logs correctly, cooldown duplicates works, and Day column is logged."""
        from attendance import mark_attendance
        
        test_loc = "28.6139, 77.2090"
        test_evidence = "data/evidence/test_snap.jpg"
        expected_day = datetime.now().strftime("%A")
        
        # First log - should succeed
        success, msg = mark_attendance("John Doe", "IN", test_loc, test_evidence)
        self.assertTrue(success)
        self.assertIn("Successfully logged", msg)
        
        # Verify CSV file exists and has content
        self.assertTrue(os.path.exists(self.test_csv_path))
        with open(self.test_csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)  # Header + 1 record
            # Headers: Name, Status, Date, Day, Time, Location, Evidence_Path, Timestamp
            self.assertIn("John Doe,IN", lines[1])
            self.assertIn(expected_day, lines[1])
            self.assertIn(test_loc, lines[1])
            self.assertIn(test_evidence, lines[1])

        # Verify Excel file exists
        self.assertTrue(os.path.exists(self.test_xlsx_path))
        
        # Second log (immediate duplicate) - should fail due to cooldown
        success2, msg2 = mark_attendance("John Doe", "IN", test_loc, test_evidence)
        self.assertFalse(success2)
        self.assertIn("Already logged", msg2)
        
        # Verify no duplicate row was added to CSV
        with open(self.test_csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 2)
            
        # Different student or status should work
        success3, msg3 = mark_attendance("Jane Smith", "IN", test_loc, test_evidence)
        self.assertTrue(success3)
        
        success4, msg4 = mark_attendance("John Doe", "OUT", test_loc, test_evidence)
        self.assertTrue(success4)
        
        # Test Urgent Exit and Return Duration Calculation
        success_exit, msg_exit = mark_attendance("John Doe", "URGENT_EXIT", test_loc, test_evidence)
        self.assertTrue(success_exit)
        
        # Immediate return should work and log duration in seconds
        success_ret, msg_ret = mark_attendance("John Doe", "URGENT_RETURN", test_loc, test_evidence)
        self.assertTrue(success_ret)
        
        # Verify Duration column exists in last line and is populated
        with open(self.test_csv_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Headers: Name, Status, Date, Day, Time, Location, Evidence_Path, Timestamp, Duration
            self.assertIn("John Doe,URGENT_RETURN", lines[-1])
            self.assertTrue(any(term in lines[-1] for term in ["secs", "mins"]))

    def test_surveillance_system(self):
        """Verify SurveillanceSystem checks lock hours and runs person detection."""
        from security import SurveillanceSystem
        system = SurveillanceSystem()
        
        # Check lock hours method returns boolean
        is_locked = system.is_lock_hours()
        self.assertIsInstance(is_locked, bool)
        
        # Test frame processing on mock frame (should not detect person)
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        person_detected, person_bbox = system.detect_person(dummy_frame)
        self.assertFalse(person_detected)
        self.assertIsNone(person_bbox)

    def test_gesture_detector_init(self):
        """Verify detector initializes with MediaPipe Hands."""
        from detect_gesture import GestureDetector
        
        try:
            detector = GestureDetector()
            self.assertIsNotNone(detector.hands)
            print("[TEST] GestureDetector MediaPipe hands initialized successfully!")
            
            # Run inference on a blank dummy image
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            detections = detector.detect(dummy_frame)
            self.assertIsInstance(detections, list)
            print(f"[TEST] Run mock detection. Number of detections found: {len(detections)}")
        except Exception as e:
            self.fail(f"Gesture detector test failed: {e}")

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
