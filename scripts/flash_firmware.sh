#!/usr/bin/env bash
# Script para gravação de firmware no ODrive/STM32 via DFU no Linux

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIRMWARE_HEX="$SCRIPT_DIR/firmware/ffbeast-wheel-odrive-RC.26.1.1.hex"

echo "=========================================================="
echo "    Gravador de Firmware FFBeast (DFU Flasher)"
echo "=========================================================="
echo "Arquivo de Firmware: $FIRMWARE_HEX"
echo ""

if ! command -v dfu-util &> /dev/null; then
    echo "⚠️  'dfu-util' não foi encontrado."
    echo "Para instalar no Fedora: sudo dnf install dfu-util"
    echo "Para instalar no Ubuntu/Debian: sudo apt install dfu-util"
    exit 1
fi

echo "Verificando se o dispositivo está em modo DFU (VID: 0483, PID: df11)..."
DFU_DEV=$(dfu-util -l | grep -i "0483:df11" || true)

if [ -z "$DFU_DEV" ]; then
    echo "❌ Nenhum dispositivo em modo DFU detectado."
    echo "Dicas:"
    echo "1. Se o volante já estiver rodando, use 'ffbeast-cli dfu' ou o botão na interface gráfica."
    echo "2. Ou coloque o jumper DFU na placa ODrive e ligue o cabo USB."
    exit 1
fi

echo "✅ Dispositivo DFU detectado!"
echo "Iniciando gravação do firmware..."

# Converter HEX para BIN temporário se necessário
TEMP_BIN="/tmp/ffbeast_firmware.bin"
if command -v objcopy &> /dev/null; then
    objcopy -I ihex -O binary "$FIRMWARE_HEX" "$TEMP_BIN"
    dfu-util -a 0 -s 0x08000000:leave -D "$TEMP_BIN"
    rm -f "$TEMP_BIN"
else
    # Tentativa direta se suportado
    dfu-util -a 0 -D "$FIRMWARE_HEX"
fi

echo ""
echo "🎉 Firmware gravado com sucesso! O controlador será reiniciado."
