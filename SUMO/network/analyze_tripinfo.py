import xml.etree.ElementTree as ET

tree = ET.parse('tripinfo.xml')
root = tree.getroot()

total_duration = 0
total_waiting = 0
total_distance = 0
vehicle_count = 0

for trip in root.findall('tripinfo'):
    duration = float(trip.attrib['duration'])
    waiting = float(trip.attrib['waitingTime'])
    distance = float(trip.attrib['routeLength'])

    total_duration += duration
    total_waiting += waiting
    total_distance += distance
    vehicle_count += 1

# Tính trung bình
if vehicle_count > 0:
    avg_duration = total_duration / vehicle_count
    avg_waiting = total_waiting / vehicle_count
    avg_distance = total_distance / vehicle_count

    print(f"Tổng số xe: {vehicle_count}")
    print(f"Thời gian di chuyển trung bình: {avg_duration:.2f} giây")
    print(f"Thời gian chờ trung bình: {avg_waiting:.2f} giây")
    print(f"Quãng đường trung bình: {avg_distance:.2f} mét")
else:
    print("Không có phương tiện nào trong file.")
