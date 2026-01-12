# Доп

олнительные методы для video-menu-dialog-v2.py
# Добавить эти методы в класс VideoMenu после метода _validate_and_convert_time

def _edit_intro_times_curses(self, intro_start: str, intro_end: str):
    """
    Редактировать времена Intro через curses-виджет
    
    Args:
        intro_start: Начальное значение Intro Start в формате MM:SS
        intro_end: Начальное значение Intro End в формате MM:SS
    
    Returns:
        Tuple[str, str]: (intro_start, intro_end) или None если отменено
    """
    def curses_wrapper_intro(stdscr):
        widget = TimeInputWidget(stdscr, "Настройка времени Intro", intro_start, intro_end)
        return widget.run()
    
    try:
        result = curses.wrapper(curses_wrapper_intro)
        return result
    except Exception as e:
        self.d.msgbox(f"Ошибка при редактировании времени: {e}", height=8, width=60)
        return None

def _edit_outro_time_curses(self, credits: str):
    """
    Редактировать время Outro через curses-виджет
    
    Args:
        credits: Начальное значение в формате MM:SS
    
    Returns:
        str: время в MM:SS или None если отменено
    """
    def curses_wrapper_outro(stdscr):
        widget = SingleTimeInputWidget(stdscr, "Настройка времени Outro", credits)
        return widget.run()
    
    try:
        result = curses.wrapper(curses_wrapper_outro)
        return result
    except Exception as e:
        self.d.msgbox(f"Ошибка при редактировании времени: {e}", height=8, width=60)
        return None
