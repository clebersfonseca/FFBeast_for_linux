"""
FFBeast USB Communication Protocol Definitions.
Direct 1:1 mapping of C structs and enums from official FFBeast firmware.
"""

import ctypes
from enum import IntEnum

# Device USB Identifiers
USB_VID = 1115          # 0x045B
WHEEL_PID_FS = 22999    # 0x59D7
JOYSTICK_PID_FS = 22888 # 0x5968
RUDDER_PID_FS = 22777   # 0x58F9

DFU_VID = 0x0483
DFU_PID = 0xDF11

# USB Interfaces
INTERFACE_VENDOR = 0
INTERFACE_JOYSTICK = 1


class SettingsFieldEnum(IntEnum):
    DIRECT_X_CONSTANT_DIRECTION = 0
    DIRECT_X_SPRING_STRENGTH = 1
    DIRECT_X_CONSTANT_STRENGTH = 2
    DIRECT_X_PERIODIC_STRENGTH = 3
    TOTAL_EFFECT_STRENGTH = 4
    MOTION_RANGE = 5
    SOFT_STOP_STRENGTH = 6
    SOFT_STOP_RANGE = 7
    STATIC_DAMPENING_STRENGTH = 8
    SOFT_STOP_DAMPENING_STRENGTH = 9
    DYNAMIC_DAMPENING_STRENGTH = 10
    FORCE_ENABLED = 11
    DEBUG_TORQUE = 12
    AMPLIFIER_GAIN = 13
    CALIBRATION_MAGNITUDE = 15
    CALIBRATION_SPEED = 16
    POWER_LIMIT = 17
    BRAKING_LIMIT = 18
    POSITION_SMOOTHING = 19
    SPEED_BUFFER_SIZE = 20
    ENCODER_DIRECTION = 21
    FORCE_DIRECTION = 22
    POLE_PAIRS = 23
    ENCODER_CPR = 24
    P_GAIN = 25
    I_GAIN = 26
    EXTENSION_MODE = 27
    PIN_MODE = 28
    BUTTON_MODE = 29
    SPI_MODE = 30
    SPI_LATCH_MODE = 31
    SPI_LATCH_DELAY = 32
    SPI_CLK_PULSE_LENGTH = 33
    ADC_MIN_DEAD_ZONE = 34
    ADC_MAX_DEAD_ZONE = 35
    ADC_TO_BUTTON_LOW = 36
    ADC_TO_BUTTON_HIGH = 37
    ADC_SMOOTHING = 38
    ADC_INVERT = 39
    RESET_CENTER_ON_Z0 = 41
    INTEGRATED_SPRING_STRENGTH = 43


class PinModeEnum(IntEnum):
    NONE = 0
    GPIO = 1
    ANALOG = 2
    SPI_CS = 3
    SPI_SCK = 4
    SPI_MISO = 5
    ENABLE_EFFECTS = 6
    CENTER_RESET = 7
    BRAKING_PWM = 8
    EFFECT_LED = 9
    REBOOT = 10


PIN_MODE_NAMES = {
    PinModeEnum.NONE: "Disabled",
    PinModeEnum.GPIO: "Generic Button",
    PinModeEnum.ANALOG: "Analog (ADC)",
    PinModeEnum.SPI_CS: "SPI CS",
    PinModeEnum.SPI_SCK: "SPI SCK",
    PinModeEnum.SPI_MISO: "SPI MISO",
    PinModeEnum.ENABLE_EFFECTS: "Enable Effects Switch",
    PinModeEnum.CENTER_RESET: "Center Reset Button",
    PinModeEnum.BRAKING_PWM: "Braking PWM Output",
    PinModeEnum.EFFECT_LED: "Effect LED (Reserved)",
    PinModeEnum.REBOOT: "Reboot Controller Button",
}


class ButtonModeEnum(IntEnum):
    NONE = 0
    NORMAL = 1
    INVERTED = 2
    PULSE = 3
    PULSE_INVERTED = 4


