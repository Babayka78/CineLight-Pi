#!/bin/bash
# test_tput_simple.sh - Простой тест tput виджета редактирования времени

# Простейшая версия tput редактора (только для одного поля)
simple_time_input() {
    local initial_value="$1"
    
    # Значение по умолчанию
    [ -z "$initial_value" ] && initial_value="00:00"
    
    # Массив символов
    local chars=( ${initial_value:0:1} ${initial_value:1:1} : ${initial_value:3:1} ${initial_value:4:1} )
    
    local cursor_pos=0
    
    # Скрыть системный курсор
    tput civis
    
    # Сохранить состояние терминала
    local old_tty=$(stty -g)
    stty -echo -icanon time 0 min 1
    
    echo "=== DEBUG: Запуск редактора ===" >> /tmp/tput_debug.log
    
    while true; do
        # Очистить экран
        clear
        
        echo "=== DEBUG: Новая итерация ===" >> /tmp/tput_debug.log
        
        # Нарисовать заголовок
        echo ""
        echo "  ╔════════════════════════════╗"
        echo "  ║  Редактор времени (MM:SS)  ║"
        echo "  ╚════════════════════════════╝"
        echo ""
        
        # Показать текущее значение
        echo -n "  Время: "
        
        # Отрисовать каждый символ
        for i in 0 1 2 3 4; do
            if [ $i -eq 2 ]; then
                # Двоеточие
                echo -n "${chars[$i]}"
            elif [ $cursor_pos -eq $i ]; then
                # Курсор - желтый фон
                tput setab 3
                tput setaf 0
                echo -n "${chars[$i]}"
                tput sgr0
            else
                # Обычный символ
                echo -n "${chars[$i]}"
            fi
        done
        
        echo ""
        echo ""
        echo "  ←/→: передвижение    0-9: ввод"
        echo "  Enter: сохранить     Esc: отмена"
        
        # Читать клавишу
        local key
        IFS= read -rsn1 key
        
        echo "=== DEBUG: Клавиша: '$key'" >> /tmp/tput_debug.log
        
        # ESC
        if [[ $key == $'\x1b' ]]; then
            read -rsn2 -t 0.1 rest
            echo "=== DEBUG: ESC + '$rest'" >> /tmp/tput_debug.log
            
            if [ "$rest" = "[C" ]; then
                # Стрелка вправо
                if [ $cursor_pos -eq 1 ]; then
                    cursor_pos=3
                elif [ $cursor_pos -lt 4 ]; then
                    cursor_pos=$((cursor_pos + 1))
                fi
            elif [ "$rest" = "[D" ]; then
                # Стрелка влево
                if [ $cursor_pos -eq 3 ]; then
                    cursor_pos=1
                elif [ $cursor_pos -gt 0 ]; then
                    cursor_pos=$((cursor_pos - 1))
                fi
            elif [ -z "$rest" ]; then
                # Чистый ESC без последовательности - выход
                tput cnorm
                stty $old_tty
                clear
                return 1
            fi
        # Цифра
        elif [[ $key =~ ^[0-9]$ ]]; then
            # Валидация секунд
            if [ $cursor_pos -eq 3 ] && [ $key -gt 5 ]; then
                continue
            fi
            
            chars[$cursor_pos]=$key
            
            # Переместить курсор
            if [ $cursor_pos -eq 1 ]; then
                cursor_pos=3
            elif [ $cursor_pos -lt 4 ]; then
                cursor_pos=$((cursor_pos + 1))
            fi
        # Enter
        elif [ "$key" = "" ]; then
            local result="${chars[0]}${chars[1]}:${chars[3]}${chars[4]}"
            tput cnorm
            stty $old_tty
            clear
            echo "Результат: $result"
            return 0
        fi
    done
}

# Главная функция
main() {
    echo "Тест tput редактора времени"
    echo ""
    
    rm -f /tmp/tput_debug.log
    
    if simple_time_input "01:23"; then
        echo "✓ Успешно"
    else
        echo "✗ Отменено"
    fi
    
    echo ""
    echo "Лог:"
    cat /tmp/tput_debug.log 2>/dev/null
}

main
