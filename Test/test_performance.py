#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тест производительности пула соединений
"""

import os
import sys
import time
import tempfile
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from vlc_db import VlcDatabase


def test_performance():
    """Тест производительности пула соединений"""
    print("Тестирование производительности пула соединений...")
    
    # Создаем временную базу данных
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_path = Path(temp_db.name)
    
    try:
        # Инициализируем базу данных
        db = VlcDatabase(db_path)
        with db as db_instance:
            db_instance.init_db()
        
        # Тестируем производительность с пулом соединений
        print("Тестирование с пулом соединений...")
        start_time = time.time()
        
        # Выполняем множество операций с базой данных
        for i in range(100):
            filename = f"test_video_{i}.mp4"
            position = i * 10
            duration = 1000
            percent = i % 100
            
            with db as db_instance:
                # Сохраняем и получаем данные
                db_instance.save_playback(filename, position, duration, percent)
                result = db_instance.get_playback_percent(filename)
                status = db_instance.get_playback_status(filename)
        
        end_time = time.time()
        pool_time = end_time - start_time
        
        print(f"Время с пулом соединений: {pool_time:.3f} секунд")
        print(f"Среднее время на операцию: {pool_time/100*1000:.2f} мс")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при тестировании производительности: {e}")
        return False
    finally:
        # Удаляем временный файл
        if db_path.exists():
            db_path.unlink()


if __name__ == "__main__":
    success = test_performance()
    if success:
        print("\n✅ Тест производительности успешно пройден!")
    else:
        print("\n❌ Тест производительности не пройден!")
        sys.exit(1)
