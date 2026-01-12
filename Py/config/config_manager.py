#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Менеджер конфигурации для VLC проекта
Работает с таблицей config в базе данных
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Any, Dict
from enum import Enum
from datetime import datetime


class ConfigType(Enum):
    """Типы значений конфигурации"""
    STRING = 'string'
    INT = 'int'
    BOOL = 'bool'
    PATH = 'path'


class ConfigCategory(Enum):
    """Категории конфигурации"""
    GENERAL = 'general'
    CEC = 'cec'
    MEDIA = 'media'
    UI = 'ui'


class ConfigManager:
    """Менеджер конфигурации"""
    
    def __init__(self, db_path: Path):
        """Инициализация менеджера конфигурации
        
        Args:
            db_path: путь к базе данных
        """
        self.db_path = db_path
        self._init_db()
        self._load_defaults()
    
    def _init_db(self) -> bool:
        """Создание таблицы config если её нет"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS config (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        type TEXT,
                        category TEXT,
                        description TEXT,
                        modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка инициализации таблицы config: {e}", file=__import__('sys').stderr)
            return False
    
    def _load_defaults(self) -> None:
        """Загрузка значений по умолчанию"""
        defaults = [
            # General settings
            ('db_path', str(self.db_path), ConfigType.STRING, ConfigCategory.GENERAL, 
             'Путь к базе данных'),
            ('log_dir', 'Log', ConfigType.PATH, ConfigCategory.GENERAL, 
             'Директория для логов'),
            ('auto_save_interval', '60', ConfigType.INT, ConfigCategory.GENERAL, 
             'Интервал автосохранения (сек)'),
            ('debug_mode', 'false', ConfigType.BOOL, ConfigCategory.GENERAL, 
             'Режим отладки'),
            
            # CEC settings
            ('cec_device', '/dev/cec1', ConfigType.STRING, ConfigCategory.CEC, 
             'Устройство CEC'),
            ('cec_key_play', '0', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки OK (Play/Pause)'),
            ('cec_key_pause', '0', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки PAUSE'),
            ('cec_key_up', '1', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки UP'),
            ('cec_key_down', '2', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки DOWN'),
            ('cec_key_left', '3', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки LEFT'),
            ('cec_key_right', '4', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки RIGHT'),
            ('cec_key_red', '68', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки RED'),
            ('cec_key_green', '113', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки GREEN'),
            ('cec_key_yellow', '116', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки YELLOW'),
            ('cec_key_blue', '217', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки BLUE'),
            ('cec_key_0', '32', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 0'),
            ('cec_key_1', '33', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 1'),
            ('cec_key_2', '34', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 2'),
            ('cec_key_3', '35', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 3'),
            ('cec_key_4', '36', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 4'),
            ('cec_key_5', '37', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 5'),
            ('cec_key_6', '38', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 6'),
            ('cec_key_7', '39', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 7'),
            ('cec_key_8', '40', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 8'),
            ('cec_key_9', '41', ConfigType.INT, ConfigCategory.CEC, 
             'Код кнопки 9'),
            
            # Media settings
            ('media_dir', '/media', ConfigType.PATH, ConfigCategory.MEDIA, 
             'Директория с медиа файлами'),
            ('video_extensions', 'avi,mp4,mkv,mov,wmv,flv', ConfigType.STRING, ConfigCategory.MEDIA, 
             'Расширения видеофайлов'),
            
            # UI settings
            ('menu_height', '20', ConfigType.INT, ConfigCategory.UI, 
             'Высота меню'),
            ('menu_width', '60', ConfigType.INT, ConfigCategory.UI, 
             'Ширина меню'),
        ]
        
        for key, value, type_, category, description in defaults:
            self.set(key, value, type_, category, description, overwrite=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение по ключу
        
        Args:
            key: ключ настройки
            default: значение по умолчанию если ключ не найден
        
        Returns:
            Значение настройки или default
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value, type FROM config WHERE key = ?", (key,))
                result = cursor.fetchone()
                
                if result is None:
                    return default
                
                value_str, type_str = result
                return self._parse_value(value_str, type_str)
        except sqlite3.Error as e:
            print(f"Ошибка получения настройки {key}: {e}", file=__import__('sys').stderr)
            return default
    
    def set(self, key: str, value: Any, type_: ConfigType, 
            category: ConfigCategory, description: str, 
            overwrite: bool = True) -> bool:
        """Установить значение настройки
        
        Args:
            key: ключ настройки
            value: значение
            type_: тип значения
            category: категория
            description: описание
            overwrite: перезаписывать если существует
        
        Returns:
            True при успехе, False при ошибке
        """
        try:
            value_str = str(value)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if overwrite:
                    cursor.execute("""
                        INSERT INTO config (key, value, type, category, description, modified_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            value = ?,
                            type = ?,
                            category = ?,
                            description = ?,
                            modified_at = ?
                    """, (key, value_str, type_.value, category.value, description, datetime.now(),
                          value_str, type_.value, category.value, description, datetime.now()))
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO config (key, value, type, category, description)
                        VALUES (?, ?, ?, ?, ?)
                    """, (key, value_str, type_.value, category.value, description))
                
                conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка установки настройки {key}: {e}", file=__import__('sys').stderr)
            return False
    
    def get_category(self, category: ConfigCategory) -> Dict[str, Any]:
        """Получить все настройки категории
        
        Args:
            category: категория настроек
        
        Returns:
            Словарь {key: value}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value, type FROM config WHERE category = ?", 
                             (category.value,))
                
                result = {}
                for key, value_str, type_str in cursor.fetchall():
                    result[key] = self._parse_value(value_str, type_str)
                
                return result
        except sqlite3.Error as e:
            print(f"Ошибка получения категории {category}: {e}", file=__import__('sys').stderr)
            return {}
    
    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """Получить все настройки с метаданными
        
        Returns:
            Словарь {key: {value, type, category, description, modified_at}}
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT key, value, type, category, description, modified_at
                    FROM config
                    ORDER BY category, key
                """)
                
                result = {}
                for row in cursor.fetchall():
                    key, value_str, type_str, category, description, modified_at = row
                    result[key] = {
                        'value': self._parse_value(value_str, type_str),
                        'type': type_str,
                        'category': category,
                        'description': description,
                        'modified_at': modified_at
                    }
                
                return result
        except sqlite3.Error as e:
            print(f"Ошибка получения всех настроек: {e}", file=__import__('sys').stderr)
            return {}
    
    def delete(self, key: str) -> bool:
        """Удалить настройку
        
        Args:
            key: ключ настройки
        
        Returns:
            True при успехе, False при ошибке
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM config WHERE key = ?", (key,))
                conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка удаления настройки {key}: {e}", file=__import__('sys').stderr)
            return False
    
    def export_config(self, file_path: Path) -> bool:
        """Экспорт конфигурации в JSON
        
        Args:
            file_path: путь к файлу экспорта
        
        Returns:
            True при успехе, False при ошибке
        """
        try:
            config_data = self.get_all()
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False, default=str)
            return True
        except Exception as e:
            print(f"Ошибка экспорта конфигурации: {e}", file=__import__('sys').stderr)
            return False
    
    def import_config(self, file_path: Path, overwrite: bool = True) -> bool:
        """Импорт конфигурации из JSON
        
        Args:
            file_path: путь к файлу импорта
            overwrite: перезаписывать существующие настройки
        
        Returns:
            True при успехе, False при ошибке
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for key, data in config_data.items():
                value = data['value']
                type_ = ConfigType(data['type'])
                category = ConfigCategory(data['category'])
                description = data['description']
                
                self.set(key, value, type_, category, description, overwrite=overwrite)
            
            return True
        except Exception as e:
            print(f"Ошибка импорта конфигурации: {e}", file=__import__('sys').stderr)
            return False
    
    def _parse_value(self, value_str: str, type_str: str) -> Any:
        """Преобразовать строку в значение нужного типа
        
        Args:
            value_str: строковое значение
            type_str: тип значения
        
        Returns:
            Преобразованное значение
        """
        try:
            if type_str == ConfigType.INT.value:
                return int(value_str)
            elif type_str == ConfigType.BOOL.value:
                return value_str.lower() in ('true', '1', 'yes')
            elif type_str == ConfigType.PATH.value:
                return Path(value_str)
            else:  # STRING
                return value_str
        except (ValueError, TypeError):
            return value_str


if __name__ == "__main__":
    # Тест
    import sys
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("vlc_media.db")
    
    config = ConfigManager(db_path)
    
    print("=== Тест ConfigManager ===")
    print(f"\nGeneral settings:")
    for key, value in config.get_category(ConfigCategory.GENERAL).items():
        print(f"  {key}: {value}")
    
    print(f"\nCEC settings:")
    for key, value in config.get_category(ConfigCategory.CEC).items():
        print(f"  {key}: {value}")
    
    print(f"\n✓ Тест пройден!")