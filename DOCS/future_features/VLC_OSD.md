# VLC OSD (On-Screen Display) Возможности

**Дата:** 01.12.2025  
**Статус:** Исследование

---

## Основной способ: Marquee Filter

VLC поддерживает отображение текста поверх видео через **marquee video filter**.

### Запуск с параметрами командной строки

```bash
cvlc video.mkv \
  --sub-filter marq \
  --marq-marquee "Добро пожаловать!" \
  --marq-position 8 \
  --marq-color 16777215 \
  --marq-size 24
```

### Параметры marquee:

| Параметр | Описание | Значения |
|----------|----------|----------|
| `--sub-filter marq` | Включить marquee фильтр | - |
| `--marq-marquee "text"` | Текст для отображения | Любой текст |
| `--marq-position N` | Позиция на экране | 0=center, 1=left, 2=right, 4=top, 8=bottom, 5=top-left, 6=top-right, 9=bottom-left, 10=bottom-right |
| `--marq-color N` | Цвет текста (RGB) | 16777215=белый, 16711680=красный, 65280=зелёный, 255=синий |
| `--marq-size N` | Размер шрифта | В пикселях (например, 24, 32) |
| `--marq-opacity N` | Прозрачность | 0-255 (255=непрозрачный) |
| `--marq-timeout N` | Автоскрытие | В миллисекундах (0=не скрывать) |

---

## Управление через RC Interface

**ВАЖНО:** Можно динамически менять текст во время воспроизведения!

### Включение RC + Marquee:

```bash
cvlc video.mkv \
  --extraintf rc \
  --rc-host localhost:4212 \
  --sub-filter marq \
  --marq-marquee "" \
  --marq-position 8
```

### Команды через netcat:

```bash
# Показать текст
echo "marq-marquee: Эпизод 1" | nc localhost 4212

# Изменить позицию
echo "marq-position: 5" | nc localhost 4212

# Изменить цвет (красный)
echo "marq-color: 16711680" | nc localhost 4212

# Изменить размер
echo "marq-size: 32" | nc localhost 4212

# Скрыть текст
echo "marq-marquee: " | nc localhost 4212
```

---

## Практические примеры

### 1. Показать название эпизода при запуске

```bash
vlc "Show.S01E01.mkv" \
  --sub-filter marq \
  --marq-marquee "S01E01 - Episode Title" \
  --marq-position 10 \
  --marq-size 28 \
  --marq-timeout 5000 \
  --fullscreen
```
*Текст исчезнет через 5 секунд*

### 2. Постоянная информация о прогрессе

```bash
# Запуск с пустым marquee
vlc video.mkv --sub-filter marq --extraintf rc --rc-host localhost:4212

# В другом окне - обновление каждые 10 секунд
while true; do
    current=$(echo "get_time" | nc -w 1 localhost 4212 | grep -oE '[0-9]+')
    total=$(echo "get_length" | nc -w 1 localhost 4212 | grep -oE '[0-9]+')
    percent=$((current * 100 / total))
    
    echo "marq-marquee: Прогресс: ${percent}%" | nc localhost 4212
    sleep 10
done
```

### 3. Уведомление об автопродолжении

```bash
# Перед запуском следующего эпизода
echo "marq-marquee: Следующий эпизод: S01E02" | nc localhost 4212
echo "marq-timeout: 3000" | nc localhost 4212
sleep 3
```

---

## Альтернативные способы

### 1. OSD через команды VLC

VLC имеет встроенные OSD сообщения, но они менее гибкие:

```bash
# Показать время (только через GUI)
echo "osd" | nc localhost 4212
```

### 2. Субтитры как OSD

Можно создать динамический .srt файл:

```srt
1
00:00:00,000 --> 00:00:05,000
Добро пожаловать!

2
00:00:05,000 --> 00:00:10,000
Эпизод 1
```

```bash
vlc video.mkv --sub-file message.srt
```

---

## Интеграция в VLC проект

### Предлагаемое использование:

1. **При запуске видео** - показать название эпизода + версию (HDR/1080p)
   ```bash
   echo "marq-marquee: S01E01 - HDR.2160p" | nc localhost 4212
   echo "marq-timeout: 4000" | nc localhost 4212
   ```

2. **Уведомление о найденных версиях**
   ```bash
   echo "marq-marquee: ⚠️ Найдена другая версия (1080p, 33%)" | nc localhost 4212
   echo "marq-timeout: 5000" | nc localhost 4212
   ```

3. **Защита от засыпания** (будущая фича)
   ```bash
   echo "marq-marquee: Продолжить? (осталось 30 сек)" | nc localhost 4212
   ```

### Где добавить в код:

**Файл:** `vlc-cec.sh` или новый `vlc-osd.sh`

```bash
# Функция показа OSD
show_osd_message() {
    local message="$1"
    local timeout="${2:-3000}"  # По умолчанию 3 секунды
    
    echo "marq-marquee: $message" | nc -w 1 localhost 4212 2>/dev/null
    echo "marq-timeout: $timeout" | nc -w 1 localhost 4212 2>/dev/null
}

# Использование:
show_osd_message "S01E01 - Episode Title" 5000
```

---

## Ограничения

❌ **Не работает:**
- Интерактивные элементы (кнопки, меню)
- Сложное форматирование (только простой текст)
- Изображения/иконки

✅ **Работает:**
- Простой текст
- Изменение позиции/цвета/размера
- Динамическое обновление через RC
- Автоматическое скрытие

---

## Рекомендации

1. **Запускать VLC с marquee по умолчанию:**
   ```bash
   --sub-filter marq --marq-marquee ""
   ```

2. **Сохранить RC порт для управления:**
   ```bash
   --extraintf rc --rc-host localhost:4212
   ```

3. **Использовать timeout для автоматического скрытия:**
   - Короткие уведомления: 3-5 секунд
   - Важные сообщения: 5-10 секунд

4. **Цвета для разных типов сообщений:**
   - Белый `16777215` - обычная информация
   - Зелёный `65280` - успешные действия
   - Жёлтый `16776960` - предупреждения
   - Красный `16711680` - ошибки

---

## Примеры кодов цветов

| Цвет | RGB | Hex | Decimal |
|------|-----|-----|---------|
| Белый | (255,255,255) | #FFFFFF | 16777215 |
| Чёрный | (0,0,0) | #000000 | 0 |
| Красный | (255,0,0) | #FF0000 | 16711680 |
| Зелёный | (0,255,0) | #00FF00 | 65280 |
| Синий | (0,0,255) | #0000FF | 255 |
| Жёлтый | (255,255,0) | #FFFF00 | 16776960 |
| Голубой | (0,255,255) | #00FFFF | 65535 |
| Розовый | (255,0,255) | #FF00FF | 16711935 |

---

## Источники

- [VLC Command-Line Help](https://wiki.videolan.org/VLC_command-line_help/)
- [VLC Marquee Filter Documentation](https://wiki.videolan.org/Documentation:Modules/marq/)
- Web Search: "cvlc VLC command line OSD on-screen display text message"
