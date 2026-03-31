from socketcan_initializer import CANConfig, SocketCANInitializer
import argparse


def parse_bitrate(bitrate_str):
    """
    ビットレート文字列をパース
    例: "1M" -> 1000000, "125k" -> 125000, "1000000" -> 1000000
    """
    bitrate_str = str(bitrate_str).strip().upper()
    
    if bitrate_str.endswith('M'):
        return int(float(bitrate_str[:-1]) * 1000000)
    elif bitrate_str.endswith('K'):
        return int(float(bitrate_str[:-1]) * 1000)
    else:
        return int(bitrate_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SocketCANインターフェースの初期化")
    parser.add_argument("interface", type=str, help="CANインターフェース名")
    parser.add_argument("--bitrate", type=str, default="1M", help="ビットレート (例: 1M, 500k, 1000000) (デフォルト: 1M)")
    parser.add_argument("--fd", action="store_true", help="CAN FDを有効化")
    parser.add_argument("--dbitrate", type=str, help="データフェーズビットレート (例: 5M, 2000000) (CAN FD時)")
    parser.add_argument("--sample-point", type=float, help="サンプルポイント (0.0-1.0)")
    parser.add_argument("--dsample-point", type=float, help="データフェーズサンプルポイント (0.0-1.0)")
    args = parser.parse_args()

    bitrate = parse_bitrate(args.bitrate)
    dbitrate = parse_bitrate(args.dbitrate) if args.dbitrate else None

    initializer = SocketCANInitializer(interface=args.interface)
    config = CANConfig(
        bitrate=bitrate,
        dbitrate=dbitrate if args.fd else None,
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