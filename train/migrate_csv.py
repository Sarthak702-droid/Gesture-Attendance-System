import csv
import os
import sys
from datetime import datetime

# Add src/ to python path so we can import sync_to_excel
sys.path.append(os.path.abspath("src"))
from attendance import sync_to_excel

def main():
    csv_path = os.path.join("data", "attendance.csv")
    
    if not os.path.exists(csv_path):
        print("[INFO] No attendance CSV file found on disk. Migration not required.")
        return
        
    print("[INFO] Migrating attendance CSV records...")
    migrated_rows = []
    
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("[INFO] CSV file is empty.")
            return
            
        for row_idx, row in enumerate(reader, start=2):
            if not row:
                continue
                
            # Mode 1: Old 7-column schema
            if len(row) == 7:
                name, status, date, time, location, ev_path, ts = row
                try:
                    dt = datetime.strptime(date.strip(), "%Y-%m-%d")
                    day = dt.strftime("%A")
                except Exception:
                    day = "Monday"
                new_row = [name.strip(), status.strip().upper(), date.strip(), day, time.strip(), location.strip(), ev_path.strip(), ts.strip(), ""]
            # Mode 2: Older 8-column schema
            elif len(row) == 8:
                name, status, date, day, time, location, ev_path, ts = row
                new_row = [name.strip(), status.strip().upper(), date.strip(), day.strip(), time.strip(), location.strip(), ev_path.strip(), ts.strip(), ""]
            # Mode 3: Latest 9-column schema
            elif len(row) == 9:
                new_row = [item.strip() for item in row]
            # Fallback
            else:
                new_row = row[:9] + [""] * (9 - len(row))
                new_row = [item.strip() for item in new_row]
                
            migrated_rows.append(new_row)
            
    # Write back clean rows
    new_header = ["Name", "Status", "Date", "Day", "Time", "Location", "Evidence_Path", "Timestamp", "Duration"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(new_header)
        writer.writerows(migrated_rows)
        
    print(f"[SUCCESS] Successfully migrated {len(migrated_rows)} records in attendance.csv.")
    
    # Sync to Excel
    print("[INFO] Rebuilding Excel sync file...")
    sync_to_excel()
    print("[SUCCESS] Excel synced successfully with all 9 columns.")

if __name__ == "__main__":
    main()
