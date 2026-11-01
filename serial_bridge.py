# serial_bridge.py
import asyncio
import json
import serial
from config import CFG

async def serial_reader(queue: asyncio.Queue, loop):
    try:
        ser = serial.Serial(CFG.serial_port, CFG.baud_rate, timeout=1)
        print(f"✅ 串口 {CFG.serial_port} 已打开")
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    data = json.loads(line)
                    asyncio.run_coroutine_threadsafe(queue.put(data), loop)
                except json.JSONDecodeError:
                    pass
    except serial.SerialException as e:
        print(f"❌ 串口错误: {e}")