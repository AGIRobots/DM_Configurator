"""
Socket CAN Interface Implementation
Socket CANを使用したCAN通信の実装（Linuxネイティブ）
"""

import can
from can_interface import CANInterface


class SocketCANInterface(CANInterface):
    """
    Socket CAN implementation
    Linuxのネイティブsocket CANインターフェースを使用
    """

    def __init__(self, interface: str, bitrate=1000000):
        """
        Initialize Socket CAN interface
        
        :param interface: CAN interface name (e.g., 'can0', 'vcan0')
        :param bitrate: CAN bitrate (default: 1000000 bps)
        """
        super().__init__(bitrate)
        self.interface = interface
    
    def connect(self):
        """
        Connect to Socket CAN interface
        
        :return: True if successful, False otherwise
        """
        try:
            self.bus = can.Bus(interface='socketcan', channel=self.interface, 
                             bitrate=self.bitrate)
            self.is_connected = True
            return True
        except Exception as e:
            self.bus = None
            self.is_connected = False
            return False
    
    def disconnect(self):
        """
        Disconnect from Socket CAN interface
        
        :return: True if successful, False otherwise
        """
        try:
            if self.bus is not None:
                self.bus.shutdown()
                self.bus = None
            
            self.is_connected = False
            print("Socket CAN disconnected")
            return True
        except Exception as e:
            print(f"Socket CAN disconnection error: {e}")
            return False
    
    def send_message(self, can_id: int, data: bytes):
        """
        Send CAN message
        
        :param can_id: CAN message ID (11-bit for standard, 29-bit for extended)
        :param data: Message data (up to 8 bytes)
        :return: True if successful, False otherwise
        """
        if not self.is_connected or self.bus is None:
            print("CAN bus not connected")
            return False
        
        try:
            msg = can.Message(arbitration_id=can_id, data=data, is_extended_id=self.is_extended_id)
            self.bus.send(msg)
            return True
        except Exception as e:
            print(f"Failed to send CAN message: {e}")
            return False
    
    def receive_message(self, timeout=0.1):
        """
        Receive CAN message
        
        :param timeout: Timeout in seconds
        :return: (can_id, data) tuple or None if no message received
        """
        if not self.is_connected or self.bus is None:
            return None
        
        try:
            msg = self.bus.recv(timeout=timeout)
            if msg is not None:
                return (msg.arbitration_id, bytes(msg.data))
            return None
        except Exception as e:
            return None
