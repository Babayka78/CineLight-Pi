#!/usr/bin/env python3
"""
video-menu-Prompt_toolkit.py - TUI меню на prompt_toolkit
Версия с улучшенным UX для настроек сериалов
Версия: 2.2.0 (prompt_toolkit)
"""

import sys
import os
from pathlib import Path
import subprocess
from typing import Optional, Dict, List, Tuple


try:
    from prompt_toolkit import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout, HSplit, VSplit, Window, FormattedTextControl, Dimension
    from prompt_toolkit.widgets import Frame
    from prompt_toolkit.formatted_text import HTML, FormattedText
    from prompt_toolkit.layout.containers import FloatContainer, Float
    from prompt_toolkit.styles import Style
except ImportError as e:
    print("❌ Ошибка: prompt_toolkit не установлен!")
    print("Установите: pip install prompt_toolkit")
    print(f"Детали: {e}")
    sys.exit(1)

try:
    from vlc_db import VlcDatabase
except ImportError:
    print("❌ Ошибка: vlc_db.py не найден!")
    sys.exit(1)

# Настройки
VIDEO_EXTENSIONS = {'.avi', '.mp4', '.mkv', '.mov', '.wmv', '.flv', '.m4v'}
VLC_SCRIPT = "../vlc-cec.sh"
DB_MANAGER_SCRIPT = "./db-manager.sh"


class TimeInput:
    """Виджет для ввода времени в формате MM:SS с режимом замены и контрастным цветом"""
    
    def __init__(self, initial_value: str = "00:00"):
        self.value = initial_value if initial_value else "00:00"
        self.cursor_pos = 0  # Позиция курсора (0-4, пропуская ':')
        self.enabled = True
        
    def _get_cursor_char_index(self) -> int:
        """Получить индекс символа в строке (0,1,3,4)"""
        positions = [0, 1, 3, 4]  # Пропускаем ':' на позиции 2
        return positions[self.cursor_pos] if self.cursor_pos < len(positions) else 0
    
    def move_left(self):
        """Переместить курсор влево"""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
    
    def move_right(self):
        """Переместить курсор вправо"""
        if self.cursor_pos < 3:  # 4 позиции (0-3)
            self.cursor_pos += 1
    
    def input_digit(self, digit: str):
        """Ввести цифру в текущую позицию (режим замены)"""
        if not digit.isdigit():
            return
        
        chars = list(self.value)
        char_idx = self._get_cursor_char_index()
        
        # Валидация для минут (первые две цифры)
        if self.cursor_pos == 0:  # Первая цифра минут
            chars[char_idx] = digit
        elif self.cursor_pos == 1:  # Вторая цифра минут
            chars[char_idx] = digit
        # Валидация для секунд (0-59)
        elif self.cursor_pos == 2:  # Первая цифра секунд
            if int(digit) <= 5:  # Секунды не могут начинаться с цифры > 5
                chars[char_idx] = digit
        elif self.cursor_pos == 3:  # Вторая цифра секунд
            chars[char_idx] = digit
        
        self.value = ''.join(chars)
        self.move_right()
    
    def get_formatted_text(self) -> FormattedText:
        """Получить отформатированный текст с подсветкой курсора"""
        if not self.enabled:
            return FormattedText([('class:disabled', self.value)])
        
        result = []
        char_idx = self._get_cursor_char_index()
        
        for i, char in enumerate(self.value):
            if i == char_idx:
                result.append(('class:cursor', char))
            else:
                result.append(('class:time', char))
        
        return FormattedText(result)
    
    def to_seconds(self) -> Optional[int]:
        """Конвертировать MM:SS в секунды"""
        try:
            parts = self.value.split(':')
            minutes = int(parts[0])
            seconds = int(parts[1])
            if seconds >= 60:
                return None
            return minutes * 60 + seconds
        except:
            return None


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


