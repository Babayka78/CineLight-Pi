#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для системы конфигурации
"""

import sys
import os
import tempfile
from pathlib import Path

# Добавляем родительскую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Py.config.config_manager import ConfigManager, ConfigType, ConfigCategory


def test_basic_operations():
    """Тест базовых операций"""
    print("=== Тест базовых операций ===")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # Тест get/set
        result = config.set('test_key', 'test_value', ConfigType.STRING, 
                           ConfigCategory.GENERAL, 'Тестовая настройка')
        assert result, "Ошибка установки настройки"
        
        value = config.get('test_key')
        assert value == 'test_value', f"Ожидается 'test_value', получено '{value}'"
        
        # Тест несуществующего ключа
        value = config.get('nonexistent_key', 'default')
        assert value == 'default', f"Ожидается 'default', получено '{value}'"
        
        print("✓ Базовые операции: OK")
        return True
    except AssertionError as e:
        print(f"✗ Базовые операции: {e}")
        return False
    finally:
        db_path.unlink()


def test_categories():
    """Тест категорий"""
    print("\n=== Тест категорий ===")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # Проверка всех категорий
        for category in ConfigCategory:
            configs = config.get_category(category)
            assert isinstance(configs, dict), f"Категория {category} не является словарём"
            print(f"  {category.value}: {len(configs)} настроек")
        
        # Проверка CEC настроек
        cec_keys = config.get_category(ConfigCategory.CEC)
        assert 'cec_key_play' in cec_keys, "cec_key_play не найден"
        assert cec_keys['cec_key_play'] == 0, "Неверное значение cec_key_play"
        
        print("✓ Категории: OK")
        return True
    except AssertionError as e:
        print(f"✗ Категории: {e}")
        return False
    finally:
        db_path.unlink()


def test_types():
    """Тест типов значений"""
    print("\n=== Тест типов значений ===")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # STRING
        config.set('test_string', 'hello', ConfigType.STRING, ConfigCategory.GENERAL, '')
        assert config.get('test_string') == 'hello'
        
        # INT
        config.set('test_int', '42', ConfigType.INT, ConfigCategory.GENERAL, '')
        assert config.get('test_int') == 42
        assert isinstance(config.get('test_int'), int)
        
        # BOOL
        config.set('test_bool_true', 'true', ConfigType.BOOL, ConfigCategory.GENERAL, '')
        assert config.get('test_bool_true') is True
        
        config.set('test_bool_false', 'false', ConfigType.BOOL, ConfigCategory.GENERAL, '')
        assert config.get('test_bool_false') is False
        
        # PATH
        config.set('test_path', '/tmp/test', ConfigType.PATH, ConfigCategory.GENERAL, '')
        assert isinstance(config.get('test_path'), Path)
        
        print("✓ Типы значений: OK")
        return True
    except AssertionError as e:
        print(f"✗ Типы значений: {e}")
        return False
    finally:
        db_path.unlink()


def test_export_import():
    """Тест экспорта/импорта"""
    print("\n=== Тест экспорта/импорта ===")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    export_file = Path('/tmp/test_config_export.json')
    
    try:
        config = ConfigManager(db_path)
        
        # Изменить значение
        config.set('test_key', 'original', ConfigType.STRING, ConfigCategory.GENERAL, '')
        
        # Экспорт
        assert config.export_config(export_file), "Ошибка экспорта"
        assert export_file.exists(), "Файл экспорта не создан"
        
        # Изменить значение
        config.set('test_key', 'modified', ConfigType.STRING, ConfigCategory.GENERAL, '')
        assert config.get('test_key') == 'modified'
        
        # Импорт
        assert config.import_config(export_file), "Ошибка импорта"
        assert config.get('test_key') == 'original', "Значение не восстановлено"
        
        print("✓ Экспорт/импорт: OK")
        return True
    except AssertionError as e:
        print(f"✗ Экспорт/импорт: {e}")
        return False
    finally:
        db_path.unlink()
        if export_file.exists():
            export_file.unlink()


def test_delete():
    """Тест удаления"""
    print("\n=== Тест удаления ===")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # Создать настройку
        config.set('test_delete', 'value', ConfigType.STRING, ConfigCategory.GENERAL, '')
        assert config.get('test_delete') == 'value'
        
        # Удалить
        assert config.delete('test_delete'), "Ошибка удаления"
        assert config.get('test_delete') is None, "Настройка не удалена"
        
        print("✓ Удаление: OK")
        return True
    except AssertionError as e:
        print(f"✗ Удаление: {e}")
        return False
    finally:
        db_path.unlink()


def test_get_all():
    """Тест получения всех настроек"""
    print("\n=== Тест получения всех настроек ===")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = Path(f.name)
    
    try:
        config = ConfigManager(db_path)
        
        # Получить все настройки
        all_configs = config.get_all()
        assert isinstance(all_configs, dict), "Не является словарём"
        assert len(all_configs) > 0, "Нет настроек"
        
        # Проверить структуру
        for key, data in all_configs.items():
            assert 'value' in data, f"Нет 'value' в {key}"
            assert 'type' in data, f"Нет 'type' в {key}"
            assert 'category' in data, f"Нет 'category' в {key}"
            assert 'description' in data, f"Нет 'description' в {key}"
        
        print(f"  Всего настроек: {len(all_configs)}")
        print("✓ Получение всех настроек: OK")
        return True
    except AssertionError as e:
        print(f"✗ Получение всех настроек: {e}")
        return False
    finally:
        db_path.unlink()


def main():
    """Главная функция"""
    print("Тесты системы конфигурации\n")
    
    results = []
    results.append(test_basic_operations())
    results.append(test_categories())
    results.append(test_types())
    results.append(test_export_import())
    results.append(test_delete())
    results.append(test_get_all())
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✓ Все тесты пройдены! ({passed}/{total})")
        return 0
    else:
        print(f"✗ Некоторые тесты не пройдены ({passed}/{total})")
        return 1


if __name__ == "__main__":
    sys.exit(main())