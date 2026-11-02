"""
FFBeast Linux Control Suite
Open-source Linux driver and configuration system for FFBeast force feedback devices.
"""

from .protocol import (
    USB_VID,
    WHEEL_PID_FS,
    JOYSTICK_PID_FS,
    RUDDER_PID_FS,
    SettingsFieldEnum,
    PinModeEnum,
    ButtonModeEnum,
    AmplifierGainEnum,
)
from .client import FFBeastDevice
from .profile_manager import ProfileManager
from .iracing import find_iracing_ini_paths, optimize_iracing_ini, read_ini_section_values

__version__ = "1.0.0"

