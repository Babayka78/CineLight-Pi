#!/bin/bash

# serials.sh - Библиотека для управления настройками сериалов
# Версия: 0.2.0
# Дата: 01.12.2025
# Changelog:
#   0.1.0 - Первая версия (файловое хранение)
#   0.2.0 - Переход на SQLite БД с композитным ключом

# Подключаем БД библиотеку
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/db-manager.sh"

# Лог файл для отладки
LOG_DIR="$SCRIPT_DIR/Log"
LOG_FILE="$LOG_DIR/serials.log"
LOG_MAX_SIZE=1048576  # 1 MB максимальный размер

# Создать директорию для логов если нет
mkdir -p "$LOG_DIR"

# Функция ротации лога (если файл больше 1MB, оставляем последние 100KB)
rotate_log_if_needed() {
    if [ -f "$LOG_FILE" ]; then
        local log_size=$(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null)
        if [ "$log_size" -gt "$LOG_MAX_SIZE" ]; then
            # Оставляем последние 100KB
            tail -c 102400 "$LOG_FILE" > "$LOG_FILE.tmp"
            mv "$LOG_FILE.tmp" "$LOG_FILE"
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Лог ротирован (превысил 1MB) ===" >> "$LOG_FILE"
        fi
    fi
}

# Функция для отображения меню настроек сериалов
# Параметры:
#   $1 - текущая директория (для поиска видеофайлов)
show_series_settings() {
    local current_dir="$1"
    
    # Найти первый видеофайл сериала в директории
    local first_video=$(find "$current_dir" -maxdepth 1 -type f \( -name "*.mkv" -o -name "*.mp4" -o -name "*.avi" \) 2>/dev/null | head -1)
    
    if [ -z "$first_video" ]; then
        dialog --msgbox "Не найдено видеофайлов в директории" 7 50
        return 1
    fi
    
    local filename=$(basename "$first_video")
    local series_prefix=$(extract_series_prefix "$filename")
    local series_suffix=$(extract_series_suffix "$filename")
    
    # Если не сериал - выход
    if [ -z "$series_prefix" ]; then
        dialog --msgbox "Это не сериал" 7 40
        return 1
    fi
    
    # Загружаем настройки из БД
    local settings=$(db_get_series_settings "$series_prefix" "$series_suffix")
    
    # Парсим: autoplay|skip_intro|skip_outro|intro_start|intro_end|outro_start
    local autoplay="off"
    local skip_intro="off"
    local skip_outro="off"
    
    if [ -n "$settings" ]; then
        IFS='|' read -r auto intro outro intro_start intro_end outro_start <<< "$settings"
        [ "$auto" == "1" ] && autoplay="on"
        [ "$intro" == "1" ] && skip_intro="on"
        [ "$outro" == "1" ] && skip_outro="on"
    fi
    
    # Восстанавливаем TTY
    exec < /dev/tty
    exec > /dev/tty
    
    # Показываем checklist
    local selected=$(dialog --output-fd 1 \
        --title "Настройки: $series_prefix" \
        --checklist "Выберите опции (SPACE для выбора):" 12 60 3 \
        "autoplay" "Автопродолжение следующей серии" $autoplay \
        "skip_intro" "Пропуск начальной заставки" $skip_intro \
        "skip_outro" "Пропуск конечных титров" $skip_outro \
        2>/dev/tty)
    
    local exit_code=$?
    
    # Если пользователь нажал OK, сохраняем настройки
    if [ $exit_code -eq 0 ]; then
        # Ротация лога если нужно
        rotate_log_if_needed
        
        # Логирование начала сохранения
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Сохранение настроек ===" >> "$LOG_FILE"
        echo "  Директория: $current_dir" >> "$LOG_FILE"
        echo "  Файл: $filename" >> "$LOG_FILE"
        echo "  Series prefix: $series_prefix" >> "$LOG_FILE"
        echo "  Series suffix: $series_suffix" >> "$LOG_FILE"
        echo "  Выбранные опции: $selected" >> "$LOG_FILE"
        
        # Конвертируем выбранные опции в 0/1
        local auto=0; echo "$selected" | grep -q "autoplay" && auto=1
        local intro=0; echo "$selected" | grep -q "skip_intro" && intro=1
        local outro=0; echo "$selected" | grep -q "skip_outro" && outro=1
        
        echo "  Значения: auto=$auto intro=$intro outro=$outro" >> "$LOG_FILE"
        
        # Сохраняем в БД (перенаправляем вывод в лог)
        db_save_series_settings "$series_prefix" "$series_suffix" $auto $intro $outro >> "$LOG_FILE" 2>&1
        
        local save_result=$?
        echo "  Результат сохранения: $save_result" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
    fi
}

