from http.server import BaseHTTPRequestHandler, HTTPServer
import socket
import json
import urllib.parse
import threading
import time

# Global variable to hold GPS data
GPS_DATA = {
    "latitude": None,
    "longitude": None,
    "timestamp": None
}

def get_local_ip():
    """Retrieves the local IP address of the machine in the network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class GPSServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging console spam
        return

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            # Geolocation sharing HTML page
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>GPS Link</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                        background: #0f172a;
                        color: #f8fafc;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        margin: 0;
                        padding: 20px;
                        text-align: center;
                    }
                    .card {
                        background: #1e293b;
                        padding: 30px;
                        border-radius: 12px;
                        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
                        max-width: 400px;
                        width: 100%;
                        border: 1px solid #334155;
                    }
                    h1 { color: #38bdf8; margin-top: 0; font-size: 24px; }
                    p { color: #94a3b8; line-height: 1.5; font-size: 15px; }
                    .btn {
                        background: #0ea5e9;
                        color: white;
                        border: none;
                        padding: 14px 24px;
                        font-size: 16px;
                        font-weight: bold;
                        border-radius: 8px;
                        cursor: pointer;
                        transition: background 0.2s;
                        margin-top: 20px;
                        width: 100%;
                    }
                    .btn:hover { background: #0284c7; }
                    .status {
                        margin-top: 20px;
                        font-weight: 600;
                        color: #f43f5e;
                        font-size: 14px;
                    }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Employee Mobile GPS Link</h1>
                    <p>Please share your phone's GPS location with the office attendance system.</p>
                    <button class="btn" onclick="shareLocation()">📍 Share Location</button>
                    <div id="status" class="status">Click button to fetch GPS...</div>
                </div>

                <script>
                    function shareLocation() {
                        const statusDiv = document.getElementById("status");
                        statusDiv.style.color = "#94a3b8";
                        statusDiv.innerHTML = "Fetching GPS coordinates from phone...";
                        
                        if (!navigator.geolocation) {
                            statusDiv.style.color = "#ef4444";
                            statusDiv.innerHTML = "❌ Geolocation not supported by this browser.";
                            return;
                        }

                        navigator.geolocation.getCurrentPosition(
                            (position) => {
                                const lat = position.coords.latitude;
                                const lon = position.coords.longitude;
                                
                                statusDiv.innerHTML = "Sending coordinates to system...";
                                
                                // Send coordinates back to python
                                fetch('/submit', {
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/x-www-form-urlencoded',
                                    },
                                    body: `lat=${lat}&lon=${lon}`
                                })
                                .then(response => response.text())
                                .then(data => {
                                    statusDiv.style.color = "#10b981";
                                    statusDiv.innerHTML = "✅ GPS Sent successfully!<br>Latitude: " + lat.toFixed(5) + "<br>Longitude: " + lon.toFixed(5);
                                })
                                .catch(err => {
                                    statusDiv.style.color = "#ef4444";
                                    statusDiv.innerHTML = "❌ Error submitting GPS: " + err;
                                });
                            },
                            (error) => {
                                statusDiv.style.color = "#ef4444";
                                switch(error.code) {
                                    case error.PERMISSION_DENIED:
                                        statusDiv.innerHTML = "❌ Permission Denied. Please enable GPS location permission.";
                                        break;
                                    case error.POSITION_UNAVAILABLE:
                                        statusDiv.innerHTML = "❌ Location unavailable.";
                                        break;
                                    case error.TIMEOUT:
                                        statusDiv.innerHTML = "❌ Request timed out.";
                                        break;
                                    default:
                                        statusDiv.innerHTML = "❌ Location error occurred.";
                                }
                            },
                            { enableHighAccuracy: true, timeout: 10000 }
                        );
                    }
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_POST(self):
        if self.path == "/submit":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            params = urllib.parse.parse_qs(post_data)
            
            global GPS_DATA
            if 'lat' in params and 'lon' in params:
                GPS_DATA["latitude"] = float(params['lat'][0])
                GPS_DATA["longitude"] = float(params['lon'][0])
                GPS_DATA["timestamp"] = time.time()
                
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK")
            else:
                self.send_response(400)
                self.end_headers()

def start_gps_server():
    """Starts the local GPS HTTP server on port 5000 in a daemon background thread."""
    try:
        server = HTTPServer(('', 5000), GPSServerHandler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        print(f"[GPS_SERVER] Running on http://{get_local_ip()}:5000")
        return server
    except Exception as e:
        print(f"[WARNING] Could not start GPS server: {e}")
        return None
