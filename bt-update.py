#! /usr/bin/env python
import sys
import asyncio
from bleak import BleakClient

ADDRESS = "51F61396-51B3-EDE5-56B3-FBA716A5A861"
FEE1_CHARACTERISTIC = "0000fee1-0000-1000-8000-00805f9b34fb"

WRITE_REQUESTS = [
    "77616E67000000000000000000000000",
    "00050000000000000000000000000000",
    "000000000000E10C06172D2300000000",
    "00000000000000000000000000000000",
    "00C6C6C6C6FEC6C6C6C600000000007C",
    "C6FEC0C67C000038181818181818183C",
    "000038181818181818183C0000000000",
    "7CC6C6C6C67C00000000000000000000"
]

async def main(address):
    async with BleakClient(ADDRESS) as client:
        print(f"Connected: {client.is_connected}")
        for i in range (0, len(WRITE_REQUESTS)):
            byte_array = bytes.fromhex(WRITE_REQUESTS[i])
            await client.write_gatt_char(FEE1_CHARACTERISTIC, byte_array, response=True)
            print(f"Written bytearray: {str(byte_array)}")

asyncio.run(main(ADDRESS))
