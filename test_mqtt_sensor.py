import paho.mqtt.client as mqtt
import time
import random
import json
from datetime import datetime

# MQTT Configuration
BROKER = "10.160.0.102"
PORT = 1883
TOPIC = "sensors/temperature/1"  # This should match the topic in your diagnostic code
QOS = 0

def generate_sensor_data(custom_value=None):
    """Generate sensor data that simulates temperature readings"""
    if custom_value is not None:
        temperature = float(custom_value)
    else:
        # Generate a temperature between 15 and 35 degrees Celsius
        temperature = 40
    
    # Create a payload with timestamp and value
    payload = {
        "value": temperature,
        "timestamp": datetime.now().isoformat(),
        "unit": "°C"
    }
    
    return json.dumps(payload)

def generate_simple_value(custom_value=None):
    """Generate just the temperature value"""
    if custom_value is not None:
        temperature = float(custom_value)
    else:
        # Generate a temperature between 15 and 35 degrees Celsius
        temperature = 30
    return str(temperature)

def publish_data(client, topic, payload_type="json", custom_value=None):
    """Publish data to MQTT topic with specified payload type
    
    Args:
        client: MQTT client instance
        topic: MQTT topic to publish to
        payload_type: Type of payload to send ("json" or "simple")
        custom_value: Optional custom value to use instead of default
    """
    if payload_type == "json":
        payload = generate_sensor_data(custom_value)
    else:  # simple
        payload = generate_simple_value(custom_value)
    
    client.publish(topic, payload, qos=QOS)
    print(f"Published to {topic}: {payload}")

def main():
    # Create MQTT client
    client = mqtt.Client()
    
    try:
        # Connect to broker
        print(f"Connecting to MQTT broker at {BROKER}:{PORT}")
        client.connect(BROKER, PORT)
        
        # Start the loop
        client.loop_start()
        
        print(f"Publishing to topic: {TOPIC}")
        print("Press Ctrl+C to stop")
        
        while True:
            # Ask user for payload type
            print("\nChoose payload type:")
            print("1. JSON payload (with timestamp and unit)")
            print("2. Simple value only")
            choice = input("Enter choice (1 or 2): ")
            
            payload_type = "json" if choice == "1" else "simple"
            
            # Ask user if they want to use a custom value
            print("\nDo you want to use a custom value?")
            print("1. Use default value")
            print("2. Enter custom value")
            value_choice = input("Enter choice (1 or 2): ")
            
            custom_value = None
            if value_choice == "2":
                try:
                    custom_value = input("Enter custom value: ")
                    # Validate that it's a number
                    float(custom_value)
                    print(f"Using custom value: {custom_value}")
                except ValueError:
                    print("Invalid value. Using default value instead.")
                    custom_value = None
            
            publish_data(client, TOPIC, payload_type, custom_value)
            
            # Wait for 2 seconds before next publish
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nStopping sensor simulation...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main() 