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
        except ValueError:
            print("Invalid input. Please enter a valid integer.")
            continue

        client = AsyncModbusTcpClient(ip, port=port)
        await client.connect()

        if not client.connected:
            print("Failed to connect to Modbus server. Retrying...")
            await client.close()
            continue

        result = await client.write_registers(address=0, values=[value])

        if result.isError():
            print("Write failed:", result)
        else:
            print(f"Write successful: Wrote value {value} to register")

        await client.close()

if __name__ == "__main__":
    asyncio.run(write_holding_registers(ip="127.0.0.1", port=5021))