#!/usr/bin/env python3
"""
time_input_widget.py - Curses виджет для ввода времени в формате MM:SS
Версия: 1.0.0
"""

import curses
from typing import Optional, Tuple


class TimeInputWidget:
    """
    Curses-виджет для ввода времени в формате MM:SS
    
    Features:
    - Overwrite mode (замена цифр)
    - Highlighted cursor (желтый фон + черный текст)
    - Navigation with arrows (←/→)
    - Validation (секунды 0-59)
    """
    
    def __init__(self, stdscr, label: str = "Enter time", intro_start: str = "00:00", intro_end: str = "00:00"):
        """
        Инициализация виджета
        
        Args:
            stdscr: curses screen object
            label: Заголовок виджета
            intro_start: Начальное значение для Intro Start
            intro_end: Начальное значение для Intro End
        """
        self.stdscr = stdscr
        self.label = label
        
        # Два поля ввода
        self.intro_start = list(intro_start)  # ["0", "0", ":", "0", "0"]
        self.intro_end = list(intro_end)
        
        # Текущее поле (0 = start, 1 = end)
        self.current_field = 0
        
        # Позиция курсора в текущем поле (0, 1, 3, 4 - пропускаем ':')
        self.cursor_pos = 0
        
        # Инициализация цветов
        self._init_colors()
        
    def _init_colors(self):
        """Инициализировать цветовые пары"""
        curses.start_color()
        curses.use_default_colors()
        
        # Цветовые пары
        curses.init_pair(1, curses.COLOR_WHITE, -1)      # Обычный текст
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)  # Курсор
        curses.init_pair(3, curses.COLOR_CYAN, -1)       # Label
        curses.init_pair(4, curses.COLOR_GREEN, -1)      # Активное поле
        curses.init_pair(5, curses.COLOR_WHITE, -1)      # Неактивное поле
    
    def _get_cursor_char_index(self) -> int:
        """Получить индекс символа в строке (0, 1, 3, 4)"""
        positions = [0, 1, 3, 4]  # Пропускаем ':' на позиции 2
        return positions[self.cursor_pos] if self.cursor_pos < len(positions) else 0
    
    def _move_cursor_left(self):
        """Переместить курсор влево"""
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
    
    def _move_cursor_right(self):
        """Переместить курсор вправо"""
        if self.cursor_pos < 3:  # 4 позиции (0-3)
            self.cursor_pos += 1
    
    def _input_digit(self, digit: str):
        """Ввести цифру в текущую позицию (режим замены)"""
        if not digit.isdigit():
            return
        
        current_value = self.intro_start if self.current_field == 0 else self.intro_end
        char_idx = self._get_cursor_char_index()
        
        # Валидация для секунд
        if self.cursor_pos == 2:  # Первая цифра секунд (позиция 3 в строке)
            if int(digit) > 5:  # Секунды не могут начинаться с цифры > 5
                curses.beep()
                return
        
        current_value[char_idx] = digit
        self._move_cursor_right()
    
    def _draw(self):
        """Отрисовать виджет"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Рамка
        start_y = height // 2 - 5
        start_x = width // 2 - 30
        
        try:
            # Заголовок
            self.stdscr.addstr(start_y, start_x, "═" * 60, curses.color_pair(3))
            self.stdscr.addstr(start_y + 1, start_x + 2, self.label, curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(start_y + 2, start_x, "═" * 60, curses.color_pair(3))
            
            # Intro Start
            label_y = start_y + 4
            self.stdscr.addstr(label_y, start_x + 2, "Intro Start:", curses.color_pair(1))
            
            # Отрисовка значения Intro Start
            value_x = start_x + 18
            for i, char in enumerate(self.intro_start):
                if self.current_field == 0 and i == self._get_cursor_char_index():
                    # Курсор
                    self.stdscr.addstr(label_y, value_x + i, char, 
                                      curses.color_pair(2) | curses.A_BOLD)
                else:
                    color = curses.color_pair(4) if self.current_field == 0 else curses.color_pair(5)
                    self.stdscr.addstr(label_y, value_x + i, char, color)
            
            # Intro End
            label_y += 2
            self.stdscr.addstr(label_y, start_x + 2, "Intro End:", curses.color_pair(1))
            
            # Отрисовка значения Intro End
            for i, char in enumerate(self.intro_end):
                if self.current_field == 1 and i == self._get_cursor_char_index():
                    # Курсор
                    self.stdscr.addstr(label_y, value_x + i, char,
                                      curses.color_pair(2) | curses.A_BOLD)
                else:
                    color = curses.color_pair(4) if self.current_field == 1 else curses.color_pair(5)
                    self.stdscr.addstr(label_y, value_x + i, char, color)
            
            # Подсказки
            help_y = start_y + 9
            self.stdscr.addstr(help_y, start_x, "─" * 60, curses.color_pair(1))
            help_text = "↑/↓: switch field  ←/→: move  0-9: input  Enter: OK  Esc: Cancel"
            self.stdscr.addstr(help_y + 1, start_x + 2, help_text, curses.color_pair(1))
            
        except curses.error:
            # Игнорируем ошибки отрисовки (если терминал слишком мал)
            pass
        
        self.stdscr.refresh()
    
    def _validate(self) -> bool:
        """Валидация введенных значений"""
        # Проверка формата
        for value in [self.intro_start, self.intro_end]:
            if len(value) != 5 or value[2] != ':':
                return False
            
            try:
                mins = int(''.join(value[0:2]))
                secs = int(''.join(value[3:5]))
                
                if secs >= 60:
                    return False
            except ValueError:
                return False
        
        # Проверка: intro_end > intro_start
        start_secs = self._mmss_to_seconds(''.join(self.intro_start))
        end_secs = self._mmss_to_seconds(''.join(self.intro_end))
        
        if end_secs <= start_secs:
            return False
        
        return True
    
    def _mmss_to_seconds(self, mmss: str) -> int:
        """Конвертировать MM:SS в секунды"""
        parts = mmss.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    
    def run(self) -> Optional[Tuple[str, str]]:
        """
        Запустить виджет
        
        Returns:
            Tuple[str, str]: (intro_start, intro_end) в формате MM:SS или None если отменено
        """
        curses.curs_set(0)  # Скрыть системный курсор
        
        while True:
            self._draw()
            
            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                return None
            
            # Обработка клавиш
            if key == curses.KEY_UP:
                # Переключение на предыдущее поле
                if self.current_field > 0:
                    self.current_field -= 1
                    self.cursor_pos = 0
            
            elif key == curses.KEY_DOWN:
                # Переключение на следующее поле
                if self.current_field < 1:
                    self.current_field += 1
                    self.cursor_pos = 0
            
            elif key == curses.KEY_LEFT:
                self._move_cursor_left()
            
            elif key == curses.KEY_RIGHT:
                self._move_cursor_right()
            
            elif ord('0') <= key <= ord('9'):
                self._input_digit(chr(key))
            
            elif key == 10 or key == curses.KEY_ENTER:  # Enter
                if self._validate():
                    intro_start = ''.join(self.intro_start)
                    intro_end = ''.join(self.intro_end)
                    return (intro_start, intro_end)
                else:
                    # Показать ошибку
                    height, width = self.stdscr.getmaxyx()
                    error_msg = "Error: Invalid time or End <= Start"
                    self.stdscr.addstr(height - 2, (width - len(error_msg)) // 2, 
                                      error_msg, curses.color_pair(1) | curses.A_REVERSE)
                    self.stdscr.refresh()
                    curses.napms(1500)  # Показать на 1.5 сек
            
            elif key == 27:  # Esc
                return None
            
            elif key == ord('q') or key == ord('Q'):
                return None


class SingleTimeInputWidget:
    """
    Упрощенный виджет для ввода одного времени (для Outro Duration)
    """
    
    def __init__(self, stdscr, label: str = "Enter time", initial_value: str = "00:00"):
        self.stdscr = stdscr
        self.label = label
        self.value = list(initial_value)
        self.cursor_pos = 0
        self._init_colors()
    
    def _init_colors(self):
        """Инициализировать цветовые пары"""
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
    
    def _get_cursor_char_index(self) -> int:
        positions = [0, 1, 3, 4]
        return positions[self.cursor_pos] if self.cursor_pos < len(positions) else 0
    
    def _move_cursor_left(self):
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
    
    def _move_cursor_right(self):
        if self.cursor_pos < 3:
            self.cursor_pos += 1
    
    def _input_digit(self, digit: str):
        if not digit.isdigit():
            return
        
        char_idx = self._get_cursor_char_index()
        
        if self.cursor_pos == 2:
            if int(digit) > 5:
                curses.beep()
                return
        
        self.value[char_idx] = digit
        self._move_cursor_right()
    
    def _draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        start_y = height // 2 - 3
        start_x = width // 2 - 25
        
        try:
            self.stdscr.addstr(start_y, start_x, "═" * 50, curses.color_pair(3))
            self.stdscr.addstr(start_y + 1, start_x + 2, self.label, 
                              curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(start_y + 2, start_x, "═" * 50, curses.color_pair(3))
            
            label_y = start_y + 4
            self.stdscr.addstr(label_y, start_x + 2, "Duration:", curses.color_pair(1))
            
            value_x = start_x + 15
            for i, char in enumerate(self.value):
                if i == self._get_cursor_char_index():
                    self.stdscr.addstr(label_y, value_x + i, char,
                                      curses.color_pair(2) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(label_y, value_x + i, char, curses.color_pair(4))
            
            help_y = start_y + 7
            self.stdscr.addstr(help_y, start_x, "─" * 50, curses.color_pair(1))
            help_text = "←/→: move  0-9: input  Enter: OK  Esc: Cancel"
            self.stdscr.addstr(help_y + 1, start_x + 2, help_text, curses.color_pair(1))
            
        except curses.error:
            pass
        
        self.stdscr.refresh()
    
    def run(self) -> Optional[str]:
        """
        Запустить виджет
        
        Returns:
            str: время в формате MM:SS или None если отменено
        """
        curses.curs_set(0)
        
        while True:
            self._draw()
            
            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                return None
            
            if key == curses.KEY_LEFT:
                self._move_cursor_left()
            elif key == curses.KEY_RIGHT:
                self._move_cursor_right()
            elif ord('0') <= key <= ord('9'):
                self._input_digit(chr(key))
            elif key == 10 or key == curses.KEY_ENTER:
                return ''.join(self.value)
            elif key == 27 or key == ord('q') or key == ord('Q'):
                return None




class AllTimesInputWidget:
    """
    Виджет для редактирования всех времен сразу:
    - Intro Start
    - Intro End  
    - Outro Duration
    """
    
    def __init__(self, stdscr, label: str = "Настройка времени", 
                 intro_start: str = "00:00", intro_end: str = "00:00", outro: str = "00:00"):
        self.stdscr = stdscr
        self.label = label
        
        # Три поля ввода
        self.intro_start = list(intro_start)
        self.intro_end = list(intro_end)
        self.outro = list(outro)
        
        # Текущее поле (0 = intro_start, 1 = intro_end, 2 = outro)
        self.current_field = 0
        
        # Позиция курсора в текущем поле
        self.cursor_pos = 0
        
        self._init_colors()
    
    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, -1)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_YELLOW)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_WHITE, -1)
    
    def _get_cursor_char_index(self) -> int:
        positions = [0, 1, 3, 4]
        return positions[self.cursor_pos] if self.cursor_pos < len(positions) else 0
    
    def _move_cursor_left(self):
        if self.cursor_pos > 0:
            self.cursor_pos -= 1
    
    def _move_cursor_right(self):
        if self.cursor_pos < 3:
            self.cursor_pos += 1
    
    def _input_digit(self, digit: str):
        if not digit.isdigit():
            return
        
        # Выбираем текущее поле
        if self.current_field == 0:
            current_value = self.intro_start
        elif self.current_field == 1:
            current_value = self.intro_end
        else:
            current_value = self.outro
        
        char_idx = self._get_cursor_char_index()
        
        # Валидация секунд
        if self.cursor_pos == 2:
            if int(digit) > 5:
                curses.beep()
                return
        
        current_value[char_idx] = digit
        self._move_cursor_right()
    
    def _draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        start_y = height // 2 - 6
        start_x = width // 2 - 30
        
        try:
            # Заголовок
            self.stdscr.addstr(start_y, start_x, "═" * 60, curses.color_pair(3))
            self.stdscr.addstr(start_y + 1, start_x + 2, self.label, 
                              curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(start_y + 2, start_x, "═" * 60, curses.color_pair(3))
            
            # Intro Start
            label_y = start_y + 4
            self.stdscr.addstr(label_y, start_x + 2, "Intro Start:", curses.color_pair(1))
            
            value_x = start_x + 18
            for i, char in enumerate(self.intro_start):
                if self.current_field == 0 and i == self._get_cursor_char_index():
                    self.stdscr.addstr(label_y, value_x + i, char,
                                      curses.color_pair(2) | curses.A_BOLD)
                else:
                    color = curses.color_pair(4) if self.current_field == 0 else curses.color_pair(5)
                    self.stdscr.addstr(label_y, value_x + i, char, color)
            
            # Intro End
            label_y += 2
            self.stdscr.addstr(label_y, start_x + 2, "Intro End:", curses.color_pair(1))
            
            for i, char in enumerate(self.intro_end):
                if self.current_field == 1 and i == self._get_cursor_char_index():
                    self.stdscr.addstr(label_y, value_x + i, char,
                                      curses.color_pair(2) | curses.A_BOLD)
                else:
                    color = curses.color_pair(4) if self.current_field == 1 else curses.color_pair(5)
                    self.stdscr.addstr(label_y, value_x + i, char, color)
            
            # Outro Duration
            label_y += 2
            self.stdscr.addstr(label_y, start_x + 2, "Outro Duration:", curses.color_pair(1))
            
            for i, char in enumerate(self.outro):
                if self.current_field == 2 and i == self._get_cursor_char_index():
                    self.stdscr.addstr(label_y, value_x + i, char,
                                      curses.color_pair(2) | curses.A_BOLD)
                else:
                    color = curses.color_pair(4) if self.current_field == 2 else curses.color_pair(5)
                    self.stdscr.addstr(label_y, value_x + i, char, color)
            
            # Подсказки
            help_y = start_y + 11
            self.stdscr.addstr(help_y, start_x, "─" * 60, curses.color_pair(1))
            help_text = "↑/↓: switch  ←/→: move  0-9: input  Enter: OK  Esc: Cancel"
            self.stdscr.addstr(help_y + 1, start_x + 2, help_text, curses.color_pair(1))
            
        except curses.error:
            pass
        
        self.stdscr.refresh()
    
    def _validate(self) -> bool:
        """Валидация: Intro End > Intro Start"""
        try:
            start_secs = self._mmss_to_seconds(''.join(self.intro_start))
            end_secs = self._mmss_to_seconds(''.join(self.intro_end))
            
            if end_secs <= start_secs:
                return False
            
            return True
        except:
            return False
    
    def _mmss_to_seconds(self, mmss: str) -> int:
        parts = mmss.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    
    def run(self) -> Optional[Tuple[str, str, str]]:
        """
        Запустить виджет
        
        Returns:
            Tuple[str, str, str]: (intro_start, intro_end, outro) или None если отменено
        """
        curses.curs_set(0)
        
        while True:
            self._draw()
            
            try:
                key = self.stdscr.getch()
            except KeyboardInterrupt:
                return None
            
            if key == curses.KEY_UP:
                if self.current_field > 0:
                    self.current_field -= 1
                    self.cursor_pos = 0
            
            elif key == curses.KEY_DOWN:
                if self.current_field < 2:
                    self.current_field += 1
                    self.cursor_pos = 0
            
            elif key == curses.KEY_LEFT:
                self._move_cursor_left()
            
            elif key == curses.KEY_RIGHT:
                self._move_cursor_right()
            
            elif ord('0') <= key <= ord('9'):
                self._input_digit(chr(key))
            
            elif key == 10 or key == curses.KEY_ENTER:
                if self._validate():
                    intro_start = ''.join(self.intro_start)
                    intro_end = ''.join(self.intro_end)
                    outro = ''.join(self.outro)
                    return (intro_start, intro_end, outro)
                else:
                    height, width = self.stdscr.getmaxyx()
                    error_msg = "Error: Intro End must be > Intro Start"
                    self.stdscr.addstr(height - 2, (width - len(error_msg)) // 2,
                                      error_msg, curses.color_pair(1) | curses.A_REVERSE)
                    self.stdscr.refresh()
                    curses.napms(1500)
            
            elif key == 27 or key == ord('q') or key == ord('Q'):
                return None


def test_widget(stdscr):
    """Тестовая функция"""
    widget = TimeInputWidget(stdscr, "Test Intro Times", "01:23", "02:45")
    result = widget.run()
    
    stdscr.clear()
    if result:
        stdscr.addstr(0, 0, f"Result: Start={result[0]}, End={result[1]}")
    else:
        stdscr.addstr(0, 0, "Cancelled")
    stdscr.addstr(1, 0, "Press any key to exit...")
    stdscr.getch()


if __name__ == '__main__':
    # Тест виджета
    curses.wrapper(test_widget)
