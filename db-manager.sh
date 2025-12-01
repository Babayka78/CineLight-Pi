#!/bin/bash

# db-manager.sh - Библиотека для работы с SQLite БД
# Версия: 0.1.0
# Дата: 29.11.2025

# Константы
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB_PATH="${SCRIPT_DIR}/vlc_media.db"

# ============================================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# ============================================================================

# Проверка наличия sqlite3
if ! command -v sqlite3 &> /dev/null; then
    echo "❌ ОШИБКА: sqlite3 не найден!"
    echo ""
    echo "Для установки на Raspberry Pi (Debian) выполните:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install -y sqlite3"
    echo ""
    echo "Или используйте готовый скрипт:"
    echo "  bash install-sqlite3.sh"
    echo ""
    return 1 2>/dev/null || exit 1
fi

# ============================================================================
# ИНИЦИАЛИЗАЦИЯ БД
# ============================================================================

# Создание БД и таблиц если их нет
db_init() {
    # Создание таблицы прогресса воспроизведения
    sqlite3 "$DB_PATH" <<EOF
CREATE TABLE IF NOT EXISTS playback (
    filename TEXT PRIMARY KEY,
    position INTEGER,
    duration INTEGER,
    percent INTEGER,
    series_prefix TEXT DEFAULT NULL,
    series_suffix TEXT DEFAULT NULL,
    description TEXT DEFAULT NULL
);
EOF

    # Создание таблицы настроек сериалов
    sqlite3 "$DB_PATH" <<EOF
CREATE TABLE IF NOT EXISTS series_settings (
    series_prefix TEXT NOT NULL,
    series_suffix TEXT NOT NULL,
    autoplay BOOLEAN DEFAULT 0,
    skip_intro BOOLEAN DEFAULT 0,
    skip_outro BOOLEAN DEFAULT 0,
    intro_start INTEGER DEFAULT NULL,
    intro_end INTEGER DEFAULT NULL,
    outro_start INTEGER DEFAULT NULL,
    description TEXT DEFAULT NULL,
    PRIMARY KEY (series_prefix, series_suffix)
);
EOF
}

# ============================================================================
# УТИЛИТЫ
# ============================================================================

# Извлечение series_prefix из имени файла (название сериала + сезон)
# Параметры: $1 - filename
# Возвращает: "ShowName.S##" или пустую строку для фильмов
extract_series_prefix() {
    local filename="$1"
    
    # Проверяем паттерн S##E## или S##.E##
    if echo "$filename" | grep -qiE '[._\ ]S[0-9]{1,2}[._\ ]?E[0-9]{1,2}'; then
        # Извлекаем всё до E## (включая S##)
        local prefix=$(echo "$filename" | sed -E 's/([._\ ]S[0-9]{1,2})[._\ ]?E[0-9]{1,2}.*/\1/')
        
        # Нормализуем номер сезона (убрать leading zeros, потом добавить обратно)
        local show_part=$(echo "$prefix" | sed -E 's/[._\ ]S[0-9]{1,2}$//')
        local season=$(echo "$prefix" | sed -E 's/.*[._\ ]S([0-9]{1,2})$/\1/')
        
        # Убрать leading zeros
        season=$(echo "$season" | sed 's/^0*//')
        [ -z "$season" ] && season=0
        
        # Форматировать с leading zero
        local season_padded=$(printf "%02d" "$season")
        
        echo "${show_part}.S${season_padded}"
    else
        echo ""  # Не сериал
    fi
}

# Извлечение series_suffix из имени файла (всё после E##, включая расширение)
# Параметры: $1 - filename
# Возвращает: "HDR.2160p.mkv", "720p.mp4", "mkv" или пустую строку
extract_series_suffix() {
    local filename="$1"
    
    # Проверяем паттерн S##E## или S##.E##
    if echo "$filename" | grep -qiE '[._\ ]S[0-9]{1,2}[._\ ]?E[0-9]{1,2}'; then
        # Извлекаем всё после E## (включая расширение)
        local suffix=$(echo "$filename" | sed -E 's/.*[._\ ]S[0-9]{1,2}[._\ ]?E[0-9]{1,2}[._\ ]?//')
        
        # Убрать leading точки/подчёркивания/пробелы
        suffix=$(echo "$suffix" | sed 's/^[._ ]*//')
        
        echo "$suffix"
    else
        echo ""  # Не сериал
    fi
}

# Извлечение композитного series_key (для обратной совместимости)
# Параметры: $1 - filename
# Возвращает: "prefix||suffix" или пустую строку
extract_series_key() {
    local filename="$1"
    local prefix=$(extract_series_prefix "$filename")
    local suffix=$(extract_series_suffix "$filename")
    
    if [ -n "$prefix" ]; then
        echo "${prefix}||${suffix}"
    else
        echo ""  # Не сериал
    fi
}

# ============================================================================
# PLAYBACK ФУНКЦИИ
# ============================================================================

# Сохранение прогресса воспроизведения
# Параметры: $1 - filename, $2 - position, $3 - duration, $4 - percent, 
#            $5 - series_prefix (optional), $6 - series_suffix (optional)
db_save_playback() {
    local filename="$1"
    local position="$2"
    local duration="$3"
    local percent="$4"
    local series_prefix="${5:-NULL}"
    local series_suffix="${6:-NULL}"
    
    # Если series_prefix пустая строка, заменяем на NULL
    if [ -z "$series_prefix" ]; then
        series_prefix="NULL"
    else
        series_prefix="'$series_prefix'"
    fi
    
    # Если series_suffix пустая строка, заменяем на NULL
    if [ -z "$series_suffix" ]; then
        series_suffix="NULL"
    else
        series_suffix="'$series_suffix'"
    fi
    
    sqlite3 "$DB_PATH" <<EOF
INSERT INTO playback (filename, position, duration, percent, series_prefix, series_suffix)
VALUES ('$filename', $position, $duration, $percent, $series_prefix, $series_suffix)
ON CONFLICT(filename) DO UPDATE SET
    position = $position,
    duration = $duration,
    percent = $percent,
    series_prefix = $series_prefix,
    series_suffix = $series_suffix;
EOF
}

