#!/usr/bin/env python3
"""
Raspberry Pi Camera Streamer
Captures video from Pi Camera V2 and streams via MJPEG over HTTP

Setup Instructions:
1. Enable camera: sudo raspi-config → Interface Options → Camera → Enable
2. Reboot: sudo reboot
3. Install dependencies: pip3 install opencv-python
4. Run: python3 camera.py

Hardware: Raspberry Pi 3 + Pi Camera V2
Streaming: MJPEG over HTTP (low latency, Pi 3 compatible)
"""

import cv2
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
from io import BytesIO

# --- Configuration ---
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15  # Lower FPS for Pi 3 performance
HTTP_PORT = 8080
JPEG_QUALITY = 80  # Balance between quality and bandwidth

class CameraStreamer:
    def __init__(self):
        # Initialize Pi Camera via OpenCV
        # Note: On Pi, cv2.VideoCapture(0) uses Pi camera if enabled
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            raise Exception("❌ Cannot open Pi Camera! Check connection and enable via raspi-config")
        
        # Configure camera settings
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        
        print(f"✅ Pi Camera initialized: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
        
        # Latest frame storage (thread-safe)
        self.frame = None
        self.frame_lock = threading.Lock()
        self.running = True
        
        # Start camera capture thread
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def _capture_frames(self):
        """Continuous frame capture in separate thread"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.frame_lock:
                    self.frame = frame
            else:
                print("⚠️ Failed to capture frame")
                time.sleep(0.1)
    
    def get_latest_frame(self):
        """Get the most recent frame (thread-safe)"""
        with self.frame_lock:
            return self.frame.copy() if self.frame is not None else None
    
    def stop(self):
        """Clean shutdown"""
        self.running = False
        self.cap.release()
        print("📹 Camera stopped")

class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/stream':
            # MJPEG stream endpoint
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            try:
                while True:
                    frame = camera.get_latest_frame()
                    if frame is not None:
                        # Encode frame as JPEG
                        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                        _, buffer = cv2.imencode('.jpg', frame, encode_param)
                        
                        # Send MJPEG frame
                        self.wfile.write(b'--jpgboundary\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', len(buffer))
                        self.end_headers()
                        self.wfile.write(buffer)
                        self.wfile.write(b'\r\n')
                    
                    time.sleep(1.0 / CAMERA_FPS)  # Control stream rate
                    
            except Exception as e:
                print(f"⚠️ Client disconnected: {e}")
        
        elif self.path == '/':
            # Simple web page to view stream
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            html = f"""
            <html>
            <head><title>Pi Camera Stream</title></head>
            <body>
                <h1>Raspberry Pi Camera Stream</h1>
                <img src="/stream" width="{CAMERA_WIDTH}" height="{CAMERA_HEIGHT}">
                <p>Stream URL: http://{{your_pi_ip}}:{HTTP_PORT}/stream</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_error(404)
    
    def log_message(self, format, *args):
        # Suppress HTTP logs for cleaner output
        pass

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    pass

def get_pi_ip():
    """Get Pi's local IP address"""
    import socket
    try:
        # Connect to external address to find local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

if __name__ == "__main__":
    try:
        # Initialize camera
        camera = CameraStreamer()
        
        # Start HTTP server
        server = ThreadedHTTPServer(('', HTTP_PORT), StreamingHandler)
        pi_ip = get_pi_ip()
        
        print("🚀 Camera streaming started!")
        print(f"📡 Stream URL: http://{pi_ip}:{HTTP_PORT}/stream")
        print(f"🌐 Web view: http://{pi_ip}:{HTTP_PORT}/")
        print("Press Ctrl+C to stop")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        camera.stop()
        server.shutdown()
        print("✅ Stopped successfully")
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'camera' in locals():
            camera.stop()