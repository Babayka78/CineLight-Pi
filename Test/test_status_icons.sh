#!/bin/bash
# Диагностика статусов иконок

echo "========================================="
echo "Диагностика статусов иконок video-menu"
echo "========================================="
echo ""

cd ~/mac_disk/Project/vlc || exit 1

echo "1. Проверка версии bash:"
bash --version | head -1
echo ""

echo "2. Проверка vlc_db.py get_batch:"
first_video=$(find ~/mac_disk/T7 -maxdepth 1 -type f \( -iname "*.mkv" -o -iname "*.avi" -o -iname "*.mp4" \) | head -1)
if [ -n "$first_video" ]; then
    filename=$(basename "$first_video")
    directory=$(dirname "$first_video")
    echo "   Файл: $filename"
    echo "   Папка: $directory"
    echo ""
    echo "   Результат get_batch:"
    python3 vlc_db.py get_batch "$directory" "$filename"
    echo ""
else
    echo "   ❌ Видеофайлы не найдены"
fi

echo "3. Проверка кеша:"
source ./playback-tracker.sh

if [ -n "$first_video" ]; then
    filename=$(basename "$first_video")
    directory=$(dirname "$first_video")
    
    echo "   Вызываем cache_playback_percents..."
    cache_playback_percents "$directory" "$filename"
    
    echo "   Кеш: ${PLAYBACK_PERCENT_CACHE[$filename]}"
    
    icon=$(get_status_icon "$directory" "$filename")
    echo "   Иконка: '$icon'"
fi

echo ""
echo "Диагностика завершена"
