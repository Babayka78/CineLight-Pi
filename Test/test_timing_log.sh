#!/bin/bash

# Тест логирования тайминга

# Создаём временную структуру папок
TEST_DIR="/tmp/vlc_timing_test"
mkdir -p "$TEST_DIR/Series/Show1"
mkdir -p "$TEST_DIR/Movies"

# Создаём тестовые "видео" файлы
touch "$TEST_DIR/Series/Show1/Episode.S01E01.mkv"
touch "$TEST_DIR/Series/Show1/Episode.S01E02.mkv"
touch "$TEST_DIR/Movies/Movie1.mp4"
touch "$TEST_DIR/Movies/Movie2.mkv"

echo "Тестовые файлы созданы в $TEST_DIR"
echo ""
echo "Для тестирования:"
echo "1. Измените START_DIR в video-menu.sh на: $TEST_DIR"
echo "2. Запустите video-menu.sh"
echo "3. Походите по папкам"
echo "4. Проверьте лог: cat Log/video-menu-timing.log"
echo ""
echo "Формат лога:"
echo "[YYYY-MM-DD HH:MM:SS] [ENTER] /path/to/folder"
echo "[YYYY-MM-DD HH:MM:SS] [BUILD_LIST] Files: 5, Time: 0.123s"
echo "[YYYY-MM-DD HH:MM:SS] [DIALOG] Time: 0.056s"
echo "[YYYY-MM-DD HH:MM:SS] [TOTAL] Time: 0.234s"
echo "[YYYY-MM-DD HH:MM:SS] [EXIT] /from/folder -> /to/folder"
