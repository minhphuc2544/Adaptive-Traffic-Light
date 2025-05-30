import time
import json
import paho.mqtt.client as mqtt
from ultralytics import YOLO
import cv2
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

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Run YOLO detection
    results = model(frame)
    counts = {}  

    # Đếm phương tiện trong frame hiện tại
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

    # Gửi mỗi 2 giây nếu có dữ liệu
    current_time = time.time()
    if current_time - last_sent_time >= SEND_INTERVAL and counts:
        message = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
            "camera_id": CAMERA_ID,
            "vehicles": counts
        }
        client.publish(MQTT_TOPIC_TRAFFIC, json.dumps(message))
        print("📤 Published:", message)
        last_sent_time = current_time

    # Hiển thị
    annotated_frame = results[0].plot()
    annotated_frame = cv2.resize(annotated_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
    cv2.imshow('Traffic Monitoring', annotated_frame)

    if cv2.waitKey(1) == 27:
        break

    time.sleep(0.1)

cap.release()
cv2.destroyAllWindows()
