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

# Font character codes - hex-encoded 11-byte bitmaps for each character
CHAR_CODES = {
    "0": "007CC6CEDEF6E6C6C67C00",
    "1": "0018387818181818187E00",
    "2": "007CC6060C183060C6FE00",
    "3": "007CC606063C0606C67C00",
    "4": "000C1C3C6CCCFE0C0C1E00",
    "5": "00FEC0C0FC060606C67C00",
    "6": "007CC6C0C0FCC6C6C67C00",
    "7": "00FEC6060C183030303000",
    "8": "007CC6C6C67CC6C6C67C00",
    "9": "007CC6C6C67E0606C67C00",
    "#": "006C6CFE6C6CFE6C6C0000",
    "&": "00386C6C3876DCCCCC7600",
    "_": "00000000000000000000FF",
    "-": "0000000000FE0000000000",
    "?": "007CC6C60C181800181800",
    "@": "00003C429DA5ADB6403C00",
    "(": "000C183030303030180C00",
    ")": "0030180C0C0C0C0C183000",
    "=": "0000007E00007E00000000",
    "+": "00000018187E1818000000",
    "!": "00183C3C3C181800181800",
    "'": "1818081000000000000000",
    ":": "0000001818000018180000",
    "%": "006092966C106CD2920C00",
    "/": "000002060C183060C08000",
    '"': "6666222200000000000000",
    "[": "003C303030303030303C00",
    "]": "003C0C0C0C0C0C0C0C3C00",
    " ": "0000000000000000000000",
    "*": "000000663CFF3C66000000",
    ",": "0000000000000030301020",
    ".": "0000000000000000303000",
    "$": "107CD6D6701CD6D67C1010",
    "~": "0076DC0000000000000000",
    "{": "000E181818701818180E00",
    "}": "00701818180E1818187000",
    "<": "00060C18306030180C0600",
    ">": "006030180C060C18306000",
    "^": "386CC60000000000000000",
    "`": "1818100800000000000000",
    ";": "0000001818000018180810",
    "\\": "0080C06030180C06020000",
    "|": "0018181818001818181800",
    "a": "00000000780C7CCCCC7600",
    "b": "00E060607C666666667C00",
    "c": "000000007CC6C0C0C67C00",
    "d": "001C0C0C7CCCCCCCCC7600",
    "e": "000000007CC6FEC0C67C00",
    "f": "001C363078303030307800",
    "g": "00000076CCCCCC7C0CCC78",
    "h": "00E060606C76666666E600",
    "i": "0018180038181818183C00",
    "j": "0C0C001C0C0C0C0CCCCC78",
    "k": "00E06060666C78786CE600",
    "l": "0038181818181818183C00",
    "m": "00000000ECFED6D6D6C600",
    "n": "00000000DC666666666600",
    "o": "000000007CC6C6C6C67C00",
    "p": "000000DC6666667C6060F0",
    "q": "0000007CCCCCCC7C0C0C1E",
    "r": "00000000DE76606060F000",
    "s": "000000007CC6701CC67C00",
    "t": "00103030FC303030341800",
    "u": "00000000CCCCCCCCCC7600",
    "v": "00000000C6C6C66C381000",
    "w": "00000000C6D6D6D6FE6C00",
    "x": "00000000C66C38386CC600",
    "y": "000000C6C6C6C67E060CF8",
    "z": "00000000FE8C183062FE00",
    "A": "00386CC6C6FEC6C6C6C600",
    "B": "00FC6666667C666666FC00",
    "C": "007CC6C6C0C0C0C6C67C00",
    "D": "00FC66666666666666FC00",
    "E": "00FE66626878686266FE00",
    "F": "00FE66626878686060F000",
    "G": "007CC6C6C0C0CEC6C67E00",
    "H": "00C6C6C6C6FEC6C6C6C600",
    "I": "003C181818181818183C00",
    "J": "001E0C0C0C0C0CCCCC7800",
    "K": "00E6666C6C786C6C66E600",
    "L": "00F060606060606266FE00",
    "M": "0082C6EEFED6C6C6C6C600",
    "N": "0086C6E6F6DECEC6C6C600",
    "O": "007CC6C6C6C6C6C6C67C00",
    "P": "00FC6666667C606060F000",
    "Q": "007CC6C6C6C6C6D6DE7C06",
    "R": "00FC6666667C6C6666E600",
    "S": "007CC6C660380CC6C67C00",
    "T": "007E7E5A18181818183C00",
    "U": "00C6C6C6C6C6C6C6C67C00",
    "V": "00C6C6C6C6C6C66C381000",
    "W": "00C6C6C6C6D6FEEEC68200",
    "X": "00C6C66C7C387C6CC6C600",
    "Y": "00666666663C1818183C00",
    "Z": "00FEC6860C183062C6FE00",
    "Á": "0810386cc6c6fec6c6c600",
    "À": "2010386cc6c6fec6c6c600",
    "Â": "1028386CC6C6FEC6C6C600",
    "Ä": "2800386CC6C6FEC6C6C600",
    "Å": "1028107CC6C6FEC6C6C600",
    "É": "0810FE626878686266FE00",
    "È": "2010FE626878686266FE00",
    "Ê": "1028FE626878686266FE00",
    "Ë": "2800FE626878686266FE00",
    "Ě": "2810FE626878686266FE00",
    "Í": "04083C1818181818183C00",
    "Ì": "10083C1818181818183C00",
    "Î": "08143C1818181818183C00",
    "Ï": "14003C1818181818183C00",
    "Ó": "08107CC6C6C6C6C6C67C00",
    "Ò": "20107CC6C6C6C6C6C67C00",
    "Ô": "10287CC6C6C6C6C6C67C00",
    "Ö": "28007CC6C6C6C6C6C67C00",
    "Ő": "14287CC6C6C6C6C6C67C00",
    "Ú": "0810C6C6C6C6C6C6C67C00",
    "Ù": "2010C6C6C6C6C6C6C67C00",
    "Û": "1028C6C6C6C6C6C6C67C00",
    "Ü": "2800C6C6C6C6C6C6C67C00",
    "Ű": "1428C6C6C6C6C6C6C67C00",
    "Ů": "102810C6C6C6C6C6C67C00",
    "Ý": "04086666663C1818183C00",
    "Ÿ": "14006666663C1818183C00",
    "á": "00000810780C7CCCCC7600",
    "à": "00002010780C7CCCCC7600",
    "â": "00102800780C7CCCCC7600",
    "ä": "00002800780C7CCCCC7600",
    "å": "00102810780C7CCCCC7600",
    "é": "000008107CC6FEC0C67C00",
    "è": "000020107CC6FEC0C67C00",
    "ê": "001028007CC6FEC0C67C00",
    "ë": "000028007CC6FEC0C67C00",
    "ě": "000028107CC6FEC0C67C00",
    "í": "0000081038181818183C00",
    "ì": "0000201038181818183C00",
    "î": "0008140038181818183C00",
    "ï": "0000140038181818183C00",
    "ó": "000008107CC6C6C6C67C00",
    "ò": "000020107CC6C6C6C67C00",
    "ô": "001028007CC6C6C6C67C00",
    "ö": "000028007CC6C6C6C67C00",
    "ő": "000014287CC6C6C6C67C00",
    "ú": "00000810CCCCCCCCCC7600",
    "ù": "00002010CCCCCCCCCC7600",
    "û": "00102800CCCCCCCCCC7600",
    "ü": "00002800CCCCCCCCCC7600",
    "ű": "00001428CCCCCCCCCC7600",
    "ů": "00102810CCCCCCCCCC7600",
    "ý": "000810C6C6C6C67E060CF8",
    "ÿ": "002800C6C6C6C67E060CF8",
    "Ç": "007CC6C6C0C0C0C67C1030",
    "ç": "000000007CC6C0467C1030",
    "Ñ": "342CC6E6F6DECEC6C6C600",
    "ñ": "00342C00DC666666666600",
    "Č": "28107CC6C6C0C0C6C67C00",
    "č": "000028107CC6C0C0C67C00",
    "Ď": "2810FC666666666666FC00",
    "ď": "02061C0C7CCCCCCCCC7600",
    "Ň": "2810C6E6F6DECEC6C6C600",
    "ň": "00002810DC666666666600",
    "Ř": "2810FC66667C6C6666E600",
    "ř": "00002810DE76606060F000",
    "Š": "28107CC6E0380CC6C67C00",
    "š": "000028107CC6701CC67C00",
    "Ť": "14087E7E5A181818183C00",
    "ť": "00143430FC303030341800",
    "Ž": "2810FE860C183062C6FE00",
    "ž": "00002810FE8C183062FE00",
}

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
    message_text = ' '.join(args.message)

    # First, replace :icon: patterns with their control characters
    import re
    def replace_icon(m):
        name = m.group(1)
        if name == '':
            return ':'
        if name in BITMAP_NAMED:
            return BITMAP_NAMED[name][2]
        # Unknown icon - keep as literal
        return ':' + name + ':'

    processed_text = re.sub(r':([^:]*):', replace_icon, message_text)

    # Now convert each character to hex using CHAR_CODES
    message_hex_parts = []
    cols = 0
    for ch in processed_text:
        if ord(ch) < 32 and ch != ' ':
            # Control character (icon) - get from BITMAP_BUILTIN
            from badge_common import BITMAP_BUILTIN
            if ch in BITMAP_BUILTIN:
                bitmap_data = BITMAP_BUILTIN[ch][0]
                message_hex_parts.append(bytes_to_hex_string(bitmap_data))
                cols += BITMAP_BUILTIN[ch][1]
        elif ch in CHAR_CODES:
            message_hex_parts.append(CHAR_CODES[ch])
            cols += 1
        else:
            # Unknown character - use space
            message_hex_parts.append(CHAR_CODES[" "])
            cols += 1

    message_hex = "".join(message_hex_parts)

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
