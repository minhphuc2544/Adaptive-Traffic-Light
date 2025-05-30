import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MQTT Related Env Vars
    MQTT_BROKER_IP = os.environ['MQTT_BROKER_IP']
    MQTT_PORT = int(os.environ['MQTT_PORT'])
    MQTT_TOPIC_TRAFFIC = os.environ['MQTT_TOPIC_TRAFFIC']
    MQTT_TOPIC_RANDOM_TRAFFIC = os.environ['MQTT_TOPIC_RANDOM_TRAFFIC']
    MQTT_TOPIC_RESPONSE = os.environ['MQTT_TOPIC_RESPONSE']

    # Raspberri Pi Related Env Vars
    PI_CAMERA_URL = os.environ['PI_CAMERA_URL']