#!/bin/bash

# Тест оптимизации пакетной загрузки процентов

echo "=== Тест оптимизации video-menu.sh ==="
echo ""

source ./playback-tracker.sh

# Создаём тестовые данные в БД
echo "Создаём тестовые данные..."
for i in {1..32}; do
    python3 vlc_db.py save_playback "test_video_$i.mkv" $((i*100)) 3600 $((i*3)) "" "" > /dev/null
done

echo "✅ 32 тестовых файла созданы в БД"
echo ""

# Тест 1: Старый способ (N запросов)
echo "🐌 Старый способ (N отдельных запросов к БД):"
start=$(date +%s.%N)
for i in {1..32}; do
    percent=$(db_get_playback_percent "test_video_$i.mkv")
done
end=$(date +%s.%N)
old_time=$(echo "$end - $start" | bc)
echo "   Время: ${old_time}s для 32 файлов"
echo ""

# Тест 2: Новый способ (1 пакетный запрос)
echo "🚀 Новый способ (1 пакетный запрос):"
start=$(date +%s.%N)
filenames=()
for i in {1..32}; do
    filenames+=("test_video_$i.mkv")
done
cache_playback_percents "/tmp/test" "${filenames[@]}"
for i in {1..32}; do
    percent="${PLAYBACK_PERCENT_CACHE[test_video_$i.mkv]}"
done
end=$(date +%s.%N)
new_time=$(echo "$end - $start" | bc)
echo "   Время: ${new_time}s для 32 файлов"
echo ""

speedup=$(echo "scale=2; $old_time / $new_time" | bc)
echo "📊 Результат:"
echo "   Старый способ: ${old_time}s"
echo "   Новый способ:  ${new_time}s"
echo "   Ускорение:     ${speedup}x"
echo ""

echo "=== Тест завершён ==="
