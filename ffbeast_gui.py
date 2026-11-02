#!/usr/bin/env python3
"""
FFBeast Linux Control Center.
Modern graphical application built with Qt6 (PySide6) for Fedora Linux and KDE Plasma.
"""

import math
import os
import sys
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt, QTimer, QPointF
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPen,
    QBrush,
    QIcon,
    QFont,
    QLinearGradient,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QGridLayout,
    QListWidget,
    QMessageBox,
    QFileDialog,
    QStatusBar,
    QFrame,
    QScrollArea,
)

from ffbeast import (
    FFBeastDevice,
    ProfileManager,
    SettingsFieldEnum,
    PinModeEnum,
    ButtonModeEnum,
    AmplifierGainEnum,
)
from ffbeast.protocol import PIN_MODE_NAMES, AMPLIFIER_GAIN_NAMES


class SteeringWheelWidget(QWidget):
    """Custom interactive steering wheel widget that rotates in real-time."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self.angle_degrees: float = 0.0
        self.torque_percent: float = 0.0

    def set_angle(self, angle: float):
        self.angle_degrees = angle
        self.update()

    def set_torque(self, torque: float):
        self.torque_percent = torque
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        center = QPointF(w / 2.0, h / 2.0)
        radius = (side / 2.0) - 15

        # Background circular glow
        radial = QRadialGradient(center, radius)
        radial.setColorAt(0.0, QColor(25, 30, 42))
        radial.setColorAt(0.9, QColor(15, 18, 26))
        radial.setColorAt(1.0, QColor(10, 12, 18))
        painter.setBrush(QBrush(radial))
        painter.setPen(QPen(QColor(40, 50, 70), 2))
        painter.drawEllipse(center, radius + 10, radius + 10)

        # Torque Ring (LED indicator arc)
        if abs(self.torque_percent) > 0.01:
            t_pen = QPen(QColor(0, 180, 255) if self.torque_percent >= 0 else QColor(255, 60, 60), 4)
            painter.setPen(t_pen)
            painter.setBrush(Qt.NoBrush)
            span = int(-self.torque_percent * 180 * 16)
            painter.drawArc(
                int(center.x() - radius - 5),
                int(center.y() - radius - 5),
                int((radius + 5) * 2),
                int((radius + 5) * 2),
                90 * 16,
                span,
            )

        painter.save()
        painter.translate(center)
        painter.rotate(self.angle_degrees)

        # Steering Wheel Rim (outer ring)
        rim_grad = QLinearGradient(-radius, -radius, radius, radius)
        rim_grad.setColorAt(0.0, QColor(60, 65, 75))
        rim_grad.setColorAt(0.5, QColor(30, 32, 38))
        rim_grad.setColorAt(1.0, QColor(50, 54, 64))

        painter.setPen(QPen(QColor(20, 22, 28), 3))
        painter.setBrush(QBrush(rim_grad))
        painter.drawEllipse(QPointF(0, 0), radius, radius)

        # Inner cut-out (hole)
        inner_r = radius * 0.72
        painter.setBrush(QBrush(QColor(15, 18, 25)))
        painter.setPen(QPen(QColor(70, 80, 95), 1.5))
        painter.drawEllipse(QPointF(0, 0), inner_r, inner_r)

        # Center Stripe (12 o'clock marker)
        painter.setBrush(QBrush(QColor(255, 60, 60)))
        painter.setPen(Qt.NoPen)
        stripe_w = radius * 0.12
        stripe_h = radius - inner_r + 4
        painter.drawRoundedRect(
            int(-stripe_w / 2),
            int(-radius - 2),
            int(stripe_w),
            int(stripe_h),
            2,
            2,
        )

        # Spokes (3-spoke GT wheel)
        spoke_brush = QBrush(QColor(45, 50, 60))
        painter.setBrush(spoke_brush)
        painter.setPen(QPen(QColor(25, 28, 35), 1))

        # Horizontal spokes
        spoke_h = radius * 0.22
        painter.drawRect(int(-radius + 8), int(-spoke_h / 2), int(radius * 2 - 16), int(spoke_h))

        # Bottom vertical spoke
        spoke_v_w = radius * 0.24
        painter.drawRect(int(-spoke_v_w / 2), 0, int(spoke_v_w), int(radius - 8))

        # Center Hub
        hub_r = radius * 0.38
        hub_grad = QRadialGradient(QPointF(0, 0), hub_r)
        hub_grad.setColorAt(0.0, QColor(40, 45, 55))
        hub_grad.setColorAt(0.9, QColor(22, 25, 32))
        hub_grad.setColorAt(1.0, QColor(10, 12, 16))
        painter.setBrush(QBrush(hub_grad))
        painter.setPen(QPen(QColor(80, 140, 220), 2))
        painter.drawEllipse(QPointF(0, 0), hub_r, hub_r)

        # Hub Emblem / Text
        painter.setPen(QColor(220, 230, 255))
        painter.setFont(QFont("sans-serif", 9, QFont.Bold))
        painter.drawText(int(-hub_r), int(-hub_r), int(hub_r * 2), int(hub_r * 2), Qt.AlignCenter, "FFBEAST")

        painter.restore()

        # Center Digital Angle Readout below wheel
        painter.setPen(QColor(180, 200, 230))
        painter.setFont(QFont("sans-serif", 10, QFont.Bold))
        txt = f"{self.angle_degrees:+.1f}°"
        painter.drawText(0, int(h - 22), w, 20, Qt.AlignCenter, txt)


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.device = FFBeastDevice()
        self.profile_manager = ProfileManager()

        self.setWindowTitle("FFBeast Linux Control Center")
        self.resize(960, 720)

        icon_path = os.path.join(os.path.dirname(__file__), "assets", "ffbeast_hardware_icon.png")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.apply_dark_theme()

        # Central widget and tabs
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.tab_overview = self.create_overview_tab()
        self.tab_effects = self.create_effects_tab()
        self.tab_hardware = self.create_hardware_tab()
        self.tab_periphery = self.create_periphery_tab()
        self.tab_profiles = self.create_profiles_tab()
        self.tab_iracing = self.create_iracing_tab()
        self.tab_firmware = self.create_firmware_tab()

        self.tab_widget.addTab(self.tab_overview, "📊 Visão Geral & Telemetria")
        self.tab_widget.addTab(self.tab_effects, "⚡ Efeitos FFB")
        self.tab_widget.addTab(self.tab_hardware, "⚙️ Hardware & Motor")
        self.tab_widget.addTab(self.tab_periphery, "🎛️ Periféricos & GPIO")
        self.tab_widget.addTab(self.tab_profiles, "📁 Perfis de Jogos")
        self.tab_widget.addTab(self.tab_iracing, "🏎️ iRacing Setup")
        self.tab_widget.addTab(self.tab_firmware, "🐧 Guia Linux & Firmware")

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Real-time polling timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_device)
        self.timer.start(25)  # 40 Hz polling

        # Try initial connection
        self.check_connection()

    def apply_dark_theme(self):
        """Clean dark theme harmonized with KDE Plasma Breeze Dark."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e222b;
                color: #e6e8eb;
            }
            QWidget {
                background-color: #1e222b;
                color: #e6e8eb;
                font-family: 'Segoe UI', 'Noto Sans', sans-serif;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid #2d3342;
                background-color: #242935;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #181b22;
                color: #8b94a5;
                padding: 10px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #242935;
                color: #38a2ff;
                border-bottom: 2px solid #38a2ff;
            }
            QGroupBox {
                border: 1px solid #333a4c;
                border-radius: 8px;
                margin-top: 14px;
                font-weight: bold;
                padding: 14px;
                background-color: #212631;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #58b2ff;
            }
            QPushButton {
                background-color: #2a3242;
                color: #ffffff;
                border: 1px solid #3d475c;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #354055;
                border-color: #4f5d79;
            }
            QPushButton:pressed {
                background-color: #1f2532;
            }
            QPushButton#btnPrimary {
                background-color: #0b72cc;
                border: 1px solid #1488ec;
            }
            QPushButton#btnPrimary:hover {
                background-color: #1783e2;
            }
            QPushButton#btnDanger {
                background-color: #a82323;
                border: 1px solid #cc3131;
            }
            QPushButton#btnDanger:hover {
                background-color: #bf2d2d;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #181b22;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0b72cc;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #e6e8eb;
                border: 1px solid #0b72cc;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #38a2ff;
            }
            QSpinBox, QComboBox {
                background-color: #181b22;
                border: 1px solid #3d475c;
                border-radius: 4px;
                padding: 4px 8px;
                color: #ffffff;
            }
            QListWidget {
                background-color: #181b22;
                border: 1px solid #333a4c;
                border-radius: 6px;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0b72cc;
                color: #ffffff;
            }
            QStatusBar {
                background-color: #14171d;
                color: #8b94a5;
                font-size: 12px;
            }
        """)

    # ---------------- TAB 1: OVERVIEW ----------------

    def create_overview_tab(self) -> QWidget:
        widget = QWidget()
        main_layout = QHBoxLayout(widget)

        # Left column: Wheel visualization & real-time readings
        left_box = QGroupBox("Monitoramento em Tempo Real")
        left_layout = QVBoxLayout(left_box)

        self.wheel_view = SteeringWheelWidget()
        left_layout.addWidget(self.wheel_view, alignment=Qt.AlignCenter)

        # Position readout
        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Posição Bruta (-10000 a +10000):"))
        self.lbl_raw_position = QLabel("0")
        self.lbl_raw_position.setStyleSheet("font-weight: bold; color: #58b2ff;")
        pos_layout.addWidget(self.lbl_raw_position)
        left_layout.addLayout(pos_layout)

        # Torque readout
        torq_layout = QHBoxLayout()
        torq_layout.addWidget(QLabel("Torque Atual:"))
        self.lbl_raw_torque = QLabel("0")
        self.lbl_raw_torque.setStyleSheet("font-weight: bold; color: #ff7575;")
        torq_layout.addWidget(self.lbl_raw_torque)
        left_layout.addLayout(torq_layout)

        # Quick action: Center wheel
        btn_center = QPushButton("🎯 Centralizar Volante (Reset Center)")
        btn_center.setObjectName("btnPrimary")
        btn_center.clicked.connect(self.on_center_wheel)
        left_layout.addWidget(btn_center)

        main_layout.addWidget(left_box, 1)

        # Right column: Device status & test forces
        right_box = QGroupBox("Status & Controle")
        right_layout = QVBoxLayout(right_box)

        # Connection status block
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #191c24; border-radius: 6px; padding: 10px;")
        sf_layout = QVBoxLayout(status_frame)

        self.lbl_conn_status = QLabel("❌ Desconectado")
        self.lbl_conn_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #ff5555;")
        sf_layout.addWidget(self.lbl_conn_status)

        self.lbl_fw_version = QLabel("Firmware: Desconhecido")
        sf_layout.addWidget(self.lbl_fw_version)

        self.lbl_reg_status = QLabel("Licença: Desconhecida")
        sf_layout.addWidget(self.lbl_reg_status)

        btn_reconnect = QPushButton("🔄 Reconectar USB")
        btn_reconnect.clicked.connect(self.check_connection)
        sf_layout.addWidget(btn_reconnect)

        right_layout.addWidget(status_frame)

        # Direct Forces Test Box
        test_box = QGroupBox("Teste de Força Direta (Direct Force Generator)")
        tb_layout = QGridLayout(test_box)

        tb_layout.addWidget(QLabel("Força de Mola (Spring):"), 0, 0)
        self.slider_test_spring = QSlider(Qt.Horizontal)
        self.slider_test_spring.setRange(-100, 100)
        self.slider_test_spring.setValue(0)
        tb_layout.addWidget(self.slider_test_spring, 0, 1)

        tb_layout.addWidget(QLabel("Força Constante:"), 1, 0)
        self.slider_test_constant = QSlider(Qt.Horizontal)
        self.slider_test_constant.setRange(-100, 100)
        self.slider_test_constant.setValue(0)
        tb_layout.addWidget(self.slider_test_constant, 1, 1)

        tb_layout.addWidget(QLabel("Vibração Periódica:"), 2, 0)
        self.slider_test_periodic = QSlider(Qt.Horizontal)
        self.slider_test_periodic.setRange(0, 100)
        self.slider_test_periodic.setValue(0)
        tb_layout.addWidget(self.slider_test_periodic, 2, 1)

        btn_reset_test = QPushButton("Zerar Forças de Teste")
        btn_reset_test.clicked.connect(self.reset_test_forces)
        tb_layout.addWidget(btn_reset_test, 3, 0, 1, 2)

        right_layout.addWidget(test_box)

        # Hardware maintenance buttons
        maint_layout = QHBoxLayout()
        btn_save = QPushButton("💾 Salvar na Flash & Reiniciar")
        btn_save.clicked.connect(self.on_save_and_reboot)
        maint_layout.addWidget(btn_save)

        btn_reboot = QPushButton("🔄 Reiniciar Placa")
        btn_reboot.clicked.connect(self.on_reboot)
        maint_layout.addWidget(btn_reboot)

        right_layout.addLayout(maint_layout)

        main_layout.addWidget(right_box, 1)
        return widget

    # ---------------- TAB 2: EFFECTS ----------------

    def create_effects_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)

        # Main Axis Box
        grp_axis = QGroupBox("Configurações do Eixo do Volante")
        g_axis = QGridLayout(grp_axis)

        # Motion Range
        g_axis.addWidget(QLabel("Ângulo de Rotação (Motion Range):"), 0, 0)
        self.spin_motion_range = QSpinBox()
        self.spin_motion_range.setRange(180, 2520)
        self.spin_motion_range.setValue(900)
        self.spin_motion_range.setSuffix("°")
        g_axis.addWidget(self.spin_motion_range, 0, 1)

        # Quick angle buttons
        btn_angles = QHBoxLayout()
        for deg in [360, 540, 900, 1080]:
            b = QPushButton(f"{deg}°")
            b.clicked.connect(lambda _, d=deg: self.spin_motion_range.setValue(d))
            btn_angles.addWidget(b)
        g_axis.addLayout(btn_angles, 0, 2)

        # Total Effect Strength
        g_axis.addWidget(QLabel("Força Total dos Efeitos:"), 1, 0)
        self.spin_total_strength = QSpinBox()
        self.spin_total_strength.setRange(0, 100)
        self.spin_total_strength.setValue(100)
        self.spin_total_strength.setSuffix("%")
        g_axis.addWidget(self.spin_total_strength, 1, 1)

        # Integrated Spring Strength
        g_axis.addWidget(QLabel("Mola Centralizadora Integrada:"), 2, 0)
        self.spin_integrated_spring = QSpinBox()
        self.spin_integrated_spring.setRange(0, 100)
        self.spin_integrated_spring.setValue(0)
        self.spin_integrated_spring.setSuffix("%")
        g_axis.addWidget(self.spin_integrated_spring, 2, 1)

        # Soft Stop Strength
        g_axis.addWidget(QLabel("Força do Batente Virtual (Soft Stop):"), 3, 0)
        self.spin_soft_stop_strength = QSpinBox()
        self.spin_soft_stop_strength.setRange(0, 100)
        self.spin_soft_stop_strength.setValue(80)
        self.spin_soft_stop_strength.setSuffix("%")
        g_axis.addWidget(self.spin_soft_stop_strength, 3, 1)

        # Soft Stop Range
        g_axis.addWidget(QLabel("Faixa do Batente (Soft Stop Range):"), 4, 0)
        self.spin_soft_stop_range = QSpinBox()
        self.spin_soft_stop_range.setRange(1, 45)
        self.spin_soft_stop_range.setValue(15)
        self.spin_soft_stop_range.setSuffix("°")
        g_axis.addWidget(self.spin_soft_stop_range, 4, 1)

        sc_layout.addWidget(grp_axis)

        # Dampening Box
        grp_damp = QGroupBox("Amortecimento & Resistência (Dampening)")
        g_damp = QGridLayout(grp_damp)

        g_damp.addWidget(QLabel("Amortecimento Estático (Static Dampening):"), 0, 0)
        self.spin_static_damp = QSpinBox()
        self.spin_static_damp.setRange(0, 100)
        self.spin_static_damp.setValue(20)
        self.spin_static_damp.setSuffix("%")
        g_damp.addWidget(self.spin_static_damp, 0, 1)

        g_damp.addWidget(QLabel("Amortecimento de Batente (Soft Stop Dampening):"), 1, 0)
        self.spin_soft_damp = QSpinBox()
        self.spin_soft_damp.setRange(0, 100)
        self.spin_soft_damp.setValue(50)
        self.spin_soft_damp.setSuffix("%")
        g_damp.addWidget(self.spin_soft_damp, 1, 1)

        g_damp.addWidget(QLabel("Amortecimento Dinâmico (Dynamic Dampening):"), 2, 0)
        self.spin_dynamic_damp = QSpinBox()
        self.spin_dynamic_damp.setRange(0, 100)
        self.spin_dynamic_damp.setValue(0)
        self.spin_dynamic_damp.setSuffix("%")
        g_damp.addWidget(self.spin_dynamic_damp, 2, 1)

        sc_layout.addWidget(grp_damp)

        # DirectX Forces Box
        grp_dx = QGroupBox("Efeitos DirectX / Jogos")
        g_dx = QGridLayout(grp_dx)

        g_dx.addWidget(QLabel("Força Constante DirectX:"), 0, 0)
        self.spin_dx_constant = QSpinBox()
        self.spin_dx_constant.setRange(0, 100)
        self.spin_dx_constant.setValue(100)
        self.spin_dx_constant.setSuffix("%")
        g_dx.addWidget(self.spin_dx_constant, 0, 1)

        g_dx.addWidget(QLabel("Força de Mola DirectX:"), 1, 0)
        self.spin_dx_spring = QSpinBox()
        self.spin_dx_spring.setRange(0, 100)
        self.spin_dx_spring.setValue(100)
        self.spin_dx_spring.setSuffix("%")
        g_dx.addWidget(self.spin_dx_spring, 1, 1)

        g_dx.addWidget(QLabel("Efeitos Periódicos (Vibração):"), 2, 0)
        self.spin_dx_periodic = QSpinBox()
        self.spin_dx_periodic.setRange(0, 100)
        self.spin_dx_periodic.setValue(100)
        self.spin_dx_periodic.setSuffix("%")
        g_dx.addWidget(self.spin_dx_periodic, 2, 1)

        self.chk_invert_constant = QCheckBox("Inverter Direção da Força Constante")
        g_dx.addWidget(self.chk_invert_constant, 3, 0, 1, 2)

        sc_layout.addWidget(grp_dx)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Bottom buttons
        btns = QHBoxLayout()
        btn_read = QPushButton("📥 Ler do Dispositivo")
        btn_read.clicked.connect(self.load_effects_from_device)
        btns.addWidget(btn_read)

        btn_apply = QPushButton("🚀 Enviar para o Volante")
        btn_apply.setObjectName("btnPrimary")
        btn_apply.clicked.connect(self.apply_effects_to_device)
        btns.addWidget(btn_apply)

        layout.addLayout(btns)
        return widget

    # ---------------- TAB 3: HARDWARE ----------------

    def create_hardware_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)

        # Motor Box
        grp_motor = QGroupBox("Parâmetros do Motor & Controlador ODrive")
        g_mot = QGridLayout(grp_motor)

        self.chk_enable_force = QCheckBox("Habilitar Força nos Motores (Enable Force)")
        self.chk_enable_force.setChecked(True)
        g_mot.addWidget(self.chk_enable_force, 0, 0, 1, 2)

        self.chk_debug_torque = QCheckBox("Modo Depuração de Força (Debug Torque)")
        g_mot.addWidget(self.chk_debug_torque, 1, 0, 1, 2)

        self.chk_invert_joy = QCheckBox("Inverter Saída do Joystick")
        g_mot.addWidget(self.chk_invert_joy, 2, 0)

        self.chk_invert_force = QCheckBox("Inverter Direção da Força")
        g_mot.addWidget(self.chk_invert_force, 2, 1)

        g_mot.addWidget(QLabel("Pares de Polos do Motor (Pole Pairs):"), 3, 0)
        self.spin_pole_pairs = QSpinBox()
        self.spin_pole_pairs.setRange(1, 50)
        self.spin_pole_pairs.setValue(15)  # Hoverboard default is 15
        g_mot.addWidget(self.spin_pole_pairs, 3, 1)

        g_mot.addWidget(QLabel("Resolução do Encoder (CPR):"), 4, 0)
        self.spin_encoder_cpr = QSpinBox()
        self.spin_encoder_cpr.setRange(100, 65535)
        self.spin_encoder_cpr.setValue(4000)
        g_mot.addWidget(self.spin_encoder_cpr, 4, 1)

        sc_layout.addWidget(grp_motor)

        # Power & Limits
        grp_power = QGroupBox("Limites de Potência e Frenagem")
        g_pow = QGridLayout(grp_power)

        g_pow.addWidget(QLabel("Limite de Potência do Motor (Power Limit):"), 0, 0)
        self.spin_power_limit = QSpinBox()
        self.spin_power_limit.setRange(0, 100)
        self.spin_power_limit.setValue(50)
        self.spin_power_limit.setSuffix("%")
        g_pow.addWidget(self.spin_power_limit, 0, 1)

        g_pow.addWidget(QLabel("Resistor de Frenagem (Braking Resistor Limit):"), 1, 0)
        self.spin_braking_limit = QSpinBox()
        self.spin_braking_limit.setRange(0, 100)
        self.spin_braking_limit.setValue(20)
        self.spin_braking_limit.setSuffix("%")
        g_pow.addWidget(self.spin_braking_limit, 1, 1)

        g_pow.addWidget(QLabel("Magnitude da Calibração Inicial:"), 2, 0)
        self.spin_calib_magnitude = QSpinBox()
        self.spin_calib_magnitude.setRange(1, 100)
        self.spin_calib_magnitude.setValue(10)
        self.spin_calib_magnitude.setSuffix("%")
        g_pow.addWidget(self.spin_calib_magnitude, 2, 1)

        g_pow.addWidget(QLabel("Velocidade da Calibração Inicial:"), 3, 0)
        self.spin_calib_speed = QSpinBox()
        self.spin_calib_speed.setRange(1, 100)
        self.spin_calib_speed.setValue(10)
        self.spin_calib_speed.setSuffix("%")
        g_pow.addWidget(self.spin_calib_speed, 3, 1)

        sc_layout.addWidget(grp_power)

        # Current PID & Sense
        grp_pid = QGroupBox("Ganhos de Corrente (PID Tuning)")
        g_pid = QGridLayout(grp_pid)

        g_pid.addWidget(QLabel("Ganho Proporcional (P Gain):"), 0, 0)
        self.spin_p_gain = QSpinBox()
        self.spin_p_gain.setRange(0, 255)
        self.spin_p_gain.setValue(30)
        g_pid.addWidget(self.spin_p_gain, 0, 1)

        g_pid.addWidget(QLabel("Ganho Integral (I Gain):"), 1, 0)
        self.spin_i_gain = QSpinBox()
        self.spin_i_gain.setRange(0, 65535)
        self.spin_i_gain.setValue(50)
        g_pid.addWidget(self.spin_i_gain, 1, 1)

        g_pid.addWidget(QLabel("Ganho do Amplificador de Corrente (Requer Reboot):"), 2, 0)
        self.combo_amp_gain = QComboBox()
        for k, v in AMPLIFIER_GAIN_NAMES.items():
            self.combo_amp_gain.addItem(v, k)
        g_pid.addWidget(self.combo_amp_gain, 2, 1)

        sc_layout.addWidget(grp_pid)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Bottom buttons
        btns = QHBoxLayout()
        btn_read = QPushButton("📥 Ler do Dispositivo")
        btn_read.clicked.connect(self.load_hardware_from_device)
        btns.addWidget(btn_read)

        btn_apply = QPushButton("🚀 Enviar para o Volante")
        btn_apply.setObjectName("btnPrimary")
        btn_apply.clicked.connect(self.apply_hardware_to_device)
        btns.addWidget(btn_apply)

        layout.addLayout(btns)
        return widget

    # ---------------- TAB 4: PERIPHERY ----------------

    def create_periphery_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)

        grp_pins = QGroupBox("Mapeamento de Pinos GPIO da Placa ODrive")
        g_pins = QGridLayout(grp_pins)

        self.pin_combos = []
        pin_labels = [
            "GPIO Pin 1", "GPIO Pin 2", "GPIO Pin 3", "GPIO Pin 4",
            "GPIO Pin 5", "GPIO Pin 6", "GPIO Pin 7", "GPIO Pin 8",
            "Encoder Z0", "Encoder Z1"
        ]

        for i, name in enumerate(pin_labels):
            row = i // 2
            col = (i % 2) * 2
            g_pins.addWidget(QLabel(f"{name}:"), row, col)
            cb = QComboBox()
            for p_mode, p_name in PIN_MODE_NAMES.items():
                cb.addItem(p_name, p_mode)
            g_pins.addWidget(cb, row, col + 1)
            self.pin_combos.append(cb)

        sc_layout.addWidget(grp_pins)

        grp_adc = QGroupBox("Entradas Analógicas / Pedais (ADC Deadzones)")
        g_adc = QGridLayout(grp_adc)

        self.adc_min_spins = []
        self.adc_max_spins = []
        for axis_i, axis_name in enumerate(["Eixo R1 (Acelerador)", "Eixo R2 (Freio)", "Eixo R3 (Embreagem)"]):
            g_adc.addWidget(QLabel(f"{axis_name} Mín:"), axis_i, 0)
            spin_min = QSpinBox()
            spin_min.setRange(0, 4095)
            spin_min.setValue(0)
            g_adc.addWidget(spin_min, axis_i, 1)
            self.adc_min_spins.append(spin_min)

            g_adc.addWidget(QLabel("Máx:"), axis_i, 2)
            spin_max = QSpinBox()
            spin_max.setRange(0, 4095)
            spin_max.setValue(4095)
            g_adc.addWidget(spin_max, axis_i, 3)
            self.adc_max_spins.append(spin_max)

        sc_layout.addWidget(grp_adc)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Buttons
        btns = QHBoxLayout()
        btn_read = QPushButton("📥 Ler Periféricos do Dispositivo")
        btn_read.clicked.connect(self.load_periphery_from_device)
        btns.addWidget(btn_read)

        btn_apply = QPushButton("🚀 Enviar Periféricos para o Volante")
        btn_apply.setObjectName("btnPrimary")
        btn_apply.clicked.connect(self.apply_periphery_to_device)
        btns.addWidget(btn_apply)

        layout.addLayout(btns)
        return widget

    # ---------------- TAB 5: PROFILES ----------------

    def create_profiles_tab(self) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # Profile List
        list_box = QGroupBox("Perfis de Jogos Salvos")
        lb_layout = QVBoxLayout(list_box)

        self.list_profiles = QListWidget()
        self.list_profiles.currentTextChanged.connect(self.on_profile_selected)
        lb_layout.addWidget(self.list_profiles)

        btn_refresh_p = QPushButton("🔄 Atualizar Lista")
        btn_refresh_p.clicked.connect(self.refresh_profiles_list)
        lb_layout.addWidget(btn_refresh_p)

        layout.addWidget(list_box, 1)

        # Details and Actions
        details_box = QGroupBox("Detalhes & Aplicação")
        d_layout = QVBoxLayout(details_box)

        self.lbl_profile_title = QLabel("Selecione um perfil")
        self.lbl_profile_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #58b2ff;")
        d_layout.addWidget(self.lbl_profile_title)

        self.lbl_profile_desc = QLabel("")
        self.lbl_profile_desc.setWordWrap(True)
        d_layout.addWidget(self.lbl_profile_desc)

        self.lbl_profile_summary = QLabel("")
        d_layout.addWidget(self.lbl_profile_summary)

        d_layout.addStretch()

        btn_apply_prof = QPushButton("🚀 Carregar e Aplicar no Volante")
        btn_apply_prof.setObjectName("btnPrimary")
        btn_apply_prof.clicked.connect(self.apply_selected_profile)
        d_layout.addWidget(btn_apply_prof)

        btn_save_current = QPushButton("💾 Salvar Configurações Atuais como Novo Perfil...")
        btn_save_current.clicked.connect(self.save_as_new_profile)
        d_layout.addWidget(btn_save_current)

        layout.addWidget(details_box, 1)

        self.refresh_profiles_list()
        return widget

    # ---------------- TAB 6: IRACING SETUP ----------------

    def create_iracing_tab(self) -> QWidget:
        from ffbeast import find_iracing_ini_paths, read_ini_section_values, optimize_iracing_ini

        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)

        # 1. Path detection and selection box
        grp_path = QGroupBox("Localização do iRacing (Proton / Wine)")
        gp_layout = QVBoxLayout(grp_path)

        path_row = QHBoxLayout()
        self.combo_iracing_path = QComboBox()
        self.combo_iracing_path.setEditable(True)
        self.combo_iracing_path.currentIndexChanged.connect(self.on_iracing_path_changed)
        path_row.addWidget(self.combo_iracing_path, 1)

        btn_browse = QPushButton("📁 Procurar...")
        btn_browse.clicked.connect(self.browse_iracing_ini)
        path_row.addWidget(btn_browse)

        btn_rescan = QPushButton("🔄 Re-escanear")
        btn_rescan.clicked.connect(self.scan_iracing_paths)
        path_row.addWidget(btn_rescan)
        gp_layout.addLayout(path_row)

        self.lbl_iracing_status = QLabel("Procurando app.ini do iRacing...")
        self.lbl_iracing_status.setStyleSheet("color: #8b94a5; font-size: 12px;")
        gp_layout.addWidget(self.lbl_iracing_status)

        sc_layout.addWidget(grp_path)

        # 2. Key Direct Drive Parameters
        grp_params = QGroupBox("Parâmetros do app.ini para Volante Direct Drive (FFBeast)")
        g_par = QGridLayout(grp_params)

        self.ir_param_labels = {}
        target_keys = [
            ("enableLinearFFB", "Modo Linear (Linear FFB)", "1 (Obrigatório para Direct Drive)"),
            ("forceFeedbackMinForce", "Força Mínima (Min Force)", "0.0% (Zero para eliminar oscilação central)"),
            ("displayLinearInNm", "Exibição em Nm (displayLinearInNm)", "1 (Exibe força em Newton-metros no jogo)"),
            ("calibUsingRawData", "Leitura Bruta do Encoder (calibUsingRawData)", "1 (Precisão máxima sem compressão)"),
            ("reinitBetweenSessions", "Reinicialização entre sessões", "0 (Evita desconexão abrupta no Proton)"),
            ("steeringFFBSmooth", "Suavização FFB (steeringFFBSmooth)", "0 (Direct Drive não necessita de suavização)"),
        ]

        for i, (key, label_txt, tip_txt) in enumerate(target_keys):
            g_par.addWidget(QLabel(f"<b>{label_txt}:</b>"), i, 0)
            val_lbl = QLabel("...")
            val_lbl.setStyleSheet("font-weight: bold; color: #ffaa33;")
            g_par.addWidget(val_lbl, i, 1)
            tip_lbl = QLabel(f"<i>Ideal: {tip_txt}</i>")
            tip_lbl.setStyleSheet("color: #7b8495; font-size: 11px;")
            g_par.addWidget(tip_lbl, i, 2)
            self.ir_param_labels[key] = val_lbl

        sc_layout.addWidget(grp_params)

        # 3. Action Buttons
        btn_box = QHBoxLayout()
        btn_optimize_ini = QPushButton("🔧 Otimizar app.ini para FFBeast Direct Drive")
        btn_optimize_ini.setObjectName("btnPrimary")
        btn_optimize_ini.clicked.connect(self.optimize_iracing_current_ini)
        btn_box.addWidget(btn_optimize_ini)

        btn_apply_ir_profile = QPushButton("🏎️ Aplicar Perfil iRacing no Volante (900° Linear)")
        btn_apply_ir_profile.clicked.connect(self.apply_iracing_profile_to_wheel)
        btn_box.addWidget(btn_apply_ir_profile)
        sc_layout.addLayout(btn_box)

        # 4. Guide / Instructions
        grp_guide = QGroupBox("Guia de Calibração Dentro do iRacing")
        gg_layout = QVBoxLayout(grp_guide)

        guide_txt = QLabel("""
