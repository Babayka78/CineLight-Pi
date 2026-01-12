# План разработки системы конфигурации

**Дата:** 12.01.2026  
**Статус:** План

---

## Цель

Создать систему конфигурации для управления настройками проекта:
1. Общие настройки (пути к БД, логи, медиа)
2. Настройки CEC (кнопки пульта)
3. Тестирование на отдельных модулях БЕЗ подключения к основному проекту

---

## Этап 1: Структура БД для конфигурации

### Таблица `config`

```sql
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT,
    type TEXT,  -- 'string', 'int', 'bool', 'path'
    category TEXT,  -- 'general', 'cec', 'media', 'ui'
    description TEXT,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Примеры настроек

| key | value | type | category | description |
|-----|-------|------|----------|-------------|
| db_path | /path/to/vlc_media.db | path | general | Путь к базе данных |
| log_dir | Log | path | general | Директория для логов |
| media_dir | /media | path | media | Директория с медиа |
| cec_device | /dev/cec1 | string | cec | Устройство CEC |
| cec_key_play | 0 | int | cec | Код кнопки OK |
| cec_key_pause | 0 | int | cec | Код кнопки OK (toggle) |
| cec_key_up | 1 | int | cec | Код кнопки UP |
| cec_key_down | 2 | int | cec | Код кнопки DOWN |
| cec_key_left | 3 | int | cec | Код кнопки LEFT |
| cec_key_right | 4 | int | cec | Код кнопки RIGHT |
| cec_key_red | 68 | int | cec | Код кнопки RED |
| cec_key_green | 113 | int | cec | Код кнопки GREEN |
| cec_key_yellow | 116 | int | cec | Код кнопки YELLOW |
| cec_key_blue | 217 | int | cec | Код кнопки BLUE |
| cec_key_0 | 32 | int | cec | Код кнопки 0 |
| cec_key_1 | 33 | int | cec | Код кнопки 1 |
| ... | ... | ... | ... | ... |
| auto_save_interval | 60 | int | general | Интервал автосохранения (сек) |
| debug_mode | false | bool | general | Режим отладки |

---

## Этап 2: Python модуль для конфигурации

### Файл: `Py/config_manager.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
from pathlib import Path
from typing import Optional, Any, Dict
from enum import Enum

class ConfigType(Enum):
    STRING = 'string'
    INT = 'int'
    BOOL = 'bool'
    PATH = 'path'

class ConfigCategory(Enum):
    GENERAL = 'general'
    CEC = 'cec'
    MEDIA = 'media'
    UI = 'ui'

class ConfigManager:
    """Менеджер конфигурации"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()
        self._load_defaults()
    
    def _init_db(self):
        """Создание таблицы config"""
        # ... код создания таблицы ...
    
    def _load_defaults(self):
        """Загрузка значений по умолчанию"""
        defaults = {
            # General
            ('db_path', ConfigType.PATH, ConfigCategory.GENERAL, 
             'Путь к базе данных', str(self.db_path)),
            ('log_dir', ConfigType.PATH, ConfigCategory.GENERAL, 
             'Директория для логов', 'Log'),
            ('auto_save_interval', ConfigType.INT, ConfigCategory.GENERAL, 
             'Интервал автосохранения (сек)', 60),
            ('debug_mode', ConfigType.BOOL, ConfigCategory.GENERAL, 
             'Режим отладки', False),
            
            # CEC
            ('cec_device', ConfigType.STRING, ConfigCategory.CEC, 
             'Устройство CEC', '/dev/cec1'),
            ('cec_key_play', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки OK', 0),
            ('cec_key_pause', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки PAUSE', 0),
            ('cec_key_up', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки UP', 1),
            ('cec_key_down', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки DOWN', 2),
            # ... остальные кнопки ...
        }
        
        for key, type_, category, desc, value in defaults:
            self.set(key, value, type_, category, desc, overwrite=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу"""
        # ... код получения ...
    
    def set(self, key: str, value: Any, type_: ConfigType, 
            category: ConfigCategory, description: str, 
            overwrite: bool = True) -> bool:
        """Установить значение"""
        # ... код установки ...
    
    def get_category(self, category: ConfigCategory) -> Dict[str, Any]:
        """Получить все настройки категории"""
        # ... код получения категории ...
    
    def export_config(self, file_path: Path) -> bool:
        """Экспорт конфигурации в JSON"""
        # ... код экспорта ...
    
    def import_config(self, file_path: Path) -> bool:
        """Импорт конфигурации из JSON"""
        # ... код импорта ...
```

---

## Этап 3: CLI интерфейс

### Файл: `Py/config_cli.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from config_manager import ConfigManager, ConfigType, ConfigCategory

def cli_get(key: str):
    """Получить значение настройки"""
    # ...

def cli_set(key: str, value: str, type_: str, category: str, description: str):
    """Установить значение настройки"""
    # ...

def cli_list(category: str = None):
    """Список всех настроек"""
    # ...

def cli_export(file_path: str):
    """Экспорт конфигурации"""
    # ...

def cli_import(file_path: str):
    """Импорт конфигурации"""
    # ...

def main():
    import sys
    if len(sys.argv) < 2:
        print("Использование: config_cli.py <command> [args]")
        print("Команды: get, set, list, export, import")
        return 1
    
    command = sys.argv[1]
    # ... обработка команд ...
