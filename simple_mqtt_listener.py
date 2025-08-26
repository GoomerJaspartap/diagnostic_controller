#!/usr/bin/env python3
"""
Simple MQTT Message Listener

A basic script to listen to all MQTT messages and print them out.
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # Subscribe to all topics
    client.subscribe("#")

def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] Topic: {msg.topic}")
    
    try:
        # Try to decode as text
        payload = msg.payload.decode('utf-8')
        print(f"Payload: {payload}")
        
        # Try to parse as JSON
        try:
            data = json.loads(payload)
            print(f"JSON: {json.dumps(data, indent=2)}")
        except:
            pass
            
    except UnicodeDecodeError:
        print(f"Raw bytes: {msg.payload}")

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("Connecting to MQTT broker...")
    client.connect("10.160.0.170", 1883, 60)
    
    print("Listening for messages... (Press Ctrl+C to stop)")
    client.loop_forever()

if __name__ == "__main__":
    main()

