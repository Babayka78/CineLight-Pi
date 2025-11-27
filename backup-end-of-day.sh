#!/bin/bash
# Скрипт для создания бэкапов на конец рабочего дня
# Использование: ./backup-end-of-day.sh

TODAY=$(date +%y%m%d)
TIMESTAMP=$(date +%y%m%d_%H%M)

# Создать папку для бэкапов
mkdir -p BAK/$TODAY

echo "========================================="
echo "Создание бэкапов на конец дня: $TODAY"
echo "========================================="
echo ""

# Бэкап RELIS файлов (ВСЕГДА, даже если не было изменений)
echo "📦 Бэкап RELIS файлов..."
if [ -f "vlc-cec_RELIS.sh" ]; then
    cp vlc-cec_RELIS.sh "BAK/$TODAY/vlc-cec_RELIS_V#_${TIMESTAMP}.bak"
    echo "  ✓ vlc-cec_RELIS.sh"
fi

if [ -f "video-menu_RELIS.sh" ]; then
    cp video-menu_RELIS.sh "BAK/$TODAY/video-menu_RELIS_V#_${TIMESTAMP}.bak"
    echo "  ✓ video-menu_RELIS.sh"
fi

if [ -f "series-tracker_RELIS.sh" ]; then
    cp series-tracker_RELIS.sh "BAK/$TODAY/series-tracker_RELIS_V#_${TIMESTAMP}.bak"
    echo "  ✓ series-tracker_RELIS.sh"
fi

echo ""

# Бэкап документации
echo "📝 Бэкап документации..."
if [ -f "HANDOFF-NEXT-SESSION.md" ]; then
    cp HANDOFF-NEXT-SESSION.md "BAK/$TODAY/HANDOFF-NEXT-SESSION_V#_${TIMESTAMP}.bak"
    echo "  ✓ HANDOFF-NEXT-SESSION.md"
fi

if [ -f "CHANGELOG.md" ]; then
    cp CHANGELOG.md "BAK/$TODAY/CHANGELOG_V#_${TIMESTAMP}.bak"
    echo "  ✓ CHANGELOG.md"
fi

# Бэкап Summary файлов за сегодня
SUMMARY_COUNT=$(ls Summary_${TODAY}_*.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$SUMMARY_COUNT" -gt 0 ]; then
    cp Summary_${TODAY}_*.md "BAK/$TODAY/" 2>/dev/null
    echo "  ✓ Summary_${TODAY}_*.md ($SUMMARY_COUNT файл(ов))"
fi

echo ""
echo "========================================="
echo "✅ Бэкапы созданы в BAK/$TODAY/"
echo "========================================="
echo ""
echo "⚠️  ВАЖНО: Замените V# на правильные номера версий!"
echo "    Посмотрите последние версии в BAK/ и используйте следующий номер."
echo ""
echo "Содержимое BAK/$TODAY/:"
ls -1 "BAK/$TODAY/" | head -15
echo ""