<p><b>Passo a Passo para Calibrar o FFBeast no iRacing:</b></p>
<ol>
  <li><b>Calibração do Volante no Menu do iRacing:</b>
    <ul>
      <li>Gire o volante até o batente máximo para a esquerda e para a direita.</li>
      <li>Centralize o volante perfeitamente e clique em Avançar.</li>
      <li>Gire o volante <b>90 graus</b> para a esquerda e confirme. O iRacing detectará automaticamente o ângulo calibrado (ex: 900°).</li>
    </ul>
  </li>
  <li><b>Configuração das Opções de Force Feedback (Drive Tab):</b>
    <ul>
      <li><b>Enable Force Feedback:</b> Marque esta opção.</li>
      <li><b>Linear Mode:</b> Marque esta caixa (Linear FFB).</li>
      <li><b>Min Force:</b> <b>0.0%</b> (Fundamental para Direct Drive).</li>
      <li><b>Max Force / Strength:</b> Ajuste de acordo com a força desejada (ex: 20 a 45 Nm no slider para evitar clipping). Durante a pilotagem, aperte F9 (black box de gráficos) e clique em <i>Auto</i> para calibrar o ganho perfeito sem clipping.</li>
      <li><b>Damping:</b> 0% a 5% (O perfil do FFBeast já gerencia o amortecimento estático ideal).</li>
    </ul>
  </li>
  <li><b>Status do Anti-Cheat (EAC) no Linux:</b>
    <p>O iRacing roda via Proton/Wine perfeitamente para <i>Test Drive</i>, <i>AI Racing</i>, <i>Treinos Locais</i> e replays. Corridas oficiais multijogador dependem do Easy Anti-Cheat que não tem o módulo Linux ativado oficialmente pela iRacing.</p>
  </li>
