# FFBeast Linux Control Suite 🏎️🐧

Sistema nativo completo para utilização e configuração do volante Direct Drive **FFBeast** no **Linux (Fedora com KDE Plasma e demais distribuições)**.

---

## 📋 Sumário
1. [Visão Geral & Arquitetura](#visão-geral--arquitetura)
2. [O que aconteceu com as "DLLs" do Windows?](#o-que-aconteceu-com-as-dlls-do-windows)
3. [Suporte do Kernel Linux (hid-universal-pidff)](#suporte-do-kernel-linux-hid-universal-pidff)
4. [Instalação Rápida](#instalação-rápida)
5. [Interface Gráfica (FFBeast Control Center)](#interface-gráfica-ffbeast-control-center)
6. [Utilitário de Linha de Comando (CLI)](#utilitário-de-linha-de-comando-cli)
7. [Perfis de Jogos](#perfis-de-jogos)
8. [Suporte e Otimização para iRacing no Linux](#suporte-e-otimização-para-iracing-no-linux)
9. [Configuração em Outros Jogos na Steam / Proton](#configuração-em-outros-jogos-na-steam--proton)
10. [Gravação de Firmware (DFU Flasher)](#gravação-de-firmware-dfu-flasher)

---

## 🔍 Visão Geral & Arquitetura

O ecossistema FFBeast é composto por uma controladora STM32 (ODrive, ODESC, MKS XDrive) com firmware dedicado que expõe **duas interfaces USB**:
- **Interface 0 (Vendor HID):** Interface proprietária para controle do dispositivo, alteração de parâmetros de hardware, efeitos, licença, calibração, reset de centro e modo DFU.
- **Interface 1 (Standard Joystick PID):** Dispositivo padrão de joystick USB com suporte ao protocolo USB PID (*Physical Interface Device*), responsável pelo **Force Feedback em tempo real**.

---

## 💡 O que aconteceu com as "DLLs" do Windows?

No pacote oficial do Windows, o FFBeast distribuía arquivos `.exe` e várias `.dll` (`Qt6Core.dll`, `Qt6Gui.dll`, `Qt6Widgets.dll`, `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `D3Dcompiler_47.dll` e um wrapper C de `hidapi.c` que chamava `hid.dll` e `setupapi.dll` da API Win32 do Windows).

No Linux, **não se utiliza DLLs do Windows** para gerenciar dispositivos USB de baixo nível:
1. **Comunicação USB Nativa:** O backend foi convertido para usar diretamente a biblioteca padrão do Linux **`libhidapi-hidraw.so.0`** (ou `libhidapi-libusb.so.0`), permitindo comunicação direta sem necessidade de emuladores ou Wine.
2. **Interface Gráfica Nativa:** O configurador foi reescrito em **Qt6 (PySide6)**, integrando-se perfeitamente com o tema escuro do **KDE Plasma** no Fedora.
3. **Mapeamento Binário dos Structs:** Todos os relatórios USB (Feature Reports `0x21`, `0x22`, `0xA1`, `0xA2`, `0xA3` e Input Report de telemetria) possuem mapeamento binário exato (estruturas empacotadas de 64 bytes) idêntico ao código fonte original da controladora STM32.

---

## ⚙️ Suporte do Kernel Linux (hid-universal-pidff)

Seu sistema (Fedora 44 com Kernel 6.12+) já inclui **nativamente** o módulo de driver:
```
drivers/hid/hid-universal-pidff.ko
```
Este driver possui suporte de fábrica para os identificadores de hardware do FFBeast:
- `VID: 0x045B` e `PID: 0x59D7` -> **FFBeast Wheel**
- `VID: 0x045B` e `PID: 0x5968` -> **FFBeast Joystick**
- `VID: 0x045B` e `PID: 0x58F9` -> **FFBeast Rudder Pedals**

Isso significa que o Force Feedback físico nos simuladores (como *Assetto Corsa*, *BeamNG.drive*, *Euro Truck Simulator 2*) é gerenciado diretamente pelo kernel Linux via `evdev`!

---

## 🚀 Instalação Rápida

Para instalar as permissões USB do `udev`, os atalhos no sistema e a entrada no menu do KDE Plasma:

```bash
cd /home/cleber/Projetos/FFBeast_Linux
./scripts/install.sh
```

O script realizará:
1. Cópia das regras de permissão para `/etc/udev/rules.d/99-ffbeast.rules` (permitindo usar o volante sem `sudo`).
2. Recarregamento do `udevadm`.
3. Criação dos atalhos `ffbeast-gui` e `ffbeast-cli` em `~/.local/bin/`.
4. Instalação do atalho no menu de aplicativos do KDE Plasma com ícone de alta resolução.

---

## 🖥️ Interface Gráfica (FFBeast Control Center)

Abra a aplicação pelo menu do sistema procurando por **FFBeast Control Center**, ou execute no terminal:
```bash
ffbeast-gui
```

### Funcionalidades da Interface:
- **Visão Geral & Telemetria:**
  - Volante interativo 3D/2D animado em tempo real conforme a rotação física do seu hardware.
  - Barra de leitura de torque e indicação de esforço do motor.
  - Botão **🎯 Centralizar Volante (Reset Center)** com 1 clique.
  - Gerador de Forças Diretas (teste imediato de Mola, Força Constante e Vibração Periódica).
- **Aba Efeitos FFB:**
  - Ajuste de ângulo de rotação (Motion Range) de 180° a 2520° (com atalhos rápidos 360°, 540°, 900°, 1080°).
  - Força total dos efeitos (0-100%).
  - Mola centralizadora integrada (para jogos sem suporte nativo a FFB).
  - Força e ângulo do batente virtual (Soft Stop Strength & Range).
  - Amortecimento estático, amortecimento de batente e dinâmico.
  - Forças DirectX (Constante, Mola e Periódica/Vibração).
- **Aba Hardware & Motor:**
  - Configuração de Polos do Motor (ex: 15 pares de polos para motores de hoverboard).
  - Resolução do Encoder (CPR) (ex: 4000, 16384, etc.).
  - Limite de potência máxima (Power Limit %) e resistor de frenagem (Braking Limit %).
  - Ganhos de corrente do motor (PID Proporcional e Integral).
  - Magnitude e velocidade da calibração inicial.
- **Aba Periféricos & GPIO:**
  - Configuração dos 10 pinos da placa ODrive (Pin 1 a 8, Z0 e Z1) como botões normais, analógicos (ADC), SPI ou switches de segurança.
  - Zonas mortas dos pedais de acelerador, freio e embreagem.
- **Aba Perfis de Jogos:**
  - Troca rápida de perfis pré-configurados com um clique.
  - Salvar suas próprias configurações personalizadas em arquivos JSON.

---

## ⌨️ Utilitário de Linha de Comando (CLI)

Para alterar parâmetros via scripts, atalhos de teclado do KDE ou terminal:

```bash
# Ver status da conexão e firmware
ffbeast-cli status

# Ler efeitos atuais
ffbeast-cli effects

# Ler parâmetros do motor
ffbeast-cli hardware

# Definir ângulo de rotação para 900 graus
ffbeast-cli set range 900

# Definir força total para 80%
ffbeast-cli set strength 80

# Redefinir o centro do volante (0 graus na posição atual)
ffbeast-cli center

# Salvar alterações na memória flash e reiniciar
ffbeast-cli save

# Monitorar rotação e torque em tempo real
ffbeast-cli monitor

# Listar e aplicar perfis
ffbeast-cli profile list
ffbeast-cli profile apply assetto_corsa
```

---

## 📁 Perfis de Jogos Inclusos

Na pasta `profiles/` você encontrará perfis otimizados:
- `assetto_corsa.json`: 900° com máxima fidelidade de força constante e periódica para carros GT3/Fórmula.
- `iracing.json`: 900° modo linear puro 1:1 para Direct Drive (sem molas artificiais ou compressão não-linear).
- `beamng.json`: 900° com amortecimento suave para física de veículos rodoviários e offroad.
- `euro_truck_simulator_2.json`: 1080° com mola integrada e peso de direção característico de caminhões.
- `default.json`: Perfil equilibrado padrão.

---

## 🏎️ Suporte e Otimização para iRacing no Linux

O iRacing no Linux (via Proton/Wine/LapZero) requer ajustes especiais para extrair a máxima fidelidade de volantes **Direct Drive**:

### 1. Parâmetros Críticos do `app.ini` para Direct Drive
Volantes Direct Drive como o FFBeast operam com torque instantâneo e resposta linear, diferentemente de volantes comuns de engrenagem/correia. Os parâmetros essenciais são:

| Parâmetro | Valor Ideal | Motivo |
| :--- | :--- | :--- |
| `enableLinearFFB` | `1` | **Modo Linear**: Desliga a compressão não-linear artificial do iRacing, enviando o torque em proporção 1:1 exata da física do simulador. |
| `forceFeedbackMinForce` | `0.0` | **Zero Min Force**: Impede oscilação ("cogging" violento) no ponto central do volante em retas. |
| `displayLinearInNm` | `1` | Exibe o slider de força dentro do jogo em **Nm (Newton-metros)** reais em vez de porcentagem abstrata. |
| `calibUsingRawData` | `1` | Lê a resolução nativa do encoder (ex: 4000 ou 16384 CPR) sem compressão. |
| `reinitBetweenSessions` | `0` | Evita que o driver Winebus/DirectInput tente reinicializar o volante ao trocar de servidor/sessão. |
| `steeringFFBSmooth` | `0` | Desativa filtros de atraso sintético no sinal de FFB. |

### 2. Otimização Automática pelo FFBeast Control Center
1. Abra o **FFBeast Control Center** (`ffbeast-gui`).
2. Acesse a aba **🏎️ iRacing Setup**.
3. O software detectará automaticamente a instalação do iRacing no Steam Proton (ou você pode selecionar o `app.ini` manualmente).
4. Clique em **"🔧 Otimizar app.ini para FFBeast Direct Drive"** (um backup `app.ini.bak` é criado automaticamente).
5. Clique em **"🏎️ Aplicar Perfil iRacing no Volante"** para carregar 900° lineares no motor.

Ou faça via terminal:
```bash
# Detectar e otimizar app.ini automaticamente e aplicar perfil ao volante
ffbeast-cli iracing --apply-wheel

# Especificar caminho manual se você usar Wine customizado / LapZero / Lutris
ffbeast-cli iracing --path "/caminho/para/app.ini"
```

### 3. Calibração Recomendada Dentro do iRacing
1. Nas opções de controle do iRacing, execute o assistente de calibração do volante:
   - Gire totalmente para a esquerda e para a direita até os batentes (soft stop).
   - Centralize o volante perfeitamente.
   - Gire **90 graus** para a esquerda e confirme (o iRacing detectará os 900° calibrados).
2. Na aba de direção (*Drive / Options*):
   - Ative a opção **Linear Mode**.
   - Mantenha **Min Force** em **0.0%**.
   - Durante uma volta na pista, abra a black box de gráficos (**tecla F9**) e clique no botão **Auto** para que o simulador ajuste o pico máximo de Nm para o carro atual sem saturação (*clipping*).

### 4. Status de Jogabilidade no Linux
- **Compatível e Totalmente Funcional:** Sessões de *Test Drive*, *Treinos Livres*, *Corridas contra IA (AI Racing)*, *Replays* e análise de telemetria.
- **Corridas Oficiais Online:** O iRacing utiliza o *Easy Anti-Cheat (EAC)* sem o módulo Proton ativado oficialmente pela desenvolvedora, restringindo sessões oficiais online multiplayer.

---

## 🎮 Configuração em Outros Jogos na Steam / Proton

Nos jogos executados através do Proton (Steam):
1. **Steam Input:** Recomenda-se **desativar** o Steam Input nas propriedades do jogo na Steam (*Propriedades -> Controle -> Desativar Entrada Steam*). Isso garante que o jogo acesse o volante diretamente como dispositivo de Force Feedback DirectInput ao invés de emular um controle de Xbox.
2. **Proton / Winebus:** O Proton reconhece automaticamente o dispositivo PIDFF e mapeia todos os efeitos para o jogo sem necessidade de software adicional.

---

## ⚡ Gravação de Firmware (DFU Flasher)

Se precisar atualizar ou regravar o firmware oficial do ODrive:
1. O firmware oficial testado está localizado em `firmware/ffbeast-wheel-odrive-RC.26.1.1.hex`.
2. Para gravar via `dfu-util`:
   ```bash
   ./scripts/flash_firmware.sh
   ```

