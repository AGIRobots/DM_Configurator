"""
Socket CAN Interface Initialization Module
SocketCANインターフェースの初期化・設定管理
"""

import subprocess
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class CANConfig:
    """CAN設定クラス
    
    Attributes:
        bitrate: CAN通信ビットレート (bps)
        dbitrate: CANデータフェーズビットレート (bps、オプション)
        fd: CAN FD有効フラグ
        sample_point: サンプルポイント (0.0-1.0、オプション)
        dsample_point: データフェーズサンプルポイント (0.0-1.0、オプション)
    """
    bitrate: int
    dbitrate: Optional[int] = None
    fd: bool = False
    sample_point: Optional[float] = None
    dsample_point: Optional[float] = None

    def __post_init__(self):
        """入力値の検証"""
        if self.bitrate <= 0:
            raise ValueError("bitrate must be positive")
        if self.sample_point is not None:
            if not (0.0 <= self.sample_point <= 1.0):
                raise ValueError("sample_point must be between 0.0 and 1.0")
        if self.dsample_point is not None:
            if not (0.0 <= self.dsample_point <= 1.0):
                raise ValueError("dsample_point must be between 0.0 and 1.0")
        if self.fd and self.dbitrate is not None and self.dbitrate <= 0:
            raise ValueError("dbitrate must be positive")


class SocketCANInitializer:
    """SocketCANインターフェース初期化クラス"""
    def __init__(self, interface: str = "can0"):
        self.interface = interface
        self.current_config: Optional[CANConfig] = None

    def apply(self, config: CANConfig, use_sudo: bool = False, password_callback: Optional[Callable[[], Optional[str]]] = None, use_no_interactive: bool = True) -> bool:
        try:
            # インターフェースをダウン
            cmd_down = [
                "ip", "link", "set", self.interface, "down"
            ]
            if use_sudo:
                cmd_down = ["sudo"] + cmd_down

            result = self._run_command(cmd_down, use_sudo, password_callback, use_no_interactive)
            if not result:
                return False

            # インターフェースをアップ (CAN設定付き)
            cmd_up = [
                "ip", "link", "set", self.interface,
                "up", "type", "can",
                "bitrate", str(config.bitrate)
            ]

            if config.sample_point is not None:
                cmd_up += ["sample-point", str(config.sample_point)]

            if config.fd:
                cmd_up += ["fd", "on"]
                if config.dbitrate:
                    cmd_up += ["dbitrate", str(config.dbitrate)]
                if config.dsample_point:
                    cmd_up += ["dsample-point", str(config.dsample_point)]

            if use_sudo:
                cmd_up = ["sudo"] + cmd_up

            result = self._run_command(cmd_up, use_sudo, password_callback, use_no_interactive)
            if not result:
                return False

            self.current_config = config
            return True

        except Exception as e:
            print(f"Unexpected error: {e}")
            return False

    def _run_command(self, cmd: list, use_sudo: bool, password_callback: Optional[Callable[[], Optional[str]]], use_no_interactive: bool = True) -> bool:
        try:
            # use_sudo=False の場合、またはパスワードコールバックがない場合は通常実行
            if not use_sudo:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=1)
                success = process.returncode == 0

            
            cmd_with_sudo_flag = cmd.copy()
            if use_sudo and not password_callback:
                if use_no_interactive:
                    cmd_with_sudo_flag.insert(1, "-n")  # sudo -n を追加して非対話的にする
                print("Running command with sudo (no password input): " + " ".join(cmd_with_sudo_flag))
                process = subprocess.Popen(
                    cmd_with_sudo_flag,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(timeout=1)
                success = process.returncode == 0
            else:                    
                if cmd_with_sudo_flag[0] == "sudo":
                    if use_no_interactive:
                        cmd_with_sudo_flag.insert(1, "-n")
                    cmd_with_sudo_flag.insert(1 if not use_no_interactive else 2, "-S")
            
                # パスワードコールバックからパスワードを取得
                password = password_callback()
                if not password:
                    print("Password input cancelled")
                    return False
                
                # stdin でパスワードを渡して実行
                process = subprocess.Popen(
                    cmd_with_sudo_flag,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate(input=password + "\n", timeout=1)
                success = process.returncode == 0
            
            return success                
        
        except subprocess.TimeoutExpired:
            print("sudo command timeout")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error applying CAN config: {e}")
            return False
        except Exception as e:
            print(f"Error running command: {e}")
            return False

    def get_current_config(self) -> Optional[CANConfig]:
        return self.current_config
