#! /usr/bin/env python

import asyncio
from bleak import BleakScanner, BleakClient

async def main():
    devices = await BleakScanner.discover()
    for d in devices:
        print(d)

asyncio.run(main())
