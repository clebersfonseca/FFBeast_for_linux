#!/usr/bin/env python3
"""
FFBeast Linux Command Line Interface (CLI).
Control and configure FFBeast Direct Drive devices from terminal or scripts.
"""

import argparse
import sys
import time

from ffbeast import (
    FFBeastDevice,
    ProfileManager,
    SettingsFieldEnum,
    PinModeEnum,
    ButtonModeEnum,
    AmplifierGainEnum,
)
from ffbeast.protocol import PIN_MODE_NAMES, AMPLIFIER_GAIN_NAMES


def cmd_status(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Nenhum dispositivo FFBeast detectado na interface USB.")
        print("Verifique se o cabo USB está conectado e se as regras do udev estão instaladas.")
        sys.exit(1)

    print(f"✅ Dispositivo Conectado: {device.device_type_name}")
    print(f"   VID: 0x{device.vid:04X} | PID: 0x{device.pid:04X}")
    print(f"   Path: {device.device_info.get('path', b'').decode('utf-8', errors='ignore')}")

    state = device.read_state(timeout_ms=500)
    if state:
        print(f"   Firmware: {state['firmware_version']}")
        print(f"   Modo Licença: {'PRO / Ativado' if state['is_registered'] else 'Livre / Light'}")
        pos_deg = (state['position'] / 10000.0)
        print(f"   Posição Atual: {state['position']} ({pos_deg:+.2%})")
        print(f"   Torque Atual: {state['torque']}")
    else:
        print("   ⚠️  Não foi possível ler o estado em tempo real (timeout).")


def cmd_effects(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)

    eff = device.read_effect_settings()
    if not eff:
        print("❌ Erro ao ler configurações de efeitos do dispositivo.")
        sys.exit(1)

    print("=== Configurações de Efeitos (Effects) ===")
    print(f"  Ângulo de Rotação (Motion Range): {eff['motion_range']}°")
    print(f"  Força Total (Total Effect Strength): {eff['total_effect_strength']}%")
    print(f"  Mola Integrada (Integrated Spring): {eff['integrated_spring_strength']}%")
    print(f"  Soft Stop Força: {eff['soft_stop_strength']}%")
    print(f"  Soft Stop Faixa (Range): {eff['soft_stop_range']}°")
    print(f"  Soft Stop Amortecimento (Dampening): {eff['soft_stop_dampening_strength']}%")
    print(f"  Amortecimento Estático (Static Dampening): {eff['static_dampening_strength']}%")
    print(f"  Amortecimento Dinâmico (Dynamic Dampening): {eff['dynamic_dampening_strength']}%")
    print(f"  DirectX Força Constante: {eff['directx_constant_strength']}%")
    print(f"  DirectX Mola: {eff['directx_spring_strength']}%")
    print(f"  DirectX Periódico (Vibração): {eff['directx_periodic_strength']}%")
    print(f"  Inverter Força Constante: {'Sim' if eff['directx_constant_direction'] == -1 else 'Não'}")


def cmd_hardware(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)

    hw = device.read_hardware_settings()
    if not hw:
        print("❌ Erro ao ler configurações de hardware do dispositivo.")
        sys.exit(1)

    print("=== Configurações de Hardware & Motor (Controller) ===")
    print(f"  Força Habilitada (Enable Force): {'Sim' if hw['force_enabled'] else 'Não'}")
    print(f"  Depurar Força (Debug Torque): {'Sim' if hw['debug_torque'] else 'Não'}")
    print(f"  Polos do Motor (Pole Pairs): {hw['pole_pairs']}")
    print(f"  Resolução do Encoder (CPR): {hw['encoder_cpr']}")
    print(f"  Limite de Potência (Power Limit): {hw['power_limit']}%")
    print(f"  Limite Resistor de Frenagem (Braking Limit): {hw['braking_limit']}%")
    print(f"  Magnitude de Calibração: {hw['calibration_magnitude']}%")
    print(f"  Velocidade de Calibração: {hw['calibration_speed']}%")
    print(f"  Ganho Proporcional (P Gain): {hw['proportional_gain']}")
    print(f"  Ganho Integral (I Gain): {hw['integral_gain']}")
    print(f"  Ganho Amplificador de Corrente: {AMPLIFIER_GAIN_NAMES.get(hw['amplifier_gain'], str(hw['amplifier_gain']))}")
    print(f"  Inverter Direção do Encoder: {'Sim' if hw['encoder_direction'] == -1 else 'Não'}")
    print(f"  Inverter Direção da Força: {'Sim' if hw['force_direction'] == -1 else 'Não'}")
    print(f"  Suavização de Posição: {hw['position_smoothing']}%")
    print(f"  Buffer de Amostragem de Velocidade: {hw['speed_buffer_size']}")


def cmd_set(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)

    field_name = args.field.lower()
    value = args.value

    if field_name in ["range", "motion_range", "angle"]:
        val = int(value)
        ok = device.send_uint16_setting(SettingsFieldEnum.MOTION_RANGE, 0, val)
        print(f"⚙️ Ângulo de rotação definido para {val}°: {'Sucesso' if ok else 'Falha'}")
    elif field_name in ["strength", "total_strength"]:
        val = int(value)
        ok = device.send_uint8_setting(SettingsFieldEnum.TOTAL_EFFECT_STRENGTH, 0, val)
        print(f"⚙️ Força total definida para {val}%: {'Sucesso' if ok else 'Falha'}")
    elif field_name in ["spring", "integrated_spring"]:
        val = int(value)
        ok = device.send_uint8_setting(SettingsFieldEnum.INTEGRATED_SPRING_STRENGTH, 0, val)
        print(f"⚙️ Mola integrada definida para {val}%: {'Sucesso' if ok else 'Falha'}")
    elif field_name in ["power", "power_limit"]:
        val = int(value)
        ok = device.send_uint8_setting(SettingsFieldEnum.POWER_LIMIT, 0, val)
        print(f"⚙️ Limite de potência definido para {val}%: {'Sucesso' if ok else 'Falha'}")
    elif field_name in ["dampening", "static_dampening"]:
        val = int(value)
        ok = device.send_uint16_setting(SettingsFieldEnum.STATIC_DAMPENING_STRENGTH, 0, val)
        print(f"⚙️ Amortecimento estático definido para {val}%: {'Sucesso' if ok else 'Falha'}")
    elif field_name in ["cpr", "encoder_cpr"]:
        val = int(value)
        ok = device.send_uint16_setting(SettingsFieldEnum.ENCODER_CPR, 0, val)
        print(f"⚙️ Encoder CPR definido para {val}: {'Sucesso' if ok else 'Falha'}")
    elif field_name in ["pole_pairs", "poles"]:
        val = int(value)
        ok = device.send_uint8_setting(SettingsFieldEnum.POLE_PAIRS, 0, val)
        print(f"⚙️ Pares de polo definidos para {val}: {'Sucesso' if ok else 'Falha'}")
    else:
        print(f"❌ Campo desconhecido: '{field_name}'. Campos válidos: range, strength, spring, power, dampening, cpr, poles.")
        sys.exit(1)


def cmd_center(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)
    if device.reset_center():
        print("🎯 Centro do volante redefinido com sucesso (0° na posição atual)!")
    else:
        print("❌ Falha ao enviar comando de centralização.")


def cmd_save(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)
    print("💾 Gravando configurações na memória flash e reiniciando a placa...")
    if device.save_and_reboot():
        print("✅ Salvo com sucesso! A placa foi reiniciada.")
    else:
        print("❌ Falha ao salvar configurações.")


def cmd_dfu(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)
    print("⚠️ Reiniciando a placa em modo STM32 DFU Bootloader...")
    if device.switch_to_dfu():
        print("✅ Comando aceito. Dispositivo entrando em modo DFU.")
    else:
        print("❌ Falha ao enviar comando DFU.")


def cmd_monitor(device: FFBeastDevice, args):
    if not device.connect():
        print("❌ Erro: Dispositivo não encontrado.")
        sys.exit(1)

    print("📊 Monitorando posição e torque em tempo real (Ctrl+C para sair)...")
    try:
        while True:
            st = device.read_state(timeout_ms=100)
            if st:
                pos = st["position"]
                torq = st["torque"]
                deg = pos * (900.0 / 20000.0) # approx
                bar_len = 30
                norm_pos = (pos + 10000) / 20000.0
                bar_idx = max(0, min(bar_len - 1, int(norm_pos * bar_len)))
                bar = ["-"] * bar_len
                bar[bar_idx] = "|"
                bar_str = "".join(bar)
                sys.stdout.write(f"\rPos: [{bar_str}] {pos:+06d} | Torque: {torq:+06d}    ")
                sys.stdout.flush()
            time.sleep(0.04)
    except KeyboardInterrupt:
        print("\nMonitoramento encerrado.")


def cmd_profile(device: FFBeastDevice, args):
    pm = ProfileManager()
    sub = args.profile_action

    if sub == "list":
        profiles = pm.list_profiles()
        print("=== Perfis Disponíveis ===")
        for p in profiles:
            data = pm.load_profile(p)
            desc = data.get("description", "") if data else ""
            print(f"  • {p:<25} - {desc}")
    elif sub == "apply":
        name = args.profile_name
        data = pm.load_profile(name)
        if not data:
            print(f"❌ Perfil '{name}' não encontrado.")
            sys.exit(1)

        if not device.connect():
            print("❌ Erro: Dispositivo não conectado para aplicar perfil.")
            sys.exit(1)

        print(f"🚀 Aplicando perfil '{name}'...")
        eff = data.get("effects", {})
        if "motion_range" in eff:
            device.send_uint16_setting(SettingsFieldEnum.MOTION_RANGE, 0, eff["motion_range"])
        if "total_effect_strength" in eff:
            device.send_uint8_setting(SettingsFieldEnum.TOTAL_EFFECT_STRENGTH, 0, eff["total_effect_strength"])
        if "integrated_spring_strength" in eff:
            device.send_uint8_setting(SettingsFieldEnum.INTEGRATED_SPRING_STRENGTH, 0, eff["integrated_spring_strength"])
        if "soft_stop_strength" in eff:
            device.send_uint8_setting(SettingsFieldEnum.SOFT_STOP_STRENGTH, 0, eff["soft_stop_strength"])
        if "soft_stop_range" in eff:
            device.send_uint8_setting(SettingsFieldEnum.SOFT_STOP_RANGE, 0, eff["soft_stop_range"])
        if "static_dampening_strength" in eff:
            device.send_uint16_setting(SettingsFieldEnum.STATIC_DAMPENING_STRENGTH, 0, eff["static_dampening_strength"])
        if "soft_stop_dampening_strength" in eff:
            device.send_uint16_setting(SettingsFieldEnum.SOFT_STOP_DAMPENING_STRENGTH, 0, eff["soft_stop_dampening_strength"])
        if "directx_constant_strength" in eff:
            device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_CONSTANT_STRENGTH, 0, eff["directx_constant_strength"])
        if "directx_spring_strength" in eff:
            device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_SPRING_STRENGTH, 0, eff["directx_spring_strength"])
        if "directx_periodic_strength" in eff:
            device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_PERIODIC_STRENGTH, 0, eff["directx_periodic_strength"])

        print(f"✅ Perfil '{name}' aplicado com sucesso no volante!")


