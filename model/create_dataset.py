import numpy as np
import csv

# Traffic lights' time data
cars_waiting = np.array([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
green_light_time = np.array([5, 7, 9, 12, 15, 18, 21, 24, 27, 30, 33])

# Write to .csv file
with open("traffic_data.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["cars_waiting", "green_light_time"])
    for cars, time in zip(cars_waiting, green_light_time):
        writer.writerow([cars, time])

print("CSV file 'traffic_data.csv' has been successfully created.")