#!/bin/bash

# Путь к основному скрипту VLC-CEC
#VLC_SCRIPT="$HOME/vlc/vlc-cec.sh"
VLC_SCRIPT="./vlc-cec.sh"

# Подключаем библиотеку отслеживания сериалов
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/series-tracker.sh"

# Начальная директория
START_DIR="$HOME/mac_disk"

# Проверка что скрипт VLC существует
if [ ! -f "$VLC_SCRIPT" ]; then
    echo "Ошибка: Скрипт $VLC_SCRIPT не найден!"
    echo "Создайте vlc-cec.sh в домашней директории"
    exit 1
fi

# Проверка что директория существует
if [ ! -d "$START_DIR" ]; then
    echo "Ошибка: Директория $START_DIR не найдена!"
    exit 1
fi

# Функция для отображения меню с dialog
show_menu() {
    local current_dir="$1"
    local title="Выбор видео: ${current_dir/#$HOME/~}"
    
    # Получаем список файлов и папок
    local items=()
    
    # Добавляем ".." если не в корне
    if [ "$current_dir" != "$START_DIR" ]; then
        items+=(".." "Назад")
    fi
    
    # Добавляем директории (только реальные папки, скрываем начинающиеся с точки)
    while IFS= read -r dir; do
        if [ -d "$current_dir/$dir" ] && [[ "$dir" != .* ]]; then
            items+=("$dir" "DIR")
        fi
    done < <(ls -1 "$current_dir" 2>/dev/null | sort)
    
    # Добавляем видео файлы (avi, mp4, mkv, mov, wmv, flv)
    while IFS= read -r -d '' file; do
        local filename=$(basename "$file")
        local filesize=$(du -h "$file" | cut -f1)
        
        # Добавляем иконку статуса для сериалов
        local display_name="$filename"
        if is_series_file "$filename"; then
            local status_icon=$(get_status_icon "$current_dir" "$filename")
            if [ -n "$status_icon" ]; then
                display_name="${status_icon} ${filename}"
            fi
        fi
        
        # В меню: ключ = название с иконкой, описание = только размер
        items+=("$display_name" "$filesize")
    done < <(find "$current_dir" -maxdepth 1 -type f \( -iname "*.avi" -o -iname "*.mp4" -o -iname "*.mkv" -o -iname "*.mov" -o -iname "*.wmv" -o -iname "*.flv" \) -print0 | sort -z)
    
    # Если нет элементов
    if [ ${#items[@]} -eq 0 ]; then
        dialog --title "Пусто" --msgbox "В этой директории нет видео файлов" 8 50
        return 1
    fi
    
    # Показываем меню (восстанавливаем TTY после VLC)
    # Явно восстанавливаем stdin/stdout на терминал
    exec < /dev/tty
    exec > /dev/tty
    
    # Вычисляем оптимальную ширину окна
    local max_width=120
    local longest_item=""
    local i=0
    while [ $i -lt ${#items[@]} ]; do
        local item_text="${items[$((i+1))]}"  # Берём описание (не ключ)
        local item_len=${#item_text}
        if [ $item_len -gt $max_width ]; then
            max_width=$item_len
            longest_item="$item_text"
        fi
        i=$((i + 2))  # Перескакиваем по парам (ключ, значение)
    done
    
    # Добавляем отступ для красоты и границ окна
    max_width=$((max_width + 10))
    
    # Минимальная ширина 120
    if [ $max_width -lt 120 ]; then
        max_width=120
    fi
    
    # ОТЛАДКА: показываем вычисленную ширину
    echo "DEBUG: Вычисленная ширина окна: $max_width"
    
    local choice
    choice=$(dialog --output-fd 1 \
        --title "$title" \
        --menu "Выберите файл или папку:" 20 $max_width 15 \
        "${items[@]}" \
        2>/dev/tty)
    
    local exit_code=$?
    
    # Обработка выбора
    if [ $exit_code -eq 0 ] && [ -n "$choice" ]; then
        # Убираем иконку из выбора если есть ([X] filename -> filename)
        local clean_choice="$choice"
        if [[ "$choice" =~ ^\[.\]\ (.+)$ ]]; then
            clean_choice="${BASH_REMATCH[1]}"
        fi
        
        if [ "$clean_choice" == ".." ]; then
            # Переход на уровень выше
            local parent_dir=$(dirname "$current_dir")
            if [ "$parent_dir" != "/" ]; then
                show_menu "$parent_dir"
            else
                show_menu "$START_DIR"
            fi
        elif [ -d "$current_dir/$clean_choice" ]; then
            # Переход в директорию
            show_menu "$current_dir/$clean_choice"
        elif [ -f "$current_dir/$clean_choice" ]; then
            # Запуск видео
            clear
            echo "Запуск: $clean_choice"
            echo ""
            
            # Проверяем есть ли сохранённая позиция для сериала
            if is_series_file "$clean_choice"; then
                local progress=$(load_progress "$current_dir" "$clean_choice")
                if [ -n "$progress" ]; then
                    local saved_seconds=$(echo "$progress" | cut -d: -f1)
                    local saved_percent=$(echo "$progress" | cut -d: -f3)
                    
                    # Показываем информацию о сохранённой позиции
                    echo "Найдена сохранённая позиция: ${saved_percent}% ($(($saved_seconds / 60)) мин $(($saved_seconds % 60)) сек)"
                    echo ""
                    
                    # Запуск VLC с сохранённой позиции (передаём секунды отдельным параметром)
                    "$VLC_SCRIPT" "$saved_seconds" "$current_dir/$clean_choice"
                else
                    # Запуск с начала
                    "$VLC_SCRIPT" "$current_dir/$clean_choice"
                fi
            else
                # Обычный файл - запуск с начала
                "$VLC_SCRIPT" "$current_dir/$clean_choice"
            fi
            
	    # Автоматический возврат в меню
            show_menu "$current_dir"
        fi
    elif [ $exit_code -eq 1 ]; then
        # Отмена - выход
        clear
        exit 0
    fi
}

# Проверка что установлен dialog
if ! command -v dialog &> /dev/null; then
    echo "Ошибка: Необходимо установить dialog"
    echo "Выполните: sudo apt-get install dialog"
    exit 1
fi

# Запуск меню
clear
show_menu "$START_DIR"
clear
