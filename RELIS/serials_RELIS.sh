#!/bin/bash

# serials.sh - Библиотека для управления настройками сериалов
# Версия: 0.3.0
# Дата: 29.12.2025
# Changelog:
#   0.1.0 - Первая версия (файловое хранение)
#   0.2.0 - Переход на SQLite БД с композитным ключом
#   0.2.1 - Исправлен баг: Cancel/ESC теперь не сохраняют изменения в БД
#   0.2.2 - Добавлена кнопка "Редактировать время" через extra button
#   0.3.0 - Редактор времени полностью работает: сохранение в БД через tput

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

# Функция конвертации секунд в MM:SS
seconds_to_mmss() {
    local total_seconds="$1"
    
    # Если пустое значение - возвращаем пустую строку
    if [ -z "$total_seconds" ]; then
        echo ""
        return
    fi
    
    local minutes=$((total_seconds / 60))
    local seconds=$((total_seconds % 60))
    printf "%02d:%02d" "$minutes" "$seconds"
}

# Функция конвертации MM:SS в секунды
mmss_to_seconds() {
    local mmss="$1"
    
    # Если пустое значение - возвращаем пустую строку
    if [ -z "$mmss" ]; then
        echo ""
        return
    fi
    
    # Проверка формата MM:SS
    if [[ ! "$mmss" =~ ^[0-9]+:[0-9]{2}$ ]]; then
        echo "" # Некорректный формат
        return
    fi
    
    local minutes="${mmss%:*}"
    local seconds="${mmss#*:}"
    echo $((minutes * 60 + seconds))
}

# Функция для редактирования времён skip markers
# Параметры: $1 - intro_start (секунды), $2 - intro_end (секунды), $3 - outro_start (секунды)
# Возвращает: через stdout строку "intro_start|intro_end|outro_start" в секундах, или пустую строку при Cancel
show_time_editor_dialog() {
    local intro_start_sec="$1"
    local intro_end_sec="$2"
    local outro_start_sec="$3"
    
    # Конвертируем секунды в MM:SS для отображения
    local intro_start_mm=$(seconds_to_mmss "$intro_start_sec")
    local intro_end_mm=$(seconds_to_mmss "$intro_end_sec")
    local outro_start_mm=$(seconds_to_mmss "$outro_start_sec")
    
    # Если пустые значения - поставим 00:00 как placeholder
    [ -z "$intro_start_mm" ] && intro_start_mm="00:00"
    [ -z "$intro_end_mm" ] && intro_end_mm="00:00"
    [ -z "$outro_start_mm" ] && outro_start_mm="00:00"
    
    # Восстанавливаем TTY
    exec < /dev/tty
    exec > /dev/tty
    
    # Настройка цветовой схемы для полей ввода
    local dialogrc_file="/tmp/dialogrc_$$"
    export DIALOGRC="$dialogrc_file"
    
    cat > "$dialogrc_file" << 'EOF'
use_colors = ON
form_active_text_color = (WHITE,BLUE,ON)
form_text_color = (BLACK,WHITE,OFF)
EOF
    
    # Временный файл для результата
    local tmpfile=$(mktemp)
    
    # Показываем form dialog
    dialog --output-fd 3 \
        --title "Редактирование времён (MM:SS)" \
        --form "Введите времена в формате ММ:СС\n(пустое поле = отключено)" 13 50 3 \
        "Intro Start:" 1 1 "$intro_start_mm" 1 18 10 10 \
        "Intro End:"   2 1 "$intro_end_mm"   2 18 10 10 \
        "Outro Start:" 3 1 "$outro_start_mm" 3 18 10 10 \
        3>"$tmpfile" 2>/dev/tty
    
    local exit_code=$?
    
    # Читаем результат (3 строки)
    local result=$(cat "$tmpfile")
    rm -f "$tmpfile"
    rm -f "$dialogrc_file"
    unset DIALOGRC
    
    # Если Cancel/ESC - возвращаем пустую строку
    if [ $exit_code -ne 0 ]; then
        echo ""
        return 1
    fi
    
    # Парсим результат (каждое поле на отдельной строке)
    local line_num=0
    local new_intro_start=""
    local new_intro_end=""
    local new_outro_start=""
    
    while IFS= read -r line; do
        line_num=$((line_num + 1))
        
        # Пропускаем пустые строки и "00:00"
        if [ -z "$line" ] || [ "$line" = "00:00" ]; then
            continue
        fi
        
        # Валидация формата MM:SS
        if [[ ! "$line" =~ ^[0-9]+:[0-9]{2}$ ]]; then
            dialog --msgbox "Ошибка: '$line' не соответствует формату MM:SS" 7 50
            echo ""
            return 1
        fi
        
        # Конвертируем в секунды
        local seconds=$(mmss_to_seconds "$line")
        
        case $line_num in
            1) new_intro_start="$seconds" ;;
            2) new_intro_end="$seconds" ;;
            3) new_outro_start="$seconds" ;;
        esac
    done <<< "$result"
    
    # Дополнительная валидация: intro_end должен быть больше intro_start
    if [ -n "$new_intro_start" ] && [ -n "$new_intro_end" ]; then
        if [ "$new_intro_end" -le "$new_intro_start" ]; then
            dialog --msgbox "Ошибка: Intro End должен быть больше Intro Start" 7 50
            echo ""
            return 1
        fi
    fi
    
    # Возвращаем результат (через stdout для capture, но не на экран)
    echo "${new_intro_start}|${new_intro_end}|${new_outro_start}" >&1
    return 0
}


