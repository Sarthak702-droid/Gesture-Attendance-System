import csv
import os
from datetime import datetime

CSV_PATH = os.path.join("data", "attendance.csv")
COOLDOWN_SECONDS = 300  # 5 minutes cooldown to prevent double logging

def mark_attendance(name, status):
    """
    Appends a new attendance record to the CSV file.
    Prevents duplicate entries within the cooldown window (5 minutes).
    """
    # Ensure data directory exists
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    current_ts = int(now.timestamp())
    
    file_exists = os.path.exists(CSV_PATH)
    
    # Check for duplicate entry within cooldown period
    if file_exists:
        try:
            with open(CSV_PATH, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
                
                # Check rows from most recent to oldest
                for row in reversed(rows[1:]):  # Skip header row
                    if len(row) >= 5:
                        row_name, row_status, _, _, row_ts_str = row[0], row[1], row[2], row[3], row[4]
                        try:
                            row_ts = int(row_ts_str)
                            if row_name.strip().lower() == name.strip().lower() and row_status.strip().upper() == status.strip().upper():
                                time_diff = current_ts - row_ts
                                if time_diff < COOLDOWN_SECONDS:
                                    remaining = COOLDOWN_SECONDS - time_diff
                                    rem_min = remaining // 60
                                    rem_sec = remaining % 60
                                    return False, f"Already logged {status} for {name}. Cooldown: {rem_min}m {rem_sec}s remaining."
                        except ValueError:
                            continue
        except Exception as e:
            print(f"[WARNING] Could not read attendance CSV for duplicate checking: {e}")
            
    # Append the new attendance record
    try:
        write_header = not file_exists or os.stat(CSV_PATH).st_size == 0
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["Name", "Status", "Date", "Time", "Timestamp"])
            writer.writerow([name.strip(), status.strip().upper(), date_str, time_str, current_ts])
        return True, f"Successfully logged {status} for {name}!"
    except Exception as e:
        return False, f"Error writing to attendance file: {e}"