</ol>
        """)
        guide_txt.setWordWrap(True)
        gg_layout.addWidget(guide_txt)
        sc_layout.addWidget(grp_guide)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Initial scan
        self.scan_iracing_paths()
        return widget

    def scan_iracing_paths(self):
        from ffbeast import find_iracing_ini_paths
        self.combo_iracing_path.clear()
        paths = find_iracing_ini_paths()
        for p in paths:
            self.combo_iracing_path.addItem(p)

        if paths:
            self.lbl_iracing_status.setText(f"✅ {len(paths)} instalação(ões) do iRacing detectada(s).")
            self.lbl_iracing_status.setStyleSheet("color: #44dd66; font-size: 12px;")
            self.load_iracing_ini_display(paths[0])
        else:
            self.lbl_iracing_status.setText("⚠️ Nenhuma pasta do iRacing detectada automaticamente. Clique em 'Procurar...' para selecionar o app.ini.")
            self.lbl_iracing_status.setStyleSheet("color: #ffaa33; font-size: 12px;")

    def browse_iracing_ini(self):
        ini_file, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo app.ini do iRacing",
            os.path.expanduser("~"),
            "Arquivos de Configuração (*.ini);;Todos os arquivos (*)"
        )
        if ini_file:
            self.combo_iracing_path.insertItem(0, ini_file)
            self.combo_iracing_path.setCurrentIndex(0)
            self.load_iracing_ini_display(ini_file)

    def on_iracing_path_changed(self):
        path = self.combo_iracing_path.currentText().strip()
        if path and os.path.isfile(path):
            self.load_iracing_ini_display(path)

    def load_iracing_ini_display(self, path: str):
        from ffbeast import read_ini_section_values, RECOMMENDED_FFB_SETTINGS
        values = read_ini_section_values(path, "Force Feedback")
        for k, lbl in self.ir_param_labels.items():
            curr = values.get(k, "Não definido")
            is_optimal = (curr == RECOMMENDED_FFB_SETTINGS.get(k))
            color = "#44dd66" if is_optimal else "#ff5555"
            lbl.setText(curr)
            lbl.setStyleSheet(f"font-weight: bold; color: {color};")

    def optimize_iracing_current_ini(self):
        from ffbeast import optimize_iracing_ini
        path = self.combo_iracing_path.currentText().strip()
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo app.ini válido primeiro.")
            return

        ok, msg, changes = optimize_iracing_ini(path)
        if ok:
            detail = "\n".join(changes) if changes else "Todos os parâmetros já estavam otimizados!"
            QMessageBox.information(self, "Sucesso", f"{msg}\n\nModificações realizadas:\n{detail}")
            self.load_iracing_ini_display(path)
        else:
            QMessageBox.critical(self, "Erro", msg)

    def apply_iracing_profile_to_wheel(self):
        ir_prof = self.profile_manager.load_profile("iracing")
        if not ir_prof:
            QMessageBox.warning(self, "Aviso", "Perfil 'iracing.json' não foi encontrado.")
            return

        eff = ir_prof.get("effects", {})
        if "motion_range" in eff:
            self.spin_motion_range.setValue(eff["motion_range"])
        if "total_effect_strength" in eff:
            self.spin_total_strength.setValue(eff["total_effect_strength"])
        if "integrated_spring_strength" in eff:
            self.spin_integrated_spring.setValue(eff["integrated_spring_strength"])
        if "soft_stop_strength" in eff:
            self.spin_soft_stop_strength.setValue(eff["soft_stop_strength"])
        if "soft_stop_range" in eff:
            self.spin_soft_stop_range.setValue(eff["soft_stop_range"])
        if "static_dampening_strength" in eff:
            self.spin_static_damp.setValue(eff["static_dampening_strength"])
        if "soft_stop_dampening_strength" in eff:
            self.spin_soft_damp.setValue(eff["soft_stop_dampening_strength"])
        if "directx_constant_strength" in eff:
            self.spin_dx_constant.setValue(eff["directx_constant_strength"])
        if "directx_spring_strength" in eff:
            self.spin_dx_spring.setValue(eff["directx_spring_strength"])
        if "directx_periodic_strength" in eff:
            self.spin_dx_periodic.setValue(eff["directx_periodic_strength"])

        self.apply_effects_to_device()
        QMessageBox.information(self, "Sucesso", "Perfil 'iRacing (Direct Drive)' aplicado com sucesso no volante!")

    # ---------------- TAB 7: FIRMWARE & LINUX GUIDE ----------------

    def create_firmware_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        sc_layout = QVBoxLayout(scroll_content)

        grp_info = QGroupBox("Guia de Funcionamento no Linux (Fedora & KDE Plasma)")
        gi_layout = QVBoxLayout(grp_info)

        info_text = QLabel("""
