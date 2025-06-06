import os
import sys
import time
import json
import paho.mqtt.client as mqtt
from ultralytics import YOLO
import cv2
import requests
import numpy as np
from threading import Thread
import queue
from norfair import Detection, Tracker

# Add the root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from config import Config

# --- Configuration ---
PI_CAMERA_URL = Config.PI_CAMERA_URL
MQTT_BROKER_IP = Config.MQTT_BROKER_IP
MQTT_PORT = Config.MQTT_PORT
MQTT_TOPIC_TRAFFIC = Config.MQTT_TOPIC_TRAFFIC
SEND_INTERVAL = 2
CONFIDENCE_THRESHOLD = 0.3
CAMERA_ID = "cam_01"
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720

# --- MQTT Client ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
    else:
        print(f"MQTT connection failed with code {rc}")

client = mqtt.Client()
client.on_connect = on_connect
client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)
client.loop_start()

# --- YOLO Model ---
print("Loading YOLOv8 model...")
model = YOLO('yolov8n.pt')
print("YOLOv8 model loaded successfully")

# --- Tracker ---
def euclidean_distance(detection, tracked_object):
    return np.linalg.norm(detection.points[0] - tracked_object.estimate[0])

tracker = Tracker(distance_function=euclidean_distance, distance_threshold=50)

# --- Tracking memory ---
sent_vehicle_ids = set()

class StreamDecoder:
    """Decode MJPEG stream from Pi camera"""
    def __init__(self, url):
        self.url = url
        self.frame_queue = queue.Queue(maxsize=2)
        self.running = True
        self.thread = Thread(target=self._decode_stream)
        self.thread.daemon = True
        self.thread.start()
    
    def _decode_stream(self):
        while self.running:
            try:
                response = requests.get(self.url, stream=True, timeout=10)
                if response.status_code != 200:
                    print(f"Response error: HTTP {response.status_code}")
                    time.sleep(2)
                    continue
                
                print("Connected to Pi camera stream")
                
                buffer = b''
                for chunk in response.iter_content(chunk_size=1024):
                    if not self.running:
                        break
                    
                    buffer += chunk
                    
                    while True:
                        start = buffer.find(b'\xff\xd8')
                        end = buffer.find(b'\xff\xd9')
                        
                        if start == -1 or end == -1 or end <= start:
                            break
                        
                        jpeg_data = buffer[start:end+2]
                        buffer = buffer[end+2:]
                        
                        frame = cv2.imdecode(np.frombuffer(jpeg_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            try:
                                self.frame_queue.put_nowait(frame)
                            except queue.Full:
                                try:
                                    self.frame_queue.get_nowait()
                                    self.frame_queue.put_nowait(frame)
                                except queue.Empty:
                                    pass
                
            except requests.exceptions.RequestException as e:
                print(f"Stream connection error: {e}")
                time.sleep(2)
            except Exception as e:
                print(f"Decode error: {e}")
                time.sleep(1)
    
    def get_frame(self):
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def stop(self):
        self.running = False

def yolo_to_norfair_detections(yolo_results):
    detections = []
    for result in yolo_results:
        boxes = result.boxes
        if boxes is not None:
            for box in boxes.data:
                confidence = float(box[4])
                class_id = int(box[5])
                if confidence < CONFIDENCE_THRESHOLD:
                    continue
                label = model.names[class_id]
                if label in ['car', 'bus', 'truck', 'motorcycle', 'bicycle']:
                    x1, y1, x2, y2 = box[:4].cpu().numpy()
                    centroid = np.array([[ (x1 + x2) / 2, (y1 + y2) / 2]])
                    scores = np.array([confidence])
                    detections.append(Detection(points=centroid, scores=scores, label=label))
    return detections

def detect_vehicles(frame):
    results = model(frame, verbose=False)
    norfair_detections = yolo_to_norfair_detections(results)
    tracked_objects = tracker.update(detections=norfair_detections)
    
    counts = {}
    new_vehicles = []
    for tracked_obj in tracked_objects:
        vehicle_id = tracked_obj.id
        label = tracked_obj.label
        if vehicle_id not in sent_vehicle_ids:
            counts[label] = counts.get(label, 0) + 1
            new_vehicles.append((vehicle_id, label))
    
    return counts, results, tracked_objects, new_vehicles

def send_mqtt_data(counts, new_vehicles):
    if not counts:
        return
    
    message = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime()),
        "camera_id": CAMERA_ID,
        "vehicles": counts
    }
    
    try:
        client.publish(MQTT_TOPIC_TRAFFIC, json.dumps(message))
        print("Published:", message)
        for vehicle_id, _ in new_vehicles:
            sent_vehicle_ids.add(vehicle_id)
    except Exception as e:
        print(f"MQTT publish error: {e}")

def main():
    print(f"Connecting to Pi camera stream: {PI_CAMERA_URL}")
    
    stream_decoder = StreamDecoder(PI_CAMERA_URL)
    
    last_sent_time = time.time()
    frame_count = 0
    fps_time = time.time()
    
    try:
        while True:
            frame = stream_decoder.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            counts, results, tracked_objects, new_vehicles = detect_vehicles(frame)
            
            current_time = time.time()
            if current_time - last_sent_time >= SEND_INTERVAL:
                send_mqtt_data(counts, new_vehicles)
                last_sent_time = current_time
            
            if results:
                annotated_frame = results[0].plot()
                for tracked_obj in tracked_objects:
                    centroid = tracked_obj.estimate[0]
                    cv2.putText(annotated_frame, f"ID: {tracked_obj.id}", (int(centroid[0]), int(centroid[1])),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                annotated_frame = cv2.resize(annotated_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
                
                info_text = f"Vehicles: {counts} | FPS: {frame_count/(current_time-fps_time):.1f}"
                cv2.putText(annotated_frame, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                cv2.imshow('Traffic Monitoring - Stream', annotated_frame)
            
            frame_count += 1
            if current_time - fps_time >= 1.0:
                fps = frame_count / (current_time - fps_time)
                print(f"Processing at {fps:.1f} FPS | Vehicles: {counts}")
                frame_count = 0
                fps_time = current_time
            
            if cv2.waitKey(1) == 27:
                break
                
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        stream_decoder.stop()
        cv2.destroyAllWindows()
        client.loop_stop()
        client.disconnect()
        print("Stopped successfully")

if __name__ == "__main__":
    print("Starting YOLO Traffic Detection from Pi Stream")
    print(f"Stream URL: {PI_CAMERA_URL}")
    print(f"MQTT Broker: {MQTT_BROKER_IP}:{MQTT_PORT}")
    print(f"MQTT Topic: {MQTT_TOPIC_TRAFFIC}")
    print("Press ESC to quit\n")
    
    main()