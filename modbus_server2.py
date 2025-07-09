import asyncio
from pymodbus.server import StartAsyncTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext

async def run_modbus_server():
    # Create a holding register block with 10 values initialized to 0
    store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0]*10))
    context = ModbusServerContext(slaves=store, single=True)

    # Start server on all interfaces, port 5020
    await StartAsyncTcpServer(context=context, address=("0.0.0.0", 5021))

if __name__ == "__main__":
    asyncio.run(run_modbus_server())