class SeriesSettingsDialog:
    """Диалог настроек сериала с чекбоксами и полями ввода времени"""
    
    def __init__(self, settings: Dict, db: VlcDatabase):
        self.settings = settings
        self.db = db
        self.result = None
        
        # Состояния чекбоксов (boolean флаги вместо виджетов CheckBox)
        self.autoplay_checked = bool(settings['autoplay'])
        self.skip_intro_checked = bool(settings['skip_intro'])
        self.skip_outro_checked = bool(settings['skip_outro'])
        
        # Поля ввода времени
        intro_start_mm = SeriesHelper.seconds_to_mmss(settings.get('intro_start', ''))
        intro_end_mm = SeriesHelper.seconds_to_mmss(settings.get('intro_end', ''))
        credits_mm = SeriesHelper.seconds_to_mmss(settings.get('credits_duration', ''))
        
        self.intro_start_input = TimeInput(intro_start_mm)
        self.intro_end_input = TimeInput(intro_end_mm)
        self.outro_input = TimeInput(credits_mm)
        
        # Текущий фокус (0-5: 3 чекбокса + 3 поля ввода)
        self.focus_index = 0
        self.widgets = [ # List of actual widgets that can be focused and interacted with
            self.intro_start_input,
            self.intro_end_input,
            self.outro_input
        ]
        
        # Стили
        self.style = Style.from_dict({
            'frame': 'bg:#000000 #00aaaa',
            'frame.label': 'bg:#000000 #ffffff bold',
            'checkbox': '#ffffff',
            'checkbox.selected': 'bg:#444444 #ffffff bold',
            'time': '#00ff00',
            'cursor': 'bg:#ffff00 #000000 bold',
            'disabled': '#666666',
            'button': '#ffffff',
            'button.focused': 'bg:#00aa00 #000000 bold',
            'label': '#aaaaaa',
        })
        
        # Layout
        self.layout = self._create_layout()
        
        # Key bindings
        self.kb = self._create_key_bindings()
        
        # Application
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=False
        )
    
    def _create_layout(self):
        """Создать layout диалога"""
        
        # Функция для получения стиля виджета
        def get_widget_style(index):
            return 'class:checkbox.selected' if index == self.focus_index else 'class:checkbox'
        
        # Создаём контент
        content = HSplit([
            Window(height=1),  # Отступ
            Window(
                FormattedTextControl(
                    lambda: FormattedText([
                        (get_widget_style(0), '[ ] ' if not self.autoplay_checked else '[X] '),
                        ('', 'Autoplay (автопродолжение следующей серии)')
                    ])
                ),
                height=1
            ),
            Window(height=1),
            Window(
                FormattedTextControl(
                    lambda: FormattedText([
                        (get_widget_style(1), '[ ] ' if not self.skip_intro_checked else '[X] '),
                        ('', 'Skip Intro (пропуск начальной заставки)')
                    ])
                ),
                height=1
            ),
            Window(
                FormattedTextControl(
                    lambda: FormattedText([
                        ('class:label', '    Intro Start: '),
                        (get_widget_style(3), '►' if self.focus_index == 3 else ' '),
                        ('', ' ')
                    ] + self.intro_start_input.get_formatted_text())
                ),
                height=1
            ),
            Window(
                FormattedTextControl(
                    lambda: FormattedText([
                        ('class:label', '    Intro End:   '),
                        (get_widget_style(4), '►' if self.focus_index == 4 else ' '),
                        ('', ' ')
                    ] + self.intro_end_input.get_formatted_text())
                ),
                height=1
            ),
            Window(height=1),
            Window(
                FormattedTextControl(
                    lambda: FormattedText([
                        (get_widget_style(2), '[ ] ' if not self.skip_outro_checked else '[X] '),
                        ('', 'Skip Outro (пропуск конечных титров)')
                    ])
                ),
                height=1
            ),
            Window(
                FormattedTextControl(
                    lambda: FormattedText([
                        ('class:label', '    Outro Duration: '),
                        (get_widget_style(5), '►' if self.focus_index == 5 else ' '),
                        ('', ' ')
                    ] + self.outro_input.get_formatted_text())
                ),
                height=1
            ),
            Window(height=1),
            Window(
                FormattedTextControl(
                    HTML('<b>Навигация:</b> ↑/↓ - выбор, Space - переключить чекбокс, '
                         '←/→/0-9 - редактировать время, Enter - сохранить, Esc - отмена')
                ),
                height=2
            ),
        ])
        
        # Frame с заголовком
        frame = Frame(
            content,
            title=f"Настройки сериала: {self.settings['prefix']}"
        )
        
        return Layout(frame)
    
    def _create_key_bindings(self):
        """Создать key bindings"""
        kb = KeyBindings()
        
        @kb.add('up')
        def _(event):
            if self.focus_index > 0:
                self.focus_index -= 1
        
        @kb.add('down')
        def _(event):
            if self.focus_index < 5:  # 0-5: всего 6 элементов (3 checkbox + 3 time inputs)
                self.focus_index += 1
        
        @kb.add('space')
        def _(event):
            # Переключение чекбокса (только для индексов 0, 1, 2)
            if self.focus_index == 0:
                self.autoplay_checked = not self.autoplay_checked
            elif self.focus_index == 1:
                self.skip_intro_checked = not self.skip_intro_checked
            elif self.focus_index == 2:
                self.skip_outro_checked = not self.skip_outro_checked
        
        @kb.add('left')
        def _(event):
            # Движение курсора в поле ввода времени (индексы 3, 4, 5)
            if self.focus_index == 3:
                self.intro_start_input.move_left()
            elif self.focus_index == 4:
                self.intro_end_input.move_left()
            elif self.focus_index == 5:
               self.outro_input.move_left()
        
        @kb.add('right')
        def _(event):
            # Движение курсора в поле ввода времени (индексы 3, 4, 5)
            if self.focus_index == 3:
                self.intro_start_input.move_right()
            elif self.focus_index == 4:
                self.intro_end_input.move_right()
            elif self.focus_index == 5:
                self.outro_input.move_right()
        
        # Ввод цифр 0-9
        for digit in '0123456789':
            @kb.add(digit)
            def _(event, d=digit):
                if self.focus_index == 3:
                    self.intro_start_input.input_digit(d)
                elif self.focus_index == 4:
                    self.intro_end_input.input_digit(d)
                elif self.focus_index == 5:
                    self.outro_input.input_digit(d)
        
        @kb.add('enter')
        def _(event):
            # Сохранить и выйти
            self._save_settings()
            event.app.exit()
        
        @kb.add('escape')
        def _(event):
            # Отмена
            event.app.exit()
        
        @kb.add('c-c')
        def _(event):
            # Ctrl+C - выход
            event.app.exit()
        
        return kb
    
    def _save_settings(self):
        """Сохранить настройки в БД"""
        autoplay = 1 if self.autoplay_checked else 0
        skip_intro = 1 if self.skip_intro_checked else 0
        skip_outro = 1 if self.skip_outro_checked else 0
        
        # Конвертируем времена
        intro_start_sec = None
        intro_end_sec = None
        credits_duration_sec = None
        
        if skip_intro:
            intro_start_sec = self.intro_start_input.to_seconds()
            intro_end_sec = self.intro_end_input.to_seconds()
            
            # Валидация
            if intro_start_sec and intro_end_sec and intro_end_sec <= intro_start_sec:
                print("\n❌ Ошибка: Intro End должен быть больше Intro Start")
                return
        
        if skip_outro:
            credits_duration_sec = self.outro_input.to_seconds()
        
        # Сохраняем
        self.db.save_series_settings(
            self.settings['prefix'],
            self.settings['suffix'],
            autoplay,
            skip_intro,
            skip_outro,
            intro_start_sec,
            intro_end_sec,
            credits_duration_sec
        )
        
        self.result = True
    
    def run(self):
        """Запустить диалог"""
        self.app.run()
        return self.result


