#!/bin/bash
# Wrapper для запуска video-menu-Prompt_toolkit.py с виртуальным окружением

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python3"
SCRIPT="$SCRIPT_DIR/video-menu-Prompt_toolkit.py"

# Проверяем наличие виртуального окружения
if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "Создайте его командой: python3 -m venv venv"
    echo "Установите зависимости: venv/bin/pip install -r Py/requirements.txt"
    exit 1
fi

# Запускаем скрипт с виртуальным окружением
exec "$VENV_PYTHON" "$SCRIPT" "$@"
