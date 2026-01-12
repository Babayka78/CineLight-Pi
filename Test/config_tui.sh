#!/bin/bash
# config_tui.sh - TUI редактор конфигурации на базе edit-time-tput.sh
# Использует Py/config/config_cli.py для работы с БД

CONFIG_DB="Py/config/vlc_media.db"

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

# Получить список настроек
get_configs() {
    python3 Py/config/config_cli.py list "$1" 2>/dev/null | grep -v "^$" | grep -v "===" | tail -n +3
}

# Редактор значения
edit_value() {
    local key="$1"
    local current_value="$2"
    local type="$3"
    local category="$4"
    
    # Если это путь к директории - используем диалог выбора
    if [[ "$key" == *"dir"* ]] || [[ "$key" == *"path"* ]]; then
        # Используем dialog для выбора директории
        local new_path=$(dialog --title "Выбрать директорию" --dselect "$current_value" 10 60 3>&1 1>&2 2>&3 3>&-)
        local exit_code=$?
        clear
        
        if [ $exit_code -eq 0 ] && [ -n "$new_path" ]; then
            python3 Py/config/config_cli.py set "$key" "$new_path" "$type" "$category"
        fi
        return
    fi
    
    # Для остальных значений - простой редактор
    local cursor_pos=0
    local chars=()
    local len=${#current_value}
    
    # Разбиваем значение на символы
    for ((i=0; i<len; i++)); do
        chars+=("${current_value:$i:1}")
    done
    
    # Принудительно восстановить TTY
    exec < /dev/tty
    exec > /dev/tty
    stty sane
    tput civis
    
    local old_tty=$(stty -g)
    stty -echo -icanon time 0 min 1
    
    while true; do
        clear
        
        # Заголовок
        echo ""
        echo "  ╔═══════════════════════════════════╗"
        echo "  ║  Редактирование: $key        ║"
        echo "  ╚═══════════════════════════════════╝"
        echo ""
        echo -n "  Текущее: "
        for ((i=0; i<${#chars[@]}; i++)); do
            if [ $i -eq $cursor_pos ]; then
                tput setab 3; tput setaf 0
                echo -n "${chars[$i]}"
                tput sgr0
            else
                echo -n "${chars[$i]}"
            fi
        done
        echo ""
        echo ""
        echo "  ←/→: move cursor   Backspace: delete"
        echo "  Любая клавиша: insert   Enter: save   Esc: cancel"
        
        # Читать клавишу
        local key
        IFS= read -rsn1 key
        
        # ESC sequences
        if [[ $key == $'\x1b' ]]; then
            IFS= read -rsn1 -t 1 next
            if [ "$next" = "[" ]; then
                IFS= read -rsn1 -t 1 arrow
                case "$arrow" in
                    'D') # Left
                        [ $cursor_pos -gt 0 ] && cursor_pos=$((cursor_pos - 1))
                        ;;
                    'C') # Right
                        [ $cursor_pos -lt $((${#chars[@]})) ] && cursor_pos=$((cursor_pos + 1))
                        ;;
                esac
            else
                # ESC - выход
                tput cnorm
                stty $old_tty
                clear
                return
            fi
        # Backspace
        elif [ "$key" = $'\x7f' ] || [ "$key" = $'\x08' ]; then
            if [ $cursor_pos -gt 0 ]; then
                chars=("${chars[@]:0:$((cursor_pos-1))}" "${chars[@]:$cursor_pos}")
                cursor_pos=$((cursor_pos - 1))
            fi
        # Enter
        elif [ "$key" = "" ]; then
            local new_value=""
            for char in "${chars[@]}"; do
                new_value+="$char"
            done
            python3 Py/config/config_cli.py set "$key" "$new_value" "$type" "$category"
            tput cnorm
            stty $old_tty
            clear
            return
        # Любой другой символ
        else
            chars=("${chars[@]:0:$cursor_pos}" "$key" "${chars[@]:$cursor_pos}")
            cursor_pos=$((cursor_pos + 1))
        fi
    done
}

# Главное меню
main_menu() {
    local categories=("general" "cec" "media" "ui" "exit")
    local selected=0
    
    while true; do
        clear
        
        # Заголовок
        echo ""
        echo "  ╔═══════════════════════════════════╗"
        echo "  ║  Конфигурация CineLight-Pi       ║"
        echo "  ╚═══════════════════════════════════╝"
        echo ""
        
        # Меню категорий
        for i in "${!categories[@]}"; do
            if [ $i -eq $selected ]; then
                echo -ne "  > ${CYAN}"
            else
                echo -ne "    "
            fi
            case "${categories[$i]}" in
                general) echo "Общие настройки" ;;
                cec) echo "CEC управление" ;;
                media) echo "Медиа настройки" ;;
                ui) echo "Интерфейс" ;;
                exit) echo "Выход" ;;
            esac
            echo -ne "${RESET}"
            echo ""
        done
        
        echo ""
        echo "  ↑/↓: select   Enter: choose"
        
        # Читать клавишу
        local key
        IFS= read -rsn1 key
        
        if [[ $key == $'\x1b' ]]; then
            IFS= read -rsn1 -t 1 next
            if [ "$next" = "[" ]; then
                IFS= read -rsn1 -t 1 arrow
                case "$arrow" in
                    'A') # Up
                        [ $selected -gt 0 ] && selected=$((selected - 1))
                        ;;
                    'B') # Down
                        [ $selected -lt $((${#categories[@]} - 1)) ] && selected=$((selected + 1))
                        ;;
                esac
            fi
        elif [ "$key" = "" ]; then
            local choice="${categories[$selected]}"
            if [ "$choice" = "exit" ]; then
                clear
                echo ""
                exit 0
            fi
            edit_category "$choice"
        fi
    done
}

# Редактирование категории
edit_category() {
    local category="$1"
    local configs=()
    local selected=0
    
    # Получить настройки категории
    while IFS=': ' read -r key value; do
        configs+=("$key:$value")
    done < <(get_configs "$category")
    
    while true; do
        clear
        
        # Заголовок
        echo ""
        echo "  ╔═══════════════════════════════════╗"
        echo "  ║  $category              ║"
        echo "  ╚═══════════════════════════════════╝"
        echo ""
        
        # Список настроек
        for i in "${!configs[@]}"; do
            local key="${configs[$i]%%:*}"
            local value="${configs[$i]#*:}"
            
            if [ $i -eq $selected ]; then
                echo -ne "  > ${YELLOW}"
            else
                echo -ne "    "
            fi
            printf "%-20s: %s\n" "$key" "$value"
            echo -ne "${RESET}"
        done
        
        echo ""
        echo "  ↑/↓: select   Enter: edit   Esc: back"
        
        # Читать клавишу
        local key
        IFS= read -rsn1 key
        
        if [[ $key == $'\x1b' ]]; then
            IFS= read -rsn1 -t 1 next
            if [ "$next" = "[" ]; then
                IFS= read -rsn1 -t 1 arrow
                case "$arrow" in
                    'A') # Up
                        [ $selected -gt 0 ] && selected=$((selected - 1))
                        ;;
                    'B') # Down
                        [ $selected -lt $((${#configs[@]} - 1)) ] && selected=$((selected + 1))
                        ;;
                esac
            else
                # ESC - назад
                return
            fi
        elif [ "$key" = "" ]; then
            local config="${configs[$selected]}"
            local key="${config%%:*}"
            local value="${config#*:}"
            local type=$(python3 Py/config/config_cli.py get "$key" 2>/dev/null | cut -d' ' -f2)
            edit_value "$key" "$value" "$type" "$category"
            # Обновить список
            configs=()
            while IFS=': ' read -r k v; do
                configs+=("$k:$v")
            done < <(get_configs "$category")
        fi
    done
}

# Запуск
main_menu
