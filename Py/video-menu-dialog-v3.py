#!/usr/bin/env python3
"""
video-menu-dialog-v3.py - Clean implementation с dialog + curses
Полностью переписанная версия на основе video-menu.sh
Версия: 3.0.0
"""

import sys
import os
import curses
from pathlib import Path
import subprocess
from typing import Optional, Tuple, List

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dialog import Dialog
except ImportError:
    print("❌ Ошибка: pythondialog не установлен!")
    print("Установите: pip install pythondialog")
    sys.exit(1)

try:
    from vlc_db import VlcDatabase
except ImportError:
    print("❌ Ошибка: vlc_db.py не найден!")
    sys.exit(1)

try:
    from time_input_widget import AllTimesInputWidget
except ImportError:
    print("❌ Ошибка: time_input_widget.py не найден!")
    sys.exit(1)

# Настройки
VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mkv', '.mov', '.wmv', '.flv', '.m4v'}
VLC_SCRIPT = "../vlc-cec.sh"
DB_MANAGER_SCRIPT = "./db-manager.sh"


def seconds_to_mmss(seconds) -> str:
    """Конвертация секунд в MM:SS"""
    if not seconds:
        return "00:00"
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"
    except:
        return "00:00"


def mmss_to_seconds(mmss: str) -> Optional[int]:
    """Конвертация MM:SS в секунды"""
    import re
    if not re.match(r'^\d{1,2}:\d{2}$', mmss):
        return None
    try:
        parts = mmss.split(':')
        minutes = int(parts[0])
        seconds = int(parts[1])
        if seconds >= 60:
            return None
        return minutes * 60 + seconds
    except:
        return None


def extract_series_info(filename: str) -> Tuple[str, str]:
    """Извлечь prefix и suffix через db-manager.sh"""
    try:
        result = subprocess.run(
            ['bash', '-c', f'source {DB_MANAGER_SCRIPT} && extract_series_prefix "{filename}"'],
            capture_output=True, text=True, timeout=2
        )
        prefix = result.stdout.strip()
        
        result = subprocess.run(
            ['bash', '-c', f'source {DB_MANAGER_SCRIPT} && extract_series_suffix "{filename}"'],
            capture_output=True, text=True, timeout=2
        )
        suffix = result.stdout.strip()
        
        return (prefix, suffix)
    except:
        return ("", "")


def get_series_settings(db: VlcDatabase, current_dir: Path) -> Optional[dict]:
    """Получить настройки сериала для текущей директории"""
    # Найти первый видеофайл
    video_files = [f for f in current_dir.iterdir() if f.suffix.lower() in VIDEO_EXTENSIONS]
    
    if not video_files:
        return None
    
    prefix, suffix = extract_series_info(video_files[0].name)
    
    if not prefix:
        return None
    
    settings = db.get_series_settings(prefix, suffix)
    
    if settings:
        return {
            'prefix': prefix,
            'suffix': suffix,
            'autoplay': settings[0],
            'skip_intro': settings[1],
            'skip_outro': settings[2],
            'intro_start': settings[3] if settings[3] else '',
            'intro_end': settings[4] if settings[4] else '',
            'credits_duration': settings[5] if settings[5] else ''
        }
    
    return {
        'prefix': prefix,
        'suffix': suffix,
        'autoplay': 0,
        'skip_intro': 0,
        'skip_outro': 0,
        'intro_start': '',
        'intro_end': '',
        'credits_duration': ''
    }


