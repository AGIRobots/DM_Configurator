"""
SLCAN CAN interface implementation
SLCANを使用したCAN通信の実装（USB-CANアダプタ向け）
"""

import can
from can_interface import CANInterface

class SLCANInterface(CANInterface):
    """
    SLCAN implementation
    USB-CANアダプタ向けのSLCANインターフェース
    """

    def __init__(self, interface: str, bitrate=1000000):
        """
        Initialize SLCAN interface
        
        :param interface: Serial device path (e.g., '/dev/ttyACM0')
        :param bitrate: CAN bitrate (default: 1000000 bps)
        """
        super().__init__(bitrate)
        self.interface = interface
    
    def connect(self):
        """
        Connect to SLCAN interface
        
        :return: True if successful, False otherwise
        """
        try:
            self.bus = can.Bus(interface='slcan', channel=self.interface, 
                             bitrate=self.bitrate)
            self.is_connected = True
            print(f"Connected to SLCAN interface: {self.interface}")
            return True
        except Exception as e:
            print(f"SLCAN connection error: {e}")
            self.bus = None
            self.is_connected = False
            return False
    
    def disconnect(self):
        """
        Disconnect from SLCAN interface
        
        :return: True if successful, False otherwise
        """
        try:
            if self.bus is not None:
                self.bus.shutdown()
                self.bus = None
            
            self.is_connected = False
            print("SLCAN disconnected")
            return True
        except Exception as e:
            print(f"SLCAN disconnection error: {e}")
            return False
        
    def send_message(self, can_id: int, data: bytes):
        """
        Send CAN message
        
        :param can_id: CAN message ID
        :param data: Message data (up to 8 bytes)
        :return: True if successful, False otherwise
        """
        try:
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=False)
            self.bus.send(msg)
            return True
        except Exception as e:
            print(f"SLCAN send error: {e}")
            return False
        
    def receive_message(self, timeout=0.1):
        """
        Receive CAN message
        
        :param timeout: Timeout in seconds
        :return: (can_id, data) tuple or None if no message received
        """
        try:
            msg = self.bus.recv(timeout)
            if msg is not None:
                return (msg.arbitration_id, msg.data)
            else:
                return None
        except Exception as e:
            print(f"SLCAN receive error: {e}")
            return None
    
    def is_connected_status(self):
        """Get connection status"""
        return self.is_connected