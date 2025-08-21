#!/usr/bin/env python3
"""
MQTT Test Publisher

This script publishes test messages to various topics to help test the MQTT listener.
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

def on_connect(client, userdata, flags, rc):
    print(f"Publisher connected with result code {rc}")

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    
    print("Connecting to MQTT broker...")
    client.connect("localhost", 1883, 60)
    client.loop_start()
    
    # Wait for connection
    time.sleep(1)
    
    print("Publishing test messages...")
    
    # Test message 1: Simple text
    client.publish("test/simple", "Hello MQTT World!")
    print("Published: test/simple")
    
    # Test message 2: JSON data
    sensor_data = {
        "temperature": 23.5,
        "humidity": 45.2,
        "timestamp": datetime.now().isoformat(),
        "location": "room_101"
    }
    client.publish("sensors/room_101", json.dumps(sensor_data))
    print("Published: sensors/room_101")
    
    # Test message 3: Another sensor
    sensor_data2 = {
        "temperature": 24.1,
        "humidity": 43.8,
        "timestamp": datetime.now().isoformat(),
        "location": "room_102"
    }
    client.publish("sensors/room_102", json.dumps(sensor_data2))
    print("Published: sensors/room_102")
    
    # Test message 4: Status message
    status_msg = {
        "status": "online",
        "device_id": "mqtt_test_device",
        "uptime": 3600,
        "last_seen": datetime.now().isoformat()
    }
    client.publish("device/status", json.dumps(status_msg))
    print("Published: device/status")
    
    # Test message 5: Binary-like data (simulated)
    binary_data = b"BINARY_DATA_12345"
    client.publish("test/binary", binary_data)
    print("Published: test/binary")
    
    print("\nAll test messages published!")
    print("Check your MQTT listener to see these messages.")
    
    # Keep connection alive for a bit
    time.sleep(2)
    
    client.loop_stop()
    client.disconnect()
    print("Publisher disconnected.")

if __name__ == "__main__":
    main()
