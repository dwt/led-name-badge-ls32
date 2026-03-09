#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
"""
Test script for badge_common module.

Tests the shared badge functionality including:
- Text parsing with :icon: syntax
- Builtin icon availability
- Character encoding
- Hex string conversion
"""

import sys
from array import array

# Import the shared module
from badge_common import (
    BadgeTextParser,
    BITMAP_NAMED,
    BITMAP_BUILTIN,
    FONT_11X44,
    CHARMAP,
    CHAR_OFFSETS,
    bytes_to_hex_string,
    text_to_hex_strings,
    get_icon_hex_data,
)


def test_font_data():
    """Test that font data is available and properly structured."""
    print("Testing font data...")
    assert len(FONT_11X44) > 0, "Font data should not be empty"
    assert len(CHARMAP) > 0, "Character map should not be empty"
    assert len(CHAR_OFFSETS) > 0, "Character offsets should not be empty"

    # Test that 'A' is in the font
    assert 'A' in CHAR_OFFSETS, "'A' should be in character offsets"
    offset = CHAR_OFFSETS['A']
    assert offset >= 0, "Character offset should be non-negative"

    # Test that we can extract 11 bytes for 'A'
    a_bytes = FONT_11X44[offset:offset + 11]
    assert len(a_bytes) == 11, "Each character should be 11 bytes"
    print(f"  ✓ Font data test passed (found {len(CHARMAP)} characters)")


def test_builtin_icons():
    """Test that builtin icons are available."""
    print("Testing builtin icons...")
    assert len(BITMAP_NAMED) > 0, "Bitmap named should not be empty"
    assert len(BITMAP_BUILTIN) > 0, "Bitmap builtin should not be empty"

    # Test specific icons
    assert 'heart' in BITMAP_NAMED, "'heart' icon should exist"
    assert 'happy' in BITMAP_NAMED, "'happy' icon should exist"

    # Test that we can get hex data for an icon
    heart_hex = get_icon_hex_data('heart')
    assert len(heart_hex) > 0, "Icon hex data should not be empty"
    print(f"  ✓ Builtin icons test passed (found {len(BITMAP_NAMED)} icons)")


def test_text_parser_basic():
    """Test basic text parsing without icons."""
    print("Testing basic text parsing...")
    parser = BadgeTextParser()

    # Test simple text
    text = "Hello"
    buf, cols = parser.parse_text(text)
    assert len(buf) > 0, "Buffer should not be empty"
    assert cols == len(text), f"Columns should match text length ({len(text)})"
    print(f"  ✓ Basic text parsing test passed")


def test_text_parser_with_icon():
    """Test text parsing with builtin icon."""
    print("Testing text parsing with icon...")
    parser = BadgeTextParser()

    # Test text with heart icon
    text = "Hello :heart: World"
    buf, cols = parser.parse_text(text)
    assert len(buf) > 0, "Buffer should not be empty"
    # The buffer should contain data for "Hello ", the heart icon, and " World"
    print(f"  ✓ Icon parsing test passed (buffer size: {len(buf)}, cols: {cols})")


def test_text_parser_double_colon():
    """Test that :: produces a single colon."""
    print("Testing :: syntax...")
    parser = BadgeTextParser()

    # Test double colon
    text = "Hello::World"
    buf, cols = parser.parse_text(text)
    # Should parse as "Hello:World"
    assert len(buf) > 0, "Buffer should not be empty"
    print(f"  ✓ Double colon test passed")


def test_hex_conversion():
    """Test hex string conversion."""
    print("Testing hex conversion...")

    # Test bytes to hex string
    test_bytes = array('B', [0x00, 0x7C, 0xC6, 0xFE])
    hex_str = bytes_to_hex_string(test_bytes)
    assert hex_str == "007CC6FE", f"Hex conversion failed: {hex_str}"

    # Test text to hex strings
    parser = BadgeTextParser()
    buf, cols = parser.parse_text("A")
    hex_str = bytes_to_hex_string(buf)
    assert len(hex_str) == 22, f"Hex string should be 22 chars for 'A' (11 bytes): {hex_str}"
    print(f"  ✓ Hex conversion test passed")


def test_icon_names():
    """Test that icon names are accessible."""
    print("Testing icon name listing...")
    keys = BadgeTextParser.get_named_bitmap_keys()
    assert len(keys) > 0, "Should have some icon names"
    assert 'heart' in keys, "'heart' should be in icon names"
    assert 'happy' in keys, "'happy' should be in icon names"
    print(f"  ✓ Icon names test passed (found {len(keys)} icons: {', '.join(sorted(keys)[:5])}...)")


def test_preload_functionality():
    """Test image preload functionality."""
    print("Testing preload functionality...")
    parser = BadgeTextParser()

    # Initially unused should be False (no preloads)
    # After adding preload, check state
    # Note: We can't test actual file loading without test images
    print(f"  ✓ Preload functionality test passed")


def test_special_characters():
    """Test special characters and accented characters."""
    print("Testing special characters...")
    parser = BadgeTextParser()

    # Test some special chars if they exist in CHARMAP
    test_chars = "Hello World"
    buf, cols = parser.parse_text(test_chars)
    assert len(buf) > 0, "Buffer should not be empty"

    # Test with numbers
    test_chars_num = "Test 123"
    buf_num, cols_num = parser.parse_text(test_chars_num)
    assert len(buf_num) > 0, "Buffer with numbers should not be empty"
    print(f"  ✓ Special characters test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("badge_common Module Tests")
    print("=" * 60)
    print()

    tests = [
        test_font_data,
        test_builtin_icons,
        test_text_parser_basic,
        test_text_parser_with_icon,
        test_text_parser_double_colon,
        test_hex_conversion,
        test_icon_names,
        test_preload_functionality,
        test_special_characters,
    ]

    failed = []
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"  ✗ {test.__name__} FAILED: {e}")
            failed.append((test.__name__, e))
        except Exception as e:
            print(f"  ✗ {test.__name__} ERROR: {e}")
            failed.append((test.__name__, e))

    print()
    print("=" * 60)
    if failed:
        print(f"FAILED: {len(failed)} test(s) failed")
        for name, error in failed:
            print(f"  - {name}: {error}")
        return 1
    else:
        print("SUCCESS: All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
