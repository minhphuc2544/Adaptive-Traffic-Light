import time
import json
import cv2
import paho.mqtt.client as mqtt
from ultralytics import YOLO

# --- Config ---
MQTT_BROKER = '192.168.79.8'
MQTT_PORT = 1883
MQTT_TOPIC = 'iot/traffic'
CONFIDENCE_THRESHOLD = 0.3
IMAGE_PATH = r'Yolo_model/pic.jpg'
CAMERA_ID = "cam_01"

# --- MQTT Setup ---
client = mqtt.Client()
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# --- Load YOLO model ---
model = YOLO('yolov8n.pt')

# --- Load and process image ---
img = cv2.imread(IMAGE_PATH)
if img is None:
    print("❌ Không thể đọc ảnh!")
    exit()
else:
    print("✅ Ảnh đã được tải thành công.")

# --- Run YOLO detection ---
results = model(img)
counts = {}

# --- Đếm phương tiện ---
for result in results:
    boxes = result.boxes
    if boxes is not None:
        for box in boxes.data:
            confidence = float(box[4])
            class_id = int(box[5])

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            label = model.names[class_id]
            if label in ['car', 'bus', 'truck', 'motorcycle', 'bicycle']:
                counts[label] = counts.get(label, 0) + 1

# --- Gửi dữ liệu nếu có phương tiện ---
if counts:
    current_time = time.time()
    message = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
        "camera_id": CAMERA_ID,
        "vehicles": counts
    }
    client.publish(MQTT_TOPIC, json.dumps(message))
    print("📤 Published:", message)
else:
    print("ℹ️ Không phát hiện phương tiện nào.")

# --- (Tùy chọn) Hiển thị ảnh annotate ---
annotated_img = results[0].plot()
cv2.imshow("Detected Image", annotated_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