def format_settings_status(settings: dict) -> str:
    """Форматировать строку статуса настроек"""
    if not settings:
        return ""
    
    auto_icon = "X" if settings['autoplay'] else " "
    intro_icon = "X" if settings['skip_intro'] else " "
    outro_icon = "X" if settings['skip_outro'] else " "
    
    intro_times = ""
    if settings['intro_start'] or settings['intro_end']:
        start = seconds_to_mmss(settings['intro_start'])
        end = seconds_to_mmss(settings['intro_end'])
        intro_times = f": {start}-{end}"
    
    credits_time = ""
    if settings['credits_duration']:
        credits_mm = seconds_to_mmss(settings['credits_duration'])
        credits_time = f": {credits_mm}"
    
    return f"[{auto_icon}] Auto  [{intro_icon}] Intro{intro_times}  [{outro_icon}] Outro{credits_time}"


def show_settings(d: Dialog, db: VlcDatabase, current_dir: Path):
    """Показать настройки сериала"""
    settings = get_series_settings(db, current_dir)
    
    if not settings:
        d.msgbox("Это не сериал", width=40, height=7)
        return
    
    # Шаг 1: Показать чекбоксы через dialog
    choices = [
        ("autoplay", "Автопродолжение следующей серии", settings['autoplay']),
        ("skip_intro", "Пропуск начальной заставки", settings['skip_intro']),
        ("skip_outro", "Пропуск конечных титров", settings['skip_outro'])
    ]
    
    code, tags = d.checklist(
        f"Настройки: {settings['prefix']}",
        choices=choices,
        title="Настройки сериала",
        extra_button=True,
        extra_label="Редактировать время",
        height=12,
        width=60
    )
    
    if code == d.CANCEL or code == d.ESC:
        return  # Отмена
    
    autoplay = 1 if "autoplay" in tags else 0
    skip_intro = 1 if "skip_intro" in tags else 0
    skip_outro = 1 if "skip_outro" in tags else 0
    
    intro_start_sec = settings.get('intro_start')
    intro_end_sec = settings.get('intro_end')
    credits_duration_sec = settings.get('credits_duration')
    
    # Шаг 2: Если нажата кнопка "Редактировать время" - открыть curses виджет
    if code == d.EXTRA:
        intro_start_mm = seconds_to_mmss(settings.get('intro_start', ''))
        intro_end_mm = seconds_to_mmss(settings.get('intro_end', ''))
        outro_mm = seconds_to_mmss(settings.get('credits_duration', ''))
        
        def curses_all_times(stdscr):
            widget = AllTimesInputWidget(stdscr, "Настройка времени", intro_start_mm, intro_end_mm, outro_mm)
            return widget.run()
        
        try:
            result = curses.wrapper(curses_all_times)
            if result is None:
                # Отменено - вернуться к выбору чекбоксов
                return show_settings(d, db, current_dir)
            
            intro_start_mm, intro_end_mm, outro_mm = result
            intro_start_sec = mmss_to_seconds(intro_start_mm)
            intro_end_sec = mmss_to_seconds(intro_end_mm)
            credits_duration_sec = mmss_to_seconds(outro_mm)
            
            if intro_start_sec is None or intro_end_sec is None or credits_duration_sec is None:
                d.msgbox("Ошибка: Неверный формат времени", height=7, width=50)
                return show_settings(d, db, current_dir)
        except Exception as e:
            d.msgbox(f"Ошибка: {e}", height=8, width=60)
            return show_settings(d, db, current_dir)
    
    # Сохранить настройки
    db.save_series_settings(
        settings['prefix'],
        settings['suffix'],
        autoplay,
        skip_intro,
        skip_outro,
        intro_start_sec,
        intro_end_sec,
        credits_duration_sec
    )


def format_size(size: int) -> str:
    """Форматирование размера файла"""
    for unit in ['B', 'K', 'M', 'G', 'T']:
        if size < 1024.0:
            return f"{size:.0f}{unit}"
        size /= 1024.0
    return f"{size:.0f}P"


