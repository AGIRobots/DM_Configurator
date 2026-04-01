#!/bin/bash

# SocketCAN Interface Initialization Script
# ビットレート設定: 1M, 500k, 1000000 など対応

parse_bitrate() {
    local bitrate_str="$1"
    bitrate_str=$(echo "$bitrate_str" | tr '[:lower:]' '[:upper:]')
    
    if [[ $bitrate_str =~ ^([0-9.]+)M$ ]]; then
        echo "${BASH_REMATCH[1]} * 1000000" | bc | tr -d '.'
    elif [[ $bitrate_str =~ ^([0-9.]+)K$ ]]; then
        echo "${BASH_REMATCH[1]} * 1000" | bc | tr -d '.'
    else
        echo "$bitrate_str" | grep -E '^[0-9]+$' && echo "$bitrate_str" || echo ""
    fi
}

usage() {
    cat << EOF
使用方法: $0 <interface> [オプション]

引数:
  interface                CANインターフェース名 (例: can0, can1)

オプション:
  --bitrate BITRATE       ビットレート (例: 1M, 500k, 1000000) (デフォルト: 1M)
  --fd                    CAN FDを有効化
  --dbitrate BITRATE      データフェーズビットレート (例: 5M, 2000000)
  --sample-point POINT    サンプルポイント (0.0-1.0)
  --dsample-point POINT   データフェーズサンプルポイント (0.0-1.0)
  -h, --help              ヘルプを表示

例:
  $0 can0
  $0 can0 --bitrate 125k
  $0 can0 --bitrate 500k --fd --dbitrate 5M
EOF
    exit 1
}

# デフォルト値
INTERFACE=""
BITRATE="1M"
FD=false
DBITRATE=""
SAMPLE_POINT=""
DSAMPLE_POINT=""

# 引数解析
if [ $# -lt 1 ]; then
    usage
fi

# ヘルプチェック
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    usage
fi

INTERFACE="$1"
shift

while [ $# -gt 0 ]; do
    case "$1" in
        --bitrate)
            BITRATE="$2"
            shift 2
            ;;
        --fd)
            FD=true
            shift
            ;;
        --dbitrate)
            DBITRATE="$2"
            shift 2
            ;;
        --sample-point)
            SAMPLE_POINT="$2"
            shift 2
            ;;
        --dsample-point)
            DSAMPLE_POINT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "エラー: 不明なオプション: $1"
            usage
            ;;
    esac
done

# ビットレートをパース
BITRATE_BPS=$(parse_bitrate "$BITRATE")
if [ -z "$BITRATE_BPS" ]; then
    echo "エラー: 無効なビットレート: $BITRATE"
    exit 1
fi

if [ "$FD" = true ] && [ -n "$DBITRATE" ]; then
    DBITRATE_BPS=$(parse_bitrate "$DBITRATE")
    if [ -z "$DBITRATE_BPS" ]; then
        echo "エラー: 無効なデータフェーズビットレート: $DBITRATE"
        exit 1
    fi
fi

# インターフェースをダウン
echo "Setting $INTERFACE down..."
sudo ip link set "$INTERFACE" down
if [ $? -ne 0 ]; then
    echo "エラー: インターフェースをダウンできません"
    exit 1
fi

# インターフェースをアップ (CAN設定付き)
CMD="sudo ip link set $INTERFACE up type can bitrate $BITRATE_BPS"

if [ -n "$SAMPLE_POINT" ]; then
    CMD="$CMD sample-point $SAMPLE_POINT"
fi

if [ "$FD" = true ]; then
    CMD="$CMD fd on"
    if [ -n "$DBITRATE_BPS" ]; then
        CMD="$CMD dbitrate $DBITRATE_BPS"
    fi
    if [ -n "$DSAMPLE_POINT" ]; then
        CMD="$CMD dsample-point $DSAMPLE_POINT"
    fi
fi

echo "Setting $INTERFACE up..."
eval "$CMD"
if [ $? -ne 0 ]; then
    echo "エラー: インターフェースをアップできません"
    exit 1
fi

# 成功メッセージ
MODE="CAN"
if [ "$FD" = true ]; then
    MODE="CAN FD"
fi

echo ""
echo "✓ $INTERFACE initialized successfully as $MODE"
echo "  Bitrate: $BITRATE_BPS bps"
if [ "$FD" = true ] && [ -n "$DBITRATE_BPS" ]; then
    echo "  Data Bitrate: $DBITRATE_BPS bps"
fi
