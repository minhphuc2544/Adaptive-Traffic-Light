#!/usr/bin/env python3
"""
YOLO Traffic Detection from Pi Camera Stream
Receives MJPEG stream from Raspberry Pi and performs vehicle detection

Usage:
1. Start camera.py on Raspberry Pi first
2. Update PI_CAMERA_URL with your Pi's IP address
3. Run: python3 read_streaming_model.py

Dependencies: pip install ultralytics opencv-python paho-mqtt requests
"""

import time
import json
import paho.mqtt.client as mqtt
from ultralytics import YOLO
import cv2
import requests
import numpy as np
from threading import Thread
import queue

# --- Configuration ---
PI_CAMERA_URL = 'http://192.168.79.249:8080/stream'  # Update with your Pi's IP
MQTT_BROKER = '192.168.79.8'
MQTT_PORT = 1883
MQTT_TOPIC = 'iot/traffic'
SEND_INTERVAL = 2
CONFIDENCE_THRESHOLD = 0.3
CAMERA_ID = "cam_01"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 600

# --- MQTT Client ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker")
    else:
        print(f"❌ MQTT connection failed with code {rc}")

client = mqtt.Client()
client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# --- YOLO Model ---
print("🤖 Loading YOLOv8 model...")
model = YOLO('yolov8n.pt')
print("✅ YOLOv8 model loaded successfully")

class StreamDecoder:
    """Decode MJPEG stream from Pi camera"""
    def __init__(self, url):
        self.url = url
        self.frame_queue = queue.Queue(maxsize=2)  # Small buffer
        self.running = True
        self.thread = Thread(target=self._decode_stream)
        self.thread.daemon = True
        self.thread.start()
    
    def _decode_stream(self):
        """Continuously decode MJPEG stream"""
        while self.running:
            try:
                # Connect to stream
                response = requests.get(self.url, stream=True, timeout=10)
                if response.status_code != 200:
                    print(f"❌ Stream error: HTTP {response.status_code}")
                    time.sleep(2)
                    continue
                
                print("🔗 Connected to Pi camera stream")
                
                # Parse MJPEG stream
                buffer = b''
                for chunk in response.iter_content(chunk_size=1024):
                    if not self.running:
                        break
                    
                    buffer += chunk
                    
                    # Look for JPEG boundaries
                    while True:
                        start = buffer.find(b'\xff\xd8')  # JPEG start
                        end = buffer.find(b'\xff\xd9')    # JPEG end
                        
                        if start == -1 or end == -1 or end <= start:
                            break
                        
                        # Extract JPEG frame
                        jpeg_data = buffer[start:end+2]
                        buffer = buffer[end+2:]
                        
                        # Decode image
                        frame = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            # Add to queue (non-blocking)
                            try:
                                self.frame_queue.put_nowait(frame)
                            except queue.Full:
                                # Remove old frame if queue is full
                                try:
                                    self.frame_queue.get_nowait()
                                    self.frame_queue.put_nowait(frame)
                                except queue.Empty:
                                    pass
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Stream connection error: {e}")
                time.sleep(2)
            except Exception as e:
                print(f"⚠️ Decode error: {e}")
                time.sleep(1)
    
    def get_frame(self):
        """Get latest frame (non-blocking)"""
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop(self):
        self.running = False

def detect_vehicles(frame):
    """Run YOLO detection on frame and return vehicle counts"""
    results = model(frame, verbose=False)
    counts = {}
    
    for result in results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes.data:
                confidence = box[4]
                class_id = int(box[5])
                
                if confidence < CONFIDENCE_THRESHOLD:
                    continue
                
                label = model.names[class_id]
                if label in ['car', 'bus', 'truck', 'motorcycle', 'bicycle']:
                    counts[label] = counts.get(label, 0) + 1
    
    return counts, results

def send_mqtt_data(counts):
    """Send vehicle counts to MQTT broker"""
    if not counts:
        return
    
    message = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()),
        "camera_id": CAMERA_ID,
        "vehicles": counts
    }
    
    try:
        client.publish(MQTT_TOPIC, json.dumps(message))
        print("📤 Published:", message)
    except Exception as e:
        print(f"⚠️ MQTT publish error: {e}")

def main():
    print(f"🔍 Connecting to Pi camera stream: {PI_CAMERA_URL}")
    
    # Initialize stream decoder
    stream_decoder = StreamDecoder(PI_CAMERA_URL)
    
    # Detection loop
    last_sent_time = time.time()
    frame_count = 0
    fps_time = time.time()
    
    try:
        while True:
            # Get latest frame
            frame = stream_decoder.get_frame()
            if frame is None:
                time.sleep(0.01)  # Small delay if no frame available
                continue
            
            # Run vehicle detection
            counts, results = detect_vehicles(frame)
            
            # Send MQTT data every 2 seconds
            current_time = time.time()
            if current_time - last_sent_time >= SEND_INTERVAL:
                send_mqtt_data(counts)
                last_sent_time = current_time
            
            # Display annotated frame
            if results:
                annotated_frame = results[0].plot()
                annotated_frame = cv2.resize(annotated_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
                
                # Add info overlay
                info_text = f"Vehicles: {counts} | FPS: {frame_count/(current_time-fps_time):.1f}"
                cv2.putText(annotated_frame, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('Traffic Monitoring - Stream', annotated_frame)
            
            # Calculate FPS
            frame_count += 1
            if current_time - fps_time >= 1.0:
                fps = frame_count / (current_time - fps_time)
                print(f"🎥 Processing at {fps:.1f} FPS | Vehicles: {counts}")
                frame_count = 0
                fps_time = current_time
            
            # Exit on ESC key
            if cv2.waitKey(1) == 27:
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    finally:
        stream_decoder.stop()
        cv2.destroyAllWindows()
        client.loop_stop()
        client.disconnect()
        print("✅ Stopped successfully")

if __name__ == "__main__":
    print("🚀 Starting YOLO Traffic Detection from Pi Stream")
    print(f"📡 Stream URL: {PI_CAMERA_URL}")
    print(f"📊 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"📝 MQTT Topic: {MQTT_TOPIC}")
    print("Press ESC to quit\n")
    
    main()