```

---

## Этап 4: TUI интерфейс для конфигурации

### Файл: `Test/config_tui.py` (тестовый модуль)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TUI интерфейс для редактирования конфигурации
Тестовый модуль - НЕ подключается к основному проекту
"""

import curses
from config_manager import ConfigManager, ConfigCategory

class ConfigTUI:
    """TUI интерфейс для конфигурации"""
    
    def __init__(self, stdscr, db_path: str):
        self.stdscr = stdscr
        self.config = ConfigManager(Path(db_path))
        self.current_category = ConfigCategory.GENERAL
        self.running = True
    
    def run(self):
        """Запуск TUI"""
        curses.curs_set(0)
        self.stdscr.clear()
        
        while self.running:
            self._draw_menu()
            self._handle_input()
        
        curses.endwin()
    
    def _draw_menu(self):
        """Отрисовка меню"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Заголовок
        title = f"Конфигурация: {self.current_category.value}"
        self.stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Список настроек
        configs = self.config.get_category(self.current_category)
        y = 2
        for key, value in configs.items():
            self.stdscr.addstr(y, 2, f"{key}: {value}")
            y += 1
        
        # Подсказки
        help_text = "[Q] Выход  [TAB] Смена категории  [E] Редактировать"
        self.stdscr.addstr(height - 1, 2, help_text)
        
        self.stdscr.refresh()
    
    def _handle_input(self):
        """Обработка ввода"""
        key = self.stdscr.getch()
        
        if key == ord('q') or key == ord('Q'):
            self.running = False
        elif key == 9:  # TAB
            self._next_category()
        elif key == ord('e') or key == ord('E'):
            self._edit_config()
    
    def _next_category(self):
        """Переключение категории"""
        categories = list(ConfigCategory)
        idx = categories.index(self.current_category)
        self.current_category = categories[(idx + 1) % len(categories)]
    
    def _edit_config(self):
        """Редактирование настройки"""
        # ... диалог редактирования ...

def main(stdscr):
    import sys
    if len(sys.argv) < 2:
        print("Использование: config_tui.py <db_path>")
        return 1
    
    db_path = sys.argv[1]
    tui = ConfigTUI(stdscr, db_path)
    tui.run()
    return 0

if __name__ == "__main__":
    import curses
    sys.exit(curses.wrapper(main))
```

---

## Этап 5: Тестирование

### Тестовый файл: `Test/test_config.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для системы конфигурации
"""

import tempfile
import os
from pathlib import Path
from Py.config_manager import ConfigManager, ConfigType, ConfigCategory

def test_basic_operations():
    """Тест базовых операций"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # Тест get/set
        config.set('test_key', 'test_value', ConfigType.STRING, 
                   ConfigCategory.GENERAL, 'Тестовая настройка')
        assert config.get('test_key') == 'test_value'
        
        # Тест категории
        general = config.get_category(ConfigCategory.GENERAL)
        assert 'test_key' in general
        
        print("✓ Базовые операции: OK")
    finally:
        db_path.unlink()

def test_cec_keys():
    """Тест CEC кнопок"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # Проверка дефолтных значений CEC
        cec_keys = config.get_category(ConfigCategory.CEC)
        assert 'cec_key_play' in cec_keys
        assert cec_keys['cec_key_play'] == 0
        
        print("✓ CEC кнопки: OK")
    finally:
        db_path.unlink()

def test_export_import():
    """Тест экспорта/импорта"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    export_file = Path('/tmp/test_config_export.json')
    
    try:
        config = ConfigManager(db_path)
        
        # Экспорт
        assert config.export_config(export_file)
        assert export_file.exists()
        
        # Импорт
        config.set('test_key', 'modified', ConfigType.STRING, 
                   ConfigCategory.GENERAL, 'Тест')
        assert config.import_config(export_file)
        
        print("✓ Экспорт/импорт: OK")
    finally:
        db_path.unlink()
        if export_file.exists():
            export_file.unlink()

if __name__ == "__main__":
    test_basic_operations()
    test_cec_keys()
    test_export_import()
    print("\n✓ Все тесты пройдены!")
```

---

## Этап 6: Интеграция (только после тестирования)

**ВНИМАНИЕ:** Интеграция с основным проектом ТОЛЬКО после успешного тестирования!

1. Добавить `config_manager.py` в основной проект
2. Обновить `vlc_db.py` для использования `ConfigManager`
3. Обновить bash скрипты для чтения конфигурации
4. Обновить CEC обработку для чтения кнопок из конфигурации

---

## Порядок реализации

1. ✅ Создать структуру БД (таблица `config`)
2. ✅ Реализовать `Py/config_manager.py`
3. ✅ Реализовать `Py/config_cli.py`
4. ✅ Реализовать `Test/config_tui.py` (отдельный модуль)
5. ✅ Создать `Test/test_config.py`
6. ✅ Протестировать всё на отдельной БД
7. ⏸️ Интеграция с основным проектом (после тестирования)

---

## Требования к тестированию

- Все модули работают автономно
- Используется отдельная тестовая БД
- Тесты покрывают все основные функции
- TUI интерфейс работает без подключения к основному проекту
- Экспорт/импорт конфигурации работает корректно