import can

try:
    # interface='slcan' を使い、channel に正しいパスを入れる
    bus = can.interface.Bus(
        interface='slcan', 
        channel='/dev/ttyACM6', # ← ここを ls で確認した名前に変える
        bitrate=1000000
    )
    
    msg = can.Message(arbitration_id=0x123, data=[1, 2, 3, 4], is_extended_id=False)
    bus.send(msg)
    print("送信成功！")
    bus.shutdown()

except Exception as e:
    print(f"エラーが発生しました: {e}")