import http.server
import socketserver
import webbrowser
import threading
import time
import os

PORT = 8000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

def open_browser():
    # Wait a second for the server to spin up
    time.sleep(1.0)
    print("[INFO] Opening dashboard in your default browser...")
    webbrowser.open(f"http://localhost:{PORT}/index.html")

def run_server():
    # Change working directory to the project root
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(root_dir)
    
    handler = CORSHTTPRequestHandler
    
    # Allow port reuse to avoid 'Address already in use' errors
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print("==================================================================")
        print(f"   ◐ Pulse Dashboard server running at http://localhost:{PORT}")
        print("   Press Ctrl+C to stop the dashboard server.")
        print("==================================================================")
        
        # Start browser thread
        t = threading.Thread(target=open_browser, daemon=True)
        t.start()
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Dashboard server stopped.")
            httpd.shutdown()

if __name__ == "__main__":
    run_server()

def parse_duration_to_hours(duration_str):
    if not isinstance(duration_str, str) or not duration_str or duration_str == "N/A":
        return 0.0
    try:
        parts = duration_str.strip().split()
        if len(parts) >= 2:
            val = float(parts[0])
            unit = parts[1].lower()
            if "sec" in unit:
                return val / 3600.0
            elif "min" in unit:
                return val / 60.0
            elif "hour" in unit:
                return val
    except Exception:
        pass
    return 0.0

