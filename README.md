# 🚦 Adaptive Traffic Light System

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![SUMO](https://img.shields.io/badge/SUMO-1.15.0-green.svg)](https://www.eclipse.org/sumo/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-red.svg)](https://ultralytics.com/yolov8)

An intelligent traffic management system that uses computer vision and reinforcement learning to optimize traffic light timing based on real-time vehicle detection.

## 🌐 System Architecture

### IoT Reference Model
![IoT Reference Architecture](figures/iot_reference_model.png)

This diagram shows the core components of our IoT system:
- **Raspberry Pi** with camera captures and streams video
- **YOLO Model Server** processes the stream for vehicle detection
- **Reinforcement Learning Server** makes traffic light decisions
- **ESP32 Microcontroller** controls physical traffic lights
- **MQTT Broker** facilitates communication between components
- **ThingsBoard** for IoT dashboard and monitoring

### Workflow Diagram
![System Workflow](figures/system_workflow.png)

The end-to-end workflow:
1. Street cameras capture real-time traffic footage
2. Video streams are processed by the YOLO model for vehicle detection
3. Traffic data is analyzed by the Reinforcement Learning model
4. Optimal traffic light phases are determined
5. Commands are sent to:
   - SUMO for simulation updates
   - ESP32 controllers for physical lights
6. Traffic signals adapt based on current conditions

## 📌 Features

- **Real-time Vehicle Detection**: Uses YOLOv8 model to detect and classify vehicles from camera streams
- **Adaptive Traffic Control**: Implements Q-learning algorithm to optimize traffic light phases
- **Multi-Platform Support**: Works with Raspberry Pi cameras, USB cameras, and video files
- **IoT Integration**: Controls physical traffic lights via MQTT and Arduino
- **Simulation Environment**: Includes SUMO traffic simulation for testing and development
- **Modular Architecture**: Separates components for easy maintenance and extension

## 🗂 Project Structure

```
adaptive-traffic-light/
│   .gitignore
│   config.py                      # Configuration loader
│   README.md
│   requirements.txt
│   
├───IoT
│   ├───rasppi_camera
│   │       camera.py              # Camera streaming server
│   │       README.md              # Raspberry Pi setup guide
│   │   
│   └───lights_controller
│           lights_controller.ino  # Arduino traffic light controller
│           README.md              # ESP32 setup guide
│           
├───SUMO
│   │   generate_vehicles.py       # SUMO vehicle generator with RL
│   │   
│   ├───config
│   │       simulation.sumocfg     # SUMO configuration
│   │       
│   ├───network
│   │       simple.add.xml         # Additional network elements
│   │       simple.edg.xml         # Edge definitions
│   │       simple.nod.xml         # Node definitions
│   │       
│   └───routes
│           random_routes.rou.xml  # Vehicle routes
│           
├───Yolo_model
│       read_pic_model.py          # Image vehicle detection
│       read_streaming_model.py    # Live stream detection
│       read_video_model.py        # Video file detection
└───ThingsBoard
        docker-compose.yml         # Docker Compose file for running ThingsBoard
        README.md                  # ThingsBoard setup guide
        traffic_monitor.json       # Exported Dashboard
```

## 🛠 Installation

### Prerequisites

- Python 3.8+
- SUMO (≥1.15.0)
- Arduino IDE (for hardware controller)
- Raspberry Pi (optional for physical deployment)
- Docker, Docker Compose

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/minhphuc2544/Adaptive-Traffic-Light.git
   cd Adaptive-Traffic-Light
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` with example values:
   ```ini
   # MQTT Related Env Vars
   MQTT_BROKER_IP=192.168.141.8
   MQTT_PORT=1883
   MQTT_TOPIC_TRAFFIC=iot/traffic
   MQTT_TOPIC_RANDOM_TRAFFIC=iot/sumo_traffic
   MQTT_TOPIC_RESPONSE=iot/response

   # Raspberri Pi Related Env Vars
   PI_CAMERA_URL=http://192.168.154.249:8080/stream

   # ThingsBoard config
   THINGSBOARD_IP=192.168.141.43
   THINGSBOARD_TOKEN_EAST=VGIdxL7vvabXy1MZt8sQ
   THINGSBOARD_TOKEN_WEST=LicRjJxRfkosKLWQGBzh
   THINGSBOARD_TOKEN_SOUTH=uw0NoTwMcwMJAIfjrXOL
   THINGSBOARD_TOKEN_NORTH=q4FfGpO1SCaKPH0YtpSG
   ```

4. For Raspberry Pi setup, follow the [IoT/rasppi_camera/README.md](IoT/rasppi_camera/README.md) guide.

## 🚀 Usage

### Running ThingsBoard

Follow the instruction in [ThingsBoard/README.md](ThingsBoard/README.md)

### Running the Simulation

1. Run the vehicle generator with RL controller:
   ```bash
   python SUMO/generate_vehicles.py
   ```

### Using the Camera System

1. Start the camera streamer (on Raspberry Pi):
   ```bash
   python IoT/rasppi_camera/camera.py
   ```

2. Run vehicle detection on the stream:
   ```bash
   python Yolo_model/read_streaming_model.py
   ```

### Controlling Physical Lights

Follow the instruction in [IoT/lights_controller/README.md](IoT/lights_controller/README.md)

## 🤖 Tech Stack

- **Computer Vision**: YOLOv8, OpenCV
- **Simulation**: SUMO, TraCI
- **IoT**: MQTT, ESP32 (Arduino)
- **Reinforcement Learning**: Q-learning with state discretization
- **Edge Computing**: Raspberry Pi with PiCamera
- **Tracking**: Norfair object tracking

## 📊 MQTT API Reference

| Topic              | Direction   | Format                          | Description |
|--------------------|-------------|---------------------------------|-------------|
| `iot/traffic`      | Camera → RL | `{"vehicles": {"car": 3, ...}}` | Vehicle counts from detection |
| `iot/random_traffic` | SUMO → UI  | `{"traffic": {"W2TL": {...}}}`  | Simulated traffic data |
| `iot/response`     | RL → Lights | `{"phase": "EW_green", ...}`    | Traffic light phase commands |

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feat/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feat/AmazingFeature`)
5. Open a Pull Request

## 📜 License

Distributed under the Apache License 2.0. See `LICENSE` for more information.

## 🙏 Credits

- SUMO for traffic simulation capabilities
- Ultralytics for YOLOv8 model
- Norfair for object tracking