# Получение данных воспроизведения
# Параметры: $1 - filename
# Возвращает: position|duration|percent|series_prefix|series_suffix
db_get_playback() {
    local filename="$1"
    
    sqlite3 "$DB_PATH" <<EOF
SELECT position, duration, percent, COALESCE(series_prefix, ''), COALESCE(series_suffix, '')
FROM playback
WHERE filename = '$filename';
EOF
}

# Получение процента просмотра
# Параметры: $1 - filename
# Возвращает: percent (0 если нет записи)
db_get_playback_percent() {
    local filename="$1"
    
    local result=$(sqlite3 "$DB_PATH" "SELECT percent FROM playback WHERE filename = '$filename';")
    
    if [ -z "$result" ]; then
        echo "0"
    else
        echo "$result"
    fi
}

# ============================================================================
# SERIES SETTINGS ФУНКЦИИ
# ============================================================================

# Сохранение настроек сериала
# Параметры: $1 - series_prefix, $2 - series_suffix, $3 - autoplay, $4 - skip_intro, $5 - skip_outro,
#            $6 - intro_start, $7 - intro_end, $8 - outro_start
db_save_series_settings() {
    local series_prefix="$1"
    local series_suffix="$2"
    local autoplay="$3"
    local skip_intro="$4"
    local skip_outro="$5"
    local intro_start="${6:-NULL}"
    local intro_end="${7:-NULL}"
    local outro_start="${8:-NULL}"
    
    sqlite3 "$DB_PATH" <<EOF
INSERT INTO series_settings (series_prefix, series_suffix, autoplay, skip_intro, skip_outro, intro_start, intro_end, outro_start)
VALUES ('$series_prefix', '$series_suffix', $autoplay, $skip_intro, $skip_outro, $intro_start, $intro_end, $outro_start)
ON CONFLICT(series_prefix, series_suffix) DO UPDATE SET
    autoplay = $autoplay,
    skip_intro = $skip_intro,
    skip_outro = $skip_outro,
    intro_start = $intro_start,
    intro_end = $intro_end,
    outro_start = $outro_start;
EOF
}

# Получение настроек сериала
# Параметры: $1 - series_prefix, $2 - series_suffix
# Возвращает: autoplay|skip_intro|skip_outro|intro_start|intro_end|outro_start
db_get_series_settings() {
    local series_prefix="$1"
    local series_suffix="$2"
    
    sqlite3 "$DB_PATH" <<EOF
SELECT autoplay, skip_intro, skip_outro, 
       COALESCE(intro_start, ''), COALESCE(intro_end, ''), COALESCE(outro_start, '')
FROM series_settings
WHERE series_prefix = '$series_prefix' AND series_suffix = '$series_suffix';
EOF
}

# Проверка существования настроек
# Параметры: $1 - series_prefix, $2 - series_suffix
# Возвращает: 0 если есть, 1 если нет
db_series_settings_exist() {
    local series_prefix="$1"
    local series_suffix="$2"
    
    local result=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM series_settings WHERE series_prefix = '$series_prefix' AND series_suffix = '$series_suffix';")
    
    if [ "$result" -gt 0 ]; then
        return 0
    else
        return 1
    fi
}

# Поиск других версий сериала с тем же prefix, но другим suffix
# Параметры: $1 - series_prefix, $2 - series_suffix (текущий, может быть пустым)
# Возвращает: список suffix|last_filename|max_percent (по строке на версию)
db_find_other_versions() {
    local series_prefix="$1"
    local current_suffix="$2"
    
    # Нормализуем текущий suffix для сравнения (пустая строка остаётся пустой)
    local normalized_current="${current_suffix}"
    
    sqlite3 "$DB_PATH" <<EOF
SELECT DISTINCT COALESCE(p1.series_suffix, ''),
       (SELECT filename FROM playback p2 
        WHERE p2.series_prefix = p1.series_prefix 
          AND COALESCE(p2.series_suffix, '') = COALESCE(p1.series_suffix, '')
        ORDER BY rowid DESC LIMIT 1) as last_filename,
       (SELECT MAX(percent) FROM playback p3 
        WHERE p3.series_prefix = p1.series_prefix 
          AND COALESCE(p3.series_suffix, '') = COALESCE(p1.series_suffix, '')) as max_percent
FROM playback p1
WHERE p1.series_prefix = '$series_prefix' 
  AND COALESCE(p1.series_suffix, '') != COALESCE('$normalized_current', '');
EOF
}

# ============================================================================
# ТЕСТОВЫЕ/DEBUG ФУНКЦИИ (только для разработки)
# ============================================================================

# Запись debug данных в description
# Параметры: $1 - filename, $2 - debug_data
db_save_debug_info() {
    local filename="$1"
    local debug_data="$2"
    
    sqlite3 "$DB_PATH" <<EOF
UPDATE playback
SET description = '$debug_data'
WHERE filename = '$filename';
EOF
}

# Чтение debug данных из description
# Параметры: $1 - filename
# Возвращает: содержимое description
db_get_debug_info() {
    local filename="$1"
    
    sqlite3 "$DB_PATH" "SELECT COALESCE(description, '') FROM playback WHERE filename = '$filename';"
}

# ============================================================================
# АВТОИНИЦИАЛИЗАЦИЯ
# ============================================================================

# Инициализируем БД при загрузке библиотеки
db_init