def show_menu(d: Dialog, db: VlcDatabase, current_dir: Path, default_item: Optional[str] = None):
    """Показать меню выбора видео"""
    # Получаем список элементов
    items = []
    
    # Добавляем parent directory если не в HOME
    if current_dir != Path.home():
        items.append(("..", "Назад"))
    
    # Сортированный список директорий и файлов
    try:
        contents = sorted(current_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        d.msgbox("Нет доступа к директории", height=7, width=50)
        return None
    
    # Добавляем директории
    for item in contents:
        if item.name.startswith('.'):
            continue
        if item.is_dir():
            items.append((item.name, "DIR"))
    
    # Видео файлы
    video_files = [item for item in contents if item.suffix.lower() in VIDEO_EXTENSIONS]
    
    # Пакетная загрузка статусов
    if video_files:
        filenames = [f.name for f in video_files]
        statuses = db.get_playback_batch_status(str(current_dir), filenames)
        
        for video in video_files:
            size = video.stat().st_size
            size_str = format_size(size)
            status = statuses.get(video.name, '')
            
            if status == 'watched':
                status_icon = '[X]'
            elif status == 'partial':
                status_icon = '[T]'
            else:
                status_icon = '[ ]'
            
            items.append((video.name, f"{status_icon} {size_str}"))
    
    if not items:
        d.msgbox("Директория пуста или нет видео файлов", height=8, width=50)
        return None
    
    # Заголовок с настройками
    settings = get_series_settings(db, current_dir)
    title = f"Выбор видео: {current_dir}"
    
    if settings:
        status_line = format_settings_status(settings)
        title = f"{status_line}\n\n{title}"
    
    # Показываем меню
    menu_kwargs = {
        'choices': items,
        'extra_button': True,
        'extra_label': "Настройки",
        'height': 22,
        'width': 120,
        'menu_height': 15
    }
    
    if default_item:
        menu_kwargs['default_item'] = default_item
    
    code, tag = d.menu(title, **menu_kwargs)
    
    if code == d.EXTRA:
        # Кнопка настроек
        show_settings(d, db, current_dir)
        # Вернуться в меню
        return show_menu(d, db, current_dir, default_item)
    
    elif code == d.OK and tag:
        if tag == "..":
            # Вверх
            parent = current_dir.parent
            folder_name = current_dir.name
            return show_menu(d, db, parent, folder_name)
        
        elif (current_dir / tag).is_dir():
            # Вход в директорию
            return show_menu(d, db, current_dir / tag)
        
        else:
            # Видео файл
            return str(current_dir / tag)
    
    elif code == d.CANCEL or code == d.ESC:
        # Выход
        os.system('clear')
        return None
    
    return None


def main():
    """Главная функция"""
    start_dir = Path.home()
    
    if len(sys.argv) > 1:
        start_dir = Path(sys.argv[1])
        if not start_dir.exists() or not start_dir.is_dir():
            print(f"Ошибка: {start_dir} не существует или не является директорией")
            sys.exit(1)
    
    d = Dialog(dialog="dialog", autowidgetsize=True)
    db = VlcDatabase()
    
    try:
        with db:
            selected_file = show_menu(d, db, start_dir)
            
            if selected_file:
                print(f"\n✓ Выбран файл: {selected_file}\n")
                
                vlc_script = Path(__file__).parent.parent / "vlc-cec.sh"
                
                if vlc_script.exists():
                    print(f"Запуск VLC через {vlc_script}...\n")
                    
                    # Проверяем сохранённую позицию
                    basename = Path(selected_file).name
                    playback = db.get_playback(basename)
                    
                    if playback:
                        position, duration, percent, _, _ = playback
                        print(f"Найдена сохранённая позиция: {percent}% ({position // 60} мин {position % 60} сек)\n")
                        subprocess.run([str(vlc_script), str(position), selected_file], check=True)
                    else:
                        subprocess.run([str(vlc_script), selected_file], check=True)
                    
                    # Возврат в меню
                    print("\nВозврат в меню...\n")
                    main()
                else:
                    print(f"⚠ VLC скрипт не найден: {vlc_script}")
            else:
                print("\nВыход из меню.")
    
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
