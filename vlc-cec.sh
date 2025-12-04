#!/bin/bash

# Парсинг параметров: [секунды] файл
if [ $# -eq 2 ]; then
    START_TIME="$1"
    VIDEO_FILE="$2"
elif [ $# -eq 1 ]; then
    START_TIME=""
    VIDEO_FILE="$1"
else
    echo "Использование: $0 [секунды] <видеофайл>"
    exit 1
fi

if [ ! -f "$VIDEO_FILE" ]; then
    echo "❌ Файл не найден: $VIDEO_FILE"
    exit 1
fi

# Подключаем библиотеку отслеживания прогресса
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/playback-tracker.sh"

# Проверяем совместимость версии библиотеки
REQUIRED_TRACKER_VERSION="0.2.0"
if ! check_version_compatibility "$REQUIRED_TRACKER_VERSION"; then
    exit 1
fi

# Подключаем библиотеку работы с БД для skip markers
source "$SCRIPT_DIR/db-manager.sh"

# Skip Intro/Outro - переменные состояния
SKIP_SETUP_MODE=0  # 0=выключен, 1=intro_start, 2=intro_end, 3=outro_start
INTRO_START_TIME=0
INTRO_END_TIME=0
OUTRO_START_TIME=0

# Загруженные skip markers из БД
LOADED_INTRO_START=""
LOADED_INTRO_END=""
LOADED_OUTRO_START=""

# ВАЖНО: Укажите ваше CEC устройство
CEC_DEVICE="/dev/cec1"

if [ ! -e "$CEC_DEVICE" ]; then
    echo "❌ CEC устройство не найдено: $CEC_DEVICE"
    echo "Доступные устройства:"
    ls -la /dev/cec* 2>/dev/null || echo "  Нет CEC устройств"
    exit 1
fi

# ============================================================================
# ФУНКЦИИ SKIP INTRO/OUTRO
# ============================================================================

# Загрузка skip markers из БД
load_skip_markers() {
    local video_file="$1"
    local basename=$(basename "$video_file")
    
    # Извлекаем series_prefix и series_suffix
    local series_prefix=$(extract_series_prefix "$basename")
    local series_suffix=$(extract_series_suffix "$basename")
    
    if [ -n "$series_prefix" ]; then
        # Получаем skip markers из БД (JSON)
        local skip_data=$(db_get_skip_markers "$series_prefix" "$series_suffix" 2>/dev/null)
        
        if [ -n "$skip_data" ]; then
            # Парсим JSON с помощью grep (простой вариант без jq)
            LOADED_INTRO_START=$(echo "$skip_data" | grep -oP '"intro_start":\s*\K[0-9]+' || echo "")
            LOADED_INTRO_END=$(echo "$skip_data" | grep -oP '"intro_end":\s*\K[0-9]+' || echo "")
            LOADED_OUTRO_START=$(echo "$skip_data" | grep -oP '"outro_start":\s*\K[0-9]+' || echo "")
            
            if [ -n "$LOADED_INTRO_START" ] && [ -n "$LOADED_INTRO_END" ]; then
                echo "✓ Загружены intro markers: ${LOADED_INTRO_START}s - ${LOADED_INTRO_END}s"
            fi
            if [ -n "$LOADED_OUTRO_START" ]; then
                echo "✓ Загружен outro marker: ${LOADED_OUTRO_START}s"
            fi
        fi
    fi
}

# Обработка RED кнопки для установки skip markers
handle_red_button() {
    local video_file="$1"
    local basename=$(basename "$video_file")
    
    # Извлекаем series info
    local series_prefix=$(extract_series_prefix "$basename")
    local series_suffix=$(extract_series_suffix "$basename")
    
    if [ -z "$series_prefix" ]; then
        echo "⚠️  Не сериал - skip markers недоступны"
        return
    fi
    
    # Получаем текущую позицию и длительность
    local current_time=$(echo "get_time" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
    local total_length=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
    
    if [ -z "$current_time" ] || [ -z "$total_length" ]; then
        echo "⚠️  Ошибка получения времени"
        return
    fi
    
    # Определяем фазу видео (в процентах)
    local position_percent=$((current_time * 100 / total_length))
    
    case $SKIP_SETUP_MODE in
        0)  # Установка Intro Start (только в начале, <20%)
            if [ $position_percent -lt 20 ]; then
                INTRO_START_TIME=$current_time
                SKIP_SETUP_MODE=1
                echo "📍 Intro Start: ${current_time}s"
            else
                echo "⚠️  Intro Start можно установить только в начале видео (<20%)"
            fi
            ;;
        1)  # Установка Intro End
            INTRO_END_TIME=$current_time
            SKIP_SETUP_MODE=2
            
            # Сохраняем в БД
            if db_set_intro_markers "$series_prefix" "$series_suffix" "$INTRO_START_TIME" "$INTRO_END_TIME"; then
                echo "✓ Intro saved: ${INTRO_START_TIME}s - ${INTRO_END_TIME}s"
                # Обновляем загруженные значения
                LOADED_INTRO_START=$INTRO_START_TIME
                LOADED_INTRO_END=$INTRO_END_TIME
            else
                echo "✗ Ошибка сохранения intro"
                SKIP_SETUP_MODE=0
            fi
            ;;
        2)  # Установка Outro Start (только в конце, >80%)
            if [ $position_percent -gt 80 ]; then
                OUTRO_START_TIME=$current_time
                
                # Сохраняем в БД
                if db_set_outro_marker "$series_prefix" "$series_suffix" "$current_time"; then
                    echo "✓ Outro Start: ${current_time}s"
                    LOADED_OUTRO_START=$current_time
                    SKIP_SETUP_MODE=0  # Сброс
                else
                    echo "✗ Ошибка сохранения outro"
                fi
            else
                echo "⚠️  Outro Start можно установить только в конце видео (>80%)"
            fi
            ;;
        *)
            SKIP_SETUP_MODE=0  # Сброс при некорректном состоянии
            ;;
    esac
}

