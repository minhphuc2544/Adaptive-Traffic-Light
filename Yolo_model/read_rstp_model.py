#!/usr/bin/env python3
"""
RTSP YOLO Traffic Detection System
Connects to Raspberry Pi RTSP stream and performs vehicle detection
"""

import time
import json
import paho.mqtt.client as mqtt
from ultralytics import YOLO
import cv2
import logging

# --- Configuration ---
RTSP_URL = 'rtsp://192.168.79.249:8554/stream'  # Replace with your Pi's IP
MQTT_BROKER = '192.168.61.8'
MQTT_PORT = 1883
MQTT_TOPIC = 'iot/traffic'
SEND_INTERVAL = 2
CONFIDENCE_THRESHOLD = 0.3
CAMERA_ID = "cam_01_rtsp"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 600

# Video buffer settings for real-time processing
RTSP_BUFFER_SIZE = 1  # Minimal buffer for low latency
RTSP_TIMEOUT = 10000  # 10 seconds timeout

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RTSPTrafficDetector:
    def __init__(self):
        self.mqtt_client = None
        self.yolo_model = None
        self.video_capture = None
        self.counts = {}
        self.last_sent_time = time.time()
        self.frame_count = 0
        self.detection_start_time = time.time()
        
    def setup_mqtt(self):
        """Initialize MQTT connection"""
        try:
            self.mqtt_client = mqtt.Client()
            
            # MQTT callbacks
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    logger.info("✅ Connected to MQTT broker")
                else:
                    logger.error(f"❌ MQTT connection failed with code {rc}")
            
            def on_publish(client, userdata, mid):
                logger.debug(f"📤 Message {mid} published")
                
            def on_disconnect(client, userdata, rc):
                logger.warning(f"⚠️  MQTT disconnected with code {rc}")
            
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_publish = on_publish
            self.mqtt_client.on_disconnect = on_disconnect
            
            # Connect to broker
            self.mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.mqtt_client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ MQTT setup failed: {e}")
            return False
    
    def setup_yolo(self):
        """Initialize YOLO model"""
        try:
            logger.info("🧠 Loading YOLO model...")
            self.yolo_model = YOLO('yolov8n.pt')
            logger.info("✅ YOLO model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ YOLO model loading failed: {e}")
            return False
    
    def setup_rtsp_stream(self):
        """Initialize RTSP video stream"""
        try:
            logger.info(f"📡 Connecting to RTSP stream: {RTSP_URL}")
            
            # Configure OpenCV for RTSP
            self.video_capture = cv2.VideoCapture(RTSP_URL)
            
            # Set buffer size for real-time processing
            self.video_capture.set(cv2.CAP_PROP_BUFFERSIZE, RTSP_BUFFER_SIZE)
            
            # Set timeout
            self.video_capture.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, RTSP_TIMEOUT)
            self.video_capture.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, RTSP_TIMEOUT)
            
            # Try to read a frame to verify connection
            if not self.video_capture.isOpened():
                raise Exception("Unable to open RTSP stream")
                
            ret, frame = self.video_capture.read()
            if not ret or frame is None:
                raise Exception("Unable to read from RTSP stream")
                
            # Get stream info
            fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logger.info(f"✅ RTSP stream connected: {width}x{height} @ {fps:.1f}fps")
            return True
            
        except Exception as e:
            logger.error(f"❌ RTSP stream setup failed: {e}")
            logger.error(f"🔍 Make sure your Pi is streaming at: {RTSP_URL}")
            return False
    
    def detect_vehicles(self, frame):
        """Run YOLO detection on frame and count vehicles"""
        try:
            # Run YOLO detection
            results = self.yolo_model(frame, verbose=False)
            current_counts = {}
            
            # Process detection results
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes.data:
                        confidence = float(box[4])
                        class_id = int(box[5])
                        
                        # Filter by confidence threshold
                        if confidence < CONFIDENCE_THRESHOLD:
                            continue
                        
                        # Get class label
                        label = self.yolo_model.names[class_id]
                        
                        # Count vehicles only
                        if label in ['car', 'bus', 'truck', 'motorcycle', 'bicycle']:
                            current_counts[label] = current_counts.get(label, 0) + 1
            
            return results, current_counts
            
        except Exception as e:
            logger.error(f"❌ Detection error: {e}")
            return None, {}
    
    def publish_counts(self, counts):
        """Publish vehicle counts to MQTT"""
        try:
            if not counts:
                return
                
            current_time = time.time()
            message = {
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
                "camera_id": CAMERA_ID,
                "vehicles": counts,
                "frame_number": self.frame_count
            }
            
            # Publish to MQTT
            result = self.mqtt_client.publish(MQTT_TOPIC, json.dumps(message))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Published: {counts} (Frame: {self.frame_count})")
            else:
                logger.warning(f"⚠️  MQTT publish failed with code {result.rc}")
                
            self.last_sent_time = current_time
            
        except Exception as e:
            logger.error(f"❌ MQTT publish error: {e}")
    
    def process_frame(self, frame):
        """Process a single frame with detection and display"""
        try:
            # Run vehicle detection
            results, counts = self.detect_vehicles(frame)
            
            if results is None:
                return False
                
            # Update global counts
            self.counts = counts
            
            # Send MQTT data every SEND_INTERVAL seconds
            current_time = time.time()
            if current_time - self.last_sent_time >= SEND_INTERVAL and counts:
                self.publish_counts(counts)
            
            # Display annotated frame
            if results:
                annotated_frame = results[0].plot()
                
                # Add frame info overlay
                info_text = f"Frame: {self.frame_count} | Vehicles: {sum(counts.values()) if counts else 0}"
                cv2.putText(annotated_frame, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Add vehicle counts overlay
                y_offset = 60
                for vehicle_type, count in counts.items():
                    count_text = f"{vehicle_type}: {count}"
                    cv2.putText(annotated_frame, count_text, (10, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    y_offset += 25
                
                # Resize and display
                display_frame = cv2.resize(annotated_frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
                cv2.imshow('RTSP Traffic Monitoring', display_frame)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Frame processing error: {e}")
            return False
    
    def run_detection_loop(self):
        """Main detection loop"""
        logger.info("🎯 Starting traffic detection...")
        
        try:
            while True:
                # Read frame from RTSP stream
                ret, frame = self.video_capture.read()
                
                if not ret or frame is None:
                    logger.warning("⚠️  No frame received, retrying...")
                    time.sleep(0.1)
                    continue
                
                self.frame_count += 1
                
                # Process frame
                if not self.process_frame(frame):
                    continue
                
                # Log performance stats every 100 frames
                if self.frame_count % 100 == 0:
                    elapsed = time.time() - self.detection_start_time
                    avg_fps = self.frame_count / elapsed
                    logger.info(f"📊 Processed {self.frame_count} frames, Avg FPS: {avg_fps:.1f}")
                
                # Check for exit key (ESC)
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC key
                    logger.info("⏹️  Detection stopped by user")
                    break
                
                # Small delay to prevent CPU overload
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            logger.info("⏹️  Detection stopped by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"❌ Detection loop error: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        logger.info("🧹 Cleaning up resources...")
        
        if self.video_capture:
            self.video_capture.release()
            logger.info("📹 Video capture released")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("📡 MQTT disconnected")
        
        cv2.destroyAllWindows()
        logger.info("🖼️  Windows closed")
    
    def start(self):
        """Start the traffic detection system"""
        logger.info("🚀 Initializing RTSP Traffic Detection System...")
        
        # Setup components
        if not self.setup_mqtt():
            return False
            
        if not self.setup_yolo():
            return False
            
        if not self.setup_rtsp_stream():
            return False
        
        logger.info("✅ All systems ready!")
        logger.info(f"🎯 Detection threshold: {CONFIDENCE_THRESHOLD}")
        logger.info(f"📡 MQTT: {MQTT_BROKER}:{MQTT_PORT} -> {MQTT_TOPIC}")
        logger.info(f"⏱️  Sending data every {SEND_INTERVAL} seconds")
        logger.info("Press ESC to stop detection")
        
        # Start detection
        self.run_detection_loop()
        return True

def main():
    """Main function"""
    detector = RTSPTrafficDetector()
    
    try:
        detector.start()
    except Exception as e:
        logger.error(f"❌ System error: {e}")
        detector.cleanup()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        logger.error("❌ Traffic detection system failed")
        exit(1)
    
    logger.info("✅ Traffic detection system completed")