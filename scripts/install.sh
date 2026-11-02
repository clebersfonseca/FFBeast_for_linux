#!/usr/bin/env bash
# Script de instalação do FFBeast Linux Control Center
# Compatível com Fedora, Ubuntu/Debian, Arch Linux e qualquer distribuição Linux com systemd/udev.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo "    Instalador do FFBeast Linux Control Suite"
echo "=========================================================="
echo "Diretório do projeto: $SCRIPT_DIR"

# 1. Regras do Udev
echo ""
echo "[1/4] Instalando regras de permissão USB (udev)..."
if [ -w "/etc/udev/rules.d" ]; then
    cp "$SCRIPT_DIR/udev/99-ffbeast.rules" /etc/udev/rules.d/
    udevadm control --reload-rules || true
    udevadm trigger || true
    echo "  -> Regras copiadas para /etc/udev/rules.d/99-ffbeast.rules"
else
    echo "  -> Solicitando permissão sudo para copiar regras udev..."
    sudo cp "$SCRIPT_DIR/udev/99-ffbeast.rules" /etc/udev/rules.d/
    sudo udevadm control --reload-rules || true
    sudo udevadm trigger || true
    echo "  -> Regras do udev instaladas com sucesso!"
fi

# 2. Permissão de execução
echo ""
echo "[2/4] Configurando permissões dos executáveis..."
chmod +x "$SCRIPT_DIR/ffbeast_gui.py"
chmod +x "$SCRIPT_DIR/ffbeast_cli.py"

# 3. Criar binários no PATH do usuário (~/.local/bin)
echo ""
echo "[3/4] Criando atalhos em ~/.local/bin/..."
mkdir -p "$HOME/.local/bin"
ln -sf "$SCRIPT_DIR/ffbeast_gui.py" "$HOME/.local/bin/ffbeast-gui"
ln -sf "$SCRIPT_DIR/ffbeast_cli.py" "$HOME/.local/bin/ffbeast-cli"
echo "  -> 'ffbeast-gui' e 'ffbeast-cli' disponíveis no seu terminal!"

# 4. Instalar entrada no menu de aplicativos do KDE Plasma / Desktop
echo ""
echo "[4/4] Instalando atalho no menu de aplicativos do KDE Plasma..."
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"

cp "$SCRIPT_DIR/assets/ffbeast_hardware_icon.png" "$HOME/.local/share/icons/hicolor/256x256/apps/ffbeast.png"

cat <<EOF > "$HOME/.local/share/applications/ffbeast.desktop"
[Desktop Entry]
Name=FFBeast Control Center
GenericName=Force Feedback Steering Wheel Manager
Comment=Configurador e Gerenciador para Volante Force Feedback FFBeast
Exec=$SCRIPT_DIR/ffbeast_gui.py
Icon=$SCRIPT_DIR/assets/ffbeast_hardware_icon.png
Terminal=false
Type=Application
Categories=Game;Settings;HardwareSettings;Qt;
Keywords=wheel;ffb;forcefeedback;steering;simracing;odrive;ffbeast;racing;
StartupNotify=true
StartupWMClass=ffbeast_gui.py
EOF

echo "  -> Atalho criado em ~/.local/share/applications/ffbeast.desktop"

echo ""
echo "=========================================================="
echo "    Instalação concluída com sucesso!"
echo "=========================================================="
echo "Para abrir a interface gráfica:"
echo "  - Procure por 'FFBeast' no menu do KDE Plasma / Kickoff"
echo "  - Ou digite no terminal: ffbeast-gui"
echo ""
echo "Para usar no terminal:"
echo "  - Digite: ffbeast-cli --help"
echo "=========================================================="
