# SPDX-License-Identifier: MIT
# Copyright (c) 2025 David Lechner <dlechner@baylibre.com>
#
# /// script
# dependencies = [
#   "bleak",
#   "pillow",
# ]
# ///

# https://gist.github.com/dlech/24e71cd18ef46ec0c3ad94ffa0fef49a

"""
Simple script to send messages to a LSLED badge over BLE.

Run with:
    uv run --script badgemagic.py

Supports embedded icons using :icon: syntax. Examples:
    uv run --script bt-magic.py "Hello :heart: World"
    uv run --script bt-magic.py "Logo :gfx/logo.png: here"
    uv run --script bt-magic.py -l  # list available builtin icons
"""

import asyncio
import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from bleak import BleakClient, BleakScanner

from badge_common import BadgeTextParser, BITMAP_NAMED, bytes_to_hex_string

LSLED_CHAR_UUID = "0000fee1-0000-1000-8000-00805f9b34fb"

MAX_MESSAGES = 8
PACKET_START = "77616E670000"
PACKET_BYTE_SIZE = 16


class Speed(IntEnum):
    ONE = 0x00
    TWO = 0x10
    THREE = 0x20
    FOUR = 0x30
    FIVE = 0x40
    SIX = 0x50
    SEVEN = 0x60
    EIGHT = 0x70

def speedtype(number):
    try:
        return Speed[number.upper()]
    except KeyError:
        msg = ', '.join([t.name.lower() for t in Speed])
        raise argparse.ArgumentTypeError(f"Invalid choice: '{number}'. Use one of: {msg}")

class Mode(IntEnum):
    LEFT = 0x00
    RIGHT = 0x01
    UP = 0x02
    DOWN = 0x03
    FIXED = 0x04
    ANIMATION = 0x05
    SNOWFLAKE = 0x06
    PICTURE = 0x07
    LASER = 0x08
    # from here animations don't seem to work
    PACMAN = 0x09
    CHEVRONLEFT = 0x0A
    DIAMOND = 0x0B
    FEET = 0x0C
    BROKENHEARTS = 0x0D
    CUPID = 0x0E
    CYCLE = 0x0F

def modetype(astring):
    try:
        return Mode[astring.upper()]
    except KeyError:
        msg = ', '.join([t.name.lower() for t in Mode])
        raise argparse.ArgumentTypeError(f"Invalid choice: '{astring}'. Use one of: {msg}")

@dataclass(frozen=True)
class Message:
    text: str  # Raw text with :icon: syntax
    text_hex: str  # Hex-encoded bitmap data
    text_cols: int  # Number of bitmap columns (for size calculation)
    flash: bool
    marquee: bool
    speed: Speed
    mode: Mode
    animation_index: int | None = None


@dataclass(frozen=True)
class Data:
    messages: list[Message]


def get_flash(data: Data) -> str:
    flash_byte = 0
    for idx, message in enumerate(data.messages):
        flash_flag = 1 if message.flash else 0
        flash_byte |= (flash_flag << idx) & 0xFF
    return f"{flash_byte:02x}"


def get_marquee(data: Data) -> str:
    marquee_byte = 0
    for idx, message in enumerate(data.messages):
        marquee_flag = 1 if message.marquee else 0
        marquee_byte |= (marquee_flag << idx) & 0xFF
    return f"{marquee_byte:02x}"


def get_options(data: Data) -> str:
    opt_str = ["00"] * MAX_MESSAGES

    for idx, message in enumerate(data.messages):
        opt_str[idx] = f"{(message.speed | message.mode):02x}"

    return "".join(opt_str)


def get_sizes(data: Data) -> str:
    size_str = ["0000"] * MAX_MESSAGES

    for idx, message in enumerate(data.messages):
        size_str[idx] = f"{message.text_cols:04x}"

    return "".join(size_str)


def get_time(now: datetime) -> str:
    return f"{now.year % 100:02x}{now.month:02x}{now.day:02x}{now.hour:02x}{now.minute:02x}{now.second:02x}"


def get_message(data: Data) -> str:
    return "".join(message.text_hex for message in data.messages)


def convert(data: Data) -> list[bytes]:
    assert len(data.messages) <= MAX_MESSAGES, f"Max messages={MAX_MESSAGES}"
    import datetime

    message = (
        f"{PACKET_START}"
        f"{get_flash(data)}"
        f"{get_marquee(data)}"
        f"{get_options(data)}"
        f"{get_sizes(data)}"
        "000000000000"
        f"{get_time(datetime.datetime.now())}"
        "0000000000000000000000000000000000000000"
        f"{get_message(data)}"
    )
    message += "00" * (
        (PACKET_BYTE_SIZE - (len(message) // 2) % PACKET_BYTE_SIZE) % PACKET_BYTE_SIZE
    )
    chunk_size = PACKET_BYTE_SIZE * 2
    chunks = [message[i : i + chunk_size] for i in range(0, len(message), chunk_size)]
    return [bytes.fromhex(chunk) for chunk in chunks]


async def main(data: Data):
    # try this first so that it can fail early before connecting to the device
    chunks = convert(data)

    print("Scanning for LSLED device...")
    device = await BleakScanner.find_device_by_name("LSLED")
    if device is None:
        print("Device not found")
        return

    print("Found LSLED, connecting...")
    async with BleakClient(device) as client:
        for chunk in chunks:
            await client.write_gatt_char(LSLED_CHAR_UUID, chunk, response=True)

    print("All data sent!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='bt-magic',
                    description='Change the display of your LED badge via Bluetooth',
                    epilog='Examples:\n'
                           '  %(prog)s "Hello :heart: World"\n'
                           '  %(prog)s "Logo :gfx/logo.png: here"\n'
                           '  %(prog)s -l  # list available builtin icons',
                    formatter_class=argparse.RawDescriptionHelpFormatter,
                    )
    parser.add_argument('-f', '--flash', action='store_true', help='Enable flash effect')
    parser.add_argument('-m', '--marquee', action='store_true', help='Enable marquee scrolling')
    parser.add_argument('-a', '--animation', type=modetype, default=Mode.FIXED,
                        help='Animation mode (default: fixed)')
    parser.add_argument('-s', '--speed', type=speedtype, default=Speed.FOUR,
                        help='Scroll speed (default: four)')
    parser.add_argument('-l', '--list-icons', action='store_true',
                        help='List available builtin icons and exit')
    parser.add_argument('message', nargs='*', default=None,
                        help='Message text with optional :icon: syntax')
    args = parser.parse_args()

    if args.list_icons:
        print("Available builtin icons:")
        for icon_name in sorted(BITMAP_NAMED.keys()):
            print(f"  :{icon_name}:")
        print("\nUsage examples:")
        print('  uv run --script bt-magic.py "Hello :heart: World"')
        print('  uv run --script bt-magic.py "Logo :gfx/logo.png: here"')
        sys.exit(0)

    # Parse message text with :icon: syntax
    parser_obj = BadgeTextParser()
    message_text = ' '.join(args.message)
    bitmap_data, cols = parser_obj.parse_text(message_text)
    message_hex = bytes_to_hex_string(bitmap_data)

    sample_data = Data(
        messages=[
            Message(
                text=message_text,
                text_hex=message_hex,
                text_cols=cols,
                flash=args.flash,
                marquee=args.marquee,
                speed=args.speed,
                mode=args.animation,
            ),
        ]
    )
    asyncio.run(main(sample_data))
