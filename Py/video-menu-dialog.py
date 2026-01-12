#!/usr/bin/env python3
"""
video-menu.py - TUI меню на pythondialog
Прямой аналог video-menu.sh с использованием dialog
Версия: 2.0.0 (pythondialog)
"""

import sys
import os
from pathlib import Path
import subprocess
import curses

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
    from time_input_widget import TimeInputWidget, SingleTimeInputWidget
except ImportError:
    print("❌ Ошибка: time_input_widget.py не найден!")
    sys.exit(1)

# Настройки
VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mkv', '.mov', '.wmv', '.flv', '.m4v'}
VLC_SCRIPT = "../vlc-cec.sh"
DB_MANAGER_SCRIPT = "./db-manager.sh"


class SeriesHelper:
    """Вспомогательный класс для работы с сериалами"""
    
    @staticmethod
    def extract_series_prefix(filename):
        """Извлечение series_prefix через db-manager.sh"""
        try:
            result = subprocess.run(
                ['bash', '-c', f'source {DB_MANAGER_SCRIPT} && extract_series_prefix "{filename}"'],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.stdout.strip()
        except:
            return ""
    
    @staticmethod
    def extract_series_suffix(filename):
        """Извлечение series_suffix через db-manager.sh"""
        try:
            result = subprocess.run(
                ['bash', '-c', f'source {DB_MANAGER_SCRIPT} && extract_series_suffix "{filename}"'],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.stdout.strip()
        except:
            return ""
    
    @staticmethod
    def get_series_settings(db, current_dir):
        """Получение настроек сериала для текущей директории"""
        video_files = [
            f for f in Path(current_dir).iterdir()
            if f.suffix.lower() in VIDEO_EXTENSIONS
        ]
        
        if not video_files:
            return None
        
        filename = video_files[0].name
        prefix = SeriesHelper.extract_series_prefix(filename)
        suffix = SeriesHelper.extract_series_suffix(filename)
        
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
    
    @staticmethod
    def format_settings_status(settings):
        """Форматирование строки статуса настроек"""
        if not settings:
            return ""
        
        auto_icon = "X" if settings['autoplay'] else " "
        intro_icon = "X" if settings['skip_intro'] else " "
        outro_icon = "X" if settings['skip_outro'] else " "
        
        intro_times = ""
        if settings['intro_start'] or settings['intro_end']:
            start = SeriesHelper.seconds_to_mmss(settings['intro_start'])
            end = SeriesHelper.seconds_to_mmss(settings['intro_end'])
            intro_times = f": {start}-{end}"
        
        credits_time = ""
        if settings['credits_duration']:
            credits_mm = SeriesHelper.seconds_to_mmss(settings['credits_duration'])
            credits_time = f": {credits_mm}"
        
        return f"[{auto_icon}] Auto  [{intro_icon}] Intro{intro_times}  [{outro_icon}] Outro{credits_time}"
    
    @staticmethod
    def seconds_to_mmss(seconds):
        """Конвертация секунд в MM:SS"""
        if not seconds or seconds == '':
            return "00:00"
        try:
            seconds = int(seconds)
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:02d}:{secs:02d}"
        except:
            return "00:00"


class VideoMenu:
    """Класс для TUI меню выбора видео на pythondialog"""
    
    def __init__(self, start_dir):
        self.d = Dialog(dialog="dialog", autowidgetsize=True)
        self.current_dir = Path(start_dir).resolve()
        self.last_folder = None  # Для восстановления позиции курсора
        self.db = VlcDatabase()
        self.db.__enter__()
    
    def __del__(self):
        """Закрытие БД при выходе"""
        try:
            self.db.__exit__(None, None, None)
        except:
            pass
    
    def get_items(self):
        """Получить список файлов и папок для menu"""
        items = []
        
        try:
            # Родительская папка
            if self.current_dir != Path.home():
                items.append(("..", "Назад"))
            
            # Сортированный список
            contents = sorted(
                self.current_dir.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
            
            # Директории
            for item in contents:
                if item.name.startswith('.'):
                    continue
                
                if item.is_dir():
                    items.append((item.name, "DIR"))
            
            # Видео файлы
            video_files = [
                item for item in contents
                if item.suffix.lower() in VIDEO_EXTENSIONS
            ]
            
            # Пакетная загрузка статусов
            if video_files:
                filenames = [f.name for f in video_files]
                statuses = self.db.get_playback_batch_status(
                    str(self.current_dir),
                    filenames
                )
                
                for video in video_files:
                    size = video.stat().st_size
                    size_str = self._format_size(size)
                    status = statuses.get(video.name, '')
                    
                    if status == 'watched':
                        status_icon = '[X]'
                    elif status == 'partial':
                        status_icon = '[T]'
                    else:
                        status_icon = '[ ]'
                    
                    items.append((video.name, f"{status_icon} {size_str}"))
        
        except PermissionError:
            pass
        
        return items
    
    def _format_size(self, size):
        """Форматирование размера файла"""
        for unit in ['B', 'K', 'M', 'G', 'T']:
            if size < 1024.0:
                return f"{size:.0f}{unit}"
            size /= 1024.0
        return f"{size:.0f}P"
    
    def _clear_screen(self):
        """Очистка экрана после выхода из dialog"""
        os.system('clear')
    
    def show_settings(self):
        """Показать окно настроек сериала"""
        settings = SeriesHelper.get_series_settings(self.db, self.current_dir)
        
        if not settings:
            self.d.msgbox("Это не сериал", width=40, height=7)
            return
        
        # Конвертируем текущие времена в MM:SS
        intro_start_mm = SeriesHelper.seconds_to_mmss(settings.get('intro_start', '')) if settings.get('intro_start') else ""
        intro_end_mm = SeriesHelper.seconds_to_mmss(settings.get('intro_end', '')) if settings.get('intro_end') else ""
        credits_mm = SeriesHelper.seconds_to_mmss(settings.get('credits_duration', '')) if settings.get('credits_duration') else ""
        
        # mixedform: (label, y, x, item, y, x, field_length, input_length, item_type)
        # item_type: 0=readonly label, 1=input field, 2=checkbox
        elements = [
            ("Autoplay:", 1, 1, "", 0, 0, 0, 0, 2),  # тип 2 = checkbox
            ("Skip Intro:", 3, 1, "", 0, 0, 0, 0, 2),
            ("  Intro Start (MM:SS):", 4, 3, intro_start_mm, 4, 28, 8, 8, 1),  # тип 1 = input
            ("  Intro End (MM:SS):", 5, 3, intro_end_mm, 5, 28, 8, 8, 1),
            ("Skip Outro:", 7, 1, "", 0, 0, 0, 0, 2),
            ("  Outro Duration (MM:SS):", 8, 3, credits_mm, 8, 28, 8, 8, 1),
        ]
        
        # Состояния чекбоксов (1=checked, 0=unchecked)
        item_statuses = [
            settings['autoplay'],  # Autoplay
            settings['skip_intro'],  # Skip Intro
            0,  # Intro Start (не чекбокс)
            0,  # Intro End (не чекбокс)
            settings['skip_outro'],  # Skip Outro
            0,  # Outro Duration (не чекбокс)
        ]
        
        try:
            code, fields = self.d.mixedform(
                f"Настройки: {settings['prefix']}",
                elements=elements,
                item_status_list=item_statuses,
                title="Настройки сериала",
                height=18,
                width=60
            )
        except Exception as e:
            # Если mixedform не доступен - fallback на старый метод
            self._show_settings_fallback(settings)
            return
        
        if code != self.d.OK:
            return  # Отмена
        
        # Парсим результаты
        autoplay = item_statuses[0]  # Обновляется pythondialog автоматически
        skip_intro = item_statuses[1]
        intro_start_input = fields[2].strip() if len(fields) > 2 else ""
        intro_end_input = fields[3].strip() if len(fields) > 3 else ""
        skip_outro = item_statuses[4]
        credits_input = fields[5].strip() if len(fields) > 5 else ""
        
        # Валидация и конвертация времён
        intro_start_sec = None
        intro_end_sec = None
        credits_duration_sec = None
        
        if skip_intro:
            if intro_start_input:
                intro_start_sec = self._validate_and_convert_time(intro_start_input)
                if intro_start_sec is None:
                    self.d.msgbox("Ошибка: Intro Start должен быть в формате MM:SS", height=7, width=50)
                    return
            
            if intro_end_input:
                intro_end_sec = self._validate_and_convert_time(intro_end_input)
                if intro_end_sec is None:
                    self.d.msgbox("Ошибка: Intro End должен быть в формате MM:SS", height=7, width=50)
                    return
            
            # Проверка: intro_end > intro_start
            if intro_start_sec and intro_end_sec and intro_end_sec <= intro_start_sec:
                self.d.msgbox("Ошибка: Intro End должен быть больше Intro Start", height=7, width=50)
                return
        
        if skip_outro and credits_input:
            credits_duration_sec = self._validate_and_convert_time(credits_input)
            if credits_duration_sec is None:
                self.d.msgbox("Ошибка: Outro Duration должен быть в формате MM:SS", height=7, width=50)
                return
        
        # Сохраняем настройки
        self.db.save_series_settings(
            settings['prefix'],
            settings['suffix'],
            autoplay,
            skip_intro,
            skip_outro,
            intro_start_sec,
            intro_end_sec,
            credits_duration_sec
        )
    
    def _show_settings_fallback(self, settings):
        """Fallback метод если mixedform не работает"""
        # Старый двухшаговый метод
        choices = [
            ("autoplay", "Автопродолжение следующей серии", settings['autoplay']),
            ("skip_intro", "Пропуск начальной заставки", settings['skip_intro']),
            ("skip_outro", "Пропуск конечных титров", settings['skip_outro'])
        ]
        
        code, tags = self.d.checklist(
            f"Настройки: {settings['prefix']}",
            choices=choices,
            title="Настройки сериала"
        )
        
        if code != self.d.OK:
            return
        
        # Без редактирования времён в fallback режиме
        autoplay = 1 if "autoplay" in tags else 0
        skip_intro = 1 if "skip_intro" in tags else 0
        skip_outro = 1 if "skip_outro" in tags else 0
        
        self.db.save_series_settings(
            settings['prefix'],
            settings['suffix'],
            autoplay,
            skip_intro,
            skip_outro,
            settings.get('intro_start'),
            settings.get('intro_end'),
            settings.get('credits_duration')
        )
    
    def _validate_and_convert_time(self, time_str):
        """Валидация и конвертация MM:SS в секунды
        
        Returns:
            int: секунды или None если ошибка
        """
        import re
        
        # Проверка формата MM:SS
        if not re.match(r'^\d{1,2}:\d{2}$', time_str):
            return None
        
        try:
            parts = time_str.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            
            if seconds >= 60:
                return None
            
            return minutes * 60 + seconds
        except:
            return None
    
    def run(self):
        """Главный цикл меню"""
        default_item = None  # Элемент для фокуса курсора
        
        while True:
            items = self.get_items()
            
            if not items:
                self.d.msgbox("Директория пуста или нет видео файлов", height=8, width=50)
                self._clear_screen()
                return None
            
            # Статус-строка: добавляем прямо в заголовок
            settings = SeriesHelper.get_series_settings(self.db, self.current_dir)
            
            title = f"Выбор видео: {self.current_dir}"
            if settings:
                status_line = SeriesHelper.format_settings_status(settings)
                # Добавляем статус-строку в заголовок через перенос строки
                title = f"{status_line}\n\n{title}"
            
            # Показываем меню с default_item для позиции курсора
            menu_kwargs = {
                'choices': items,
                'extra_button': True,
                'extra_label': "Настройки",
                'height': 22,
                'width': 120,
                'menu_height': 15
            }
            
            # Добавляем default_item только если есть значение
            if default_item:
                menu_kwargs['default_item'] = default_item
            
            code, tag = self.d.menu(title, **menu_kwargs)
            
            if code == self.d.OK:
                # Выбран файл/папка
                if tag == "..":
                    # Вверх - запоминаем текущую папку для курсора
                    self.last_folder = self.current_dir.name
                    self.current_dir = self.current_dir.parent
                    default_item = self.last_folder  # Курсор на эту папку
                elif (self.current_dir / tag).is_dir():
                    # Вход в подпапку
                    self.current_dir = self.current_dir / tag
                    default_item = None  # Курсор в начало
                else:
                    # Видео файл - возвращаем путь
                    return str(self.current_dir / tag)
            
            elif code == self.d.EXTRA:
                # Кнопка настроек
                self.show_settings()
                # default_item не меняем - курсор остаётся на месте
            
            elif code == self.d.CANCEL or code == self.d.ESC:
                # Выход
                self._clear_screen()
                return None


def main():
    """Главная функция"""
    start_dir = Path.home()
    
    if len(sys.argv) > 1:
        start_dir = Path(sys.argv[1])
        if not start_dir.exists() or not start_dir.is_dir():
            print(f"Ошибка: {start_dir} не существует или не является директорией")
            sys.exit(1)
    
    try:
        menu = VideoMenu(start_dir)
        selected_file = menu.run()
        
        if selected_file:
            print(f"\n✓ Выбран файл: {selected_file}\n")
            
            vlc_script = Path(__file__).parent.parent / "vlc-cec.sh"
            
            if vlc_script.exists():
                print(f"Запуск VLC через {vlc_script}...\n")
                
                # Проверяем сохранённую позицию
                db = VlcDatabase()
                with db:
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