# Мониторинг для автопропуска intro/outro
monitor_skip_markers() {
    local vlc_pid="$1"
    
    while true; do
        sleep 2  # Проверяем каждые 2 секунды
        
        # Проверяем что VLC ещё работает
        if ! kill -0 "$vlc_pid" 2>/dev/null; then
            break
        fi
        
        # Получаем текущую позицию
        local current=$(echo "get_time" | nc -w 1 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        
        if [ -z "$current" ]; then
            continue
        fi
        
        # Проверяем intro (если оба маркера установлены)
        if [ -n "$LOADED_INTRO_START" ] && [ -n "$LOADED_INTRO_END" ]; then
            if [ "$current" -ge "$LOADED_INTRO_START" ] && [ "$current" -lt "$LOADED_INTRO_END" ]; then
                echo "⏩ Пропуск заставки: ${LOADED_INTRO_START}s → ${LOADED_INTRO_END}s"
                echo "seek $LOADED_INTRO_END" | nc -w 1 localhost:4212 > /dev/null 2>&1
                sleep 1  # Даём времени на перемотку
            fi
        fi
        
        # Проверяем outro
        if [ -n "$LOADED_OUTRO_START" ]; then
            if [ "$current" -ge "$LOADED_OUTRO_START" ]; then
                echo "⏹️  Конец серии (outro: ${LOADED_OUTRO_START}s)"
                echo "stop" | nc -w 1 localhost:4212 > /dev/null 2>&1
                break
            fi
        fi
    done
}

echo "Запуск VLC с RC интерфейсом..."
echo "Для ручного управления: nc localhost 4212"
echo ""

# Загружаем skip markers для текущего файла
load_skip_markers "$VIDEO_FILE"

# Запускаем VLC с RC интерфейсом
if [ -n "$START_TIME" ]; then
    cvlc --intf rc \
         --rc-host localhost:4212 \
         --fullscreen \
         --no-osd \
         --subsdec-encoding=Windows-1251 \
         "$VIDEO_FILE" :start-time=$START_TIME 2>&1 | grep -v "^\[" | grep -v "^VLC" | grep -v "^Command" &
else
    cvlc --intf rc \
         --rc-host localhost:4212 \
         --fullscreen \
         --no-osd \
         --subsdec-encoding=Windows-1251 \
         "$VIDEO_FILE" 2>&1 | grep -v "^\[" | grep -v "^VLC" | grep -v "^Command" &
fi

VLC_PID=$!
echo "VLC PID: $VLC_PID"

# Ждём пока VLC запустится
sleep 3

# Проверяем что VLC запущен
if ! kill -0 $VLC_PID 2>/dev/null; then
    echo "❌ Ошибка: VLC не запустился!"
    exit 1
fi

echo "✓ VLC запущен"
echo "✓ RC интерфейс: localhost:4212"
echo "✓ CEC мониторинг: $CEC_DEVICE"
echo ""
echo "🎮 Мониторинг пульта (нажмите любую кнопку для проверки)..."
echo ""

# Мониторим CEC с максимальной детализацией
cec-client -d 8 -t r "$CEC_DEVICE" 2>&1 | while IFS= read -r line; do
    
    # Показываем все входящие команды для отладки (кроме polling и статус-запросов)
    if [[ "$line" == *"TRAFFIC"* ]] && [[ "$line" == *">>"* ]]; then
        # Пропускаем:
        # - f0, 10, 11 = polling messages
        # - 8f = Give Device Power Status
        # - 8c = Give Device Vendor ID
        # - 83 = Give Physical Address
        # - 46 = Give OSD Name
        # - 87 = Give Device Power Status response
        if [[ "$line" != *"f0"* ]] && \
           [[ "$line" != *"<< 10"* ]] && [[ "$line" != *"<< 11"* ]] && \
           [[ "$line" != *"01:8f"* ]] && [[ "$line" != *"01:8c"* ]] && \
           [[ "$line" != *"01:83"* ]] && [[ "$line" != *"01:46"* ]] && \
           [[ "$line" != *"01:87"* ]]; then
            echo "[CEC RAW] $line"
        fi
    fi

    # === ОБРАБОТКА КНОПОК ПУЛЬТА ===
    
    # OK → Play/Pause
    if [[ "$line" == *"44:00"* ]]; then
        echo "▶️  Play/Pause"
        echo "pause" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # UP → +30 sec
    if [[ "$line" == *"44:01"* ]]; then
        echo "⏩⏩ +30 sec"
        echo "seek +30" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # DOWN → -30 sec
    if [[ "$line" == *"44:02"* ]]; then
        echo "⏪⏪ -30 sec"
        echo "seek -30" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # LEFT → -10 sec
    if [[ "$line" == *"44:03"* ]]; then
        echo "⏪ -10 sec"
        echo "seek -10" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # RIGHT → +10 sec
    if [[ "$line" == *"44:04"* ]]; then
        echo "⏩ +10 sec"
        echo "seek +10" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # BACK → Exit
    if [[ "$line" == *"44:0d"* ]] || [[ "$line" == *"44:0D"* ]]; then
        echo "⏹️  Exit"
        echo "quit" | nc -w 1 localhost 4212 >/dev/null 2>&1
        kill $VLC_PID 2>/dev/null
        kill $CEC_PID 2>/dev/null
        pkill -P $$ 2>/dev/null
        clear
        exit 0
    fi

# INFO → Show time
    if [[ "$line" == *"44:35"* ]]; then
        echo "⏱️  Запрос времени..."
        
        time_output=$(echo "get_time" | nc -w 2 localhost 4212 2>&1)
        length_output=$(echo "get_length" | nc -w 2 localhost 4212 2>&1)
        
        current=$(echo "$time_output" | grep -oE '[0-9]+' | tail -1)
        total=$(echo "$length_output" | grep -oE '[0-9]+' | tail -1)
        
        if [ -n "$current" ] && [ -n "$total" ]; then
            remaining=$((total - current))
            current_fmt=$(printf "%02d:%02d:%02d" $((current/3600)) $((current%3600/60)) $((current%60)))
            total_fmt=$(printf "%02d:%02d:%02d" $((total/3600)) $((total%3600/60)) $((total%60)))
            remaining_fmt=$(printf "%02d:%02d:%02d" $((remaining/3600)) $((remaining%3600/60)) $((remaining%60)))
            echo "⏱️  $current_fmt / $total_fmt (осталось: $remaining_fmt)"
        else
            echo "⏱️  Ошибка получения времени"
        fi
        continue
    fi

# RED → Skip Intro/Outro setup
    if [[ "$line" == *"44:72"* ]]; then
        handle_red_button "$VIDEO_FILE"
        continue
    fi
    
    # GREEN → Subtitles (циклическое переключение, включая выкл)
    if [[ "$line" == *"44:73"* ]]; then
        echo "📝 Subtitles switch"
        # Получаем текущие субтитры и переключаем (включая -1 = выкл)
        current_strack=$(echo "strack" | nc -w 1 localhost 4212 2>&1 | grep -oE 'track [0-9-]+' | grep -oE '[0-9-]+' | head -1)
        if [ -n "$current_strack" ]; then
            if [ "$current_strack" -eq "-1" ]; then
                next_strack=0
            else
                next_strack=$((current_strack + 1))
            fi
            echo "strack $next_strack" | nc -w 1 localhost 4212 >/dev/null 2>&1
            if [ "$next_strack" -eq "0" ]; then
                echo "   → Subtitles: ON (track $next_strack)"
            else
                echo "   → Subtitles: track $next_strack"
            fi
        fi
        continue
    fi
    
    # YELLOW → Volume +
    if [[ "$line" == *"44:74"* ]]; then
        echo "🔊 Volume +"
        echo "volup 1" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # BLUE → Volume -
    if [[ "$line" == *"44:71"* ]]; then
        echo "🔉 Volume -"
        echo "voldown 1" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # CHANNEL UP → +60 sec
    if [[ "$line" == *"44:30"* ]]; then
        echo "⏩⏩⏩ +60 sec"
        echo "seek +60" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # CHANNEL DOWN → -60 sec
    if [[ "$line" == *"44:31"* ]]; then
        echo "⏪⏪⏪ -60 sec"
        echo "seek -60" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
    # 0 → Start
    if [[ "$line" == *"44:20"* ]]; then
        echo "⏮️  To start"
        echo "seek 0" | nc -w 1 localhost 4212 >/dev/null 2>&1
        continue
    fi
    
# 1 → 10%
    if [[ "$line" == *"44:21"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 10%"
            echo "seek $((total * 10 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 2 → 20%
    if [[ "$line" == *"44:22"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 20%"
            echo "seek $((total * 20 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 3 → 30%
    if [[ "$line" == *"44:23"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 30%"
            echo "seek $((total * 30 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 4 → 40%
    if [[ "$line" == *"44:24"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 40%"
            echo "seek $((total * 40 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 5 → 50%
    if [[ "$line" == *"44:25"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 50%"
            echo "seek $((total * 50 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 6 → 60%
    if [[ "$line" == *"44:26"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 60%"
            echo "seek $((total * 60 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 7 → 70%
    if [[ "$line" == *"44:27"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 70%"
            echo "seek $((total * 70 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 8 → 80%
    if [[ "$line" == *"44:28"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 80%"
            echo "seek $((total * 80 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # 9 → 90%
    if [[ "$line" == *"44:29"* ]]; then
        total=$(echo "get_length" | nc -w 2 localhost 4212 2>&1 | grep -oE '[0-9]+' | tail -1)
        if [ -n "$total" ]; then
            echo "🎯 Jump to 90%"
            echo "seek $((total * 90 / 100))" | nc -w 1 localhost 4212 >/dev/null 2>&1
        fi
        continue
    fi
    
    # Проверяем что VLC ещё работает
    if ! kill -0 $VLC_PID 2>/dev/null; then
        echo "VLC завершён"
        exit 0
    fi
done &

CEC_PID=$!

# Запускаем мониторинг прогресса в фоне (ПОСЛЕ CEC)
monitor_vlc_playback "$VIDEO_FILE" $VLC_PID &
MONITOR_PID=$!

# Запускаем мониторинг skip markers в фоне
monitor_skip_markers $VLC_PID &
SKIP_MONITOR_PID=$!

# Функция для корректного завершения
cleanup() {
    echo ""
    echo "Завершение работы..."
    
    # Финальное сохранение позиции
    finalize_playback "$VIDEO_FILE"
    
    # Завершаем процессы
    kill $SKIP_MONITOR_PID 2>/dev/null
    kill $MONITOR_PID 2>/dev/null
    kill $CEC_PID 2>/dev/null
    kill $VLC_PID 2>/dev/null
    pkill -P $$ 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Ждём завершения VLC
wait $VLC_PID
