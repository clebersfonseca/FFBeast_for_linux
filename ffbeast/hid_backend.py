"""
Native Linux HIDAPI backend using ctypes to interface with libhidapi-hidraw.so.0.
Works seamlessly across Fedora, Debian/Ubuntu, Arch, openSUSE without pip compilations.
"""

import ctypes
import os
import sys
from typing import List, Optional, Dict, Any


class hid_device_info(ctypes.Structure):
    pass


hid_device_info._fields_ = [
    ("path", ctypes.c_char_p),
    ("vendor_id", ctypes.c_ushort),
    ("product_id", ctypes.c_ushort),
    ("serial_number", ctypes.c_wchar_p),
    ("release_number", ctypes.c_ushort),
    ("manufacturer_string", ctypes.c_wchar_p),
    ("product_string", ctypes.c_wchar_p),
    ("usage_page", ctypes.c_ushort),
    ("usage", ctypes.c_ushort),
    ("interface_number", ctypes.c_int),
    ("next", ctypes.POINTER(hid_device_info)),
]


def load_hidapi():
    """Attempt loading system libhidapi-hidraw or fallback to libhidapi-libusb."""
    candidates = [
        "libhidapi-hidraw.so.0",
        "libhidapi-hidraw.so",
        "libhidapi-libusb.so.0",
        "libhidapi-libusb.so",
        "libhidapi.so",
    ]
    for candidate in candidates:
        try:
            lib = ctypes.cdll.LoadLibrary(candidate)
            return lib
        except OSError:
            continue
    raise RuntimeError(
        "Could not load libhidapi. Please install hidapi (e.g., 'sudo dnf install hidapi')."
    )


_lib = load_hidapi()

# Function signatures
_lib.hid_init.restype = ctypes.c_int
_lib.hid_exit.restype = ctypes.c_int

_lib.hid_enumerate.restype = ctypes.POINTER(hid_device_info)
_lib.hid_enumerate.argtypes = [ctypes.c_ushort, ctypes.c_ushort]

_lib.hid_free_enumeration.restype = None
_lib.hid_free_enumeration.argtypes = [ctypes.POINTER(hid_device_info)]

_lib.hid_open.restype = ctypes.c_void_p
_lib.hid_open.argtypes = [ctypes.c_ushort, ctypes.c_ushort, ctypes.c_wchar_p]

_lib.hid_open_path.restype = ctypes.c_void_p
_lib.hid_open_path.argtypes = [ctypes.c_char_p]

_lib.hid_write.restype = ctypes.c_int
_lib.hid_write.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]

_lib.hid_read_timeout.restype = ctypes.c_int
_lib.hid_read_timeout.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_size_t,
    ctypes.c_int,
]

_lib.hid_read.restype = ctypes.c_int
_lib.hid_read.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]

_lib.hid_set_nonblocking.restype = ctypes.c_int
_lib.hid_set_nonblocking.argtypes = [ctypes.c_void_p, ctypes.c_int]

_lib.hid_send_feature_report.restype = ctypes.c_int
_lib.hid_send_feature_report.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_size_t,
]

_lib.hid_get_feature_report.restype = ctypes.c_int
_lib.hid_get_feature_report.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.c_uint8),
    ctypes.c_size_t,
]

_lib.hid_close.restype = None
_lib.hid_close.argtypes = [ctypes.c_void_p]

_lib.hid_error.restype = ctypes.c_wchar_p
_lib.hid_error.argtypes = [ctypes.c_void_p]

_lib.hid_init()


class HidDevice:
    """Wrapper around an open hid_device pointer."""

    def __init__(self, handle: ctypes.c_void_p, path: bytes, info: Dict[str, Any]):
        self._handle = handle
        self.path = path
        self.info = info

    def is_open(self) -> bool:
        return self._handle is not None

    def close(self):
        if self._handle:
            _lib.hid_close(self._handle)
            self._handle = None

    def write(self, data: bytes) -> int:
        if not self._handle:
            return -1
        buf = (ctypes.c_uint8 * len(data))(*data)
        return _lib.hid_write(self._handle, buf, len(data))

    def read_timeout(self, length: int, timeout_ms: int = 100) -> bytes:
        if not self._handle:
            return b""
        buf = (ctypes.c_uint8 * length)()
        res = _lib.hid_read_timeout(self._handle, buf, length, timeout_ms)
        if res < 0:
            return b""
        return bytes(buf[:res])

    def get_feature_report(self, report_id: int, length: int) -> bytes:
        if not self._handle:
            return b""
        buf = (ctypes.c_uint8 * length)()
        buf[0] = report_id
        res = _lib.hid_get_feature_report(self._handle, buf, length)
        if res < 0:
            return b""
        return bytes(buf[:res])

    def send_feature_report(self, data: bytes) -> int:
        if not self._handle:
            return -1
        buf = (ctypes.c_uint8 * len(data))(*data)
        return _lib.hid_send_feature_report(self._handle, buf, len(data))

    def get_error(self) -> str:
        if not self._handle:
            return "Device not open"
        err = _lib.hid_error(self._handle)
        return err or ""

    def __del__(self):
        self.close()


def enumerate_devices(vendor_id: int = 0, product_id: int = 0) -> List[Dict[str, Any]]:
    """Enumerate connected HID devices."""
    devices = []
    devs = _lib.hid_enumerate(vendor_id, product_id)
    cur = devs
    while cur:
        c = cur.contents
        devices.append({
            "path": c.path,
            "vendor_id": c.vendor_id,
            "product_id": c.product_id,
            "serial_number": c.serial_number or "",
            "release_number": c.release_number,
            "manufacturer_string": c.manufacturer_string or "",
            "product_string": c.product_string or "",
            "usage_page": c.usage_page,
            "usage": c.usage,
            "interface_number": c.interface_number,
        })
        cur = c.next
    _lib.hid_free_enumeration(devs)
    return devices


def open_device_path(path: bytes, info: Optional[Dict[str, Any]] = None) -> Optional[HidDevice]:
    """Open device by its sysfs path."""
    handle = _lib.hid_open_path(path)
    if not handle:
        return None
    return HidDevice(handle, path, info or {})
