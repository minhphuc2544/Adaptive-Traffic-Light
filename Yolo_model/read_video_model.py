import os
import sys
import time
import json
import paho.mqtt.client as mqtt
from ultralytics import YOLO
import cv2
import numpy as np
from norfair import Detection, Tracker

# Add the root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from config import Config

# --- Config ---
MQTT_BROKER_IP = Config.MQTT_BROKER_IP
MQTT_PORT = Config.MQTT_PORT
MQTT_TOPIC_TRAFFIC = Config.MQTT_TOPIC_TRAFFIC
SEND_INTERVAL = 2
CONFIDENCE_THRESHOLD = 0.3
VIDEO_SOURCE = r'Yolo_model/video.mp4'
CAMERA_ID = "cam_01"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 600

# --- MQTT ---
client = mqtt.Client()
client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)

# --- YOLO Model ---
model = YOLO('yolov8n.pt')

# --- Tracker ---
def euclidean_distance(detection, tracked_object):
    return np.linalg.norm(detection.points[0] - tracked_object.estimate[0])

tracker = Tracker(distance_function=euclidean_distance, distance_threshold=50)

# --- Tracking memory ---
sent_vehicle_ids = set()

# --- Video ---
cap = cv2.VideoCapture(VIDEO_SOURCE)
if not cap.isOpened():
    print("Unable to open video!")
    exit()
else:
    print("Open video successfully!")

# --- Counting memory ---
counts = {}
last_sent_time = time.time()

def yolo_to_norfair_detections(yolo_results):
    """Convert YOLO detections to Norfair format"""
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

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO detection
    results = model(frame, verbose=False)
    
    # Convert YOLO detections to Norfair
    norfair_detections = yolo_to_norfair_detections(results)
    
    # Update tracker
    tracked_objects = tracker.update(detections=norfair_detections)
    
    # Count vehicles and prepare for MQTT
    counts = {}
    new_vehicles = []
    for tracked_obj in tracked_objects:
        vehicle_id = tracked_obj.id
        label = tracked_obj.label
        if vehicle_id not in sent_vehicle_ids:
            counts[label] = counts.get(label, 0) + 1
            new_vehicles.append((vehicle_id, label))
    
    # Send MQTT data every 2 seconds if there are new vehicles
    current_time = time.time()
    if current_time - last_sent_time >= SEND_INTERVAL and counts:
        message = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
            "camera_id": CAMERA_ID,
            "vehicles": counts
        }
        client.publish(MQTT_TOPIC_TRAFFIC, json.dumps(message))
        print("Published:", message)
        # Mark vehicles as sent
        for vehicle_id, _ in new_vehicles:
            sent_vehicle_ids.add(vehicle_id)
        last_sent_time = current_time
    
    # Display annotated frame
    annotated_frame = results[0].plot()
    for tracked_obj in tracked_objects:
        centroid = tracked_obj.estimate[0]
        cv2.putText(annotated_frame, f"ID: {tracked_obj.id}", (int(centroid[0]), int(centroid[1])),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    annotated_frame = cv2.resize(annotated_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    cv2.imshow('Traffic Monitoring', annotated_frame)
    
    if cv2.waitKey(1) == 27:
        break
    
    time.sleep(0.1)

cap.release()
cv2.destroyAllWindows()
client.disconnect()