#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI интерфейс для управления конфигурацией
"""

import sys
import json
from pathlib import Path

# Добавляем родительскую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config_manager import ConfigManager, ConfigType, ConfigCategory


def print_usage():
    """Вывод справки"""
    print("""
Использование: config_cli.py <команда> [аргументы]

Команды:
  get <key>                          - Получить значение настройки
  set <key> <value> <type> <cat>    - Установить значение настройки
  list [category]                    - Список всех настроек
  export <file>                      - Экспорт конфигурации в JSON
  import <file>                      - Импорт конфигурации из JSON
  delete <key>                       - Удалить настройку
  help                               - Эта справка

Типы (type):
  string, int, bool, path

Категории (cat):
  general, cec, media, ui

Примеры:
  config_cli.py get cec_device
  config_cli.py set cec_device /dev/cec0 string cec
  config_cli.py list cec
  config_cli.py export config_backup.json
  config_cli.py import config_backup.json
""")


def cli_get(config: ConfigManager, args: list) -> int:
    """Получить значение настройки"""
    if len(args) < 1:
        print("ERROR: Укажите ключ", file=sys.stderr)
        return 1
    
    key = args[0]
    value = config.get(key)
    
    if value is None:
        print(f"Настройка '{key}' не найдена", file=sys.stderr)
        return 1
    
    print(value)
    return 0


def cli_set(config: ConfigManager, args: list) -> int:
    """Установить значение настройки"""
    if len(args) < 4:
        print("ERROR: Укажите key value type category [description]", file=sys.stderr)
        return 1
    
    key = args[0]
    value = args[1]
    type_str = args[2]
    category_str = args[3]
    description = args[4] if len(args) > 4 else ""
    
    try:
        type_ = ConfigType(type_str)
        category = ConfigCategory(category_str)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    
    if config.set(key, value, type_, category, description):
        print(f"✓ Настройка '{key}' установлена: {value}")
        return 0
    else:
        print(f"✗ Ошибка установки настройки '{key}'", file=sys.stderr)
        return 1


def cli_list(config: ConfigManager, args: list) -> int:
    """Список всех настроек"""
    if len(args) > 0:
        category_str = args[0]
        try:
            category = ConfigCategory(category_str)
            configs = config.get_category(category)
            print(f"\n=== Настройки категории: {category_str} ===\n")
        except ValueError:
            print(f"ERROR: Неизвестная категория '{category_str}'", file=sys.stderr)
            return 1
    else:
        configs = config.get_all()
        print(f"\n=== Все настройки ===\n")
    
    for key, data in configs.items():
        if isinstance(data, dict):
            print(f"{key}: {data['value']} ({data['type']})")
            if data.get('description'):
                print(f"  └─ {data['description']}")
        else:
            print(f"{key}: {data}")
    
    print()
    return 0


def cli_export(config: ConfigManager, args: list) -> int:
    """Экспорт конфигурации"""
    if len(args) < 1:
        print("ERROR: Укажите файл для экспорта", file=sys.stderr)
        return 1
    
    file_path = Path(args[0])
    
    if config.export_config(file_path):
        print(f"✓ Конфигурация экспортирована в {file_path}")
        return 0
    else:
        print(f"✗ Ошибка экспорта", file=sys.stderr)
        return 1


def cli_import(config: ConfigManager, args: list) -> int:
    """Импорт конфигурации"""
    if len(args) < 1:
        print("ERROR: Укажите файл для импорта", file=sys.stderr)
        return 1
    
    file_path = Path(args[0])
    
    if not file_path.exists():
        print(f"ERROR: Файл не найден: {file_path}", file=sys.stderr)
        return 1
    
    if config.import_config(file_path):
        print(f"✓ Конфигурация импортирована из {file_path}")
        return 0
    else:
        print(f"✗ Ошибка импорта", file=sys.stderr)
        return 1


def cli_delete(config: ConfigManager, args: list) -> int:
    """Удалить настройку"""
    if len(args) < 1:
        print("ERROR: Укажите ключ для удаления", file=sys.stderr)
        return 1
    
    key = args[0]
    
    if config.delete(key):
        print(f"✓ Настройка '{key}' удалена")
        return 0
    else:
        print(f"✗ Ошибка удаления настройки '{key}'", file=sys.stderr)
        return 1


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    # Путь к БД
    db_path = Path("Py/config/vlc_media.db")
    if not db_path.exists():
        db_path = Path("vlc_media.db")
    
    config = ConfigManager(db_path)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    commands = {
        'get': cli_get,
        'set': cli_set,
        'list': cli_list,
        'export': cli_export,
        'import': cli_import,
        'delete': cli_delete,
        'help': lambda c, a: (print_usage(), 0)[1],
    }
    
    if command in commands:
        return commands[command](config, args)
    else:
        print(f"ERROR: Неизвестная команда '{command}'", file=sys.stderr)
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())
