import os
import sys
import random
import time
import traci

NUM_VEHICLES = 50
ROUTES = ["route0"]
VEHICLE_TYPES = ["car", "motorbike"]

veh_index = 0

def generate_random_batch():
    global veh_index
    count = random.randint(1, 5)  # mỗi lần thêm 1-5 xe
    for _ in range(count):
        veh_id = f"veh{veh_index}"
        veh_type = random.choice(VEHICLE_TYPES)
        route_id = random.choice(ROUTES)
        depart_time = traci.simulation.getTime()
        lane = random.randint(0, 4)  # gán theo tuyến, lane 0 là mặc định
        try:
            traci.vehicle.add(vehID=veh_id, routeID=route_id, departLane=lane, typeID=veh_type, depart=str(depart_time))
            veh_index += 1
        except traci.TraCIException:
            pass

if __name__ == "__main__":
    if 'SUMO_HOME' not in os.environ:
        sys.exit("Please declare environment variable 'SUMO_HOME'")

    sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo-gui')
    sumo_cmd = [sumo_binary, "-c", "../config/simulation.sumocfg", "--start", "--step-length", "0.1"]

    traci.start(sumo_cmd)

    step = 0
    while step < 1000:
        if veh_index < NUM_VEHICLES:
            generate_random_batch()
        traci.simulationStep()
        time.sleep(0.1)  # delay để dễ quan sát
        step += 1

    traci.close()