# Функция для сохранения настроек в БД (вызывается только при OK)
save_settings_to_db() {
    local current_dir="$1"
    local filename="$2"
    local series_prefix="$3"
    local series_suffix="$4"
    local selected="$5"       # Строка с выбранными чекбоксами
    local intro_start="${6:-}"
    local intro_end="${7:-}"
    local credits_duration="${8:-}"
    
    rotate_log_if_needed  # Ротация лога если нужно
    
    # Парсим selected
    local auto=0; local intro=0; local outro=0
    echo "$selected" | grep -q "autoplay" && auto=1
    echo "$selected" | grep -q "skip_intro" && intro=1
    echo "$selected" | grep -q "skip_outro" && outro=1
    
    # Конвертация пустых строк в NULL для БД
    [ -z "$intro_start" ] && intro_start=""
    [ -z "$intro_end" ] && intro_end=""
    [ -z "$credits_duration" ] && credits_duration=""
    
    # Логирование
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') ===" >> "$LOG_FILE"
    echo "Сохранение: $series_prefix / $series_suffix" >> "$LOG_FILE"
    echo "  Флаги: auto=$auto intro=$intro outro=$outro" >> "$LOG_FILE"
    echo "  Времена: intro_start=$intro_start intro_end=$intro_end credits_duration=$credits_duration" >> "$LOG_FILE"
    
    # Сохранение в БД
    db_save_series_settings "$series_prefix" "$series_suffix" $auto $intro $outro "$intro_start" "$intro_end" "$credits_duration" >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "ОК: сохранено" >> "$LOG_FILE"
        return 0
    else
        echo "ERROR: ошибка сохранения" >> "$LOG_FILE"
        return 1
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
    
    # Парсим: autoplay|skip_intro|skip_outro|intro_start|intro_end|credits_duration
    local auto="0"
    local intro="0"
    local outro="0"
    local intro_start=""
    local intro_end=""
    local credits_duration=""
    
    if [ -n "$settings" ]; then
        IFS='|' read -r auto intro outro intro_start intro_end credits_duration <<< "$settings"
    fi
    
    # Преобразуем 0/1 в on/off для dialog
    local autoplay="off"; [ "$auto" == "1" ] && autoplay="on"
    local skip_intro="off"; [ "$intro" == "1" ] && skip_intro="on"
    local skip_outro="off"; [ "$outro" == "1" ] && skip_outro="on"
    
    # Восстанавливаем TTY
    exec < /dev/tty
    exec > /dev/tty
    
    # ШАГ 1: Показываем checklist для булевых опций + кнопка редактирования времени
    local tmpfile=$(mktemp)
    
    dialog --output-fd 3 \
        --title "Настройки: $series_prefix" \
        --extra-button \
        --extra-label "Редактировать время" \
        --checklist "Выберите опции (SPACE для выбора):" 12 60 3 \
        "autoplay" "Автопродолжение следующей серии" $autoplay \
        "skip_intro" "Пропуск начальной заставки" $skip_intro \
        "skip_outro" "Пропуск конечных титров" $skip_outro \
        3>"$tmpfile" 2>/dev/tty
    
    local exit_code=$?
    local selected=$(cat "$tmpfile")
    rm -f "$tmpfile"
    
    # Если Cancel (exit_code=1) или ESC (exit_code=255) - выходим без сохранения
    if [ $exit_code -eq 1 ] || [ $exit_code -eq 255 ]; then
        return 0
    fi
    
    # Если нажата кнопка "Редактировать время" (exit_code=3)
    if [ $exit_code -eq 3 ]; then
        # Конвертируем секунды в MM:SS
        local intro_start_mm=$(seconds_to_mmss "$intro_start")
        local intro_end_mm=$(seconds_to_mmss "$intro_end")
        local credits_mm=$(seconds_to_mmss "$credits_duration")
        
        # Очистить экран от dialog
        clear
        
        # Вызываем tput редактор с передачей series_prefix и series_suffix
        # Редактор сам сохранит времена в БД
        ./edit-time-tput.sh "$intro_start_mm" "$intro_end_mm" "$credits_mm" "$series_prefix" "$series_suffix"
        local edit_exit=$?
        
        # Если отменено (exit_code != 0) - просто возвращаемся к настройкам
        # БД не изменялась, поэтому просто покажем меню снова
        show_series_settings "$current_dir"
        return
    fi
    
    # ШАГ 2: Времена НЕ затираются - используются значения загруженные из БД выше
    # Времена устанавливаются через RED кнопку в vlc-cec.sh
    # Здесь мы только меняем флаги skip_intro/skip_outro, времена остаются без изменений
    
    # ЗАКОММЕНТИРОВАНО: автоматический вызов редактора времён
    # local show_time_editor=0
    # echo "$selected" | grep -q "skip_intro" && show_time_editor=1
    # echo "$selected" | grep -q "skip_outro" && show_time_editor=1
    # 
    # if [ $show_time_editor -eq 1 ]; then
    #     local time_result=$(show_time_editor_dialog "$intro_start" "$intro_end" "$outro_start")
    #     clear
    #     if [ -z "$time_result" ]; then
    #         return 0
    #     fi
    #     IFS='|' read -r intro_start intro_end outro_start <<< "$time_result"
    # else
    #     intro_start=""
    #     intro_end=""
    #     outro_start=""
    # fi
    
    # Сохраняем всё в БД (флаги + сохранённые времена)
    save_settings_to_db "$current_dir" "$filename" "$series_prefix" "$series_suffix" "$selected" "$intro_start" "$intro_end" "$credits_duration"
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
    local intro_start=""
    local intro_end=""
    local credits_duration=""
    
    if [ -n "$settings" ]; then
        IFS='|' read -r autoplay skip_intro skip_outro intro_start intro_end credits_duration <<< "$settings"
    fi
    
    # Формируем иконки
    local auto_icon=" "; [ "$autoplay" == "1" ] && auto_icon="X"
    local intro_icon=" "; [ "$skip_intro" == "1" ] && intro_icon="X"
    local outro_icon=" "; [ "$skip_outro" == "1" ] && outro_icon="X"
    
    # Формируем строку с временами
    local intro_times=""
    local credits_time=""
    
    # Intro: если есть хотя бы одно значение
    if [ -n "$intro_start" ] || [ -n "$intro_end" ]; then
        local start_mm=$(seconds_to_mmss "$intro_start")
        local end_mm=$(seconds_to_mmss "$intro_end")
        intro_times=": ${start_mm}-${end_mm}"
    fi
    
    # Credits: если есть значение
    if [ -n "$credits_duration" ]; then
        local credits_mm=$(seconds_to_mmss "$credits_duration")
        credits_time=": ${credits_mm}"
    fi
    
    echo "[$auto_icon] Auto  [$intro_icon] Intro${intro_times}  [$outro_icon] Outro${credits_time}"
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