# Функция для получения компактной строки статуса для подзаголовка
# Параметры:
#   $1 - директория
# Возвращает: строку вида "[X] Auto Continue  [ ] Intro  [X] Outro"
get_settings_status_compact() {
    local current_dir="$1"
    
    # Найти первый видеофайл
    local first_video=$(find "$current_dir" -maxdepth 1 -type f \( -name "*.mkv" -o -name "*.mp4" -o -name "*.avi" \) 2>/dev/null | head -1)
    
    if [ -z "$first_video" ]; then
        echo ""  # Нет видео
        return
    fi
    
    local filename=$(basename "$first_video")
    local series_prefix=$(extract_series_prefix "$filename")
    local series_suffix=$(extract_series_suffix "$filename")
    
    if [ -z "$series_prefix" ]; then
        echo ""  # Не сериал
        return
    fi
    
    # Загружаем из БД
    local settings=$(db_get_series_settings "$series_prefix" "$series_suffix")
    
    local autoplay="0"
    local skip_intro="0"
    local skip_outro="0"
    
    if [ -n "$settings" ]; then
        IFS='|' read -r autoplay skip_intro skip_outro intro_start intro_end outro_start <<< "$settings"
    fi
    
    # Формируем иконки
    local auto_icon=" "; [ "$autoplay" == "1" ] && auto_icon="X"
    local intro_icon=" "; [ "$skip_intro" == "1" ] && intro_icon="X"
    local outro_icon=" "; [ "$skip_outro" == "1" ] && outro_icon="X"
    
    echo "[$auto_icon] Auto Continue  [$intro_icon] Intro  [$outro_icon] Outro"
}

# Функция для получения значения настройки (для использования в других скриптах)
# Параметры:
#   $1 - директория
#   $2 - ключ настройки (autoplay, skip_intro, skip_outro)
# Возвращает: "1" или "0" или пустую строку если не найдено
get_setting_value() {
    local current_dir="$1"
    local key="$2"
    
    # Найти первый видеофайл
    local first_video=$(find "$current_dir" -maxdepth 1 -type f \( -name "*.mkv" -o -name "*.mp4" -o -name "*.avi" \) 2>/dev/null | head -1)
    
    if [ -z "$first_video" ]; then
        echo ""
        return
    fi
    
    local filename=$(basename "$first_video")
    local series_prefix=$(extract_series_prefix "$filename")
    local series_suffix=$(extract_series_suffix "$filename")
    
    if [ -z "$series_prefix" ]; then
        echo ""
        return
    fi
    
    # Загружаем из БД
    local settings=$(db_get_series_settings "$series_prefix" "$series_suffix")
    
    if [ -z "$settings" ]; then
        echo ""
        return
    fi
    
    # Парсим и возвращаем нужное значение
    IFS='|' read -r autoplay skip_intro skip_outro intro_start intro_end outro_start <<< "$settings"
    
    case "$key" in
        "autoplay")
            echo "$autoplay"
            ;;
        "skip_intro")
            echo "$skip_intro"
            ;;
        "skip_outro")
            echo "$skip_outro"
            ;;
        *)
            echo ""
            ;;
    esac
}
