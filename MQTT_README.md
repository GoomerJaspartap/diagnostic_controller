# MQTT Message Listener Scripts

This directory contains Python scripts to listen to and test MQTT messages from your Docker-based MQTT broker.

## Files

- **`mqtt_listener.py`** - Full-featured MQTT listener with detailed logging and error handling
- **`simple_mqtt_listener.py`** - Basic MQTT listener for simple testing
- **`mqtt_test_publisher.py`** - Test script that publishes sample messages
- **`MQTT_README.md`** - This documentation file

## Prerequisites

1. **MQTT Broker Running**: Your Docker MQTT broker (Mosquitto) must be running
2. **Python Dependencies**: The `paho-mqtt` library must be installed

## Quick Start

### 1. Start Your MQTT Broker

Make sure your Docker MQTT broker is running:

```bash
# If using docker-compose
docker-compose up -d mqtt-broker

# Or check if it's already running
docker ps | grep mqtt
```

### 2. Run the MQTT Listener

Choose one of the listener scripts:

**Option A: Full-featured listener (recommended)**
```bash
python3 mqtt_listener.py
```

**Option B: Simple listener**
```bash
python3 simple_mqtt_listener.py
```

### 3. Test with Sample Messages

In another terminal, run the test publisher:

```bash
python3 mqtt_test_publisher.py
```

## What You'll See

The listener will display:

- **Connection status** to the MQTT broker
- **All incoming messages** with:
  - Topic name
  - Message payload (text, JSON, or raw bytes)
  - Timestamp
  - QoS level
  - Retain flag
  - Message size

## Configuration

### MQTT Broker Settings

The scripts are configured to connect to:
- **Host**: `localhost` (or `127.0.0.1`)
- **Port**: `1883` (default MQTT port)
- **Authentication**: None (anonymous access)

### Customizing Connection

If you need to change the broker settings, edit these lines in the scripts:

```python
MQTT_BROKER_HOST = "your_broker_ip"  # Change from localhost
MQTT_BROKER_PORT = 1883              # Change if using different port
```

## Troubleshooting

### Connection Issues

1. **"Connection refused"**: 
   - Check if MQTT broker is running: `docker ps | grep mqtt`
   - Verify port 1883 is accessible: `netstat -an | grep 1883`

2. **"Connection timeout"**:
   - Check firewall settings
   - Verify network connectivity to broker

3. **"Authentication failed"**:
   - Check if broker requires credentials
   - Update `mosquitto.conf` if needed

### No Messages Received

1. **Check subscription**: The scripts subscribe to `#` (all topics)
2. **Verify publisher**: Make sure something is publishing to topics
3. **Check broker logs**: `docker logs <mqtt_container_name>`

## Advanced Usage

### Filtering Topics

To listen to specific topics instead of all topics, modify the subscription:

```python
# Instead of subscribing to "#" (all topics)
client.subscribe("sensors/#")        # Only sensor topics
client.subscribe("device/status")    # Only device status
client.subscribe("test/+")           # Test topics with single-level wildcard
```

### Saving Messages to File

Add this to the `on_message` function to log messages to a file:

```python
def on_message(client, userdata, msg):
    # ... existing code ...
    
    # Log to file
    with open("mqtt_messages.log", "a") as f:
        f.write(f"{timestamp} | {msg.topic} | {payload_text}\n")
```

### Custom Message Processing

Modify the `on_message` function to process messages as needed:

```python
def on_message(client, userdata, msg):
    if msg.topic.startswith("sensors/"):
        # Process sensor data
        process_sensor_data(msg.payload)
    elif msg.topic == "device/status":
        # Process device status
        process_device_status(msg.payload)
```

## Docker Integration

If you're running the listener from within Docker, you may need to:

1. **Use service name instead of localhost**:
   ```python
   MQTT_BROKER_HOST = "mqtt-broker"  # Docker service name
   ```

2. **Ensure network connectivity** between containers

3. **Use the same network** as defined in your `docker-compose.yml`

## Security Notes

- **Current setup allows anonymous access** - suitable for development/testing
- **For production**: Enable authentication in `mosquitto.conf`
- **Consider TLS/SSL** for encrypted communication
- **Limit topic access** using ACLs if needed

## Support

If you encounter issues:

1. Check the MQTT broker logs: `docker logs <mqtt_container_name>`
2. Verify network connectivity
3. Test with a simple MQTT client like `mosquitto_pub`/`mosquitto_sub`
4. Check the script output for error messages

