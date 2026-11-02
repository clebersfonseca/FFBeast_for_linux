"""
High-level Python API client for FFBeast hardware on Linux.
"""

import ctypes
import struct
import time
from typing import Optional, Dict, Any, Tuple

from .protocol import (
    USB_VID,
    WHEEL_PID_FS,
    JOYSTICK_PID_FS,
    RUDDER_PID_FS,
    INTERFACE_VENDOR,
    SettingsFieldEnum,
    ReportDataEnum,
    ReportTypeEnum,
    DeviceStateTypeDef,
    EffectSettingsTypeDef,
    HardwareSettingsTypeDef,
    GpioExtensionSettingsTypeDef,
    AdcExtensionSettingsTypeDef,
    DirectControlTypeDef,
)
from .hid_backend import HidDevice, enumerate_devices, open_device_path


class FFBeastDevice:
    """Client for communicating with FFBeast Direct Drive hardware via Vendor Interface 0."""

    SUPPORTED_PIDS = {
        WHEEL_PID_FS: "FFBeast Wheel",
        JOYSTICK_PID_FS: "FFBeast Joystick",
        RUDDER_PID_FS: "FFBeast Rudder Pedals",
    }

    def __init__(self, vid: int = USB_VID, pid: int = WHEEL_PID_FS):
        self.vid = vid
        self.pid = pid
        self.device: Optional[HidDevice] = None
        self.device_info: Dict[str, Any] = {}
        self.device_type_name: str = "FFBeast Wheel"

    def is_connected(self) -> bool:
        return self.device is not None and self.device.is_open()

    def connect(self) -> bool:
        """Search for FFBeast vendor interface (Interface 0) and establish connection."""
        self.disconnect()

        # Check all known FFBeast PIDs if default not found
        pids_to_try = [self.pid] + [p for p in self.SUPPORTED_PIDS.keys() if p != self.pid]

        for test_pid in pids_to_try:
            devs = enumerate_devices(self.vid, test_pid)
            for d in devs:
                if d.get("interface_number") == INTERFACE_VENDOR:
                    handle = open_device_path(d["path"], d)
                    if handle:
                        self.device = handle
                        self.device_info = d
                        self.pid = test_pid
                        self.device_type_name = self.SUPPORTED_PIDS.get(test_pid, "FFBeast Device")
                        return True

        return False

    def disconnect(self):
        """Close connection to device."""
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
            self.device = None
            self.device_info = {}

    # Command Methods

    def reset_center(self) -> bool:
        """Tell controller to set current position as center (0 degrees)."""
        return self._send_command(ReportDataEnum.DATA_COMMAND_RESET_CENTER)

    def save_and_reboot(self) -> bool:
        """Save settings to controller flash memory and reboot."""
        return self._send_command(ReportDataEnum.DATA_COMMAND_SAVE_SETTINGS)

    def reboot(self) -> bool:
        """Reboot controller."""
        return self._send_command(ReportDataEnum.DATA_COMMAND_REBOOT)

    def switch_to_dfu(self) -> bool:
        """Reboot controller into STM32 DFU bootloader mode for firmware updates."""
        return self._send_command(ReportDataEnum.DATA_COMMAND_DFU_MODE)

    def _send_command(self, cmd_id: int) -> bool:
        if not self.is_connected():
            return False
        # ReportId (1B) = 0xA3, Buffer[0] = cmd_id, rest zeros. Total 65 bytes
        packet = bytearray(65)
        packet[0] = ReportTypeEnum.REPORT_GENERIC_INPUT_OUTPUT
        packet[1] = cmd_id
        res = self.device.write(bytes(packet))
        return res == 65

    # Direct Control / Forces Test

    def send_direct_control(
        self,
        spring_force: int = 0,
        constant_force: int = 0,
        periodic_force: int = 0,
        force_drop: int = 0,
    ) -> bool:
        """
        Send direct force override report.
        Forces range: -10000 to +10000.
        Force drop range: 0 to 100.
        """
        if not self.is_connected():
            return False

        # Constrain values
        spring = max(-10000, min(10000, int(spring_force)))
        constant = max(-10000, min(10000, int(constant_force)))
        periodic = max(-10000, min(10000, int(periodic_force)))
        drop = max(0, min(100, int(force_drop)))

        control = DirectControlTypeDef(
            SpringForce=spring,
            ConstantForce=constant,
            PeriodicForce=periodic,
            ForceDrop=drop,
        )

        packet = bytearray(65)
        packet[0] = ReportTypeEnum.REPORT_GENERIC_INPUT_OUTPUT
        packet[1] = ReportDataEnum.DATA_OVERRIDE_DATA
        control_bytes = bytes(control)
        packet[2 : 2 + len(control_bytes)] = control_bytes

        res = self.device.write(bytes(packet))
        return res == 65

    # Real-Time State

    def read_state(self, timeout_ms: int = 100) -> Optional[Dict[str, Any]]:
        """
        Read real-time device state (position, torque, registered status, firmware version).
        Returns None if read timed out or failed.
        """
        if not self.is_connected():
            return None

        data = self.device.read_timeout(65, timeout_ms)
        if len(data) < 65:
            return None

        # Byte 0 is ReportId, bytes 1:65 are DeviceStateTypeDef
        state = DeviceStateTypeDef.from_buffer_copy(data[1:65])
        return {
            "firmware_version": state.FirmwareVersion.to_string(),
            "is_registered": bool(state.IsRegistered),
            "position": state.Position,       # -10000 to +10000
            "torque": state.Torque,           # -10000 to +10000
        }

    # Settings Reading (Feature Reports)

    def read_effect_settings(self) -> Optional[Dict[str, Any]]:
        """Fetch effect settings from hardware via Feature Report 0x22."""
        if not self.is_connected():
            return None

        data = self.device.get_feature_report(ReportTypeEnum.REPORT_EFFECT_SETTINGS_FEATURE, 65)
        if len(data) < 65:
            return None

        eff = EffectSettingsTypeDef.from_buffer_copy(data[1:65])
        return {
            "motion_range": eff.MotionRange,
            "static_dampening_strength": eff.StaticDampeningStrength,
            "soft_stop_dampening_strength": eff.SoftStopDampeningStrength,
            "total_effect_strength": eff.TotalEffectStrength,
            "integrated_spring_strength": eff.IntegratedSpringStrength,
            "soft_stop_range": eff.SoftStopRange,
            "soft_stop_strength": eff.SoftStopStrength,
            "directx_constant_direction": eff.DirectXConstantDirection,
            "directx_spring_strength": eff.DirectXSpringStrength,
            "directx_constant_strength": eff.DirectXConstantStrength,
            "directx_periodic_strength": eff.DirectXPeriodicStrength,
        }

    def read_hardware_settings(self) -> Optional[Dict[str, Any]]:
        """Fetch hardware settings from hardware via Feature Report 0x21."""
        if not self.is_connected():
            return None

        data = self.device.get_feature_report(ReportTypeEnum.REPORT_HARDWARE_SETTINGS_FEATURE, 65)
        if len(data) < 65:
            return None

        hw = HardwareSettingsTypeDef.from_buffer_copy(data[1:65])
        return {
            "encoder_cpr": hw.EncoderCPR,
            "integral_gain": hw.IntegralGain,
            "proportional_gain": hw.ProportionalGain,
            "force_enabled": bool(hw.ForceEnabled),
            "debug_torque": bool(hw.DebugTorque),
            "amplifier_gain": hw.AmplifierGain,
            "calibration_magnitude": hw.CalibrationMagnitude,
            "calibration_speed": hw.CalibrationSpeed,
            "power_limit": hw.PowerLimit,
            "braking_limit": hw.BrakingLimit,
            "position_smoothing": hw.PositionSmoothing,
            "speed_buffer_size": hw.SpeedBufferSize,
            "encoder_direction": hw.EncoderDirection,
            "force_direction": hw.ForceDirection,
            "pole_pairs": hw.PolePairs,
        }

    def read_gpio_settings(self) -> Optional[Dict[str, Any]]:
        """Fetch GPIO settings via Feature Report 0xA1."""
        if not self.is_connected():
            return None

        data = self.device.get_feature_report(ReportTypeEnum.REPORT_GPIO_SETTINGS_FEATURE, 65)
        if len(data) < 65:
            return None

        gpio = GpioExtensionSettingsTypeDef.from_buffer_copy(data[1:65])
        return {
            "extension_mode": gpio.ExtensionMode,
            "pin_modes": list(gpio.PinMode),
            "button_modes": list(gpio.ButtonMode),
            "spi_mode": gpio.SpiMode,
            "spi_latch_mode": gpio.SpiLatchMode,
            "spi_latch_delay": gpio.SpiLatchDelay,
            "spi_clk_pulse_length": gpio.SpiClkPulseLength,
        }

    def read_adc_settings(self) -> Optional[Dict[str, Any]]:
        """Fetch ADC / Pedal settings via Feature Report 0xA2."""
        if not self.is_connected():
            return None

        data = self.device.get_feature_report(ReportTypeEnum.REPORT_ADC_SETTINGS_FEATURE, 65)
        if len(data) < 65:
            return None

        adc = AdcExtensionSettingsTypeDef.from_buffer_copy(data[1:65])
        return {
            "axis_min": list(adc.RAxisMin),
            "axis_max": list(adc.RAxisMax),
            "axis_smoothing": list(adc.RAxisSmoothing),
            "axis_to_button_low": list(adc.RAxisToButtonLow),
            "axis_to_button_high": list(adc.RAxisToButtonHigh),
            "axis_invert": list(adc.RAxisInvert),
        }

    # Settings Writing (Field Reports)

    def send_uint8_setting(self, field_id: int, index: int, value: int) -> bool:
        val_bytes = struct.pack("<B", int(value) & 0xFF)
        return self._send_setting_field(field_id, index, val_bytes)

    def send_int8_setting(self, field_id: int, index: int, value: int) -> bool:
        val_bytes = struct.pack("<b", int(value))
        return self._send_setting_field(field_id, index, val_bytes)

    def send_uint16_setting(self, field_id: int, index: int, value: int) -> bool:
        val_bytes = struct.pack("<H", int(value) & 0xFFFF)
        return self._send_setting_field(field_id, index, val_bytes)

    def send_int16_setting(self, field_id: int, index: int, value: int) -> bool:
        val_bytes = struct.pack("<h", int(value))
        return self._send_setting_field(field_id, index, val_bytes)

    def send_float_setting(self, field_id: int, index: int, value: float) -> bool:
        val_bytes = struct.pack("<f", float(value))
        return self._send_setting_field(field_id, index, val_bytes)

    def _send_setting_field(self, field_id: int, index: int, value_bytes: bytes) -> bool:
        if not self.is_connected():
            return False

        packet = bytearray(65)
        packet[0] = ReportTypeEnum.REPORT_GENERIC_INPUT_OUTPUT
        packet[1] = ReportDataEnum.DATA_SETTINGS_FIELD_DATA
        packet[2] = field_id & 0xFF
        packet[3] = index & 0xFF
        packet[4 : 4 + len(value_bytes)] = value_bytes

        res = self.device.write(bytes(packet))
        return res == 65