<h3>Arquitetura FFBeast no Linux:</h3>
<p><b>1. Suporte Nativo do Kernel:</b> Seu sistema Linux (Fedora 44 / Kernel 6.12+) já inclui nativamente o módulo <code>hid-universal-pidff</code>, que reconhece o hardware FFBeast (VID 0x045B, PID 0x59D7) diretamente como um volante USB PID Force Feedback compatível com DirectInput / evdev.</p>
<p><b>2. Jogos na Steam / Proton:</b> Jogos como <i>Assetto Corsa, Assetto Corsa Competizione, BeamNG.drive, Euro Truck Simulator 2, Dirt Rally 2.0</i> funcionam diretamente via Proton. O Proton converte chamadas DirectInput FFB para as ioctls do Linux de forma automática.</p>
<p><b>3. Regras Udev:</b> O instalador configura o arquivo <code>/etc/udev/rules.d/99-ffbeast.rules</code> para permitir acesso ao volante sem permissões de root.</p>
        """)
        info_text.setWordWrap(True)
        gi_layout.addWidget(info_text)
        sc_layout.addWidget(grp_info)

        # Firmware Flashing section
        grp_dfu = QGroupBox("Gravação de Firmware (STM32 DFU Flasher)")
        gd_layout = QVBoxLayout(grp_dfu)

        gd_layout.addWidget(QLabel("Para atualizar o firmware da placa ODrive via USB:"))
        gd_layout.addWidget(QLabel("1. Clique em 'Entrar em Modo DFU' ou coloque o jumper DFU na placa ODrive."))
        gd_layout.addWidget(QLabel("2. O script gravará o firmware <code>ffbeast-wheel-odrive-RC.26.1.1.hex</code> via <code>dfu-util</code>."))

        btn_enter_dfu = QPushButton("⚡ Colocar Dispositivo em Modo DFU")
        btn_enter_dfu.setObjectName("btnDanger")
        btn_enter_dfu.clicked.connect(self.on_enter_dfu)
        gd_layout.addWidget(btn_enter_dfu)

        sc_layout.addWidget(grp_dfu)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return widget

    # ---------------- POLLING & DEVICE INTERACTIONS ----------------

    def check_connection(self):
        """Check USB device connection and update UI labels."""
        if self.device.connect():
            self.lbl_conn_status.setText(f"✅ Conectado: {self.device.device_type_name}")
            self.lbl_conn_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #44dd66;")
            self.status_bar.showMessage(f"Dispositivo conectado na interface USB 0 (Path: {self.device.device_info.get('path', b'')})")

            # Load initial settings from device
            self.load_effects_from_device()
            self.load_hardware_from_device()
        else:
            self.lbl_conn_status.setText("❌ Desconectado")
            self.lbl_conn_status.setStyleSheet("font-size: 15px; font-weight: bold; color: #ff5555;")
            self.status_bar.showMessage("Nenhum volante FFBeast encontrado.")

    def poll_device(self):
        """Periodic real-time poll for position and torque feedback."""
        if not self.device.is_connected():
            return

        state = self.device.read_state(timeout_ms=10)
        if state:
            self.lbl_fw_version.setText(f"Firmware: {state['firmware_version']}")
            self.lbl_reg_status.setText(f"Licença: {'PRO / Ativado' if state['is_registered'] else 'Livre / Light'}")

            pos = state["position"]
            torq = state["torque"]
            self.lbl_raw_position.setText(f"{pos:+d}")
            self.lbl_raw_torque.setText(f"{torq:+d}")

            # Calculate degrees based on current motion range
            range_deg = self.spin_motion_range.value() if self.spin_motion_range.value() > 0 else 900
            deg = (pos / 10000.0) * (range_deg / 2.0)
            self.wheel_view.set_angle(deg)
            self.wheel_view.set_torque(torq / 10000.0)

        # Check if direct test forces need to be sent
        sp = self.slider_test_spring.value()
        cf = self.slider_test_constant.value()
        pf = self.slider_test_periodic.value()
        if sp != 0 or cf != 0 or pf != 0:
            # Send direct control
            self.device.send_direct_control(
                spring_force=sp * 100,
                constant_force=cf * 100,
                periodic_force=pf * 100,
            )

    def reset_test_forces(self):
        self.slider_test_spring.setValue(0)
        self.slider_test_constant.setValue(0)
        self.slider_test_periodic.setValue(0)
        if self.device.is_connected():
            self.device.send_direct_control(0, 0, 0, 0)

    def on_center_wheel(self):
        if not self.device.is_connected():
            QMessageBox.warning(self, "Aviso", "Dispositivo não está conectado.")
            return
        if self.device.reset_center():
            self.status_bar.showMessage("Centro do volante redefinido com sucesso!", 3000)
        else:
            QMessageBox.critical(self, "Erro", "Falha ao enviar comando de centralização.")

    def on_save_and_reboot(self):
        if not self.device.is_connected():
            return
        res = QMessageBox.question(
            self,
            "Confirmar Gravação",
            "Deseja gravar as configurações atuais na memória FLASH da placa e reiniciar?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.device.save_and_reboot()
            self.status_bar.showMessage("Gravado com sucesso! A placa está reiniciando...", 5000)

    def on_reboot(self):
        if not self.device.is_connected():
            return
        self.device.reboot()
        self.status_bar.showMessage("Reiniciando a placa...", 3000)

    def on_enter_dfu(self):
        if not self.device.is_connected():
            return
        res = QMessageBox.warning(
            self,
            "Modo DFU",
            "A placa será reiniciada no bootloader STM32 DFU. Deseja continuar?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            self.device.switch_to_dfu()

    # ---------------- SETTINGS LOAD/APPLY ----------------

    def load_effects_from_device(self):
        eff = self.device.read_effect_settings()
        if not eff:
            return
        self.spin_motion_range.setValue(eff["motion_range"])
        self.spin_total_strength.setValue(eff["total_effect_strength"])
        self.spin_integrated_spring.setValue(eff["integrated_spring_strength"])
        self.spin_soft_stop_strength.setValue(eff["soft_stop_strength"])
        self.spin_soft_stop_range.setValue(eff["soft_stop_range"])
        self.spin_static_damp.setValue(eff["static_dampening_strength"])
        self.spin_soft_damp.setValue(eff["soft_stop_dampening_strength"])
        self.spin_dynamic_damp.setValue(eff["dynamic_dampening_strength"])
        self.spin_dx_constant.setValue(eff["directx_constant_strength"])
        self.spin_dx_spring.setValue(eff["directx_spring_strength"])
        self.spin_dx_periodic.setValue(eff["directx_periodic_strength"])
        self.chk_invert_constant.setChecked(eff["directx_constant_direction"] == -1)
        self.status_bar.showMessage("Configurações de efeitos lidas com sucesso.", 3000)

    def apply_effects_to_device(self):
        if not self.device.is_connected():
            QMessageBox.warning(self, "Aviso", "Dispositivo não está conectado.")
            return

        self.device.send_uint16_setting(SettingsFieldEnum.MOTION_RANGE, 0, self.spin_motion_range.value())
        self.device.send_uint8_setting(SettingsFieldEnum.TOTAL_EFFECT_STRENGTH, 0, self.spin_total_strength.value())
        self.device.send_uint8_setting(SettingsFieldEnum.INTEGRATED_SPRING_STRENGTH, 0, self.spin_integrated_spring.value())
        self.device.send_uint8_setting(SettingsFieldEnum.SOFT_STOP_STRENGTH, 0, self.spin_soft_stop_strength.value())
        self.device.send_uint8_setting(SettingsFieldEnum.SOFT_STOP_RANGE, 0, self.spin_soft_stop_range.value())
        self.device.send_uint16_setting(SettingsFieldEnum.STATIC_DAMPENING_STRENGTH, 0, self.spin_static_damp.value())
        self.device.send_uint16_setting(SettingsFieldEnum.SOFT_STOP_DAMPENING_STRENGTH, 0, self.spin_soft_damp.value())
        self.device.send_uint16_setting(SettingsFieldEnum.DYNAMIC_DAMPENING_STRENGTH, 0, self.spin_dynamic_damp.value())
        self.device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_CONSTANT_STRENGTH, 0, self.spin_dx_constant.value())
        self.device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_SPRING_STRENGTH, 0, self.spin_dx_spring.value())
        self.device.send_uint8_setting(SettingsFieldEnum.DIRECT_X_PERIODIC_STRENGTH, 0, self.spin_dx_periodic.value())
        inv_c = -1 if self.chk_invert_constant.isChecked() else 1
        self.device.send_int8_setting(SettingsFieldEnum.DIRECT_X_CONSTANT_DIRECTION, 0, inv_c)

        self.status_bar.showMessage("Configurações de efeitos enviadas para o volante!", 3000)

    def load_hardware_from_device(self):
        hw = self.device.read_hardware_settings()
        if not hw:
            return
        self.chk_enable_force.setChecked(hw["force_enabled"])
        self.chk_debug_torque.setChecked(hw["debug_torque"])
        self.chk_invert_joy.setChecked(hw["encoder_direction"] == -1)
        self.chk_invert_force.setChecked(hw["force_direction"] == -1)
        self.spin_pole_pairs.setValue(hw["pole_pairs"])
        self.spin_encoder_cpr.setValue(hw["encoder_cpr"])
        self.spin_power_limit.setValue(hw["power_limit"])
        self.spin_braking_limit.setValue(hw["braking_limit"])
        self.spin_calib_magnitude.setValue(hw["calibration_magnitude"])
        self.spin_calib_speed.setValue(hw["calibration_speed"])
        self.spin_p_gain.setValue(hw["proportional_gain"])
        self.spin_i_gain.setValue(hw["integral_gain"])

        idx = self.combo_amp_gain.findData(hw["amplifier_gain"])
        if idx >= 0:
            self.combo_amp_gain.setCurrentIndex(idx)

        self.status_bar.showMessage("Configurações de hardware lidas com sucesso.", 3000)

    def apply_hardware_to_device(self):
        if not self.device.is_connected():
            QMessageBox.warning(self, "Aviso", "Dispositivo não está conectado.")
            return

        self.device.send_uint8_setting(SettingsFieldEnum.FORCE_ENABLED, 0, 1 if self.chk_enable_force.isChecked() else 0)
        self.device.send_uint8_setting(SettingsFieldEnum.DEBUG_TORQUE, 0, 1 if self.chk_debug_torque.isChecked() else 0)
        self.device.send_int8_setting(SettingsFieldEnum.ENCODER_DIRECTION, 0, -1 if self.chk_invert_joy.isChecked() else 1)
        self.device.send_int8_setting(SettingsFieldEnum.FORCE_DIRECTION, 0, -1 if self.chk_invert_force.isChecked() else 1)
        self.device.send_uint8_setting(SettingsFieldEnum.POLE_PAIRS, 0, self.spin_pole_pairs.value())
        self.device.send_uint16_setting(SettingsFieldEnum.ENCODER_CPR, 0, self.spin_encoder_cpr.value())
        self.device.send_uint8_setting(SettingsFieldEnum.POWER_LIMIT, 0, self.spin_power_limit.value())
        self.device.send_uint8_setting(SettingsFieldEnum.BRAKING_LIMIT, 0, self.spin_braking_limit.value())
        self.device.send_uint8_setting(SettingsFieldEnum.CALIBRATION_MAGNITUDE, 0, self.spin_calib_magnitude.value())
        self.device.send_uint8_setting(SettingsFieldEnum.CALIBRATION_SPEED, 0, self.spin_calib_speed.value())
        self.device.send_uint8_setting(SettingsFieldEnum.P_GAIN, 0, self.spin_p_gain.value())
        self.device.send_uint16_setting(SettingsFieldEnum.I_GAIN, 0, self.spin_i_gain.value())
        self.device.send_uint8_setting(SettingsFieldEnum.AMPLIFIER_GAIN, 0, self.combo_amp_gain.currentData())

        self.status_bar.showMessage("Configurações de hardware enviadas para o volante!", 3000)

    def load_periphery_from_device(self):
        gpio = self.device.read_gpio_settings()
        if gpio and "pin_modes" in gpio:
            for i, mode_val in enumerate(gpio["pin_modes"]):
                if i < len(self.pin_combos):
                    idx = self.pin_combos[i].findData(mode_val)
                    if idx >= 0:
                        self.pin_combos[i].setCurrentIndex(idx)

        adc = self.device.read_adc_settings()
        if adc:
            for i in range(min(3, len(self.adc_min_spins))):
                self.adc_min_spins[i].setValue(adc["axis_min"][i])
                self.adc_max_spins[i].setValue(adc["axis_max"][i])

        self.status_bar.showMessage("Periféricos lidos com sucesso.", 3000)

    def apply_periphery_to_device(self):
        if not self.device.is_connected():
            return
        for i, cb in enumerate(self.pin_combos):
            self.device.send_uint8_setting(SettingsFieldEnum.PIN_MODE, i, cb.currentData())

        for i in range(min(3, len(self.adc_min_spins))):
            self.device.send_uint16_setting(SettingsFieldEnum.ADC_MIN_DEAD_ZONE, i, self.adc_min_spins[i].value())
            self.device.send_uint16_setting(SettingsFieldEnum.ADC_MAX_DEAD_ZONE, i, self.adc_max_spins[i].value())

        self.status_bar.showMessage("Periféricos gravados no volante!", 3000)

    # ---------------- PROFILES ----------------

    def refresh_profiles_list(self):
        self.list_profiles.clear()
        profiles = self.profile_manager.list_profiles()
        for p in profiles:
            self.list_profiles.addItem(p)
        if profiles:
            self.list_profiles.setCurrentRow(0)

    def on_profile_selected(self, name: str):
        if not name:
            return
        data = self.profile_manager.load_profile(name)
        if not data:
            return
        self.lbl_profile_title.setText(data.get("name", name))
        self.lbl_profile_desc.setText(data.get("description", "Sem descrição"))

        eff = data.get("effects", {})
        summary = (
            f"<b>Ângulo:</b> {eff.get('motion_range', 900)}° | "
            f"<b>Força Total:</b> {eff.get('total_effect_strength', 100)}% | "
            f"<b>Mola Integrada:</b> {eff.get('integrated_spring_strength', 0)}%<br>"
            f"<b>Amortecimento Estático:</b> {eff.get('static_dampening_strength', 20)}% | "
            f"<b>Batente Soft Stop:</b> {eff.get('soft_stop_strength', 80)}%"
        )
        self.lbl_profile_summary.setText(summary)

    def apply_selected_profile(self):
        cur = self.list_profiles.currentItem()
        if not cur:
            return
        name = cur.text()
        data = self.profile_manager.load_profile(name)
        if not data:
            return

        eff = data.get("effects", {})
        if "motion_range" in eff:
            self.spin_motion_range.setValue(eff["motion_range"])
        if "total_effect_strength" in eff:
            self.spin_total_strength.setValue(eff["total_effect_strength"])
        if "integrated_spring_strength" in eff:
            self.spin_integrated_spring.setValue(eff["integrated_spring_strength"])
        if "soft_stop_strength" in eff:
            self.spin_soft_stop_strength.setValue(eff["soft_stop_strength"])
        if "soft_stop_range" in eff:
            self.spin_soft_stop_range.setValue(eff["soft_stop_range"])
        if "static_dampening_strength" in eff:
            self.spin_static_damp.setValue(eff["static_dampening_strength"])
        if "soft_stop_dampening_strength" in eff:
            self.spin_soft_damp.setValue(eff["soft_stop_dampening_strength"])
        if "directx_constant_strength" in eff:
            self.spin_dx_constant.setValue(eff["directx_constant_strength"])
        if "directx_spring_strength" in eff:
            self.spin_dx_spring.setValue(eff["directx_spring_strength"])
        if "directx_periodic_strength" in eff:
            self.spin_dx_periodic.setValue(eff["directx_periodic_strength"])

        self.apply_effects_to_device()
        QMessageBox.information(self, "Sucesso", f"Perfil '{name}' aplicado com sucesso ao volante!")

    def save_as_new_profile(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Salvar Perfil", "Nome do novo perfil:")
        if ok and name.strip():
            slug = name.strip().lower().replace(" ", "_")
            data = {
                "name": name.strip(),
                "description": f"Perfil criado pelo usuário ({name.strip()})",
                "effects": {
                    "motion_range": self.spin_motion_range.value(),
                    "total_effect_strength": self.spin_total_strength.value(),
                    "integrated_spring_strength": self.spin_integrated_spring.value(),
                    "soft_stop_strength": self.spin_soft_stop_strength.value(),
                    "soft_stop_range": self.spin_soft_stop_range.value(),
                    "static_dampening_strength": self.spin_static_damp.value(),
                    "soft_stop_dampening_strength": self.spin_soft_damp.value(),
                    "dynamic_dampening_strength": self.spin_dynamic_damp.value(),
                    "directx_constant_strength": self.spin_dx_constant.value(),
                    "directx_spring_strength": self.spin_dx_spring.value(),
                    "directx_periodic_strength": self.spin_dx_periodic.value(),
                    "directx_constant_direction": -1 if self.chk_invert_constant.isChecked() else 1,
                },
                "hardware": {
                    "encoder_cpr": self.spin_encoder_cpr.value(),
                    "integral_gain": self.spin_i_gain.value(),
                    "proportional_gain": self.spin_p_gain.value(),
                    "force_enabled": self.chk_enable_force.isChecked(),
                    "debug_torque": self.chk_debug_torque.isChecked(),
                    "amplifier_gain": self.combo_amp_gain.currentData(),
                    "calibration_magnitude": self.spin_calib_magnitude.value(),
                    "calibration_speed": self.spin_calib_speed.value(),
                    "power_limit": self.spin_power_limit.value(),
                    "braking_limit": self.spin_braking_limit.value(),
                    "pole_pairs": self.spin_pole_pairs.value(),
                    "encoder_direction": -1 if self.chk_invert_joy.isChecked() else 1,
                    "force_direction": -1 if self.chk_invert_force.isChecked() else 1,
                }
            }
            self.profile_manager.save_profile(slug, data)
            self.refresh_profiles_list()
            QMessageBox.information(self, "Salvo", f"Perfil '{name}' salvo com sucesso!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
