from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox,
    QSlider, QSpinBox, QCheckBox, QGridLayout, QGroupBox,
    QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer

import sys
import csv
import os
try:
    from DM_CAN import MotorControl, Motor, Control_Type
except ImportError:
    MotorControl = None
    Motor = None
    Control_Type = None

class mainGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DM tool")
        self.resize(1200, 800)
        # メインレイアウト（垂直）
        self.main_layout = QVBoxLayout(self)

        # 接続管理
        self.motor_control = None
        self.is_connected = False
        self.last_ports = []

        # 1. ツールバー領域（画像の上部グレー部分を再現）
        self.create_toolbar_mimic()

        # スクロールエリアの追加（画面が小さくなってもスクロール可能にする）
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.central_widget = QWidget()
        self.central_grid = QGridLayout(self.central_widget)
        
        # グリッドの間隔を調整
        self.central_grid.setSpacing(10)

        # 設定値を辞書で管理（以前と同様）
        self.settings_dict = {}

        # 2. 各セクションの作成とグリッドへの配置
        # (行, 列) の位置は画像に基づいています。

        # --- 1行目 ---
        # (0, 0) 接続 (Connection)
        self.central_grid.addWidget(self.create_connection_group(), 0, 0)
        
        # (0, 1) ID/FeedBack (ID/FeedBack)
        self.central_grid.addWidget(self.create_id_feedback_group(), 0, 1)
        
        # (0, 2) 動作 (Motion)
        self.central_grid.addWidget(self.create_motion_group(), 0, 2)

        # --- 2行目 ---
        # (1, 0) 各種ボタン (Action Buttons)
        # 画像では2行目の左下エリアに配置
        self.central_grid.addWidget(self.create_action_buttons_group(), 1, 0)
        
        # (1, 1) 保護まわり (Protection)
        self.central_grid.addWidget(self.create_protection_group(), 1, 1)
        
        # (1, 2) ゲイン (Gain)
        self.central_grid.addWidget(self.create_gain_group(), 1, 2)

        # 各列の伸縮比率を設定 (ID/Protectionのある中央を広くするなど)
        self.central_grid.setColumnStretch(0, 1)
        self.central_grid.setColumnStretch(1, 2)
        self.central_grid.setColumnStretch(2, 1)
        # 各行の伸縮比率
        self.central_grid.setRowStretch(0, 1)
        self.central_grid.setRowStretch(1, 1)

        self.scroll_area.setWidget(self.central_widget)
        self.main_layout.addWidget(self.scroll_area)

        # ボタンのシグナルを接続
        self.setup_button_signals()

    def setup_button_signals(self):
        """ボタンのシグナルをセットアップ"""
        self.connect_btn.clicked.connect(self.on_connect)
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        
        # インターフェースタイプ変更時にシグナル接続
        self.interface_type.currentTextChanged.connect(self.on_interface_type_changed)
        
        # インターフェース更新タイマーをセットアップ
        self.interface_update_timer = QTimer()
        self.interface_update_timer.timeout.connect(self.update_interface_periodically)
        self.interface_update_timer.start(1000)  # 1秒ごとに更新

    def on_connect(self):
        """接続ボタン押下時の処理"""
        if MotorControl is None or Motor is None:
            print("Error: DM_CAN module not found")
            return
        
        try:
            interface_type = self.interface_type.currentText().lower()
            interface = self.can_interface.currentText()
            if interface == "利用可能なインターフェースなし" or interface == "利用可能なシリアルポートなし":
                print("Error: No CAN interface available")
                return
                
            bitrate = int(self.bitrate.currentText())
            motor_type_text = self.motor_type.currentText()
            motor_id = self.motor_id.value()
            
            # モータータイプのマッピング（文字列をインデックスに変換）
            motor_type_map = {
                "DM4310": 0, "DM4310_48V": 1, "DM4340": 2, "DM4340_48V": 3,
                "DM6006": 4, "DM8006": 5, "DM8009": 6, "DM10010L": 7,
                "DM10010": 8, "DMH3510": 9, "DMG62150": 10, "DMH6220": 11
            }
            motor_type_idx = motor_type_map.get(motor_type_text, 0)
            
            # MotorControl オブジェクトを作成（インターフェースタイプを指定）
            self.motor_control = MotorControl(interface, bitrate, interface_type)
            
            # Motor オブジェクトを追加
            motor = Motor(motor_type_idx, motor_id, 0)
            self.motor_control.addMotor(motor)
            
            self.is_connected = True
            self.update_connection_indicator()
            self.interface_type.setEnabled(False)
            self.can_interface.setEnabled(False)
            self.bitrate.setEnabled(False)
            self.motor_type.setEnabled(False)
            self.motor_id.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            print(f"Connected to {interface} ({interface_type}) - Motor: {motor_type_text} (ID: {motor_id})")
        except Exception as e:
            print(f"Connection error: {e}")
            import traceback
            traceback.print_exc()
            self.is_connected = False
            self.update_connection_indicator()

    def on_disconnect(self):
        """切断ボタン押下時の処理"""
        try:
            if self.motor_control is not None:
                # CANインターフェースの切断
                if hasattr(self.motor_control, 'can_interface'):
                    self.motor_control.can_interface.disconnect()
            self.is_connected = False
            self.motor_control = None
            self.update_connection_indicator()
            self.interface_type.setEnabled(True)
            self.can_interface.setEnabled(True)
            self.bitrate.setEnabled(True)
            self.motor_type.setEnabled(True)
            self.motor_id.setEnabled(True)
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            print("Disconnected")
        except Exception as e:
            print(f"Disconnection error: {e}")

    def update_connection_indicator(self):
        """接続状態インジケータを更新"""
        if self.is_connected:
            self.connection_indicator.setStyleSheet("color: green; font-size: 18px;")
        else:
            self.connection_indicator.setStyleSheet("color: red; font-size: 18px;")

    # ==============================
    # ツールバー（模倣）
    # ==============================
    def create_toolbar_mimic(self):
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #f0f0f0; border-radius: 10px;")
        toolbar.setFixedHeight(50)
        self.main_layout.addWidget(toolbar)

    # ==============================
    # ユーティリティ関数
    # ==============================
    def update_interface_periodically(self):
        """利用可能なCANインターフェースまたはシリアルポートを定期的に更新"""
        interface_type = self.interface_type.currentText()
        if interface_type.lower() == "slcan":
            self.update_serial_ports()
        else:
            self.update_can_interfaces()
    
    def update_can_interfaces(self):
        """利用可能なCANインターフェースを定期的に更新"""
        current_interfaces = self.get_available_can_interfaces()
        
        # インターフェースのリストが変更された場合のみ更新
        if current_interfaces != self.last_ports:
            self.last_ports = current_interfaces
            
            # 接続していない場合のみインターフェース選択肢を更新
            if not self.is_connected:
                current_selection = self.can_interface.currentText()
                self.can_interface.clear()
                self.can_interface.addItems(current_interfaces)
                
                # 以前選択されていたインターフェースが存在すれば復元
                index = self.can_interface.findText(current_selection)
                if index >= 0:
                    self.can_interface.setCurrentIndex(index)

    # ==============================
    # ==============================
    def get_available_can_interfaces(self):
        """利用可能なCANインターフェースを取得"""
        interfaces = []
        # /sys/class/net/を確認してCANインターフェースを探す
        try:
            if os.path.exists('/sys/class/net'):
                for interface in os.listdir('/sys/class/net'):
                    if interface.startswith('can') or interface.startswith('vcan'):
                        interfaces.append(interface)
        except Exception as e:
            print(f"Error detecting CAN interfaces: {e}")
        
        return sorted(interfaces) if interfaces else ["利用可能なインターフェースなし"]
    
    def get_available_serial_ports(self):
        """利用可能なシリアルポートを取得"""
        import glob
        ports = []
        try:
            # Linux上のシリアルポートを探す
            if os.path.exists('/dev'):
                # ttyUSB*, ttyACM* などを探す
                for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/ttyS*']:
                    ports.extend(glob.glob(pattern))
        except Exception as e:
            print(f"Error detecting serial ports: {e}")
        
        return sorted(ports) if ports else ["利用可能なシリアルポートなし"]
    
    def update_serial_ports(self):
        """利用可能なシリアルポートを定期的に更新"""
        current_ports = self.get_available_serial_ports()
        
        # ポートのリストが変更された場合のみ更新
        if current_ports != self.last_ports:
            self.last_ports = current_ports
            
            # 接続していない場合のみポート選択肢を更新
            if not self.is_connected:
                current_selection = self.can_interface.currentText()
                self.can_interface.clear()
                self.can_interface.addItems(current_ports)
                
                # 以前選択されていたポートが存在すれば復元
                index = self.can_interface.findText(current_selection)
                if index >= 0:
                    self.can_interface.setCurrentIndex(index)

    # ==============================
    # 各セクション作成用メソッド
    # ==============================

    # --- (0, 0) 接続 ---
    def create_connection_group(self):
        group = QGroupBox("接続")
        layout = QGridLayout()

        row = 0
        
        # インターフェースタイプ
        layout.addWidget(QLabel("インターフェースタイプ"), row, 0)
        self.interface_type = QComboBox()
        self.interface_type.addItems(["SocketCAN", "SLCAN"])
        self.interface_type.setFixedWidth(300)
        layout.addWidget(self.interface_type, row, 1)
        row += 1
        
        # インターフェース/シリアルポート（ラベルは動的に変更される）
        self.interface_label = QLabel("CANインターフェース")
        layout.addWidget(self.interface_label, row, 0)
        self.can_interface = QComboBox()
        available_interfaces = self.get_available_can_interfaces()
        self.can_interface.addItems(available_interfaces)
        self.can_interface.setFixedWidth(300)
        layout.addWidget(self.can_interface, row, 1)
        row += 1
        
        # CANビットレート
        layout.addWidget(QLabel("CANビットレート"), row, 0)
        self.bitrate = QComboBox()
        self.bitrate.addItems(["1000000", "500000", "250000", "125000"])
        self.bitrate.setCurrentText("1000000")
        layout.addWidget(self.bitrate, row, 1)
        row += 1
        
        # モータータイプ
        layout.addWidget(QLabel("モーターの種類"), row, 0)
        self.motor_type = QComboBox()
        self.motor_type.addItems(["DM4310", "DM4310_48V", "DM4340", "DM4340_48V", "DM6006", "DM8006", "DM8009", "DM10010L", "DM10010", "DMH3510", "DMG62150", "DMH6220"])
        layout.addWidget(self.motor_type, row, 1)
        row += 1
        
        # モーターID
        layout.addWidget(QLabel("モーターID"), row, 0)
        self.motor_id = QSpinBox()
        self.motor_id.setRange(0, 127)
        self.motor_id.setValue(1)
        layout.addWidget(self.motor_id, row, 1)
        row += 1
        
        # 接続状態インジケータ
        layout.addWidget(QLabel("接続状態"), row, 0)
        self.connection_indicator = QLabel("●")
        self.connection_indicator.setStyleSheet("color: red; font-size: 18px;")
        self.is_connected = False
        layout.addWidget(self.connection_indicator, row, 1)
        row += 1
        
        # 接続・切断ボタン
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("接続")
        self.disconnect_btn = QPushButton("切断")
        self.disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self.connect_btn)
        btn_layout.addWidget(self.disconnect_btn)
        layout.addLayout(btn_layout, row, 0, 1, 2)
        row += 1
        
        layout.setRowStretch(row, 1)
        group.setLayout(layout)
        return group
    
    def on_interface_type_changed(self):
        """インターフェースタイプが変更された時の処理"""
        self.update_interface_display()
    
    def update_interface_display(self):
        """インターフェースタイプに応じてラベルと選択肢を更新"""
        interface_type = self.interface_type.currentText()
        if interface_type.lower() == "slcan":
            self.interface_label.setText("シリアルポート")
            if not self.is_connected:
                current_selection = self.can_interface.currentText()
                self.can_interface.clear()
                self.can_interface.addItems(self.get_available_serial_ports())
                # 以前選択されていたポートが存在すれば復元
                index = self.can_interface.findText(current_selection)
                if index >= 0:
                    self.can_interface.setCurrentIndex(index)
        else:
            self.interface_label.setText("CANインターフェース")
            if not self.is_connected:
                current_selection = self.can_interface.currentText()
                self.can_interface.clear()
                self.can_interface.addItems(self.get_available_can_interfaces())
                # 以前選択されていたインターフェースが存在すれば復元
                index = self.can_interface.findText(current_selection)
                if index >= 0:
                    self.can_interface.setCurrentIndex(index)

    # --- (0, 1) ID / FeedBack ---
    def create_id_feedback_group(self):
        group = QGroupBox("ID") # 画像では「ID ESC-ID Feed back」
        layout = QGridLayout()

        row = 0
        # MST_ID [0, 0x7FF]
        layout.addWidget(QLabel("MST_ID"), row, 0)
        self.MST_ID = QSpinBox()
        self.MST_ID.setRange(0, 0x7FF)
        self.MST_ID.setDisplayIntegerBase(16) # 16進数表示に
        layout.addWidget(self.MST_ID, row, 1)
        self.settings_dict["MST_ID"] = self.MST_ID
        row += 1

        # ESC_ID [0, 0x7FF]
        layout.addWidget(QLabel("ESC_ID"), row, 0)
        self.ESC_ID = QSpinBox()
        self.ESC_ID.setRange(0, 0x7FF)
        self.ESC_ID.setDisplayIntegerBase(16)
        layout.addWidget(self.ESC_ID, row, 1)
        self.settings_dict["ESC_ID"] = self.ESC_ID
        row += 1
        

        layout.addWidget(QLabel("-------------------"), row, 0, 1, 2, Qt.AlignCenter)
        row += 1
        
        layout.addWidget(QLabel("CANボーレート"), row, 0)
        self.can_br = QSpinBox()
        self.can_br.setRange(0, 4)
        layout.addWidget(self.can_br, row, 1)
        self.settings_dict["can_br"] = self.can_br
        row += 1


        layout.addWidget(QLabel("Feed back"), row, 0)
        self.feed_back_label = QLabel("0.0")
        self.feed_back_label.setStyleSheet("border: 1px solid gray; padding: 2px;")
        layout.addWidget(self.feed_back_label, row, 1)
        
        layout.setRowStretch(row + 1, 1) # 残りのスペースを伸縮
        group.setLayout(layout)
        return group

    # --- (0, 2) 動作 ---
    def create_motion_group(self):
        group = QGroupBox("動作")
        layout = QGridLayout()
        
        items = [
            ("CTRL_MODE", self, QSpinBox, (1, 4), "CTRL_MODE (制御モード)"),
            ("MAX_SPD", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "MAX_SPD (最大速度)"),
            ("ACC", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "ACC (加速)"),
            ("DEC", self, QDoubleSpinBox, (-3.4e38, 0.0, 2), "DEC (減速)"),
            ("PMAX", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "PMAX (位置マップ)"),
            ("VMAX", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "VMAX (速度マップ)"),
            ("TMAX", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "TMAX (トルクマップ)"),
            ("KT_Value", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "KT_Value (トルク係数)"),
            ("I_BW", self, QDoubleSpinBox, (100.0, 10000.0, 2), "I_BW (電流ループ帯域)"),
        ]

        for i, (key, obj, widget_class, range_info, label_text) in enumerate(items):
            layout.addWidget(QLabel(label_text), i, 0)
            widget = widget_class()
            if widget_class == QDoubleSpinBox:
                widget.setRange(range_info[0], range_info[1])
                widget.setDecimals(range_info[2])
            else:
                widget.setRange(range_info[0], range_info[1])
            setattr(obj, key, widget) # self.KEY = widget と同じ
            layout.addWidget(widget, i, 1)
            self.settings_dict[key] = widget
            
        layout.setRowStretch(len(items), 1)
        group.setLayout(layout)
        return group

    # --- (1, 0) 各種ボタン ---
    def create_action_buttons_group(self):
        # 画像の「モーターへ」と「設定ファイル」の読み書きボタンを再現
        group = QGroupBox("")
        layout = QVBoxLayout()
        
        # モーターへ読み書き
        motor_label = QLabel("motor")
        motor_label.setAlignment(Qt.AlignCenter)
        motor_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(motor_label)
        
        motor_btns_layout = QHBoxLayout()
        self.motor_write_btn = QPushButton("書き込み")
        self.motor_read_btn = QPushButton("読み込み")
        motor_btns_layout.addWidget(self.motor_write_btn)
        motor_btns_layout.addWidget(self.motor_read_btn)
        layout.addLayout(motor_btns_layout)
        
        # スペーサー
        layout.addWidget(QLabel(" "))
        
        # 設定ファイル読み書き
        file_label = QLabel("設定ファイル")
        file_label.setAlignment(Qt.AlignCenter)
        file_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(file_label)
        
        file_btns_layout = QHBoxLayout()
        self.save_btn = QPushButton("書き込み") # 元の save_btn
        self.load_btn = QPushButton("読み込み") # 元の load_btn
        file_btns_layout.addWidget(self.save_btn)
        file_btns_layout.addWidget(self.load_btn)
        layout.addLayout(file_btns_layout)
        
        layout.addStretch() # 下部にスペースを作る
        group.setLayout(layout)
        return group

    # --- (1, 1) 保護まわり ---
    def create_protection_group(self):
        group = QGroupBox("保護まわり")
        # 元のコードで【保護】セクションにあった項目を配置
        layout = QGridLayout()
        
        items = [
            ("OV_Value", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "OV_Value (過電圧)"),
            ("UV_Value", self, QDoubleSpinBox, (10.0, 3.4e38, 2), "UV_Value (低電圧)"),
            ("OC_Value", self, QDoubleSpinBox, (0.0, 1.0, 3), "OC_Value (過電流)"),
            ("OT_Value", self, QDoubleSpinBox, (80.0, 200.0, 2), "OT_Value (過熱)"),
            ("TIMEOUT", self, QSpinBox, (0, 2**31 - 1), "TIMEOUT (タイムアウト)"),
        ]

        for i, (key, obj, widget_class, range_info, label_text) in enumerate(items):
            layout.addWidget(QLabel(label_text), i, 0)
            widget = widget_class()
            if widget_class == QDoubleSpinBox:
                widget.setRange(range_info[0], range_info[1])
                widget.setDecimals(range_info[2])
            else:
                widget.setRange(range_info[0], range_info[1])
            setattr(obj, key, widget)
            layout.addWidget(widget, i, 1)
            self.settings_dict[key] = widget
            
        layout.setRowStretch(len(items), 1)
        group.setLayout(layout)
        return group

    # --- (1, 2) ゲイン ---
    def create_gain_group(self):
        group = QGroupBox("ゲイン")
        # 元のコードで【ゲイン】セクションにあった項目を配置
        layout = QGridLayout()
        
        items = [
            ("KP_APR", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "KP_APR (位置Kp)"),
            ("KI_APR", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "KI_APR (位置Ki)"),
            ("KP_ASR", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "KP_ASR (速度Kp)"),
            ("KI_ASR", self, QDoubleSpinBox, (0.0, 3.4e38, 2), "KI_ASR (速度Ki)"),
            ("Deta", self, QDoubleSpinBox, (1.0, 30.0, 2), "Deta (ダンピング)"),
            ("V_BW", self, QDoubleSpinBox, (0.0, 500.0, 2), "V_BW (速度ループゲイン)"),
            ("IQ_V", self, QDoubleSpinBox, (100.0, 10000.0, 2), "IQ_V (電流ループゲイン)"),
            ("VL_c1", self, QDoubleSpinBox, (0.0, 10000.0, 2), "VL_c1 (速度ゲイン2)"),
        ]

        for i, (key, obj, widget_class, range_info, label_text) in enumerate(items):
            layout.addWidget(QLabel(label_text), i, 0)
            widget = widget_class()
            if widget_class == QDoubleSpinBox:
                widget.setRange(range_info[0], range_info[1])
                widget.setDecimals(range_info[2])
            else:
                widget.setRange(range_info[0], range_info[1])
            setattr(obj, key, widget)
            layout.addWidget(widget, i, 1)
            self.settings_dict[key] = widget
            
        layout.setRowStretch(len(items), 1)
        group.setLayout(layout)
        return group


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = mainGUI()
    window.show()
    sys.exit(app.exec())
