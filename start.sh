#!/bin/bash
echo "=============================="
echo " DKEC 工作進度追蹤系統"
echo "=============================="
echo ""

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[錯誤] 找不到 Python3，請先安裝"
    exit 1
fi

# Install Flask if needed
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[安裝] 正在安裝 Flask..."
    pip3 install flask
    echo ""
fi

echo "[啟動] 正在啟動伺服器..."
echo "[開啟] http://localhost:5000"
echo ""
echo "按 Ctrl+C 可停止伺服器"
echo ""

# Open browser (works on Mac and Linux)
(sleep 2 && open http://localhost:5000 2>/dev/null || xdg-open http://localhost:5000 2>/dev/null) &

# Start Flask
python3 app.py
