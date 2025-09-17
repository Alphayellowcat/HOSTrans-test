import importlib
import pathlib
import sys
from unittest.mock import Mock, patch

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


@pytest.fixture
def memory_utils():
    """Import memory_utils with kernel32 mocked to work on non-Windows systems."""
    if "src.memory_utils" in sys.modules:
        del sys.modules["src.memory_utils"]

    sys.modules.setdefault("psutil", Mock())

    with patch("ctypes.WinDLL", create=True) as win_dll_mock:
        kernel32_mock = Mock()
        kernel32_mock.VirtualQueryEx = Mock(return_value=0)
        win_dll_mock.return_value = kernel32_mock
        module = importlib.import_module("src.memory_utils")

    return module


def _install_fake_reader(monkeypatch, module, memory_bytes):
    base_address = 0

    def fake_read(_handle, address, size):
        start = address - base_address
        end = start + size
        if start < 0:
            raise ValueError("Invalid read start position")

        if start >= len(memory_bytes):
            return b"\x00" * size

        chunk = memory_bytes[start:end]
        if len(chunk) < size:
            chunk = chunk + b"\x00" * (size - len(chunk))
        return chunk

    monkeypatch.setattr(module, "read_process_memory", fake_read)
    return base_address


def test_read_string_utf8(memory_utils, monkeypatch):
    text = "聊天记录"
    encoded = text.encode("utf-8") + b"\x00"
    base_address = _install_fake_reader(monkeypatch, memory_utils, encoded)

    result = memory_utils.read_string(None, base_address, max_length=len(encoded), encoding_format="utf-8")

    assert result == text


def test_read_string_utf16_le(memory_utils, monkeypatch):
    text = "聊天记录"
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    base_address = _install_fake_reader(monkeypatch, memory_utils, encoded)

    result = memory_utils.read_string(None, base_address, max_length=len(encoded), encoding_format="utf-16-le")

    assert result == text


def test_read_string_unknown_encoding_fallback(memory_utils, monkeypatch):
    text = "聊天记录"
    encoded = text.encode("utf-8") + b"\x00"
    base_address = _install_fake_reader(monkeypatch, memory_utils, encoded)

    result = memory_utils.read_string(None, base_address, max_length=len(encoded), encoding_format="unknown-encoding")

    assert result == text
