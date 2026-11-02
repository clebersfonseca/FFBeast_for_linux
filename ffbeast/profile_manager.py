"""
Profile manager for saving, loading and applying game profiles.
"""

import json
import os
from typing import Dict, Any, List, Optional
from .protocol import SettingsFieldEnum


DEFAULT_EFFECT_SETTINGS = {
    "motion_range": 900,
    "total_effect_strength": 100,
    "integrated_spring_strength": 0,
    "soft_stop_strength": 80,
    "soft_stop_range": 15,
    "soft_stop_dampening_strength": 50,
    "static_dampening_strength": 20,
    "dynamic_dampening_strength": 0,
    "directx_constant_strength": 100,
    "directx_spring_strength": 100,
    "directx_periodic_strength": 100,
    "directx_constant_direction": 1,
}

DEFAULT_HARDWARE_SETTINGS = {
    "encoder_cpr": 4000,
    "integral_gain": 50,
    "proportional_gain": 30,
    "force_enabled": True,
    "debug_torque": False,
    "amplifier_gain": 0,
    "calibration_magnitude": 10,
    "calibration_speed": 10,
    "power_limit": 50,
    "braking_limit": 20,
    "position_smoothing": 0,
    "speed_buffer_size": 2,
    "encoder_direction": 1,
    "force_direction": 1,
    "pole_pairs": 15,
}


class ProfileManager:
    """Handles saving, loading and listing game configuration profiles."""

    def __init__(self, profiles_dir: Optional[str] = None):
        if not profiles_dir:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            profiles_dir = os.path.join(base_dir, "profiles")
        self.profiles_dir = profiles_dir
        os.makedirs(self.profiles_dir, exist_ok=True)

    def list_profiles(self) -> List[str]:
        """Return names of available profiles without .json extension."""
        res = []
        for f in os.listdir(self.profiles_dir):
            if f.endswith(".json"):
                res.append(f[:-5])
        res.sort()
        return res

    def load_profile(self, name: str) -> Optional[Dict[str, Any]]:
        """Load profile by name."""
        file_path = os.path.join(self.profiles_dir, f"{name}.json")
        if not os.path.isfile(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading profile {name}: {e}")
            return None

    def save_profile(self, name: str, data: Dict[str, Any]) -> bool:
        """Save profile dict to JSON."""
        file_path = os.path.join(self.profiles_dir, f"{name}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving profile {name}: {e}")
            return False

    def delete_profile(self, name: str) -> bool:
        """Delete profile by name."""
        file_path = os.path.join(self.profiles_dir, f"{name}.json")
        if os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False