class VideoMenu:
    """Класс для TUI меню выбора видео на prompt_toolkit"""
    
    def __init__(self, start_dir):
        self.current_dir = Path(start_dir).resolve()
        self.last_folder = None
        self.db = VlcDatabase()
        self.db.__enter__()
        self.selected_file = None
        self.items = []
        self.selected_index = 0
    
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
                items.append(("..", "Назад", False))
            
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
                    items.append((item.name, "DIR", True))
            
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
                    
                    items.append((video.name, f"{status_icon} {size_str}", False))
        
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
    
    def _create_menu_layout(self):
        """Создать layout меню"""
        settings = SeriesHelper.get_series_settings(self.db, self.current_dir)
        
        # Заголовок со статусом
        title_text = f"Выбор видео: {self.current_dir}"
        if settings:
            status_line = SeriesHelper.format_settings_status(settings)
            title_text = f"{status_line}\n\n{title_text}"
        
        # Список элементов
        def get_menu_items():
            result = []
            for i, (name, desc, is_dir) in enumerate(self.items):
                if i == self.selected_index:
                    prefix = '► '
                    style = 'class:selected'
                else:
                    prefix = '  '
                    style = 'class:item'
                
                result.append((style, f"{prefix}{name:<50} {desc}\n"))
            return FormattedText(result)
        
        content = HSplit([
            Window(
                FormattedTextControl(title_text),
                height=Dimension(min=3, max=5)
            ),
            Window(height=1, char='─'),
            Window(
                FormattedTextControl(get_menu_items),
                height=Dimension(min=10)
            ),
            Window(height=1, char='─'),
            Window(
                FormattedTextControl(
                    HTML('<b>Навигация:</b> ↑/↓ - выбор, Enter - открыть, '
                         'S - настройки сериала, Q/Esc - выход')
                ),
                height=2
            ),
        ])
        
        style = Style.from_dict({
            'selected': 'bg:#00aa00 #000000 bold',
            'item': '#ffffff',
        })
        
        return Layout(content), style
    
    def _create_key_bindings(self):
        """Создать key bindings для меню"""
        kb = KeyBindings()
        
        @kb.add('up')
        def _(event):
            if self.selected_index > 0:
                self.selected_index -= 1
        
        @kb.add('down')
        def _(event):
            if self.selected_index < len(self.items) - 1:
                self.selected_index += 1
        
        @kb.add('enter')
        def _(event):
            if not self.items:
                return
            
            name, _, is_dir = self.items[self.selected_index]
            
            if name == "..":
                self.last_folder = self.current_dir.name
                self.current_dir = self.current_dir.parent
                self.selected_index = 0
                self.items = self.get_items()
            elif is_dir:
                self.current_dir = self.current_dir / name
                self.selected_index = 0
                self.items = self.get_items()
            else:
                # Видео файл
                self.selected_file = str(self.current_dir / name)
                event.app.exit()
        
        @kb.add('s')
        @kb.add('S')
        def _(event):
            # Открыть настройки сериала
            event.app.exit()
            self.show_settings()
            # Перезапустить меню
            self.run()
        
        @kb.add('q')
        @kb.add('Q')
        @kb.add('escape')
        def _(event):
            self.selected_file = None
            event.app.exit()
        
        @kb.add('c-c')
        def _(event):
            self.selected_file = None
            event.app.exit()
        
        return kb
    
    def show_settings(self):
        """Показать диалог настроек сериала"""
        settings = SeriesHelper.get_series_settings(self.db, self.current_dir)
        
        if not settings:
            print("\n❌ Это не сериал\n")
            input("Нажмите Enter для продолжения...")
            return
        
        dialog = SeriesSettingsDialog(settings, self.db)
        dialog.run()
    
    def run(self):
        """Главный цикл меню"""
        self.items = self.get_items()
        
        if not self.items:
            print("\n❌ Директория пуста или нет видео файлов\n")
            return None
        
        layout, style = self._create_menu_layout()
        kb = self._create_key_bindings()
        
        app = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=True,
            mouse_support=False
        )
        
        app.run()
        
        return self.selected_file


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
