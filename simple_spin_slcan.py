#!/usr/bin/env python3
"""
SLCAN motor control example
SLCAN インターフェース経由でモーターを制御するサンプルコード
USB-CAN アダプタを使用して SLCAN 経由で DM モーターを制御します

Usage:
    python simple_spin_slcan.py

Requirements:
    - USB-CAN adapter connected to the system
    - Serial port device (e.g., /dev/ttyACM0 or /dev/ttyUSB0)
    - python-can library with slcan support
"""

import time
from DM_CAN import MotorControl, Motor, Control_Type

# === User configuration ===
# SLCAN の場合、interface はシリアルデバイスのパスを指定します
SLCAN_DEVICE = '/dev/ttyACM6'   # USB-CAN アダプタのシリアルポート
                                 # 例：/dev/ttyACM0, /dev/ttyUSB0, COM3 (Windows)
CAN_BITRATE = 1000000           # 1Mbps
SLAVE_ID = 2                     # モーターのスレーブ ID（自分のモーターに合わせてください）
MOTOR_TYPE = 0                   # 0=DM4310, 1=DM4310_48V, 2=DM4340, 3=DM4340_48V, ...
TARGET_VEL = 2.0                 # rad/s (小さい値から始めてください！)
RUNTIME_SEC = 5.0                # 実行時間（秒）
RECV_INTERVAL = 0.05             # 受信ポーリング間隔（秒）
# ==========================

def find_slcan_device():
    """
    システムに接続されているシリアルポートを探す
    Find available serial devices for SLCAN
    """
    import os
    import glob
    
    print("Searching for available serial devices...")
    
    # Linux の場合
    potential_devices = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
    if potential_devices:
        print(f"Found potential SLCAN devices:")
        for device in potential_devices:
            print(f"  - {device}")
        return potential_devices[0]
    
    print("No serial devices found")
    return None

def main():
    print("=" * 60)
    print("SLCAN Motor Control Example")
    print("=" * 60)
    
    # シリアルデバイスの確認
    slcan_device = SLCAN_DEVICE
    if not slcan_device:
        print("Error: SLCAN device not specified")
        return
    
    print(f"\nInitializing motor control via SLCAN")
    print(f"  Device: {slcan_device}")
    print(f"  Bitrate: {CAN_BITRATE} bps")
    print(f"  Motor Slave ID: {SLAVE_ID}")
    
    # SLCAN インターフェースで MotorControl を初期化
    # Note: interface_type='slcan' を指定することが重要
    mc = MotorControl(
        interface=slcan_device,
        bitrate=CAN_BITRATE,
        interface_type='slcan'
    )
    
    # 接続確認
    if mc.can_interface is None:
        print("Error: Failed to connect to SLCAN interface")
        print(f"Please check:")
        print(f"  1. USB-CAN adapter is connected")
        print(f"  2. Device path is correct: {slcan_device}")
        print(f"  3. You have permission to access the serial port")
        return
    
    print("✓ SLCAN connection successful")
    
    # モーターオブジェクトを作成して追加
    motor = Motor(MOTOR_TYPE, SLAVE_ID, 0)
    mc.addMotor(motor)
    print(f"✓ Motor added to control map")
    
    # 速度制御モードに切り替え
    try:
        mc.switchControlMode(motor, Control_Type.VEL)
        print(f"✓ Switched to velocity control mode")
    except Exception as e:
        print(f"Warning: Could not switch control mode: {e}")
    
    try:
        print("\n[Step 1] Setting zero position (safety measure)")
        mc.set_zero_position(motor)
        time.sleep(0.1)
        
        print("[Step 2] Enabling motor")
        mc.enable(motor)
        time.sleep(0.2)
        
        print(f"[Step 3] Commanding velocity {TARGET_VEL} rad/s for {RUNTIME_SEC} seconds")
        print("-" * 60)
        
        mc.control_Vel(motor, TARGET_VEL)
        
        t0 = time.time()
        sample_count = 0
        while time.time() - t0 < RUNTIME_SEC:
            # 受信処理
            mc.recv()
            
            # 速度制御コマンド送信
            mc.control_Vel(motor, TARGET_VEL)
            
            # モーター状態を取得して表示
            pos = motor.getPosition()
            vel = motor.getVelocity()
            tau = motor.getTorque()
            
            sample_count += 1
            elapsed = time.time() - t0
            print(f"[{elapsed:.2f}s] pos={pos:7.4f} rad, vel={vel:7.4f} rad/s, tau={tau:7.4f} Nm")
            
            time.sleep(RECV_INTERVAL)
        
        print("-" * 60)
        print(f"✓ Control completed ({sample_count} samples)")
        
        print("\n[Step 4] Stopping motor (commanding zero velocity)")
        mc.control_Vel(motor, 0.0)
        time.sleep(0.2)
        
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user, emergency stop")
        try:
            mc.control_Vel(motor, 0.0)
            time.sleep(0.1)
        except Exception:
            pass
            
    except Exception as e:
        print(f"\n✗ Error during motor operation: {e}")
        import traceback
        traceback.print_exc()
        try:
            mc.control_Vel(motor, 0.0)
            time.sleep(0.1)
        except Exception:
            pass
            
    finally:
        print("\n[Step 5] Cleanup")
        try:
            mc.disable(motor)
            print("✓ Motor disabled")
        except Exception as e:
            print(f"Warning: Could not disable motor: {e}")
        
        try:
            mc.can_interface.disconnect()
            print("✓ SLCAN connection closed")
        except Exception as e:
            print(f"Warning: Could not close connection: {e}")
        


if __name__ == '__main__':
    main()
