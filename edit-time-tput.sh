#!/bin/bash
# edit-time-tput.sh - Отдельный скрипт для редактирования времени через tput
# Вызывается из serials.sh как внешняя программа
# Аргументы: $1=intro_start (MM:SS), $2=intro_end (MM:SS), $3=outro_duration (MM:SS)
# Возвращает: "intro_start|intro_end|outro" в секундах через stdout

# Функция конвертации MM:SS в секунды
mmss_to_seconds() {
    local mmss="$1"
    if [ -z "$mmss" ] || [ "$mmss" = "00:00" ]; then
        echo ""
        return
    fi
    local minutes="${mmss%:*}"
    local seconds="${mmss#*:}"
    echo $((minutes * 60 + seconds))
}

# Редактор времени с tput
edit_all_times() {
    local intro_start="$1"
    local intro_end="$2"
    local outro="$3"
    
    # Значения по умолчанию
    [ -z "$intro_start" ] && intro_start="00:00"
    [ -z "$intro_end" ] && intro_end="00:00"
    [ -z "$outro" ] && outro="00:00"
    
    # Массивы символов
    local intro_start_chars=( ${intro_start:0:1} ${intro_start:1:1} : ${intro_start:3:1} ${intro_start:4:1} )
    local intro_end_chars=( ${intro_end:0:1} ${intro_end:1:1} : ${intro_end:3:1} ${intro_end:4:1} )
    local outro_chars=( ${outro:0:1} ${outro:1:1} : ${outro:3:1} ${outro:4:1} )
    
    # Текущее поле (0=intro_start, 1=intro_end, 2=outro)
    local current_field=0
    local cursor_pos=0
    
    # Принудительно восстановить TTY (важно после dialog)
    exec < /dev/tty
    exec > /dev/tty
    stty sane
    # Скрыть системный курсор
    tput civis
    
    # Сохранить состояние терминала
    local old_tty=$(stty -g)
    stty -echo -icanon time 0 min 1
    
    while true; do
        clear
        
        # Заголовок
        echo ""
        echo "  ╔═══════════════════════════════════╗"
        echo "  ║  Настройка времени (MM:SS)        ║"
        echo "  ╚═══════════════════════════════════╝"
        echo ""
        
        # Intro Start
        echo -n "  Intro Start:     "
        for i in 0 1 2 3 4; do
            if [ $i -eq 2 ]; then
                echo -n "${intro_start_chars[$i]}"
            elif [ $current_field -eq 0 ] && [ $cursor_pos -eq $i ]; then
                tput setab 3; tput setaf 0
                echo -n "${intro_start_chars[$i]}"
                tput sgr0
            elif [ $current_field -eq 0 ]; then
                tput setaf 2
                echo -n "${intro_start_chars[$i]}"
                tput sgr0
            else
                echo -n "${intro_start_chars[$i]}"
            fi
        done
        echo ""
        
        # Intro End
        echo -n "  Intro End:       "
        for i in 0 1 2 3 4; do
            if [ $i -eq 2 ]; then
                echo -n "${intro_end_chars[$i]}"
            elif [ $current_field -eq 1 ] && [ $cursor_pos -eq $i ]; then
                tput setab 3; tput setaf 0
                echo -n "${intro_end_chars[$i]}"
                tput sgr0
            elif [ $current_field -eq 1 ]; then
                tput setaf 2
                echo -n "${intro_end_chars[$i]}"
                tput sgr0
            else
                echo -n "${intro_end_chars[$i]}"
            fi
        done
        echo ""
        
        # Outro Duration
        echo -n "  Outro Duration:  "
        for i in 0 1 2 3 4; do
            if [ $i -eq 2 ]; then
                echo -n "${outro_chars[$i]}"
            elif [ $current_field -eq 2 ] && [ $cursor_pos -eq $i ]; then
                tput setab 3; tput setaf 0
                echo -n "${outro_chars[$i]}"
                tput sgr0
            elif [ $current_field -eq 2 ]; then
                tput setaf 2
                echo -n "${outro_chars[$i]}"
                tput sgr0
            else
                echo -n "${outro_chars[$i]}"
            fi
        done
        echo ""
        
        echo ""
        echo "  ↑/↓: switch field   ←/→: move cursor"
        echo "  0-9: input digit    Enter: save    Esc: cancel"
        
        # Читать клавишу
        local key
        IFS= read -rsn1 key
        
        # ESC sequences
        if [[ $key == $'\x1b' ]]; then
            # Читаем следующий символ
            IFS= read -rsn1 -t 1 next
            echo "DEBUG: ESC + next='$next'" >> /tmp/edit_time_debug.log
            
            if [ "$next" = "[" ]; then
                # Это arrow key - читаем третий символ
                IFS= read -rsn1 -t 1 arrow
                echo "DEBUG: Arrow code='$arrow'" >> /tmp/edit_time_debug.log
                
                case "$arrow" in
                    'A') # Up
                        [ $current_field -gt 0 ] && current_field=$((current_field - 1)) && cursor_pos=0
                        ;;
                    'B') # Down
                        [ $current_field -lt 2 ] && current_field=$((current_field + 1)) && cursor_pos=0
                        ;;
                    'D') # Left
                        if [ $cursor_pos -eq 3 ]; then
                            cursor_pos=1
                        elif [ $cursor_pos -gt 0 ]; then
                            cursor_pos=$((cursor_pos - 1))
                        fi
                        ;;
                    'C') # Right
                        if [ $cursor_pos -eq 1 ]; then
                            cursor_pos=3
                        elif [ $cursor_pos -lt 4 ]; then
                            cursor_pos=$((cursor_pos + 1))
                        fi
                        ;;
                esac
            else
                # Чистый ESC без последовательности - выход
                echo "DEBUG: Pure ESC, exiting" >> /tmp/edit_time_debug.log
                tput cnorm
                stty $old_tty
                clear
                echo ""
                exit 1
            fi
        # Цифра
        elif [[ $key =~ ^[0-9]$ ]]; then
            # Пропускаем двоеточие
            if [ $cursor_pos -eq 2 ]; then
                continue
            fi
            
            # Валидация секунд
            if [ $cursor_pos -eq 3 ] && [ $key -gt 5 ]; then
                continue
            fi
            
            # Обновить значение
            case $current_field in
                0) intro_start_chars[$cursor_pos]=$key ;;
                1) intro_end_chars[$cursor_pos]=$key ;;
                2) outro_chars[$cursor_pos]=$key ;;
            esac
            
            # Переместить курсор
            if [ $cursor_pos -eq 1 ]; then
                cursor_pos=3
            elif [ $cursor_pos -lt 4 ]; then
                cursor_pos=$((cursor_pos + 1))
            fi
        # Enter
        elif [ "$key" = "" ]; then
            # Собрать значения
            local final_intro_start="${intro_start_chars[0]}${intro_start_chars[1]}:${intro_start_chars[3]}${intro_start_chars[4]}"
            local final_intro_end="${intro_end_chars[0]}${intro_end_chars[1]}:${intro_end_chars[3]}${intro_end_chars[4]}"
            local final_outro="${outro_chars[0]}${outro_chars[1]}:${outro_chars[3]}${outro_chars[4]}"
            
            # Валидация: Intro End > Intro Start
            local intro_start_sec=$(mmss_to_seconds "$final_intro_start")
            local intro_end_sec=$(mmss_to_seconds "$final_intro_end")
            
            if [ -n "$intro_start_sec" ] && [ -n "$intro_end_sec" ]; then
                if [ $intro_end_sec -le $intro_start_sec ]; then
                    tput cup $((LINES - 2)) 5
                    tput setaf 1
                    echo "Error: Intro End must be > Intro Start"
                    tput sgr0
                    sleep 1.5
                    continue
                fi
            fi
            
            # Конвертировать в секунды
            local outro_sec=$(mmss_to_seconds "$final_outro")
            
            # Вернуть результат
            tput cnorm
            stty $old_tty
            clear
            echo "${intro_start_sec}|${intro_end_sec}|${outro_sec}"
            exit 0
        fi
    done
}

# Запуск
edit_all_times "$1" "$2" "$3"
