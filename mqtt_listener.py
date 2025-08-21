#!/usr/bin/env python3
"""
MQTT Message Listener Script

This script connects to the MQTT broker and listens to all incoming messages,
printing out the topic, payload, and other details for each message received.
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import sys

# MQTT Broker Configuration
MQTT_BROKER_HOST = "10.160.2.54"  # Change to your broker IP if different
MQTT_BROKER_PORT = 1883
MQTT_KEEPALIVE = 60

# Global variables
message_count = 0
is_connected = False

def on_connect(client, userdata, flags, rc):
    """Callback when connected to MQTT broker"""
    global is_connected
    
    if rc == 0:
        is_connected = True
        print(f"✅ Connected to MQTT broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
        print(f"Connection result code: {rc}")
        
        # Subscribe to all topics using wildcard
        print("🔍 Subscribing to all topics (using # wildcard)...")
        client.subscribe("#", qos=0)
        print("✅ Subscribed to all topics. Waiting for messages...")
        print("-" * 80)
        
    else:
        print(f"❌ Failed to connect to MQTT broker. Return code: {rc}")
        print("Connection failed. Please check:")
        print("1. MQTT broker is running")
        print("2. Broker host and port are correct")
        print("3. Network connectivity")

def on_disconnect(client, userdata, rc):
    """Callback when disconnected from MQTT broker"""
    global is_connected
    is_connected = False
    
    if rc != 0:
        print(f"⚠️  Unexpected disconnection. Return code: {rc}")
    else:
        print("ℹ️  Disconnected from MQTT broker")
    
    print("Attempting to reconnect...")

def on_message(client, userdata, msg):
    """Callback when a message is received"""
    global message_count
    message_count += 1
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    print(f"\n📨 MESSAGE #{message_count} - {timestamp}")
    print(f"📡 Topic: {msg.topic}")
    print(f"🔢 QoS: {msg.qos}")
    print(f"🔄 Retain: {msg.retain}")
    print(f"📏 Payload Length: {len(msg.payload)} bytes")
    
    # Try to decode payload as UTF-8 text
    try:
        payload_text = msg.payload.decode('utf-8')
        print(f"📝 Payload (UTF-8): {payload_text}")
        
        # Try to parse as JSON for better formatting
        try:
            payload_json = json.loads(payload_text)
            print(f"🔍 Payload (JSON):")
            print(json.dumps(payload_json, indent=2))
        except json.JSONDecodeError:
            print("ℹ️  Payload is not valid JSON")
            
    except UnicodeDecodeError:
        print(f"🔒 Payload (Raw Bytes): {msg.payload}")
        print("ℹ️  Payload could not be decoded as UTF-8 text")
    
    print("-" * 80)

def on_subscribe(client, userdata, mid, granted_qos):
    """Callback when subscribed to a topic"""
    print(f"✅ Subscribed with message ID: {mid}, QoS: {granted_qos}")

def on_log(client, userdata, level, buf):
    """Callback for MQTT client logs"""
    if level == mqtt.MQTT_LOG_ERR:
        print(f"❌ MQTT Error: {buf}")
    elif level == mqtt.MQTT_LOG_WARNING:
        print(f"⚠️  MQTT Warning: {buf}")
    elif level == mqtt.MQTT_LOG_NOTICE:
        print(f"ℹ️  MQTT Notice: {buf}")
    elif level == mqtt.MQTT_LOG_INFO:
        print(f"ℹ️  MQTT Info: {buf}")
    elif level == mqtt.MQTT_LOG_DEBUG:
        print(f"🔍 MQTT Debug: {buf}")

def create_mqtt_client():
    """Create and configure MQTT client"""
    client = mqtt.Client(
        client_id=f"mqtt_listener_{int(time.time())}",
        clean_session=True,
        protocol=mqtt.MQTTv311
    )
    
    # Set callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe
    client.on_log = on_log
    
    # Enable automatic reconnection
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    return client

def main():
    """Main function"""
    print("🚀 MQTT Message Listener Starting...")
    print(f"📍 Connecting to broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print("Press Ctrl+C to stop\n")
    
    # Create MQTT client
    client = create_mqtt_client()
    
    try:
        # Connect to broker
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        
        # Start the loop
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping MQTT listener...")
        client.loop_stop()
        client.disconnect()
        print(f"📊 Total messages received: {message_count}")
        print("👋 Goodbye!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        client.loop_stop()
        client.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    main()
