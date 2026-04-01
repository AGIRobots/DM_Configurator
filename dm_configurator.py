from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox,
    QSlider, QSpinBox, QCheckBox, QGridLayout, QGroupBox,
    QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QScrollArea, QFrame,
    QFileDialog, QMessageBox, QLineEdit, QInputDialog
)
from PySide6.QtCore import Qt, QTimer

import sys
import csv
import os
import subprocess
try:
    from DM_CAN import MotorControl, Motor, Control_Type, DM_variable
except ImportError:
    MotorControl = None
    Motor = None
    Control_Type = None
    DM_variable = None

try:
    from socketcan_initializer import SocketCANInitializer, CANConfig
except ImportError:
    SocketCANInitializer = None
    CANConfig = None


class mainGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DM config tool")
        self.resize(1200, 800)
        self.main_layout = QVBoxLayout(self)

        # 接続管理
        self.motor_control = None
        self.is_connected = False
        self.is_connecting = False  # 接続初期化中フラグ
        self.is_reconnecting = False  # 再接続フラグ
        self.last_ports = []
        self.cached_sudo_password = None  # SocketCANパスワードキャッシュ
        
        # 起動時に利用可能なデバイスを検出
        self.detected_interface_type = self.detect_available_interface()



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

        # --- 1行目 ---
        # (0, 0) 接続 (Connection)
        self.central_grid.addWidget(self.create_connection_group(), 0, 0)
        
        # (0, 1) ID/FeedBack (ID/FeedBack)
        self.central_grid.addWidget(self.create_id_feedback_group(), 0, 1)
        
        # (0, 2) 動作 (Motion)
        self.central_grid.addWidget(self.create_motion_group(), 0, 2)

        # --- 2行目 ---
        # (1, 0) 各種ボタン (Action Buttons)
        self.central_grid.addWidget(self.create_action_buttons_group(), 1, 0)
        
        # (1, 1) 保護まわり (Protection)
        self.central_grid.addWidget(self.create_protection_group(), 1, 1)
        
        # (1, 2) ゲイン (Gain)
        self.central_grid.addWidget(self.create_gain_group(), 1, 2)

        # 各列の伸縮比率を設定 (ID/Protectionのある中央を広くするなど)
        self.central_grid.setColumnStretch(0, 1)
        self.central_grid.setColumnStretch(1, 2)
        self.central_grid.setColumnStretch(2, 1)
        self.central_grid.setRowStretch(0, 1)
        self.central_grid.setRowStretch(1, 1)

        self.scroll_area.setWidget(self.central_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.setup_button_signals()

    def setup_button_signals(self):
        """ボタンのシグナルをセットアップ"""
        self.connect_btn.clicked.connect(self.on_connect)
        self.disconnect_btn.clicked.connect(self.on_disconnect)
        
        # インターフェースタイプ変更時にシグナル接続
        self.interface_type.currentTextChanged.connect(self.on_interface_type_changed)
        
        # モーター関連ボタンのシグナル接続
        self.motor_read_btn.clicked.connect(self.on_motor_read)
        self.motor_write_btn.clicked.connect(self.on_motor_write)
        self.motor_save_btn.clicked.connect(self.on_motor_save)
        
        # 設定ファイル関連ボタンのシグナル接続
        self.save_btn.clicked.connect(self.on_save_config)
        self.load_btn.clicked.connect(self.on_load_config)
        
        # ウィジェット値変更時のシグナル接続（リアルタイム送信）
        self.connect_widget_signals()
        
        # インターフェース更新タイマーをセットアップ
        self.interface_update_timer = QTimer()
        self.interface_update_timer.timeout.connect(self.update_interface_periodically)
        self.interface_update_timer.start(1000)  # 1秒ごとに更新

    def connect_widget_signals(self):
        # パラメータとウィジェットのマッピング
        widget_params = [
            ("MST_ID", DM_variable.MST_ID, self.MST_ID),
            ("ESC_ID", DM_variable.ESC_ID, self.ESC_ID),
            ("can_br", DM_variable.can_br, self.can_br),
            ("OV_Value", DM_variable.OV_Value, self.OV_Value),
            ("UV_Value", DM_variable.UV_Value, self.UV_Value),
            ("OC_Value", DM_variable.OC_Value, self.OC_Value),
            ("OT_Value", DM_variable.OT_Value, self.OT_Value),
            ("TIMEOUT", DM_variable.TIMEOUT, self.TIMEOUT),
            ("KP_APR", DM_variable.KP_APR, self.KP_APR),
            ("KI_APR", DM_variable.KI_APR, self.KI_APR),
            ("KP_ASR", DM_variable.KP_ASR, self.KP_ASR),
            ("KI_ASR", DM_variable.KI_ASR, self.KI_ASR),
            ("CTRL_MODE", DM_variable.CTRL_MODE, self.CTRL_MODE),
            ("MAX_SPD", DM_variable.MAX_SPD, self.MAX_SPD),
            ("ACC", DM_variable.ACC, self.ACC),
            ("DEC", DM_variable.DEC, self.DEC),
            ("PMAX", DM_variable.PMAX, self.PMAX),
            ("VMAX", DM_variable.VMAX, self.VMAX),
            ("TMAX", DM_variable.TMAX, self.TMAX),
            ("KT_Value", DM_variable.KT_Value, self.KT_Value),
            ("I_BW", DM_variable.I_BW, self.I_BW),
            ("V_BW", DM_variable.V_BW, self.V_BW),
            ("VL_c1", DM_variable.VL_c1, self.VL_c1),
            ("Deta", DM_variable.Deta, self.Deta),
        ]
        
        for param_name, rid, widget in widget_params:
            if isinstance(widget, QLineEdit) and param_name in ("ESC_ID", "MST_ID"):
                widget.editingFinished.connect(lambda p=param_name, r=rid, w=widget: self.on_hex_value_changed(p, r, w.text()))
            elif isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                widget.editingFinished.connect(lambda p=param_name, r=rid, w=widget: self.on_widget_value_changed(p, r, w.value()))
            elif isinstance(widget, QComboBox) and param_name == "can_br":
                widget.currentTextChanged.connect(lambda text, p=param_name, r=rid: self.on_combo_value_changed(p, r, text))

    def on_connect(self):
        """接続ボタン押下時の処理"""
        # 既に接続中 or 接続済みの場合はスキップ
        if self.is_connecting or self.is_connected:
            print("Connection in progress or already connected")
            return
        
        if MotorControl is None or Motor is None:
            print("Error: DM_CAN module not found")
            return
        
        # 初期化フラグを設定
        self.is_connecting = True
        # UI操作をブロック
        self.set_ui_enabled(False)
        
        try:
            interface_type = self.interface_type.currentText().lower()
            interface = self.can_interface.currentText()
            if interface == "利用可能なインターフェースなし" or interface == "利用可能なシリアルポートなし":
                print("Error: No CAN interface available")
                self.is_connecting = False
                self.set_ui_enabled(True)
                return
                
            bitrate_text = self.bitrate.currentText()
            # ボーレート文字列を数値に変換
            bitrate_map = {
                "0: 125kbps": 125000,
                "1: 200kbps": 200000,
                "2: 250kbps": 250000,
                "3: 500kbps": 500000,
                "4: 1Mbps": 1000000,
                "5: 2Mbps": 2000000,
                "6: 2.5Mbps": 2500000,
                "7: 3.2Mbps": 3200000,
                "8: 4Mbps": 4000000,
                "9: 5Mbps": 5000000
            }
            bitrate = bitrate_map.get(bitrate_text, 1000000)
            # motor_type_text = self.motor_type.currentText()
            
            # motor_id を16進数形式から数値に変換
            try:
                motor_id_hex = self.motor_id.text()
                if motor_id_hex.startswith("0x") or motor_id_hex.startswith("0X"):
                    motor_id = int(motor_id_hex, 16)
                else:
                    motor_id = int(motor_id_hex, 16)
            except ValueError:
                print(f"Error: Invalid motor ID format: {motor_id_hex}")
                self.is_connecting = False
                self.set_ui_enabled(True)
                QMessageBox.critical(self, "エラー", f"モーターID形式が無効です: {motor_id_hex}\n0xXXX形式で入力してください。")
                return
            
            # モータータイプのマッピング（文字列をインデックスに変換）
            # 将来的に実装予定
            # motor_type_map = {
            #     "DM4310": 0, "DM4310_48V": 1, "DM4340": 2, "DM4340_48V": 3,
            #     "DM6006": 4, "DM8006": 5, "DM8009": 6, "DM10010L": 7,
            #     "DM10010": 8, "DMH3510": 9, "DMG62150": 10, "DMH6220": 11
            # }
            # motor_type_idx = motor_type_map.get(motor_type_text, 0)
            motor_type_idx = 0
            
            # SocketCANの場合は初期化を試みる
            if interface_type == "socketcan":
                if not self.init_socketcan(interface, bitrate):
                    self.is_connecting = False
                    self.set_ui_enabled(True)
                    return
            
            self.motor_control = MotorControl(interface, bitrate, interface_type)
            
            motor = Motor(motor_type_idx, motor_id, 0)
            self.motor_control.addMotor(motor)
            
            # ESC IDを読み出して接続確認（リトライ付き）
            esc_id = None
            max_retries = 2
            for retry_count in range(max_retries):
                esc_id = self.motor_control.read_motor_param(motor, DM_variable.ESC_ID)
                if esc_id is not None:
                    break
                if retry_count < max_retries - 1:
                    print(f"Retrying ESC_ID read ({retry_count + 1}/{max_retries - 1})...")
            
            if esc_id is None:
                print("Error: Failed to read ESC_ID from motor - connection verification failed")
                if self.motor_control and self.motor_control.can_interface:
                    self.motor_control.can_interface.disconnect()
                self.motor_control = None
                self.is_connected = False
                self.is_connecting = False
                self.update_connection_indicator()
                self.set_ui_enabled(True)
                QMessageBox.critical(self, "接続失敗", "モーターからESC IDを読み出せませんでした。接続を確認してください。")
                return
            
            print(f"Motor ESC_ID verified: 0x{esc_id:03X}")
            
            # can_br パラメータを読み出して接続セクションを同期
            try:
                can_br_value = self.motor_control.read_motor_param(motor, DM_variable.can_br)
                if can_br_value is not None:
                    can_br_int = int(can_br_value)
                    # 接続セクションの bitrate を同期
                    self.bitrate.blockSignals(True)
                    bitrate_labels = ['125kbps', '200kbps', '250kbps', '500kbps', '1Mbps', '2Mbps', '2.5Mbps', '3.2Mbps', '4Mbps', '5Mbps']
                    bitrate_label = bitrate_labels[can_br_int] if can_br_int < len(bitrate_labels) else '1Mbps'
                    combo_text = f"{can_br_int}: {bitrate_label}"
                    self.bitrate.setCurrentText(combo_text)
                    self.bitrate.blockSignals(False)
                    print(f"Motor can_br synchronized: {combo_text}")
            except Exception as e:
                print(f"Error reading can_br on connect: {e}")
            
            self.is_connected = True
            self.is_connecting = False  # 初期化完了
            self.update_connection_indicator()
            self.interface_type.setEnabled(False)
            self.can_interface.setEnabled(False)
            self.bitrate.setEnabled(False)
            # self.motor_type.setEnabled(False)
            self.motor_id.setEnabled(False)
            self.feed_back_id.setEnabled(False)
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.set_widgets_enabled(True)  # パラメータ編集を有効化
            # print(f"Connected to {interface} ({interface_type}) - Motor: {motor_type_text} (ID: {motor_id})")
            print(f"Connected to {interface} ({interface_type}) - Motor ID: 0x{motor_id:03X}")
            
            # 接続後に自動読み込みが有効な場合は設定を読み込む（再接続時はスキップ）
            if self.auto_read_btn.isChecked() and not self.is_reconnecting:
                QTimer.singleShot(500, self.on_motor_read)
            
            # 再接続フラグをリセット
            self.is_reconnecting = False
        except Exception as e:
            print(f"Connection error: {e}")
            import traceback
            traceback.print_exc()
            # 接続失敗時はインターフェースを切断
            if self.motor_control is not None and hasattr(self.motor_control, 'can_interface'):
                try:
                    self.motor_control.can_interface.disconnect()
                except:
                    pass
            self.motor_control = None
            self.is_connected = False
            self.is_connecting = False
            self.update_connection_indicator()
            self.set_ui_enabled(True)
            QMessageBox.critical(self, "接続失敗", f"モーターに接続できませんでした。\n{str(e)}")

    def on_hex_value_changed(self, param_name, rid, hex_text):
        """16進数値(0xXXX形式)が変更されたときにモーターへ送信"""
        # ENTERキー送信がOFFの場合はスキップ
        if not self.enter_send_btn.isChecked():
            return
        
        # 接続初期化中または未接続の場合はスキップ
        if self.is_connecting or not self.is_connected or self.motor_control is None:
            return
        
        try:
            # 0xXXX形式をチェック
            if not hex_text.startswith("0x") and not hex_text.startswith("0X"):
                print(f"Invalid hex format: {hex_text}. Expected 0xXXX format.")
                return
            
            value = int(hex_text, 16)
            if value < 0 or value > 0x7FF:
                print(f"Value out of range: {hex_text}. Expected 0x000-0x7FF.")
                return
            
            motor = list(self.motor_control.motors_map.values())[0]
            self.motor_control.change_motor_param(motor, rid, value)
            print(f"Sent {param_name}: {hex_text} ({value})")
            
            # 接続セクションのID値を同期
            try:
                if param_name == "ESC_ID":
                    self.motor_id.blockSignals(True)
                    self.motor_id.setText(f"0x{value:03X}")
                    self.motor_id.blockSignals(False)
                    print(f"Updated connection motor_id to 0x{value:03X}")
                elif param_name == "MST_ID":
                    self.feed_back_id.blockSignals(True)
                    self.feed_back_id.setText(f"0x{value:03X}")
                    self.feed_back_id.blockSignals(False)
                    print(f"Updated connection feed_back_id to 0x{value:03X}")
            except Exception as e:
                print(f"Error updating widget values: {e}")
        except ValueError:
            print(f"Invalid hex value: {hex_text}")
            return
        
        # 自動再接続が有効な場合は再接続
        if self.auto_reconnect_btn.isChecked():
            print(f"{param_name} changed, reconnecting with new ID...")
            self.is_reconnecting = True
            self.on_disconnect()
            QTimer.singleShot(1000, self.on_connect)
        else:
            print(f"{param_name} changed (auto-reconnect disabled)")

    def on_disconnect(self):
        """切断ボタン押下時の処理"""
        if self.is_connecting:
            print("Connection in progress, cannot disconnect")
            return
        
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
            # self.motor_type.setEnabled(True)
            self.motor_id.setEnabled(True)
            self.feed_back_id.setEnabled(True)
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.set_widgets_enabled(False)  # パラメータ編集を無効化
            print("Disconnected")
        except Exception as e:
            print(f"Disconnection error: {e}")

    def on_widget_value_changed(self, param_name, rid, value):
        """ウィジェットの値が変更されたときにモーターへ即座に送信"""
        # ENTERキー送信がOFFの場合はスキップ
        if not self.enter_send_btn.isChecked():
            return
        
        # 接続初期化中または未接続の場合はスキップ
        if self.is_connecting or not self.is_connected or self.motor_control is None:
            return
        
        if param_name in ("MST_ID", "ESC_ID", "can_br"):
            try:
                motor = list(self.motor_control.motors_map.values())[0]
                self.motor_control.change_motor_param(motor, rid, value)
                print(f"Sent {param_name}: {value}")
                try:
                    if param_name == "ESC_ID":
                        self.motor_id.blockSignals(True)
                        self.motor_id.setText(f"0x{int(value):03X}")
                        self.motor_id.blockSignals(False)
                        print(f"Updated connection motor_id to 0x{int(value):03X}")
                    elif param_name == "MST_ID":
                        self.feed_back_id.blockSignals(True)
                        self.feed_back_id.setText(f"0x{int(value):03X}")
                        self.feed_back_id.blockSignals(False)
                        print(f"Updated connection feed_back_id to 0x{int(value):03X}")
                except Exception as e:
                    print(f"Error updating widget values: {e}")
            except Exception as e:
                print(f"Error sending {param_name}: {e}")
            
            # 自動再接続が有効な場合は再接続
            if self.auto_reconnect_btn.isChecked():
                print(f"{param_name} changed, reconnecting with new ID...")
                self.is_reconnecting = True
                self.on_disconnect()
                QTimer.singleShot(1000, self.on_connect)
            else:
                print(f"{param_name} changed (auto-reconnect disabled)")
            return
        
        try:
            motor = list(self.motor_control.motors_map.values())[0]
            success = self.motor_control.change_motor_param(motor, rid, value)
            if success:
                print(f"Sent {param_name}: {value}")
        except Exception as e:
            print(f"Error sending {param_name}: {e}")

    def on_combo_value_changed(self, param_name, rid, text):
        """ComboBox の値が変更されたときにモーターへ送信（can_br用）"""
        # 接続初期化中または未接続の場合はスキップ
        if self.is_connecting or not self.is_connected or self.motor_control is None:
            return
        
        # can_br の場合、SLCAN接続時に1Mbps以上が選択された場合は警告を表示
        if param_name == "can_br":
            interface_type = self.interface_type.currentText()
            if interface_type.lower() == "slcan":
                # SLCAN対応ビットレート：0-4（125Kbps, 250Kbps, 500Kbps, 1Mbps）
                bitrate_index = int(text.split(":")[0])
                if bitrate_index > 4:
                    reply = QMessageBox.question(
                        self,
                        "警告",
                        f"SLCAN接続時に{text}は実質的に対応していません。\nそれでも設定しますか？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        # キャンセルされたので、前の値に戻す
                        self.can_br.blockSignals(True)
                        # 最後の有効な値に戻す（0-4の範囲で最大値）
                        self.can_br.setCurrentText("4: 1Mbps")
                        self.can_br.blockSignals(False)
                        print(f"Cancelled setting {text} on SLCAN")
                        return
        
        # can_br の ComboBox から数値を抽出（例："0: 125kbps" -> 0）
        try:
            value = int(text.split(":")[0])
            motor = list(self.motor_control.motors_map.values())[0]
            self.motor_control.change_motor_param(motor, rid, value)
            print(f"Sent {param_name}: {value}")
            # 接続セクションの bitrate を同期
            self.bitrate.blockSignals(True)
            self.bitrate.setCurrentText(text)
            self.bitrate.blockSignals(False)
            print(f"Updated connection bitrate to {text}")
            
            # ボーレート変更時は切断を実行
            if param_name == "can_br":
                print(f"{param_name} changed, disconnecting...")
                self.on_disconnect()
        except Exception as e:
            print(f"Error sending {param_name}: {e}")

    def set_ui_enabled(self, enabled):
        """接続セクションのUIを有効/無効に設定"""
        self.interface_type.setEnabled(enabled)
        self.can_interface.setEnabled(enabled)
        self.bitrate.setEnabled(enabled)
        # self.motor_type.setEnabled(enabled)  # 将来的に実装予定
        self.motor_id.setEnabled(enabled)
        self.feed_back_id.setEnabled(enabled)
        self.connect_btn.setEnabled(enabled)
        # disconnect ボタンは接続時のみ有効
        if enabled:
            self.disconnect_btn.setEnabled(self.is_connected)
        else:
            self.disconnect_btn.setEnabled(False)

    def set_widgets_enabled(self, enabled):
        """パラメータウィジェットの有効/無効を設定"""
        # ID / FeedBack セクション
        self.MST_ID.setEnabled(enabled)
        self.ESC_ID.setEnabled(enabled)
        self.can_br.setEnabled(enabled)
        
        # 動作セクション
        self.CTRL_MODE.setEnabled(enabled)
        self.MAX_SPD.setEnabled(enabled)
        self.ACC.setEnabled(enabled)
        self.DEC.setEnabled(enabled)
        self.PMAX.setEnabled(enabled)
        self.VMAX.setEnabled(enabled)
        self.TMAX.setEnabled(enabled)
        self.KT_Value.setEnabled(enabled)
        self.I_BW.setEnabled(enabled)
        
        # 保護まわりセクション
        self.OV_Value.setEnabled(enabled)
        self.UV_Value.setEnabled(enabled)
        self.OC_Value.setEnabled(enabled)
        self.OT_Value.setEnabled(enabled)
        self.TIMEOUT.setEnabled(enabled)
        
        # ゲインセクション
        self.KP_APR.setEnabled(enabled)
        self.KI_APR.setEnabled(enabled)
        self.KP_ASR.setEnabled(enabled)
        self.KI_ASR.setEnabled(enabled)
        self.Deta.setEnabled(enabled)
        self.V_BW.setEnabled(enabled)
        self.IQ_V.setEnabled(enabled)
        self.VL_c1.setEnabled(enabled)

    def on_motor_read(self):
        """モーター読み込みボタン押下時の処理"""
        if not self.is_connected or self.motor_control is None:
            QMessageBox.warning(self, "エラー", "モーターに接続してください")
            return
        
        try:
            # IDセクションのパラメータを読み込み
            motor = list(self.motor_control.motors_map.values())[0]
            
            # 読み込むパラメータリスト
            read_params = [
                ("MST_ID", DM_variable.MST_ID, self.MST_ID),
                ("ESC_ID", DM_variable.ESC_ID, self.ESC_ID),
                ("can_br", DM_variable.can_br, self.can_br),
                ("OV_Value", DM_variable.OV_Value, self.OV_Value),
                ("UV_Value", DM_variable.UV_Value, self.UV_Value),
                ("OC_Value", DM_variable.OC_Value, self.OC_Value),
                ("OT_Value", DM_variable.OT_Value, self.OT_Value),
                ("TIMEOUT", DM_variable.TIMEOUT, self.TIMEOUT),
                ("KP_APR", DM_variable.KP_APR, self.KP_APR),
                ("KI_APR", DM_variable.KI_APR, self.KI_APR),
                ("KP_ASR", DM_variable.KP_ASR, self.KP_ASR),
                ("KI_ASR", DM_variable.KI_ASR, self.KI_ASR),
                ("CTRL_MODE", DM_variable.CTRL_MODE, self.CTRL_MODE),
                ("MAX_SPD", DM_variable.MAX_SPD, self.MAX_SPD),
                ("ACC", DM_variable.ACC, self.ACC),
                ("DEC", DM_variable.DEC, self.DEC),
                ("PMAX", DM_variable.PMAX, self.PMAX),
                ("VMAX", DM_variable.VMAX, self.VMAX),
                ("TMAX", DM_variable.TMAX, self.TMAX),
                ("KT_Value", DM_variable.KT_Value, self.KT_Value),
                ("I_BW", DM_variable.I_BW, self.I_BW),
                ("V_BW", DM_variable.V_BW, self.V_BW),
                ("VL_c1", DM_variable.VL_c1, self.VL_c1),
                ("Deta", DM_variable.Deta, self.Deta),
            ]
            
            for param_name, rid, widget in read_params:
                if widget is None:
                    continue
                value = self.motor_control.read_motor_param(motor, rid)
                if value is not None:
                    if isinstance(widget, QLineEdit) and param_name in ("ESC_ID", "MST_ID"):
                        # ESC_ID, MST_ID は QLineEdit なので16進数形式で設定
                        value_int = int(value)
                        widget.setText(f"0x{value_int:03X}")
                        print(f"Read {param_name}: 0x{value_int:03X}")
                    elif isinstance(widget, QComboBox) and param_name == "can_br":
                        # can_br は ComboBox なので対応するテキストを選択
                        value_int = int(value)
                        bitrate_names = ['125 Kbps', '200 Kbps', '250 Kbps', '500 Kbps', '1 Mbps', '2 Mbps', '3 Mbps', '4 Mbps', '5 Mbps']
                        if value_int < len(bitrate_names):
                            combo_text = f"{value_int}: {bitrate_names[value_int]}"
                            widget.setCurrentText(combo_text)
                            # 接続セクションの bitrate も同期
                            self.bitrate.blockSignals(True)
                            self.bitrate.setCurrentText(bitrate_names[value_int])
                            self.bitrate.blockSignals(False)
                        else:
                            print(f"Warning: can_br value {value_int} out of range")
                    else:
                        widget.setValue(value)
                        print(f"Read {param_name}: {value}")
            
            QMessageBox.information(self, "成功", "モーターパラメータを読み込みました")
            print("Motor parameters read successfully")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"読み込みエラー: {e}")
            print(f"Motor read error: {e}")
            import traceback
            traceback.print_exc()

    def on_motor_write(self):
        """モーター書き込みボタン押下時の処理"""
        if not self.is_connected:
            QMessageBox.warning(self, "エラー", "モーターに接続してください")
            return
        
        try:
            motor = list(self.motor_control.motors_map.values())[0]
            
            # 書き込むパラメータリスト
            write_params = [
                ("MST_ID", DM_variable.MST_ID, self.MST_ID),
                ("ESC_ID", DM_variable.ESC_ID, self.ESC_ID),
                ("can_br", DM_variable.can_br, self.can_br),
                ("OV_Value", DM_variable.OV_Value, self.OV_Value),
                ("UV_Value", DM_variable.UV_Value, self.UV_Value),
                ("OC_Value", DM_variable.OC_Value, self.OC_Value),
                ("OT_Value", DM_variable.OT_Value, self.OT_Value),
                ("TIMEOUT", DM_variable.TIMEOUT, self.TIMEOUT),
                ("KP_APR", DM_variable.KP_APR, self.KP_APR),
                ("KI_APR", DM_variable.KI_APR, self.KI_APR),
                ("KP_ASR", DM_variable.KP_ASR, self.KP_ASR),
                ("KI_ASR", DM_variable.KI_ASR, self.KI_ASR),
                ("CTRL_MODE", DM_variable.CTRL_MODE, self.CTRL_MODE),
                ("MAX_SPD", DM_variable.MAX_SPD, self.MAX_SPD),
                ("ACC", DM_variable.ACC, self.ACC),
                ("DEC", DM_variable.DEC, self.DEC),
                ("PMAX", DM_variable.PMAX, self.PMAX),
                ("VMAX", DM_variable.VMAX, self.VMAX),
                ("TMAX", DM_variable.TMAX, self.TMAX),
                ("KT_Value", DM_variable.KT_Value, self.KT_Value),
                ("I_BW", DM_variable.I_BW, self.I_BW),
                ("V_BW", DM_variable.V_BW, self.V_BW),
                ("VL_c1", DM_variable.VL_c1, self.VL_c1),
                ("Deta", DM_variable.Deta, self.Deta),
            ]
            
            for param_name, rid, widget in write_params:
                if isinstance(widget, QLineEdit) and param_name in ("ESC_ID", "MST_ID"):
                    # ESC_ID, MST_ID は QLineEdit なので16進数値を抽出
                    hex_text = widget.text()
                    try:
                        value = int(hex_text, 16)
                        success = self.motor_control.change_motor_param(motor, rid, value)
                        if success:
                            print(f"Wrote {param_name}: {hex_text} ({value})")
                        else:
                            print(f"Failed to write {param_name}")
                    except ValueError:
                        print(f"Invalid hex value for {param_name}: {hex_text}")
                elif isinstance(widget, QComboBox) and param_name == "can_br":
                    # can_br は ComboBox なので currentText から数値を抽出
                    text = widget.currentText()
                    value = int(text.split(":")[0])
                    success = self.motor_control.change_motor_param(motor, rid, value)
                    if success:
                        print(f"Wrote {param_name}: {value}")
                    else:
                        print(f"Failed to write {param_name}")
                else:
                    value = widget.value()
                    success = self.motor_control.change_motor_param(motor, rid, value)
                    if success:
                        print(f"Wrote {param_name}: {value}")
                    else:
                        print(f"Failed to write {param_name}")
            
            QMessageBox.information(self, "成功", "モーターパラメータを書き込みました")
            print("Motor parameters written successfully")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"書き込みエラー: {e}")
            print(f"Motor write error: {e}")
            import traceback
            traceback.print_exc()

    def on_motor_save(self):
        """フラッシュメモリに保存ボタン押下時の処理"""
        if not self.is_connected:
            QMessageBox.warning(self, "エラー", "モーターに接続してください")
            return
        
        try:
            reply = QMessageBox.question(
                self, 
                "確認", 
                "フラッシュメモリに保存します。よろしいですか？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                motor = list(self.motor_control.motors_map.values())[0]
                self.motor_control.save_motor_param(motor)
                QMessageBox.information(self, "成功", "フラッシュメモリに保存しました")
                print("Motor parameters saved to flash memory")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存エラー: {e}")
            print(f"Motor save error: {e}")
            import traceback
            traceback.print_exc()

    def on_save_config(self):
        """設定をファイルに保存ボタン押下時の処理"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "設定ファイルを保存", 
                "", 
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # ヘッダー行を書き込み
                    writer.writerow(["Parameter", "Value"])
                    
                    # settings_dictから値を書き込み
                    for key, widget in self.settings_dict.items():
                        if isinstance(widget, QLineEdit) and key in ("ESC_ID", "MST_ID"):
                            # ESC_ID, MST_ID は QLineEdit なので16進数値を抽出
                            hex_text = widget.text()
                            try:
                                value = int(hex_text, 16)
                                writer.writerow([key, hex_text])
                            except ValueError:
                                writer.writerow([key, hex_text])
                        elif isinstance(widget, QComboBox) and key == "can_br":
                            # can_br は ComboBox なので currentText から数値を抽出
                            text = widget.currentText()
                            value = int(text.split(":")[0])
                            writer.writerow([key, value])
                        else:
                            writer.writerow([key, widget.value()])
                
                QMessageBox.information(self, "成功", f"設定を保存しました: {file_path}")
                print(f"Configuration saved to {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"保存エラー: {e}")
            print(f"Save config error: {e}")
            import traceback
            traceback.print_exc()

    def on_load_config(self):
        """ファイルから設定を読み込みボタン押下時の処理"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "設定ファイルを開く", 
                "", 
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    # ヘッダー行をスキップ
                    next(reader)
                    
                    # 値を読み込んでウィジェットに設定
                    for row in reader:
                        if len(row) >= 2:
                            key, value = row[0], row[1]
                            if key in self.settings_dict:
                                try:
                                    widget = self.settings_dict[key]
                                    if isinstance(widget, QLineEdit) and key in ("ESC_ID", "MST_ID"):
                                        # ESC_ID, MST_ID は QLineEdit なので0x形式で設定
                                        if value.startswith("0x") or value.startswith("0X"):
                                            widget.setText(value)
                                        else:
                                            # 16進数値の場合は0xプレフィックスを追加
                                            value_int = int(value, 16)
                                            widget.setText(f"0x{value_int:03X}")
                                    elif isinstance(widget, QComboBox) and key == "can_br":
                                        # can_br は ComboBox なので対応するテキストを選択
                                        value_int = int(float(value))
                                        bitrate_names = ['125 Kbps', '200 Kbps', '250 Kbps', '500 Kbps', '1 Mbps', '2 Mbps', '3 Mbps', '4 Mbps', '5 Mbps']
                                        if value_int < len(bitrate_names):
                                            combo_text = f"{value_int}: {bitrate_names[value_int]}"
                                            widget.setCurrentText(combo_text)
                                        else:
                                            print(f"Warning: can_br value {value_int} out of range")
                                    else:
                                        widget.setValue(float(value))
                                    print(f"Loaded {key}: {value}")
                                except (ValueError, IndexError) as e:
                                    print(f"Invalid value for {key}: {value} ({e})")
                
                QMessageBox.information(self, "成功", f"設定を読み込みました: {file_path}")
                print(f"Configuration loaded from {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"読み込みエラー: {e}")
            print(f"Load config error: {e}")
            import traceback
            traceback.print_exc()

    def update_connection_indicator(self):
        """接続状態インジケータを更新"""
        if self.is_connected:
            self.connection_indicator.setStyleSheet("color: green; font-size: 18px;")
        else:
            self.connection_indicator.setStyleSheet("color: red; font-size: 18px;")


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

    def detect_available_interface(self):
        """
        起動時に利用可能なインターフェースを検出し、優先順位に従って返す
        優先順位: SocketCAN > SLCAN
        """
        socketcan_available = self.get_available_can_interfaces()
        slcan_available = self.get_available_serial_ports()
        
        # SocketCANが利用可能かどうかをチェック（デフォルト以外のものが存在するかどうか）
        has_socketcan = socketcan_available and socketcan_available[0] != "利用可能なインターフェースなし"
        
        # SLCANが利用可能かどうかをチェック（デフォルト以外のものが存在するかどうか）
        has_slcan = slcan_available and slcan_available[0] != "利用可能なシリアルポートなし"
        
        if has_socketcan:
            print(f"Auto-detected SocketCAN interface: {socketcan_available}")
            return "SocketCAN"
        elif has_slcan:
            print(f"Auto-detected SLCAN serial port: {slcan_available}")
            return "SLCAN"
        else:
            print("No CAN interface detected, defaulting to SLCAN")
            return None

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
    
    
    def init_socketcan(self, interface, bitrate):
            """SocketCANを初期化（必要に応じてパスワード入力・キャッシュ）"""
            if SocketCANInitializer is None or CANConfig is None:
                QMessageBox.warning(self, "エラー", "必要なモジュールが見つかりません。")
                return False

            try:
                initializer = SocketCANInitializer(interface)
                
                # 2Mbps以上の場合はCAN FDを有効化
                is_canfd = bitrate >= 2000000
                if is_canfd:
                    config = CANConfig(bitrate=1000000, dbitrate=bitrate, fd=True)
                else:
                    config = CANConfig(bitrate=bitrate, fd=False)

                # 設定を適用するヘルパー関数（重複するコードを削減）
                def try_apply(pwd=None, no_interact=False):
                    cb = (lambda: pwd) if pwd else None
                    return initializer.apply(config, use_sudo=True, password_callback=cb, use_no_interactive=no_interact)

                # 1. 既存の権限（パスワードなし）で試行
                if try_apply(no_interact=True): return True
                
                # 2. キャッシュされたパスワードで試行
                if getattr(self, 'cached_sudo_password', None) and try_apply(self.cached_sudo_password):
                    return True

                # 失敗した場合はキャッシュをクリアしてパスワード入力ダイアログを表示
                self.cached_sudo_password = None
                pwd, ok = QInputDialog.getText(
                    self, "SocketCAN初期化", 
                    "初期化に管理者権限が必要です。\nパスワードを入力してください：", 
                    QLineEdit.Password
                )
                
                if not ok or not pwd:
                    return False

                # 3. 入力された新しいパスワードで試行
                if try_apply(pwd):
                    self.cached_sudo_password = pwd  # 成功したらキャッシュに保存
                    return True

                # 全て失敗した場合 リトライの選択肢を表示
                retry = QMessageBox.question(
                    self, "エラー", "初期化に失敗しました。パスワードが正しいか確認してください。\n再試行しますか？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if retry == QMessageBox.Yes:
                    return self.init_socketcan(interface, bitrate)  # 再試行
                return False

            except Exception as e:
                QMessageBox.critical(self, "エラー", f"SocketCAN初期化エラー: {e}")
                return False
    
    def get_available_serial_ports(self):
        """利用可能なシリアルポートを取得"""
        import glob
        ports = []
        try:
            # Linux上のシリアルポートを探す
            if os.path.exists('/dev'):
                # ttyUSB*, ttyACM* などを探す（ttyS は除外）
                for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*']:
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
        group = QGroupBox("接続設定")
        layout = QGridLayout()

        row = 0
        
        # インターフェースタイプ
        layout.addWidget(QLabel("インターフェースタイプ"), row, 0)
        self.interface_type = QComboBox()
        self.interface_type.addItems(["SLCAN", "SocketCAN"])
        # 起動時に検出されたインターフェースタイプを設定
        if self.detected_interface_type:
            self.interface_type.setCurrentText(self.detected_interface_type)
        else:
            self.interface_type.setCurrentText("SLCAN")
        self.interface_type.setFixedWidth(200)
        layout.addWidget(self.interface_type, row, 1)
        row += 1
        
        # インターフェース/シリアルポート（ラベルは動的に変更される）
        self.interface_label = QLabel("シリアルポート")
        layout.addWidget(self.interface_label, row, 0)
        self.can_interface = QComboBox()
        # 検出されたインターフェースタイプに応じて初期表示を変更
        if self.detected_interface_type == "SocketCAN":
            available_items = self.get_available_can_interfaces()
            self.interface_label.setText("CAN ポート")
        else:
            available_items = self.get_available_serial_ports()
        self.can_interface.addItems(available_items)
        self.can_interface.setFixedWidth(200)
        layout.addWidget(self.can_interface, row, 1)
        row += 1
        
        # CANビットレート
        layout.addWidget(QLabel("CAN baudrate"), row, 0)
        self.bitrate = QComboBox()
        self.bitrate.addItems(["0: 125kbps", "1: 200kbps", "2: 250kbps", "3: 500kbps", "4: 1Mbps", "5: 2Mbps", "6: 2.5Mbps", "7: 3.2Mbps", "8: 4Mbps", "9: 5Mbps"])
        self.bitrate.setCurrentText("4: 1Mbps")
        layout.addWidget(self.bitrate, row, 1)
        self.update_bitrate_options()
        row += 1
        
        # # モータータイプ
        # layout.addWidget(QLabel("モーターの種類"), row, 0)
        # self.motor_type = QComboBox()
        # self.motor_type.addItems(["DM4310", "DM4310_48V", "DM4340", "DM4340_48V", "DM6006", "DM8006", "DM8009", "DM10010L", "DM10010", "DMH3510", "DMG62150", "DMH6220"])
        # layout.addWidget(self.motor_type, row, 1)
        # row += 1
        
        # モーターID
        layout.addWidget(QLabel("ESC_ID (Motor ID)"), row, 0)
        self.motor_id = QLineEdit()
        self.motor_id.setText("0x001")
        self.motor_id.setMaxLength(7)  # "0x" + 5文字
        self.motor_id.setPlaceholderText("0xXXX")
        layout.addWidget(self.motor_id, row, 1)
        row += 1

        # feed back ID
        layout.addWidget(QLabel("MST_ID(feed back ID)"), row, 0)
        self.feed_back_id = QLineEdit()
        self.feed_back_id.setText("0x000")
        self.feed_back_id.setMaxLength(7)  # "0x" + 5文字
        self.feed_back_id.setPlaceholderText("0xXXX")
        layout.addWidget(self.feed_back_id, row, 1)
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
        
        # チェックボックス：接続後に自動読み込み
        label_layout3 = QHBoxLayout()
        label_layout3.addWidget(QLabel("接続後にモーターから設定を自動読み込み"))
        self.auto_read_btn = QCheckBox()
        self.auto_read_btn.setChecked(True)
        label_layout3.addWidget(self.auto_read_btn)
        label_layout3.addStretch()
        layout.addLayout(label_layout3, row, 0, 1, 2)
        row += 1

        layout.setRowStretch(row, 1)
        group.setLayout(layout)
        return group
    
    def on_interface_type_changed(self):
        """インターフェースタイプが変更された時の処理"""
        self.update_interface_display()
        self.update_bitrate_options()
    
    def update_bitrate_options(self):
        """インターフェースタイプに応じてビットレートオプションを更新"""
        interface_type = self.interface_type.currentText()
        current_text = self.bitrate.currentText()
        
        self.bitrate.blockSignals(True)
        self.bitrate.clear()
        
        if interface_type.lower() == "slcan":
            # SLCAN対応ビットレート：0-4（125kbps, 200kbps, 250kbps, 500kbps, 1Mbps）
            self.bitrate.addItems(["0: 125kbps", "1: 200kbps", "2: 250kbps", "3: 500kbps", "4: 1Mbps"])
            self.bitrate.setCurrentText("4: 1Mbps")
        else:
            # SocketCAN対応ビットレート（全オプション）
            self.bitrate.addItems(["0: 125kbps", "1: 200kbps", "2: 250kbps", "3: 500kbps", "4: 1Mbps", "5: 2Mbps", "6: 2.5Mbps", "7: 3.2Mbps", "8: 4Mbps", "9: 5Mbps"])
            # 前の値が存在すればそれを復元、なければ1Mbpsをデフォルトに
            index = self.bitrate.findText(current_text)
            if index >= 0:
                self.bitrate.setCurrentIndex(index)
            else:
                self.bitrate.setCurrentText("4: 1Mbps")
        
        self.bitrate.blockSignals(False)
    
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
        group = QGroupBox("通信設定 (ID/baud rate)") 
        layout = QGridLayout()

        row = 0

        # ESC_ID [0, 0x7FF] - 0xXXX形式
        layout.addWidget(QLabel("ESC_ID"), row, 0)
        self.ESC_ID = QLineEdit()
        self.ESC_ID.setText("0x001")
        self.ESC_ID.setMaxLength(7)  # "0x" + 5文字
        self.ESC_ID.setPlaceholderText("0xXXX")
        layout.addWidget(self.ESC_ID, row, 1)
        self.settings_dict["ESC_ID"] = self.ESC_ID
        row += 1
        # MST_ID [0, 0x7FF] - 0xXXX形式
        layout.addWidget(QLabel("MST_ID (feed back ID)"), row, 0)
        self.MST_ID = QLineEdit()
        self.MST_ID.setText("0x000")
        self.MST_ID.setMaxLength(7)  # "0x" + 5文字
        self.MST_ID.setPlaceholderText("0xXXX")
        layout.addWidget(self.MST_ID, row, 1)
        self.settings_dict["MST_ID"] = self.MST_ID
        row += 1

        
        layout.addWidget(QLabel("CANボーレート (0-9)"), row, 0)
        self.can_br = QComboBox()
        self.can_br.addItems(["0: 125kbps", "1: 200kbps", "2: 250kbps", "3: 500kbps", "4: 1Mbps", "5: 2Mbps", "6: 2.5Mbps", "7: 3.2Mbps", "8: 4Mbps", "9: 5Mbps"])
        self.can_br.setCurrentText("4: 1Mbps")
        layout.addWidget(self.can_br, row, 1)
        self.settings_dict["can_br"] = self.can_br
        row += 1
        # チェックボックス：変更時に自動再接続
        label_layout1 = QHBoxLayout()
        label_layout1.addWidget(QLabel("変更時に自動再接続"))
        self.auto_reconnect_btn = QCheckBox()
        self.auto_reconnect_btn.setChecked(True)
        label_layout1.addWidget(self.auto_reconnect_btn)
        label_layout1.addStretch()
        layout.addLayout(label_layout1, row, 0, 1, 2)
        row += 1

        # チェックボックス：ENTERキーで値を送信
        label_layout2 = QHBoxLayout()
        label_layout2.addWidget(QLabel("ENTERキーで送信"))
        self.enter_send_btn = QCheckBox()
        self.enter_send_btn.setChecked(True)
        label_layout2.addWidget(self.enter_send_btn)
        label_layout2.addStretch()
        layout.addLayout(label_layout2, row, 0, 1, 2)
        row += 1

        layout.setRowStretch(row + 1, 1) # 残りのスペースを伸縮
        group.setLayout(layout)
        return group

    # --- (0, 2) 動作 ---
    def create_motion_group(self):
        group = QGroupBox("動作")
        layout = QGridLayout()
        
        default_values = {
            "CTRL_MODE": 3,
            "MAX_SPD": 600.0,
            "ACC": 2.0,
            "DEC": -2.0,
            "PMAX": 12.5,
            "VMAX": 30.0,
            "TMAX": 10.0,
            "KT_Value": 0.0,
            "I_BW": 1000.0,
        }
        
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
            # CSV からのデフォルト値を設定
            if key in default_values:
                widget.setValue(default_values[key])
            setattr(obj, key, widget) # self.KEY = widget と同じ
            layout.addWidget(widget, i, 1)
            self.settings_dict[key] = widget
            
        layout.setRowStretch(len(items), 1)
        group.setLayout(layout)
        return group

    # --- (1, 0) 各種ボタン ---
    def create_action_buttons_group(self):
        group = QGroupBox("設定 読み書き")
        layout = QVBoxLayout()
        
        # モーターへ読み書き
        motor_label = QLabel("モーター")
        motor_label.setAlignment(Qt.AlignCenter)
        motor_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(motor_label)
        
        motor_btns_layout = QHBoxLayout()
        self.motor_write_btn = QPushButton("すべて書き込み")
        self.motor_read_btn = QPushButton("読み込み")
        self.motor_save_btn = QPushButton("flash メモリに保存")
        motor_btns_layout.addWidget(self.motor_write_btn)
        motor_btns_layout.addWidget(self.motor_read_btn)
        motor_btns_layout.addWidget(self.motor_save_btn)
        layout.addLayout(motor_btns_layout)
        
        # スペーサー
        layout.addWidget(QLabel(" "))
        
        # 設定ファイル読み書き
        file_label = QLabel("設定ファイル")
        file_label.setAlignment(Qt.AlignCenter)
        file_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(file_label)
        
        file_btns_layout = QHBoxLayout()
        self.save_btn = QPushButton("書き込み")
        self.load_btn = QPushButton("読み込み")
        file_btns_layout.addWidget(self.save_btn)
        file_btns_layout.addWidget(self.load_btn)
        layout.addLayout(file_btns_layout)
        
        layout.addStretch()
        group.setLayout(layout)
        return group

    # --- (1, 1) 保護まわり ---
    def create_protection_group(self):
        group = QGroupBox("保護設定")
        layout = QGridLayout()
        
        default_values = {
            "OV_Value": 32.0,
            "UV_Value": 15.0,
            "OC_Value": 0.8,
            "OT_Value": 100.0,
            "TIMEOUT": 0,
        }
        
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
            if key in default_values:
                widget.setValue(default_values[key])
            setattr(obj, key, widget)
            layout.addWidget(widget, i, 1)
            self.settings_dict[key] = widget
            
        layout.setRowStretch(len(items), 1)
        group.setLayout(layout)
        return group

    # --- (1, 2) ゲイン ---
    def create_gain_group(self):
        group = QGroupBox("ゲイン")
        layout = QGridLayout()
        
        default_values = {
            "KP_APR": 54.0,
            "KI_APR": 0.0,
            "KP_ASR": 0.0,
            "KI_ASR": 0.0,
            "Deta": 4.0,
            "V_BW": 40.0,
            "IQ_V": 100.0,
            "VL_c1": 100.0,
        }
        
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
            if key in default_values:
                widget.setValue(default_values[key])
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
