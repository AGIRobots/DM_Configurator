"""
CAN Interface Abstract Base Class
CANバスの抽象化インターフェース
"""

from abc import ABC, abstractmethod
import can


class CANInterface(ABC):
    """
    CAN通信の抽象インターフェース
    複数のCAN実装（SLCAN、socket CAN等）に対応
    """
    
    def __init__(self, bitrate=1000000):
        """
        Initialize CAN interface
        
        :param bitrate: CAN bitrate (default: 1000000 bps)
        """
        self.bitrate = bitrate
        self.bus = None
        self.is_connected = False
    
    @abstractmethod
    def connect(self):
        """
        Connect to CAN bus
        
        :return: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """
        Disconnect from CAN bus
        
        :return: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def send_message(self, can_id: int, data: bytes):
        """
        Send CAN message
        
        :param can_id: CAN message ID
        :param data: Message data (up to 8 bytes)
        :return: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def receive_message(self, timeout=0.1):
        """
        Receive CAN message
        
        :param timeout: Timeout in seconds
        :return: (can_id, data) tuple or None if no message received
        """
        pass
    
    def is_connected_status(self):
        """Get connection status"""
        return self.is_connected
