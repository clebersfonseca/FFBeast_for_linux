"""
iRacing on Linux Integration & Optimizer for Direct Drive (FFBeast).
Detects and optimizes iRacing's app.ini for Direct Drive force feedback in Wine/Proton.
"""

import glob
import os
import re
import shutil
from typing import Optional, List, Dict, Tuple


IRACING_STEAM_APP_ID = "266410"

# Key Direct Drive parameters for iRacing's [Force Feedback] section
RECOMMENDED_FFB_SETTINGS = {
    "enableLinearFFB": "1",               # Essential for Direct Drive (disables non-linear compression)
    "forceFeedbackMinForce": "0.0",       # Must be 0.0% for DD (avoids oscillation at center)
    "displayLinearInNm": "1",             # Displays strength in real Newton-meters (Nm)
    "calibUsingRawData": "1",             # High-precision raw encoder reading
    "reinitBetweenSessions": "0",         # Prevents Winebus/DirectInput disconnect glitching
    "steeringFFBSmooth": "0",             # Direct Drive has instant response; smoothing adds latency
    "trueForceEnabled": "0",              # Logitech TrueForce off for non-Logitech DD
}


def find_iracing_ini_paths() -> List[str]:
    """Find possible paths for iRacing's app.ini on the Linux filesystem."""
    home = os.path.expanduser("~")
    candidates = [
        # Standard Steam Proton path
        os.path.join(home, ".steam/steam/steamapps/compatdata", IRACING_STEAM_APP_ID, "pfx/drive_c/users/steamuser/Documents/iRacing/app.ini"),
        os.path.join(home, ".local/share/Steam/steamapps/compatdata", IRACING_STEAM_APP_ID, "pfx/drive_c/users/steamuser/Documents/iRacing/app.ini"),
        # Flatpak Steam Proton path
        os.path.join(home, ".var/app/com.valvesoftware.Steam/.steam/steam/steamapps/compatdata", IRACING_STEAM_APP_ID, "pfx/drive_c/users/steamuser/Documents/iRacing/app.ini"),
        os.path.join(home, ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata", IRACING_STEAM_APP_ID, "pfx/drive_c/users/steamuser/Documents/iRacing/app.ini"),
        # Native link or Lutris / Bottles / LapZero
        os.path.join(home, "Documents/iRacing/app.ini"),
        os.path.join(home, "iRacing/app.ini"),
    ]

    # Check wildcard paths in Wine prefixes
    wildcards = [
        os.path.join(home, ".wine/drive_c/users/*/Documents/iRacing/app.ini"),
        os.path.join(home, "Games/*/drive_c/users/*/Documents/iRacing/app.ini"),
        os.path.join(home, ".local/share/bottles/bottles/*/drive_c/users/*/Documents/iRacing/app.ini"),
    ]
    for pattern in wildcards:
        for match in glob.glob(pattern):
            candidates.append(match)

    found = []
    for p in candidates:
        if os.path.isfile(p) and p not in found:
            found.append(p)

    return found


def read_ini_section_values(ini_path: str, section_name: str = "Force Feedback") -> Dict[str, str]:
    """Read key-values from a given section in app.ini, preserving case."""
    if not os.path.isfile(ini_path):
        return {}

    values = {}
    current_section = None
    section_regex = re.compile(r"^\[(.*)\]")
    key_val_regex = re.compile(r"^([a-zA-Z0-9_]+)\s*=\s*([^;\r\n]*)")

    with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            sec_match = section_regex.match(stripped)
            if sec_match:
                current_section = sec_match.group(1).strip()
                continue

            if current_section == section_name:
                kv_match = key_val_regex.match(stripped)
                if kv_match:
                    k = kv_match.group(1).strip()
                    v = kv_match.group(2).strip()
                    values[k] = v

    return values


def optimize_iracing_ini(ini_path: str) -> Tuple[bool, str, List[str]]:
    """
    Apply recommended Direct Drive settings to iRacing's app.ini.
    Returns (success, message, list_of_changes).
    """
    if not os.path.isfile(ini_path):
        return False, f"Arquivo não encontrado: {ini_path}", []

    # Backup original file
    backup_path = ini_path + ".bak"
    try:
        shutil.copyfile(ini_path, backup_path)
    except Exception as e:
        return False, f"Falha ao criar backup do app.ini: {e}", []

    lines = []
    with open(ini_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    current_section = None
    section_regex = re.compile(r"^\[(.*)\]")
    key_val_regex = re.compile(r"^([a-zA-Z0-9_]+)\s*=\s*(.*)$")

    updated_keys = set()
    changes = []
    new_lines = []

    for line in lines:
        stripped = line.strip()
        sec_match = section_regex.match(stripped)
        if sec_match:
            # If leaving [Force Feedback], add any recommended keys that were missing
            if current_section == "Force Feedback":
                for rec_k, rec_v in RECOMMENDED_FFB_SETTINGS.items():
                    if rec_k not in updated_keys:
                        new_lines.append(f"{rec_k}={rec_v}  ; Otimizado para FFBeast Direct Drive\n")
                        changes.append(f"+ Adicionado {rec_k}={rec_v}")
                        updated_keys.add(rec_k)

            current_section = sec_match.group(1).strip()
            new_lines.append(line)
            continue

        if current_section == "Force Feedback":
            kv_match = key_val_regex.match(stripped)
            if kv_match:
                k = kv_match.group(1).strip()
                old_v = kv_match.group(2).strip()
                if k in RECOMMENDED_FFB_SETTINGS:
                    rec_v = RECOMMENDED_FFB_SETTINGS[k]
                    # Preserve comment if any
                    comment = ""
                    if ";" in old_v:
                        val_part, comment = old_v.split(";", 1)
                        comment = ";" + comment
                    new_lines.append(f"{k}={rec_v} {comment}\n")
                    if old_v.split(";")[0].strip() != rec_v:
                        changes.append(f"~ {k}: {old_v.split(';')[0].strip()} -> {rec_v}")
                    updated_keys.add(k)
                    continue

        new_lines.append(line)

    # In case [Force Feedback] was at the end of the file
    if current_section == "Force Feedback":
        for rec_k, rec_v in RECOMMENDED_FFB_SETTINGS.items():
            if rec_k not in updated_keys:
                new_lines.append(f"{rec_k}={rec_v}  ; Otimizado para FFBeast Direct Drive\n")
                changes.append(f"+ Adicionado {rec_k}={rec_v}")
                updated_keys.add(rec_k)

    try:
        with open(ini_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        return False, f"Falha ao salvar app.ini modificado: {e}", []

    return True, f"app.ini otimizado com sucesso! (Backup salvo em {backup_path})", changes