BUTTON_MODE_NAMES = {
    ButtonModeEnum.NONE: "Disabled",
    ButtonModeEnum.NORMAL: "Normal",
    ButtonModeEnum.INVERTED: "Inverted",
    ButtonModeEnum.PULSE: "Pulse (Not Implemented)",
    ButtonModeEnum.PULSE_INVERTED: "Pulse Inverted",
}


class AmplifierGainEnum(IntEnum):
    GAIN_80 = 0
    GAIN_40 = 1
    GAIN_20 = 2
    GAIN_10 = 3


AMPLIFIER_GAIN_NAMES = {
    AmplifierGainEnum.GAIN_80: "80x",
    AmplifierGainEnum.GAIN_40: "40x",
    AmplifierGainEnum.GAIN_20: "20x",
    AmplifierGainEnum.GAIN_10: "10x",
}


class SpiModeEnum(IntEnum):
    SPI_MODE_0 = 0
    SPI_MODE_1 = 1
    SPI_MODE_2 = 2
    SPI_MODE_3 = 3


class SpiLatchModeEnum(IntEnum):
    LATCH_MODE_UP = 0
    LATCH_MODE_DOWN = 1


class ReportDataEnum(IntEnum):
    DATA_COMMAND_REBOOT = 0x01
    DATA_COMMAND_SAVE_SETTINGS = 0x02
    DATA_COMMAND_DFU_MODE = 0x03
    DATA_COMMAND_RESET_CENTER = 0x04
    DATA_OVERRIDE_DATA = 0x10
    DATA_FIRMWARE_ACTIVATION_DATA = 0x13
    DATA_SETTINGS_FIELD_DATA = 0x14


class ReportTypeEnum(IntEnum):
    REPORT_JOYSTICK_INPUT = 0x01
    REPORT_CREATE_NEW_EFFECT = 0x11
    REPORT_PID_BLOCK_LOAD = 0x12
    REPORT_PID_POOL = 0x13
    REPORT_SET_EFFECT = 0x11
    REPORT_SET_ENVELOPE = 0x12
    REPORT_SET_CONDITION = 0x13
    REPORT_SET_PERIODIC = 0x14
    REPORT_SET_CONSTANT_FORCE = 0x15
    REPORT_SET_RAMP_FORCE = 0x16
    REPORT_EFFECT_OPERATION = 0x1A
    REPORT_PID_STATE = 0x12
    REPORT_PID_BLOCK_FREE = 0x1B
    REPORT_PID_DEVICE_CONTROL = 0x1C
    REPORT_DEVICE_GAIN = 0x1D
    REPORT_HARDWARE_SETTINGS_FEATURE = 0x21
    REPORT_EFFECT_SETTINGS_FEATURE = 0x22
    REPORT_FIRMWARE_LICENSE_FEATURE = 0x25
    REPORT_GPIO_SETTINGS_FEATURE = 0xA1
    REPORT_ADC_SETTINGS_FEATURE = 0xA2
    REPORT_GENERIC_INPUT_OUTPUT = 0xA3


# CTypes Structures (Packed 1 byte)

class FirmwareVersionTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReleaseType", ctypes.c_uint8),
        ("ReleaseMajor", ctypes.c_uint8),
        ("ReleaseMinor", ctypes.c_uint8),
        ("ReleasePatch", ctypes.c_uint8),
    ]

    def to_string(self) -> str:
        rel = "RC" if self.ReleaseType == 0 else f"Type{self.ReleaseType}"
        return f"{rel}.{self.ReleaseMajor}.{self.ReleaseMinor}.{self.ReleasePatch}"


class DeviceStateTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("FirmwareVersion", FirmwareVersionTypeDef),
        ("IsRegistered", ctypes.c_uint8),
        ("Position", ctypes.c_int16),
        ("Torque", ctypes.c_int16),
        ("_padding", ctypes.c_uint8 * 55),
    ]


class StateReportTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReportId", ctypes.c_uint8),
        ("state", DeviceStateTypeDef),
    ]


class EffectSettingsTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("MotionRange", ctypes.c_uint16),
        ("StaticDampeningStrength", ctypes.c_uint16),
        ("SoftStopDampeningStrength", ctypes.c_uint16),
        ("TotalEffectStrength", ctypes.c_uint8),
        ("IntegratedSpringStrength", ctypes.c_uint8),
        ("SoftStopRange", ctypes.c_uint8),
        ("SoftStopStrength", ctypes.c_uint8),
        ("DirectXConstantDirection", ctypes.c_int8),
        ("DirectXSpringStrength", ctypes.c_uint8),
        ("DirectXConstantStrength", ctypes.c_uint8),
        ("DirectXPeriodicStrength", ctypes.c_uint8),
        ("_padding", ctypes.c_uint8 * 50),
    ]


class EffectSettingsReportTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReportId", ctypes.c_uint8),
        ("effectSettings", EffectSettingsTypeDef),
    ]


class HardwareSettingsTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("EncoderCPR", ctypes.c_uint16),
        ("IntegralGain", ctypes.c_uint16),
        ("ProportionalGain", ctypes.c_uint8),
        ("ForceEnabled", ctypes.c_uint8),
        ("DebugTorque", ctypes.c_uint8),
        ("AmplifierGain", ctypes.c_uint8),
        ("CalibrationMagnitude", ctypes.c_uint8),
        ("CalibrationSpeed", ctypes.c_uint8),
        ("PowerLimit", ctypes.c_uint8),
        ("BrakingLimit", ctypes.c_uint8),
        ("PositionSmoothing", ctypes.c_uint8),
        ("SpeedBufferSize", ctypes.c_uint8),
        ("EncoderDirection", ctypes.c_int8),
        ("ForceDirection", ctypes.c_int8),
        ("PolePairs", ctypes.c_uint8),
        ("_padding", ctypes.c_uint8 * 47),
    ]


class HardwareSettingsReportTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReportId", ctypes.c_uint8),
        ("hardwareSettings", HardwareSettingsTypeDef),
    ]


class GpioExtensionSettingsTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ExtensionMode", ctypes.c_uint8),
        ("PinMode", ctypes.c_uint8 * 10),
        ("ButtonMode", ctypes.c_uint8 * 32),
        ("SpiMode", ctypes.c_uint8),
        ("SpiLatchMode", ctypes.c_uint8),
        ("SpiLatchDelay", ctypes.c_uint8),
        ("SpiClkPulseLength", ctypes.c_uint8),
        ("_padding", ctypes.c_uint8 * 17),
    ]


class GpioExtensionSettingsReportTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReportId", ctypes.c_uint8),
        ("gpioExtensionSettings", GpioExtensionSettingsTypeDef),
    ]


class AdcExtensionSettingsTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("RAxisMin", ctypes.c_uint16 * 3),
        ("RAxisMax", ctypes.c_uint16 * 3),
        ("RAxisSmoothing", ctypes.c_uint8 * 3),
        ("RAxisToButtonLow", ctypes.c_uint8 * 3),
        ("RAxisToButtonHigh", ctypes.c_uint8 * 3),
        ("RAxisInvert", ctypes.c_uint8 * 3),
        ("_padding", ctypes.c_uint8 * 40),
    ]


class AdcExtensionSettingsReportTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReportId", ctypes.c_uint8),
        ("adcExtensionSettings", AdcExtensionSettingsTypeDef),
    ]


class DirectControlTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("SpringForce", ctypes.c_int16),
        ("ConstantForce", ctypes.c_int16),
        ("PeriodicForce", ctypes.c_int16),
        ("ForceDrop", ctypes.c_uint8),
    ]


class HidInOutReportTypeDef(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("ReportId", ctypes.c_uint8),
        ("Buffer", ctypes.c_uint8 * 64),
    ]
