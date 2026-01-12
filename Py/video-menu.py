#!/usr/bin/env python3
"""
video-menu.py - Полнофункциональное TUI меню на Python curses
Аналог video-menu.sh с полным соответствием функционала
Версия: 1.0.0
"""

import curses
import sys
import os
from pathlib import Path
import subprocess
import re

# Добавляем текущую директорию в PYTHONPATH для импорта vlc_db
sys.path.insert(0, str(Path(__file__).parent))

try:
    from vlc_db import VlcDatabase
except ImportError:
    print("❌ Ошибка: vlc_db.py не найден!")
    print("Убедитесь что vlc_db.py находится в той же папке")
    sys.exit(1)

# Настройки
VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mkv', '.mov', '.wmv', '.flv', '.m4v'}
VLC_SCRIPT = "../vlc-cec.sh"  # Путь к оригинальному скрипту
DB_MANAGER_SCRIPT = "./db-manager.sh"  # Для extract_series_prefix/suffix

# Константы для кнопок
BTN_SETTINGS = 0
BTN_CANCEL = 1


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
        # Найти первый видеофайл
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
        
        # Добавляем времена если есть
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


class SettingsDialog:
    """Окно настроек сериала"""
    
    def __init__(self, stdscr, settings):
        self.stdscr = stdscr
        self.settings = settings
        self.selected_idx = 0
        self.options = [
            ('autoplay', 'Автопродолжение следующей серии', settings.get('autoplay', 0)),
            ('skip_intro', 'Пропуск начальной заставки', settings.get('skip_intro', 0)),
            ('skip_outro', 'Пропуск конечных титров', settings.get('skip_outro', 0))
        ]
        # Времена в MM:SS формате
        self.intro_start = self._sec_to_mmss(settings.get('intro_start', ''))
        self.intro_end = self._sec_to_mmss(settings.get('intro_end', ''))
        self.outro_duration = self._sec_to_mmss(settings.get('credits_duration', ''))
        self.editing_field = None  # Какое поле редактируем
        self.edit_buffer = ""  # Буфер ввода
    
    def _sec_to_mmss(self, seconds):
        """Конвертация секунд в MM:SS для редактирования"""
        if not seconds or seconds == '':
            return ""
        try:
            seconds = int(seconds)
            return f"{seconds // 60:02d}:{seconds % 60:02d}"
        except:
            return ""
    
    def _mmss_to_sec(self, mmss):
        """Конвертация MM:SS в секунды"""
        if not mmss or mmss == "":
            return None
        try:
            parts = mmss.split(':')
            if len(parts) != 2:
                return None
            minutes = int(parts[0])
            seconds = int(parts[1])
            if seconds >= 60:
                return None
            return minutes * 60 + seconds
        except:
            return None
    
    def draw(self):
        """Отрисовка окна настроек"""
        height, width = self.stdscr.getmaxyx()
        
        # Размеры окна
        win_height = 16
        win_width = 70
        start_y = (height - win_height) // 2
        start_x = (width - win_width) // 2
        
        # Создаём окно
        win = curses.newwin(win_height, win_width, start_y, start_x)
        win.box()
        
        # Заголовок
        title = f" Настройки: {self.settings['prefix']} "
        win.addstr(0, (win_width - len(title)) // 2, title, curses.A_BOLD)
        
        y = 2
        
        # Чекбоксы
        for idx, (key, label, value) in enumerate(self.options):
            checkbox = "[X]" if value else "[ ]"
            attr = curses.A_REVERSE if idx == self.selected_idx and self.editing_field is None else 0
            win.addstr(y, 2, f"{checkbox} {label}", attr)
            y += 1
        
        y += 1
        
        # Поля ввода времён (только если соответствующие чекбоксы включены)
        skip_intro = self.options[1][2]  # skip_intro
        skip_outro = self.options[2][2]  # skip_outro
        
        if skip_intro:
            # Intro Start
            intro_start_label = "  Intro Start (MM:SS):"
            if self.editing_field == 'intro_start':
                intro_start_val = self.edit_buffer if self.edit_buffer else "_____"
            else:
                intro_start_val = self.intro_start if self.intro_start else "00:00"
            attr = curses.A_REVERSE if self.editing_field == 'intro_start' else 0
            win.addstr(y, 2, intro_start_label)
            win.addstr(y, 27, intro_start_val, attr)
            y += 1
            
            # Intro End
            intro_end_label = "  Intro End (MM:SS):"
            if self.editing_field == 'intro_end':
                intro_end_val = self.edit_buffer if self.edit_buffer else "_____"
            else:
                intro_end_val = self.intro_end if self.intro_end else "00:00"
            attr = curses.A_REVERSE if self.editing_field == 'intro_end' else 0
            win.addstr(y, 2, intro_end_label)
            win.addstr(y, 27, intro_end_val, attr)
            y += 1
        
        if skip_outro:
            # Outro Duration
            outro_label = "  Outro Duration (MM:SS):"
            if self.editing_field == 'outro_duration':
                outro_val = self.edit_buffer if self.edit_buffer else "_____"
            else:
                outro_val = self.outro_duration if self.outro_duration else "00:00"
            attr = curses.A_REVERSE if self.editing_field == 'outro_duration' else 0
            win.addstr(y, 2, outro_label)
            win.addstr(y, 27, outro_val, attr)
            y += 1
        
        # Подсказка
        if self.editing_field:
            help_text = "Введите MM:SS | Enter: Сохранить | Esc: Отмена"
        else:
            help_text = "SPACE: Вкл/Выкл | Enter: OK | Tab: Редактировать время | Esc: Отмена"
        win.addstr(win_height - 2, 2, help_text[:win_width - 4], curses.A_DIM)
        
        win.refresh()
        return win
    
    def run(self):
        """Главный цикл диалога настроек"""
        while True:
            win = self.draw()
            
            try:
                key = win.getch()
            except:
                continue
            
            if self.editing_field:
                # Режим редактирования времени
                if key == 27:  # Esc - отмена редактирования
                    self.editing_field = None
                    self.edit_buffer = ""
                
                elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                    # Сохранить время
                    if self._validate_time(self.edit_buffer):
                        if self.editing_field == 'intro_start':
                            self.intro_start = self.edit_buffer
                        elif self.editing_field == 'intro_end':
                            self.intro_end = self.edit_buffer
                        elif self.editing_field == 'outro_duration':
                            self.outro_duration = self.edit_buffer
                        self.editing_field = None
                        self.edit_buffer = ""
                    else:
                        # Ошибка валидации - остаёмся в режиме редактирования
                        curses.beep()
                
                elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                    self.edit_buffer = self.edit_buffer[:-1]
                
                elif key >= 32 and key <= 126:  # Печатаемые символы
                    char = chr(key)
                    if char in '0123456789:' and len(self.edit_buffer) < 5:
                        self.edit_buffer += char
                        # Автоподстановка ":"
                        if len(self.edit_buffer) == 2 and ':' not in self.edit_buffer:
                            self.edit_buffer += ':'
            
            else:
                # Режим навигации по чекбоксам
                if key == curses.KEY_UP or key == ord('k'):
                    self.selected_idx = max(0, self.selected_idx - 1)
                
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.selected_idx = min(len(self.options) - 1, self.selected_idx + 1)
                
                elif key == ord(' '):  # Space - переключить чекбокс
                    key_name, label, current = self.options[self.selected_idx]
                    self.options[self.selected_idx] = (key_name, label, 1 - current)
                
                elif key == 9:  # Tab - перейти к редактированию времени
                    skip_intro = self.options[1][2]
                    skip_outro = self.options[2][2]
                    
                    if skip_intro:
                        self.editing_field = 'intro_start'
                        self.edit_buffer = self.intro_start if self.intro_start else ""
                    elif skip_outro:
                        self.editing_field = 'outro_duration'
                        self.edit_buffer = self.outro_duration if self.outro_duration else ""
                
                elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                    # Enter - сохранить и вернуть результат
                    result = {
                        key: value
                        for key, label, value in self.options
                    }
                    
                    # Добавляем времена
                    result['intro_start'] = self._mmss_to_sec(self.intro_start) if self.intro_start else None
                    result['intro_end'] = self._mmss_to_sec(self.intro_end) if self.intro_end else None
                    result['credits_duration'] = self._mmss_to_sec(self.outro_duration) if self.outro_duration else None
                    
                    # Валидация: intro_end > intro_start
                    if result.get('skip_intro') and result['intro_start'] and result['intro_end']:
                        if result['intro_end'] <= result['intro_start']:
                            curses.beep()
                            continue
                    
                    return result
                
                elif key == 27:  # Esc - отмена
                    return None
    
    def _validate_time(self, time_str):
        """Валидация формата MM:SS"""
        import re
        if not time_str:
            return True
        return bool(re.match(r'^\d{1,2}:\d{2}$', time_str))


class VideoMenu:
    """Класс для TUI меню выбора видео"""
    
    def __init__(self, stdscr, start_dir):
        self.stdscr = stdscr
        self.current_dir = Path(start_dir).resolve()
        self.selected_idx = 0
        self.scroll_offset = 0
        self.last_folder = None  # Для сохранения позиции курсора
        self.focus_mode = 'list'  # 'list' или 'buttons'
        self.active_button = BTN_SETTINGS  # Активная кнопка внизу
        
        # База данных
        self.db = VlcDatabase()
        self.db.__enter__()  # Открываем подключение
        
        # Инициализация curses
        curses.curs_set(0)  # Скрыть курсор
        self.stdscr.keypad(True)  # Включить специальные клавиши
        
        # Цвета
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Заголовок
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Директории
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Видео файлы
            curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Выделение
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Кнопки
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_RED)     # Watched
            curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Partial
    
    def __del__(self):
        """Закрытие БД при выходе"""
        try:
            self.db.__exit__(None, None, None)
        except:
            pass
    
    def get_items(self):
        """Получить список файлов и папок"""
        items = []
        
        try:
            # Родительская папка
            if self.current_dir != Path.home():
                items.append({
                    'name': '..',
                    'type': 'DIR',
                    'description': 'Назад',
                    'path': self.current_dir.parent,
                    'status': ''
                })
            
            # Сортированный список содержимого
            contents = sorted(
                self.current_dir.iterdir(),
                key=lambda x: (not x.is_dir(), x.name.lower())
            )
            
            # Директории
            for item in contents:
                if item.name.startswith('.'):
                    continue
                
                if item.is_dir():
                    items.append({
                        'name': item.name,
                        'type': 'DIR',
                        'description': 'DIR',
                        'path': item,
                        'status': ''
                    })
            
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
                    
                    # Форматируем статус
                    if status == 'watched':
                        status_icon = '[X]'
                    elif status == 'partial':
                        status_icon = '[T]'
                    else:
                        status_icon = '[ ]'
                    
                    items.append({
                        'name': video.name,
                        'type': 'FILE',
                        'description': f"{status_icon} {size_str}",
                        'path': video,
                        'status': status
                    })
        
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
    
    def draw(self, items):
        """Отрисовка меню"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Заголовок
        title = f"Выбор видео: {self.current_dir}"
        if len(title) > width - 4:
            title = "..." + title[-(width - 7):]
        
        try:
            self.stdscr.addstr(0, 2, title, curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Статус-строка настроек (строка 1)
        settings = SeriesHelper.get_series_settings(self.db, self.current_dir)
        if settings:
            status_line = SeriesHelper.format_settings_status(settings)
            try:
                # Центрируем
                x = (width - len(status_line)) // 2
                self.stdscr.addstr(1, max(2, x), status_line)
            except curses.error:
                pass
        
        # Список начинается со строки 3
        list_start_y = 3
        
        # Кнопки внизу (последняя строка)
        self._draw_buttons(height, width)
        
        # Вычисляем видимую область
        max_visible = height - list_start_y - 2  # Место для кнопок
        
        # Автоскролл
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + max_visible:
            self.scroll_offset = self.selected_idx - max_visible + 1
        
        # Список файлов
        for idx in range(len(items)):
            if idx < self.scroll_offset:
                continue
            if idx >= self.scroll_offset + max_visible:
                break
            
            item = items[idx]
            y = list_start_y + idx - self.scroll_offset
            
            if y >= height - 2:
                break
            
            # Формируем строку
            if item['type'] == 'DIR':
                line = f"📁 {item['name']}"
                color = curses.color_pair(2)
            else:
                line = f"{item['description']} {item['name']}"
                # Цвет в зависимости от статуса
                if item['status'] == 'watched':
                    color = curses.color_pair(6)
                elif item['status'] == 'partial':
                    color = curses.color_pair(7)
                else:
                    color = curses.color_pair(3)
            
            # Обрезаем если не влезает
            if len(line) > width - 4:
                line = line[:width - 7] + "..."
            
            # Выделение
            if idx == self.selected_idx:
                attr = curses.color_pair(4) | curses.A_BOLD
            else:
                attr = color
            
            try:
                self.stdscr.addstr(y, 2, line, attr)
            except curses.error:
                pass
        
        # Индикатор прокрутки
        if len(items) > max_visible:
            try:
                scroll_info = f"[{self.selected_idx + 1}/{len(items)}]"
                self.stdscr.addstr(0, width - len(scroll_info) - 2, scroll_info, curses.A_DIM)
            except curses.error:
                pass
        
        self.stdscr.refresh()
    
    def _draw_buttons(self, height, width):
        """Отрисовка кнопок внизу"""
        button_y = height - 1
        
        # Кнопка "Настройки"
        settings_btn = "<Настройки>"
        settings_x = 5
        
        # Кнопка "Cancel"
        cancel_btn = "< Cancel >"
        cancel_x = width - len(cancel_btn) - 5
        
        try:
            # Настройки
            if self.focus_mode == 'buttons' and self.active_button == BTN_SETTINGS:
                self.stdscr.addstr(button_y, settings_x, settings_btn, curses.color_pair(5) | curses.A_BOLD)
            else:
                self.stdscr.addstr(button_y, settings_x, settings_btn)
            
            # Cancel
            if self.focus_mode == 'buttons' and self.active_button == BTN_CANCEL:
                self.stdscr.addstr(button_y, cancel_x, cancel_btn, curses.color_pair(5) | curses.A_BOLD)
            else:
                self.stdscr.addstr(button_y, cancel_x, cancel_btn)
        except curses.error:
            pass
    
    def show_settings(self):
        """Показать окно настроек"""
        settings = SeriesHelper.get_series_settings(self.db, self.current_dir)
        
        if not settings:
            # Не сериал
            return
        
        # Показываем диалог
        dialog = SettingsDialog(self.stdscr, settings)
        result = dialog.run()
        
        if result is not None:
            # Сохраняем в БД (включая времена)
            self.db.save_series_settings(
                settings['prefix'],
                settings['suffix'],
                result.get('autoplay', 0),
                result.get('skip_intro', 0),
                result.get('skip_outro', 0),
                result.get('intro_start'),
                result.get('intro_end'),
                result.get('credits_duration')
            )
    
    def run(self):
        """Главный цикл меню"""
        while True:
            items = self.get_items()
            
            if not items:
                # Пустая директория
                self.stdscr.clear()
                height, width = self.stdscr.getmaxyx()
                msg = "Директория пуста или нет видео файлов"
                try:
                    self.stdscr.addstr(height // 2, (width - len(msg)) // 2, msg)
                    self.stdscr.addstr(height // 2 + 2, (width - 20) // 2, "Нажмите q для выхода")
                except curses.error:
                    pass
                self.stdscr.refresh()
                
                key = self.stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    return None
                continue
            
            # Восстановление позиции курсора при возврате
            if self.last_folder:
                for idx, item in enumerate(items):
                    if item['name'] == self.last_folder:
                        self.selected_idx = idx
                        break
                self.last_folder = None
            
            # Проверка границ
            if self.selected_idx >= len(items):
                self.selected_idx = len(items) - 1
            
            self.draw(items)
            key = self.stdscr.getch()
            
            # Навигация
            if key == curses.KEY_UP or key == ord('k'):
                if self.selected_idx > 0:
                    self.selected_idx -= 1
            
            elif key == curses.KEY_DOWN or key == ord('j'):
                if self.selected_idx < len(items) - 1:
                    self.selected_idx += 1
            
            elif key == curses.KEY_PPAGE:  # Page Up
                self.selected_idx = max(0, self.selected_idx - 10)
            
            elif key == curses.KEY_NPAGE:  # Page Down
                self.selected_idx = min(len(items) - 1, self.selected_idx + 10)
            
            elif key == curses.KEY_HOME:
                self.selected_idx = 0
            
            elif key == curses.KEY_END:
                self.selected_idx = len(items) - 1
            
            elif key == 9:  # Tab - переключение между списком и кнопками
                if self.focus_mode == 'list':
                    self.focus_mode = 'buttons'
                else:
                    self.focus_mode = 'list'
            
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10 or key == 13:
                # Enter - ПРИОРИТЕТ: список, потом кнопки
                if self.focus_mode == 'buttons':
                    # Фокус на кнопках
                    if self.active_button == BTN_SETTINGS:
                        # Нажата кнопка настроек
                        self.show_settings()
                        self.focus_mode = 'list'  # Возврат к списку
                    elif self.active_button == BTN_CANCEL:
                        # Нажата кнопка Cancel
                        return None
                else:
                    # Фокус на списке - выбор файла/папки
                    selected = items[self.selected_idx]
                    
                    if selected['name'] == '..':
                        # Вверх - запоминаем текущую папку
                        self.last_folder = self.current_dir.name
                        self.current_dir = self.current_dir.parent
                        self.selected_idx = 0
                        self.scroll_offset = 0
                    
                    elif selected['type'] == 'DIR':
                        # Переход в dir
                        self.current_dir = selected['path']
                        self.selected_idx = 0
                        self.scroll_offset = 0
                        self.last_folder = None
                    
                    elif selected['type'] == 'FILE':
                        # Запуск видео
                        return str(selected['path'])
            
            elif key == curses.KEY_LEFT and self.focus_mode == 'buttons':
                # Стрелка влево - переключение между кнопками
                self.active_button = 1 - self.active_button
            
            elif key == ord('q') or key == ord('Q'):
                # Выход
                return None
            
            elif key == ord('h') or key == ord('H'):
                # Помощь
                self.show_help()
    
    def show_help(self):
        """Показать окно помощи"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        help_lines = [
            "═══════════════════════════════════════",
            "         СПРАВКА ПО УПРАВЛЕНИЮ",
            "═══════════════════════════════════════",
            "",
            "  ↑ / k      - Вверх",
            "  ↓ / j      - Вниз",
            "  Enter      - Выбрать / Открыть",
            "  Tab        - Переключить кнопки",
            "  q          - Выход",
            "  h          - Эта справка",
            "  Home       - В начало списка",
            "  End        - В конец списка",
            "  PgUp/PgDn  - На 10 элементов",
            "",
            "Кнопки:",
            "  <Настройки> - Настройки сериала",
            "  <Cancel>    - Выход из меню",
            "",
            "═══════════════════════════════════════",
            "",
            "Нажмите любую клавишу для возврата..."
        ]
        
        start_y = (height - len(help_lines)) // 2
        
        for i, line in enumerate(help_lines):
            try:
                x = (width - len(line)) // 2
                self.stdscr.addstr(start_y + i, max(0, x), line)
            except curses.error:
                pass
        
        self.stdscr.refresh()
        self.stdscr.getch()


