import os
import sys
import random
import time
import traci
import paho.mqtt.client as mqtt
import json

# --- MQTT Config ---
MQTT_BROKER = '192.168.79.8'
MQTT_PORT = 1883
MQTT_TOPIC_IN = 'iot/traffic'
MQTT_TOPIC_OUT = 'iot/response'
client = mqtt.Client()
client.on_connect = lambda client, userdata, flags, rc: on_connect(client, userdata, flags, rc)
client.on_message = lambda client, userdata, msg: on_message(client, userdata, msg)

# --- SUMO Config ---
NUM_VEHICLES_MAX = 10000
MAIN_EDGE = "W2TL"  # Nhánh chính lấy từ MQTT
RANDOM_EDGES = ["E2TL", "N2TL", "S2TL"]  # 3 nhánh sinh ngẫu nhiên
VEHICLE_TYPES = ["car", "motorbike", "bicycle", "bus", "truck"]
ROUTES = [
    "route_E2TL", "route_E2TL2W",  # E2TL: right, straight
    "route_N2TL", "route_N2TL2S",  # N2TL: right, straight
    "route_S2TL", "route_S2TL2N",  # S2TL: right, straight
    "route_W2TL", "route_W2TL2S"   # W2TL: straight, right
]
RANDOM_VEHICLE_RATE = 0.1  # Tỷ lệ sinh xe ngẫu nhiên mỗi bước (10%)

# --- Global variables ---
veh_index = 0
mqtt_vehicle_queue = []  # Queue để lưu xe từ MQTT

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe(MQTT_TOPIC_IN)
    else:
        print("Connection failed with code", rc)

def on_message(client, userdata, msg):
    global mqtt_vehicle_queue
    try:
        data = json.loads(msg.payload.decode())
        vehicles = data.get("vehicles", {})
        timestamp = data.get("timestamp", "")
        print(f"Received MQTT message at {timestamp}: {vehicles}")
        for veh_type, count in vehicles.items():
            if veh_type in VEHICLE_TYPES and isinstance(count, int) and count > 0:
                mqtt_vehicle_queue.extend([veh_type] * count)
            else:
                print(f"Ignored invalid vehicle type {veh_type} or count {count}")
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

# --- Generate vehicles from MQTT (for MAIN_EDGE) ---
def generate_mqtt_vehicles():
    global veh_index
    current_time = traci.simulation.getTime()
    while mqtt_vehicle_queue and veh_index < NUM_VEHICLES_MAX:
        veh_type = mqtt_vehicle_queue.pop(0)
        veh_id = f"mqtt_veh{veh_index}"
        route_id = random.choice([r for r in ROUTES if r.startswith("route_W2TL")])  # Chỉ chọn route từ W2TL
        lane = random.randint(0, 1)  # 2 làn
        try:
            traci.vehicle.add(
                vehID=veh_id,
                routeID=route_id,
                typeID=veh_type,
                departLane=lane,
                depart=str(current_time)
            )
            print(f"Added MQTT vehicle {veh_id} (type: {veh_type}) on {MAIN_EDGE} at time {current_time}")
            veh_index += 1
        except traci.TraCIException as e:
            print(f"Failed to add MQTT vehicle {veh_id}: {e}")
            break

# --- Generate random vehicles (for RANDOM_EDGES) ---
def generate_random_vehicles():
    global veh_index
    current_time = traci.simulation.getTime()
    for edge in RANDOM_EDGES:
        if random.random() < RANDOM_VEHICLE_RATE and veh_index < NUM_VEHICLES_MAX:
            veh_type = random.choice(VEHICLE_TYPES)
            veh_id = f"rand_veh{veh_index}"
            route_id = random.choice([r for r in ROUTES if r.startswith(f"route_{edge}")])  # Chọn route phù hợp với edge
            lane = random.randint(0, 1)  # 2 làn
            try:
                traci.vehicle.add(
                    vehID=veh_id,
                    routeID=route_id,
                    typeID=veh_type,
                    departLane=lane,
                    depart=str(current_time)
                )
                print(f"Added random vehicle {veh_id} (type: {veh_type}) on {edge} at time {current_time}")
                veh_index += 1
            except traci.TraCIException as e:
                print(f"Failed to add random vehicle {veh_id}: {e}")

# --- Publish SUMO traffic data to MQTT ---
def publish_traffic_data():
    current_time = traci.simulation.getTime()
    traffic_data = {}
    for edge in [MAIN_EDGE] + RANDOM_EDGES:
        vehicle_counts = {}
        for veh_type in VEHICLE_TYPES:
            count = sum(1 for veh_id in traci.edge.getLastStepVehicleIDs(edge)
                       if traci.vehicle.getTypeID(veh_id).lower() == veh_type.lower())
            if count > 0:
                vehicle_counts[veh_type] = count
        if vehicle_counts:
            traffic_data[edge] = vehicle_counts
    if traffic_data:
        message = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
            "traffic": traffic_data
        }
        client.publish(MQTT_TOPIC_OUT, json.dumps(message))
        print(f"Published SUMO traffic data: {message}")

if __name__ == "__main__":
    # Check SUMO_HOME
    if 'SUMO_HOME' not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    # SUMO configuration
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "SUMO/config/simulation.sumocfg", "--start", "--step-length", "0.1"]

    # Start MQTT client
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        print("MQTT client started")
    except Exception as e:
        sys.exit(f"Failed to connect to MQTT broker: {e}")

    # Start SUMO simulation
    try:
        traci.start(sumo_cmd)
        print("SUMO simulation started")
    except traci.TraCIException as e:
        client.loop_stop()
        client.disconnect()
        sys.exit(f"Failed to start SUMO: {e}")

    # Simulation loop
    step = 0
    while step < 1000:
        generate_mqtt_vehicles()  # Tạo xe từ MQTT cho W2TL
        generate_random_vehicles()  # Tạo xe ngẫu nhiên cho E2TL, N2TL, S2TL
        publish_traffic_data()  # Đẩy dữ liệu SUMO lên MQTT
        traci.simulationStep()
        time.sleep(0.1)
        step += 1

    # Cleanup
    traci.close()
    client.loop_stop()
    client.disconnect()
    print("Simulation ended")