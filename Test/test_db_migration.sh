#!/bin/bash

source ./db-manager.sh

echo "=== Тест рефакторинга db-manager.sh ==="
echo ""

# Тест 1: Сохранение и получение playback
echo "1️⃣ Тест save/get playback..."
db_save_playback "test_video.mkv" 100 3600 2 "Show.S01" "1080p"
result=$(db_get_playback "test_video.mkv")
echo "   Результат: $result"
if [[ "$result" == "100|3600|2|Show.S01|1080p" ]]; then
    echo "   ✅ PASS"
else
    echo "   ❌ FAIL"
fi
echo ""

# Тест 2: Получение процента
echo "2️⃣ Тест get percent..."
percent=$(db_get_playback_percent "test_video.mkv")
echo "   Процент: $percent"
if [[ "$percent" == "2" ]]; then
    echo "   ✅ PASS"
else
    echo "   ❌ FAIL"
fi
echo ""

# Тест 3: SQL Injection защита
echo "3️⃣ Тест SQL Injection защиты..."
db_save_playback "'; DROP TABLE playback; --" 50 1000 5
result=$(db_get_playback "'; DROP TABLE playback; --")
echo "   Результат: $result"
if [[ "$result" == "50|1000|5||" ]]; then
    echo "   ✅ PASS - SQL injection заблокирован"
else
    echo "   ❌ FAIL"
fi
echo ""

# Тест 4: Сохранение настроек сериала
echo "4️⃣ Тест save/get series settings..."
db_save_series_settings "Show.S01" "1080p" 1 0 1 10 60 3500
settings=$(db_get_series_settings "Show.S01" "1080p")
echo "   Настройки: $settings"
if [[ "$settings" == "1|0|1|10|60|3500" ]]; then
    echo "   ✅ PASS"
else
    echo "   ❌ FAIL"
fi
echo ""

# Тест 5: Проверка существования настроек
echo "5️⃣ Тест settings_exist..."
if db_series_settings_exist "Show.S01" "1080p"; then
    echo "   ✅ PASS - настройки существуют"
else
    echo "   ❌ FAIL"
fi
echo ""

echo "=== Тесты завершены ==="
