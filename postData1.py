from pymodbus.client import AsyncModbusTcpClient
import asyncio

async def write_holding_registers(ip="10.160.0.157", port=5021):
    while True:
        # Get user input for the value
        try:
            value = int(input("Enter the value to write to the holding register (0-65535, or -1 to exit): "))
            if value == -1:
                print("Exiting...")
                break
            if not 0 <= value <= 65535:
                print("Value must be between 0 and 65535")
                continue
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
            continue

        client = None
        try:
            client = AsyncModbusTcpClient(ip, port=port)
            await client.connect()

            if not client.connected:
                print("Failed to connect to Modbus server. Retrying...")
                continue

            result = await client.write_registers(address=0, values=[value])

            if result.isError():
                print("Write failed:", result)
            else:
                print(f"Write successful: Wrote value {value} to register")

        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            # Only close the client if it exists and is connected
            if client is not None and hasattr(client, 'close'):
                try:
                    if client.connected:
                        close_result = await client.close()
                        if close_result is not None:
                            await close_result
                except Exception as e:
                    # Silently ignore closing errors as they're not critical
                    pass

if __name__ == "__main__":
    asyncio.run(write_holding_registers(ip="127.0.0.1", port=5021))