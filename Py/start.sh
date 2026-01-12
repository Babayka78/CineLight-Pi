#!/bin/bash
# start.sh - Запуск Python video-menu для macOS
# Демонстрационный скрипт

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo "  VLC Video Menu - Python Prototype"
echo "============================================"
echo ""
echo "Запуск Python TUI меню..."
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден!"
    echo "Установите: brew install python3"
    exit 1
fi

# Запуск video-menu.py
python3 "$SCRIPT_DIR/video-menu.py" "$@"
