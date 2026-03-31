from socketcan_initializer import CANConfig, SocketCANInitializer
import argparse

# 起動時の引数でCANインターフェースを指定可能にする

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SocketCANインターフェースの初期化")
    parser.add_argument("interface", type=str, help="CANインターフェース名")
    parser.add_argument("--bitrate", type=int, default=1000000, help="ビットレート (デフォルト: 1000000)")
    parser.add_argument("--fd", action="store_true", help="CAN FDを有効化")
    parser.add_argument("--dbitrate", type=int, help="データフェーズビットレート (CAN FD時)")
    parser.add_argument("--sample-point", type=float, help="サンプルポイント (0.0-1.0)")
    parser.add_argument("--dsample-point", type=float, help="データフェーズサンプルポイント (0.0-1.0)")
    args = parser.parse_args()

    initializer = SocketCANInitializer(interface=args.interface)
    config = CANConfig(
        bitrate=args.bitrate,
        dbitrate=args.dbitrate if args.fd else None,
        fd=args.fd,
        sample_point=args.sample_point,
        dsample_point=args.dsample_point if args.fd else None
    )
    success = initializer.apply(config, use_sudo=True)

    if success:
        mode = "CAN FD" if args.fd else "CAN"
        print(f"{args.interface} initialized successfully as {mode}")
        print(f"  Bitrate: {config.bitrate} bps")
        if args.fd:
            print(f"  Data Bitrate: {config.dbitrate} bps")
    else:
        print(f"Failed to initialize {args.interface}")