def cmd_iracing(device: FFBeastDevice, args):
    from ffbeast import find_iracing_ini_paths, optimize_iracing_ini, read_ini_section_values

    target_path = args.path
    if not target_path:
        paths = find_iracing_ini_paths()
        if not paths:
            print("❌ Nenhum arquivo app.ini do iRacing foi encontrado automaticamente.")
            print("Caminhos comuns no Steam/Proton:")
            print("  ~/.steam/steam/steamapps/compatdata/266410/pfx/drive_c/users/steamuser/Documents/iRacing/app.ini")
            print("Você pode especificar o caminho manualmente com:")
            print("  ffbeast-cli iracing --path /caminho/para/app.ini")
            sys.exit(1)
        target_path = paths[0]
        print(f"🎯 Arquivo do iRacing detectado em:\n   {target_path}")
        if len(paths) > 1:
            print(f"   (Outras instalações encontradas: {len(paths) - 1})")
    else:
        if not os.path.isfile(target_path):
            print(f"❌ O caminho especificado não existe: {target_path}")
            sys.exit(1)
        print(f"🎯 Usando arquivo especificado:\n   {target_path}")

    current_values = read_ini_section_values(target_path, "Force Feedback")
    print("\n=== Parâmetros Atuais de FFB no iRacing ===")
    for k in ["enableLinearFFB", "forceFeedbackMinForce", "displayLinearInNm", "calibUsingRawData", "reinitBetweenSessions"]:
        curr = current_values.get(k, "Não definido")
        print(f"  • {k:<25} = {curr}")

    if args.check:
        print("\nModo somente verificação (--check). Nenhuma alteração foi realizada.")
        return

    print("\n🔧 Otimizando app.ini para volante Direct Drive (FFBeast)...")
    ok, msg, changes = optimize_iracing_ini(target_path)
    if ok:
        print(f"✅ {msg}")
        for ch in changes:
            print(f"   {ch}")
    else:
        print(f"❌ {msg}")
        sys.exit(1)

    # Offer to apply iRacing profile to wheel
    if args.apply_wheel:
        if device.connect():
            pm = ProfileManager()
            ir_prof = pm.load_profile("iracing")
            if ir_prof and "effects" in ir_prof:
                eff = ir_prof["effects"]
                device.send_uint16_setting(SettingsFieldEnum.MOTION_RANGE, 0, eff.get("motion_range", 900))
                device.send_uint8_setting(SettingsFieldEnum.TOTAL_EFFECT_STRENGTH, 0, eff.get("total_effect_strength", 100))
                device.send_uint8_setting(SettingsFieldEnum.INTEGRATED_SPRING_STRENGTH, 0, eff.get("integrated_spring_strength", 0))
                device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_CONSTANT_STRENGTH, 0, eff.get("directx_constant_strength", 100))
                device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_SPRING_STRENGTH, 0, eff.get("directx_spring_strength", 0))
                device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_PERIODIC_STRENGTH, 0, eff.get("directx_periodic_strength", 0))
                print("🏎️ Perfil 'iRacing (Direct Drive)' enviado para o volante com sucesso!")
        else:
            print("⚠️ Volante não conectado no momento. Conecte o USB e use 'ffbeast-cli profile apply iracing' depois.")


