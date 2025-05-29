#!/usr/bin/env python3
import cv2
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
from io import BytesIO
import numpy as np

# Try to import Pi Camera libraries
try:
    from picamera2 import Picamera2  # For newer Pi OS (Bullseye+)
    USE_PICAMERA2 = True
    print("Using PiCamera2 library")
except ImportError:
    try:
        from picamera import PiCamera  # For older Pi OS
        USE_PICAMERA2 = False
        USE_PICAMERA = True
        print("Using PiCamera library")
    except ImportError:
        USE_PICAMERA2 = False
        USE_PICAMERA = False
        print("Using OpenCV (USB camera mode)")

# --- Configuration ---
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15  # Lower FPS for Pi 3 performance
HTTP_PORT = 8080
JPEG_QUALITY = 80  # Balance between quality and bandwidth

class CameraStreamer:
    def __init__(self):
        # Latest frame storage (thread-safe)
        self.frame = None
        self.frame_lock = threading.Lock()
        self.running = True
        
        # Initialize camera based on available library
        if USE_PICAMERA2:
            self._init_picamera2()
        elif USE_PICAMERA:
            self._init_picamera()
        else:
            self._init_opencv()
        
        # Start camera capture thread
        self.capture_thread = threading.Thread(target=self._capture_frames)
        self.capture_thread.daemon = True
        self.capture_thread.start()
    
    def _init_picamera2(self):
        """Initialize using PiCamera2 (recommended for newer Pi OS)"""
        self.camera_type = "picamera2"
        self.picam2 = Picamera2()
        
        # Configure camera
        config = self.picam2.create_video_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"},
            controls={"FrameRate": CAMERA_FPS}
        )
        self.picam2.configure(config)
        self.picam2.start()
        
        print(f"PiCamera2 initialized: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
    
    def _init_picamera(self):
        """Initialize using legacy PiCamera"""
        self.camera_type = "picamera"
        self.picamera = PiCamera()
        self.picamera.resolution = (CAMERA_WIDTH, CAMERA_HEIGHT)
        self.picamera.framerate = CAMERA_FPS
        
        # Warm up camera
        time.sleep(2)
        print(f"PiCamera initialized: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
    
    def _init_opencv(self):
        """Fallback to OpenCV (for USB cameras or troubleshooting)"""
        self.camera_type = "opencv"
        
        # Try different camera indices
        for camera_index in [0, 1, 2]:
            self.cap = cv2.VideoCapture(camera_index)
            if self.cap.isOpened():
                break
        else:
            raise Exception("Cannot open any camera! Check connection and enable via raspi-config")
        
        # Configure camera settings
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        
        print(f"OpenCV Camera initialized: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
    
    def _capture_frames(self):
        """Continuous frame capture in separate thread"""
        while self.running:
            try:
                if self.camera_type == "picamera2":
                    # PiCamera2 capture
                    frame = self.picam2.capture_array()
                    # Convert RGB to BGR for OpenCV compatibility
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                elif self.camera_type == "picamera":
                    # Legacy PiCamera capture
                    stream = BytesIO()
                    self.picamera.capture(stream, format='jpeg')
                    stream.seek(0)
                    
                    # Decode JPEG to numpy array
                    data = np.frombuffer(stream.getvalue(), dtype=np.uint8)
                    frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
                    
                elif self.camera_type == "opencv":
                    # OpenCV capture
                    ret, frame = self.cap.read()
                    if not ret:
                        print("Failed to capture frame from OpenCV")
                        time.sleep(0.1)
                        continue
                
                # Store frame thread-safely
                if frame is not None:
                    with self.frame_lock:
                        self.frame = frame
                else:
                    print("Received empty frame")
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"Capture error: {e}")
                time.sleep(0.1)
    
    def get_latest_frame(self):
        """Get the most recent frame (thread-safe)"""
        with self.frame_lock:
            return self.frame.copy() if self.frame is not None else None
    
    def stop(self):
        """Clean shutdown"""
        self.running = True
        
        if self.camera_type == "picamera2":
            self.picam2.stop()
        elif self.camera_type == "picamera":
            self.picamera.close()
        elif self.camera_type == "opencv":
            self.cap.release()
            
        print("Camera stopped")

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
                print(f"Client disconnected: {e}")
        
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
        
        print("Camera streaming started!")
        print(f"Stream URL: http://{pi_ip}:{HTTP_PORT}/stream")
        print(f"Web view: http://{pi_ip}:{HTTP_PORT}/")
        print("Press Ctrl+C to stop")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        camera.stop()
        server.shutdown()
        print("Stopped successfully")
    except Exception as e:
        print(f"Error: {e}")
        if 'camera' in locals():
            camera.stop()