#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Простой тест для проверки основной функциональности vlc_db.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from vlc_db import VlcDatabase


def test_basic_functionality():
    """Тест основной функциональности базы данных"""
    print("Тестирование основной функциональности vlc_db.py...")
    
    # Создаем временную базу данных
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_path = Path(temp_db.name)
    
    try:
        # Создаем экземпляр базы данных с временным путем
        db = VlcDatabase(db_path)
        
        # Инициализируем базу данных
        with db as db_instance:
            success = db_instance.init_db()
            if not success:
                print("❌ Ошибка инициализации базы данных")
                return False
            print("✅ База данных инициализирована")
        
        # Тестируем сохранение и получение данных о воспроизведении
        filename = "test_movie.mp4"
        position = 150
        duration = 600
        percent = 25
        
        with db as db_instance:
            # Сохраняем прогресс
            success = db_instance.save_playback(filename, position, duration, percent)
            if not success:
                print("❌ Ошибка сохранения прогресса")
                return False
            print("✅ Прогресс сохранен")
            
            # Получаем сохраненные данные
            result = db_instance.get_playback(filename)
            if result is None:
                print("❌ Ошибка получения прогресса")
                return False
            
            retrieved_position, retrieved_duration, retrieved_percent, _, _ = result
            if retrieved_position != position or retrieved_duration != duration or retrieved_percent != percent:
                print("❌ Неверные данные при получении прогресса")
                return False
            print("✅ Прогресс корректно получен")
            
            # Проверяем получение процента
            retrieved_percent = db_instance.get_playback_percent(filename)
            if retrieved_percent != percent:
                print("❌ Неверный процент при получении")
                return False
            print("✅ Процент корректно получен")
            
            # Проверяем получение статуса
            status = db_instance.get_playback_status(filename)
            if status != 'partial':
                print(f"❌ Неверный статус: ожидается 'partial', получено '{status}'")
                return False
            print("✅ Статус корректно получен")
        
        # Тестируем работу с настройками сериалов
        series_prefix = "Test.Series.S01"
        series_suffix = "720p.mkv"
        
        with db as db_instance:
            # Сохраняем настройки
            success = db_instance.save_series_settings(
                series_prefix, series_suffix,
                autoplay=True, skip_intro=True, skip_outro=False,
                intro_start=30, intro_end=90, credits_duration=120
            )
            if not success:
                print("❌ Ошибка сохранения настроек сериала")
                return False
            print("✅ Настройки сериала сохранены")
            
            # Получаем настройки
            settings = db_instance.get_series_settings(series_prefix, series_suffix)
            if settings is None:
                print("❌ Ошибка получения настроек сериала")
                return False
            
            autoplay, skip_intro, skip_outro, intro_start, intro_end, credits_duration = settings
            if int(autoplay) != 1 or int(skip_intro) != 1 or int(skip_outro) != 0:
                print("❌ Неверные булевы настройки сериала")
                return False
            print("✅ Булевы настройки сериала корректны")
        
        print("🎉 Все тесты пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Произошла ошибка: {e}")
        return False
    finally:
        # Удаляем временный файл
        if db_path.exists():
            db_path.unlink()


def test_cli_commands():
    """Тест CLI команд"""
    print("\nТестирование CLI команд...")
    
    # Сохраняем оригинальные аргументы
    original_argv = sys.argv
    
    try:
        # Тестируем инициализацию
        sys.argv = ['vlc_db.py', 'init']
        from vlc_db import main as cli_main
        result = cli_main()
        if result == 0:
            print("✅ CLI команда инициализации работает")
        else:
            print("❌ CLI команда инициализации не работает")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Ошибка при тестировании CLI: {e}")
        return False
    finally:
        # Восстанавливаем оригинальные аргументы
        sys.argv = original_argv


if __name__ == "__main__":
    print("Запуск тестов для vlc_db.py с пулом соединений\n")
    
    success1 = test_basic_functionality()
    success2 = test_cli_commands()
    
    if success1 and success2:
        print("\n🎉 Все тесты прошли успешно!")
        sys.exit(0)
    else:
        print("\n❌ Один или несколько тестов не прошли")
        sys.exit(1)
