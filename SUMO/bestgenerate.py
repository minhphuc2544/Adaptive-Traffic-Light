import os
import sys
import random
import time
import traci
import paho.mqtt.client as mqtt
import json
import numpy as np
import requests

# Add the root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from config import Config

# --- MQTT Config ---
MQTT_BROKER_IP = Config.MQTT_BROKER_IP
MQTT_PORT = Config.MQTT_PORT
MQTT_TOPIC_TRAFFIC = Config.MQTT_TOPIC_TRAFFIC
MQTT_TOPIC_RANDOM_TRAFFIC = Config.MQTT_TOPIC_RANDOM_TRAFFIC
MQTT_TOPIC_RESPONSE = Config.MQTT_TOPIC_RESPONSE
THINGSBOARD_IP = Config.THINGSBOARD_IP
client = mqtt.Client()
client.on_connect = lambda client, userdata, flags, rc: on_connect(client, userdata, flags, rc)
client.on_message = lambda client, userdata, msg: on_message(client, userdata, msg)

# --- SUMO Config ---
NUM_VEHICLES_MAX = 10000
MAIN_EDGE = "W2TL"
RANDOM_EDGES = ["E2TL", "N2TL", "S2TL"]
VEHICLE_TYPES = ["car", "motorcycle", "bicycle", "bus", "truck"]
ROUTES = [
    "W_E", "W_S",
    "E_W", "E_N",
    "N_W", "N_S",
    "S_E", "S_N"
]
RANDOM_VEHICLE_RATE = 0.03
TL_ID = "TL"
YELLOW_TIME = 3.0

# --- RL Config ---
STATE_BINS = 5
ACTION_DURATIONS = [10, 15, 20, 25, 30]
ALPHA = 0.1
GAMMA = 0.9
EPSILON = 0.1
Q_TABLE = {}

# --- ThingsBoard Config ---
THINGSBOARD_URL = "http://192.168.141.43:9090/api/v1/{}/telemetry"
THINGSBOARD_TOKENS = {
    "E2TL": "VGIdxL7vvabXy1MZt8sQ",  # East
    "W2TL": "LicRjJxRfkosKLWQGBzh",  # West
    "S2TL": "uw0NoTwMcwMJAIfjrXOL",  # South
    "N2TL": "q4FfGpO1SCaKPH0YtpSG"   # North
}
SEND_INTERVAL = 5.0  # Seconds between ThingsBoard telemetry sends

# --- Global variables ---
veh_index = 0
mqtt_vehicle_queue = []
current_phase = 0
phase_end_time = 0
phase_duration = 15
sent_random_vehicle_ids = set()  # Theo dõi ID của phương tiện ngẫu nhiên đã gửi
last_sent_time = 0  # Tracks last time telemetry was sent to ThingsBoard

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe(MQTT_TOPIC_TRAFFIC)
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

# --- RL Functions ---
def get_state():
    density = []
    for edge in [MAIN_EDGE] + RANDOM_EDGES:
        num_vehicles = len(traci.edge.getLastStepVehicleIDs(edge))
        num_lanes = traci.edge.getLaneNumber(edge)
        density.append(min(num_vehicles / num_lanes, 10))
    bins = np.linspace(0, 10, STATE_BINS + 1)
    state = tuple(np.digitize(density, bins) - 1)
    return state

def choose_action(state):
    if random.random() < EPSILON:
        return random.choice(ACTION_DURATIONS)
    q_values = Q_TABLE.get(state, {a: 0 for a in ACTION_DURATIONS})
    return max(q_values, key=q_values.get)

def get_reward():
    waiting_time = 0
    for edge in [MAIN_EDGE] + RANDOM_EDGES:
        for veh_id in traci.edge.getLastStepVehicleIDs(edge):
            waiting_time += traci.vehicle.getWaitingTime(veh_id)
    return -waiting_time

def update_q_table(state, action, reward, next_state):
    if state not in Q_TABLE:
        Q_TABLE[state] = {a: 0 for a in ACTION_DURATIONS}
    if next_state not in Q_TABLE:
        Q_TABLE[next_state] = {a: 0 for a in ACTION_DURATIONS}
    current_q = Q_TABLE[state][action]
    next_max_q = max(Q_TABLE[next_state].values())
    Q_TABLE[state][action] = current_q + ALPHA * (reward + GAMMA * next_max_q - current_q)

# --- Traffic Light Control ---
def control_traffic_lights():
    global current_phase, phase_end_time, phase_duration
    current_time = traci.simulation.getTime()
    if current_time >= phase_end_time:
        if current_phase == 0:
            current_phase = 1
            trigger_phase("NS_yellow")  # Trigger yellow phase
        elif current_phase == 1:
            current_phase = 2
            trigger_phase("EW_green")  # Trigger green phase for EW
        elif current_phase == 2:
            current_phase = 3
            trigger_phase("EW_yellow")  # Trigger yellow phase
        elif current_phase == 3:
            current_phase = 0
            trigger_phase("NS_green")  # Trigger green phase for NS
        traci.trafficlight.setPhase(TL_ID, current_phase)
        phase_end_time = current_time + phase_duration
        phase_name = {0: "NS_green", 1: "NS_yellow", 2: "EW_green", 3: "EW_yellow"}[current_phase]