def main():
    parser = argparse.ArgumentParser(description="FFBeast Linux Control CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comando a executar")

    subparsers.add_parser("status", help="Exibe status da conexão e firmware")
    subparsers.add_parser("effects", help="Exibe configurações de efeitos atuais")
    subparsers.add_parser("hardware", help="Exibe configurações de hardware e motor")
    subparsers.add_parser("center", help="Define centro atual do volante (Reset Center)")
    subparsers.add_parser("save", help="Salva configurações na flash e reinicia")
    subparsers.add_parser("dfu", help="Reinicia a placa em modo STM32 DFU Bootloader")
    subparsers.add_parser("monitor", help="Monitora posição e torque em tempo real")

    set_parser = subparsers.add_parser("set", help="Ajusta um parâmetro específico")
    set_parser.add_argument("field", help="Parâmetro (range, strength, spring, power, dampening, cpr, poles)")
    set_parser.add_argument("value", help="Valor a ser gravado")

    prof_parser = subparsers.add_parser("profile", help="Gerencia perfis")
    prof_sub = prof_parser.add_subparsers(dest="profile_action")
    prof_sub.add_parser("list", help="Lista todos os perfis salvos")
    apply_p = prof_sub.add_parser("apply", help="Aplica um perfil ao volante")
    apply_p.add_argument("profile_name", help="Nome do perfil")

    ir_parser = subparsers.add_parser("iracing", help="Configura e otimiza o iRacing no Linux para o volante FFBeast")
    ir_parser.add_argument("--path", help="Caminho manual para o arquivo app.ini do iRacing")
    ir_parser.add_argument("--check", action="store_true", help="Apenas verificar sem alterar o arquivo")
    ir_parser.add_argument("--apply-wheel", action="store_true", help="Aplica também o perfil iRacing no volante conectado")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    device = FFBeastDevice()

    cmds = {
        "status": cmd_status,
        "effects": cmd_effects,
        "hardware": cmd_hardware,
        "set": cmd_set,
        "center": cmd_center,
        "save": cmd_save,
        "dfu": cmd_dfu,
        "monitor": cmd_monitor,
        "profile": cmd_profile,
        "iracing": cmd_iracing,
    }

    if args.command in cmds:
        cmds[args.command](device, args)



if __name__ == "__main__":
    main()
