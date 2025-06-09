# MQTT Testing Setup

This guide will help you set up and test the MQTT functionality with a simulated sensor.

## Prerequisites

1. Install Mosquitto MQTT broker:
   - On macOS (using Homebrew):
     ```bash
     brew install mosquitto
     ```
   - On Ubuntu/Debian:
     ```bash
     sudo apt-get install mosquitto mosquitto-clients
     ```

2. Install required Python packages:
   ```bash
   pip install paho-mqtt
   ```

## Setting up the MQTT Broker

1. Start the Mosquitto broker:
   ```bash
   mosquitto -v
   ```
   The `-v` flag enables verbose output so you can see the connections and messages.

2. Keep this terminal window open to run the broker.

## Testing the System

1. Add a new diagnostic code in the web interface:
   - Go to "Add Diagnostic Code"
   - Select "MQTT" as the data source type
   - Fill in the following details:
     - Name: "Temperature Sensor 1"
     - Description: "Test temperature sensor"
     - Broker: "localhost"
     - Port: 1883
     - Topic: "sensors/temperature/1"
     - Data Type: "float"
     - Units: "°C"
     - Set appropriate warning and critical limits (e.g., Warning: 25, Critical: 30)

2. Start the MQTT data reader:
   ```bash
   python read_mqtt_data.py
   ```

3. In a new terminal, run the test sensor:
   ```bash
   python test_mqtt_sensor.py
   ```

4. You should see:
   - The test sensor publishing temperature values every 5 seconds
   - The MQTT reader receiving and processing these values
   - The web interface updating with the latest values
   - Alerts being triggered if the values exceed the set limits

## Troubleshooting

1. If you can't connect to the broker:
   - Make sure Mosquitto is running
   - Check if the port 1883 is not blocked by a firewall
   - Verify the broker address is correct

2. If you're not seeing data:
   - Check the topic name matches exactly
   - Verify the JSON format of the messages
   - Check the MQTT reader logs for any errors

3. If alerts aren't working:
   - Verify the limits are set correctly in the diagnostic code
   - Check the alert configuration in the database
   - Verify the email settings in the .env file

## Sample Data Format

The test sensor sends data in this format:
```json
{
    "value": 25.5,
    "timestamp": "2024-03-14T12:34:56.789Z",
    "unit": "°C"
}
```

This matches the expected format in the MQTT reader implementation. 