def trigger_phase(phase):
    global current_phase, phase_end_time
    current_time = traci.simulation.getTime()
    message = {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
        "traffic_light": TL_ID,
        "phase": phase
    }
    client.publish(MQTT_TOPIC_RESPONSE, json.dumps(message))
    print(f"Triggered traffic light phase: {message}")
    if phase in ["EW_yellow", "NS_yellow"]:
        phase_duration = YELLOW_TIME  # Fixed 3 seconds for yellow
    else:
        phase_duration = choose_action(get_state())  # Dynamic duration for green
    phase_end_time = current_time + phase_duration

# --- Generate vehicles from MQTT ---
def generate_mqtt_vehicles():
    global veh_index
    current_time = traci.simulation.getTime()
    while mqtt_vehicle_queue and veh_index < NUM_VEHICLES_MAX:
        veh_type = mqtt_vehicle_queue.pop(0)
        veh_id = f"mqtt_veh{veh_index}"
        route_id = random.choice([r for r in ROUTES if r.startswith("W_")])
        lane = random.randint(0, 1)
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

# --- Generate random vehicles ---
def generate_random_vehicles():
    global veh_index, sent_random_vehicle_ids
    current_time = traci.simulation.getTime()
    new_vehicle_counts = {edge: {} for edge in RANDOM_EDGES}  # Theo dõi số xe mới trên mỗi edge
    for edge in RANDOM_EDGES:
        if random.random() < RANDOM_VEHICLE_RATE and veh_index < NUM_VEHICLES_MAX:
            veh_type = random.choice(VEHICLE_TYPES)
            veh_id = f"rand_veh{veh_index}"
            route_id = random.choice([r for r in ROUTES if r.startswith(edge[0] + "_")])
            lane = random.randint(0, 1)
            try:
                traci.vehicle.add(
                    vehID=veh_id,
                    routeID=route_id,
                    typeID=veh_type,
                    departLane=lane,
                    depart=str(current_time)
                )
                print(f"Added random vehicle {veh_id} (type: {veh_type}) on {edge} at time {current_time}")
                if veh_id not in sent_random_vehicle_ids:  # Chỉ tính xe mới
                    new_vehicle_counts[edge][veh_type] = new_vehicle_counts[edge].get(veh_type, 0) + 1
                    sent_random_vehicle_ids.add(veh_id)
                veh_index += 1
            except traci.TraCIException as e:
                print(f"Failed to add random vehicle {veh_id}: {e}")
    # Gửi dữ liệu chỉ khi có xe mới
    if any(new_vehicle_counts[edge] for edge in RANDOM_EDGES):
        publish_traffic_data(new_vehicle_counts)

# --- Publish SUMO traffic data ---
def publish_traffic_data(new_vehicle_counts):
    current_time = traci.simulation.getTime()
    traffic_data = {}
    for edge in RANDOM_EDGES:
        if new_vehicle_counts[edge]:  # Chỉ gửi nếu có xe mới trên edge
            traffic_data[edge] = new_vehicle_counts[edge]
    if traffic_data:
        message = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(current_time)),
            "traffic": traffic_data
        }
        client.publish(MQTT_TOPIC_RANDOM_TRAFFIC, json.dumps(message))
        print(f"Published SUMO traffic data for new vehicles: {message}")

def send_vehicle_counts_to_thingsboard():
    global last_sent_time
    current_time = traci.simulation.getTime()
    if current_time - last_sent_time < SEND_INTERVAL:
        return
    
    headers = {"Content-Type": "application/json"}
    edges = [MAIN_EDGE] + RANDOM_EDGES
    for edge in edges:
        vehicle_count = len(traci.edge.getLastStepVehicleIDs(edge))
        token = THINGSBOARD_TOKENS.get(edge)
        if not token:
            print(f"No ThingsBoard token for edge {edge}")
            continue
        url = THINGSBOARD_URL.format(token)
        data = {
            "ts": int(time.time() * 1000),
            "values": {
                "total_vehicle": vehicle_count
            }
        }
        try:
            response = requests.post(url, json=data, headers=headers, timeout=2)
            if response.status_code == 200:
                print(f"Sent to ThingsBoard for {edge}: {data}")
            else:
                print(f"Failed to send to ThingsBoard for {edge}: {response.status_code}")
        except Exception as e:
            print(f"Error sending to ThingsBoard for {edge}: {e}")
    
    last_sent_time = current_time

if __name__ == "__main__":
    # Check SUMO_HOME
    if 'SUMO_HOME' not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    # SUMO configuration
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "SUMO/config/simulation.sumocfg", "--start", "--step-length", "0.1"]

    # Start MQTT client
    try:
        client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)
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
    while step < 10000:
        generate_mqtt_vehicles()
        generate_random_vehicles()
        control_traffic_lights()
        send_vehicle_counts_to_thingsboard()
        traci.simulationStep()
        time.sleep(0.1)
        step += 1

    # Cleanup
    traci.close()
    client.loop_stop()
    client.disconnect()
    print("Simulation ended")