import os
import sys
import random
import time
import traci
import paho.mqtt.client as mqtt
import json

# --- MQTT Config ---
MQTT_BROKER = '172.30.203.90'
MQTT_PORT = 1883
MQTT_TOPIC = 'iot/traffic'
client = mqtt.Client()
client.on_connect = lambda client, userdata, flags, rc: on_connect(client, userdata, flags, rc)
client.on_message = lambda client, userdata, msg: on_message(client, userdata, msg)

# --- SUMO Config ---
NUM_VEHICLES_MAX = 100
ROUTES = ["route0"]
VEHICLE_TYPES = ["car", "motorbike", "bicycle", "bus"]

# --- Global variables ---
veh_index = 0
mqtt_vehicle_queue = []  # Queue to store vehicle data from MQTT

# --- MQTT Callbacks ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker!")
        client.subscribe(MQTT_TOPIC)
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

# --- Generate vehicles from MQTT ---
def generate_vehicle_batch():
    global veh_index
    current_time = traci.simulation.getTime()
    
    # Process all vehicles in the MQTT queue (up to available slots)
    while mqtt_vehicle_queue and veh_index < NUM_VEHICLES_MAX:
        veh_type = mqtt_vehicle_queue.pop(0)
        veh_id = f"veh{veh_index}"
        route_id = random.choice(ROUTES)
        lane = random.randint(0, 4)  # Random lane from 0 to 4
        try:
            traci.vehicle.add(
                vehID=veh_id,
                routeID=route_id,
                typeID=veh_type,
                departLane=lane,
                depart=str(current_time)
            )
            print(f"Added vehicle {veh_id} (type: {veh_type}) from MQTT at time {current_time}")
            veh_index += 1
        except traci.TraCIException as e:
            print(f"Failed to add vehicle {veh_id}: {e}")
            break  # Stop adding vehicles if there's an error

if __name__ == "__main__":
    # Check SUMO_HOME
    if 'SUMO_HOME' not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    # SUMO configuration
    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "SUMO\\config\\simulation.sumocfg", "--start", "--step-length", "0.1"]

    # Start MQTT client
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()  # Start MQTT loop in background
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
        generate_vehicle_batch()
        traci.simulationStep()
        time.sleep(0.1)  # Delay for observation
        step += 1

    # Cleanup
    traci.close()
    client.loop_stop()
    client.disconnect()
    print("Simulation ended")