def main():
    """Главная функция"""
    # Стартовая директория
    start_dir = Path.home()
    
    if len(sys.argv) > 1:
        start_dir = Path(sys.argv[1])
        if not start_dir.exists() or not start_dir.is_dir():
            print(f"Ошибка: {start_dir} не существует или не является директорией")
            sys.exit(1)
    
    try:
        # Запуск curses интерфейса
        selected_file = curses.wrapper(lambda stdscr: VideoMenu(stdscr, start_dir).run())
        
        if selected_file:
            print(f"\n✓ Выбран файл: {selected_file}\n")
            
            # Проверяем наличие vlc-cec.sh
            vlc_script = Path(__file__).parent.parent / "vlc-cec.sh"
            
            if vlc_script.exists():
                print(f"Запуск VLC через {vlc_script}...\n")
                
                # Проверяем есть ли сохранённая позиция
                db = VlcDatabase()
                with db:
                    basename = Path(selected_file).name
                    playback = db.get_playback(basename)
                    
                    if playback:
                        position, duration, percent, _, _ = playback
                        print(f"Найдена сохранённая позиция: {percent}% ({position // 60} мин {position % 60} сек)\n")
                        
                        # Запускаем с позиции
                        try:
                            subprocess.run([str(vlc_script), str(position), selected_file], check=True)
                        except subprocess.CalledProcessError as e:
                            print(f"Ошибка при запуске VLC: {e}")
                        except KeyboardInterrupt:
                            print("\nПрервано пользователем")
                    else:
                        # Запускаем с начала
                        try:
                            subprocess.run([str(vlc_script), selected_file], check=True)
                        except subprocess.CalledProcessError as e:
                            print(f"Ошибка при запуске VLC: {e}")
                        except KeyboardInterrupt:
                            print("\nПрервано пользователем")
                
                # После VLC возвращаемся в меню
                print("\nВозврат в меню...\n")
                main()  # Рекурсивный вызов для автовозврата
            else:
                print(f"⚠ VLC скрипт не найден: {vlc_script}")
                print(f"Для запуска используйте: ./vlc-cec.sh \"{selected_file}\"")
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
