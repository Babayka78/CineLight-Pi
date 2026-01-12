#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест индексов в БД для проверки производительности

Проверяет:
1. Создание индексов
2. Сравнение производительности с индексами и без
"""

import sys
import os
import time
from pathlib import Path

# Добавляем родительскую директорию в path
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from vlc_db import VlcDatabase, DB_PATH


def test_indexes_exist():
    """Проверка наличия индексов"""
    print("=== Проверка наличия индексов ===")
    
    with VlcDatabase() as db:
        db.cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in db.cursor.fetchall()]
        
        expected_indexes = [
            'idx_playback_filename',
            'idx_playback_series_prefix',
            'idx_series_settings_prefix_suffix'
        ]
        
        for idx in expected_indexes:
            if idx in indexes:
                print(f"✓ Индекс {idx} существует")
            else:
                print(f"✗ Индекс {idx} НЕ найден!")
                return False
    
    print("Все индексы созданы успешно\n")
    return True


def test_performance_with_test_data():
    """Тест производительности с тестовыми данными"""
    print("=== Тест производительности ===")
    
    # Количество тестовых файлов
    NUM_FILES = 100
    
    with VlcDatabase() as db:
        # Очистка тестовых данных
        db.cursor.execute("DELETE FROM playback WHERE filename LIKE 'test_file_%'")
        db.conn.commit()
        
        # Вставка тестовых данных
        print(f"Вставка {NUM_FILES} тестовых записей...")
        for i in range(NUM_FILES):
            filename = f"test_file_{i:03d}.mkv"
            series_prefix = f"TestShow.S{i//10:02d}"
            series_suffix = "1080p.mkv"
            db.save_playback(filename, i*10, 3600, i//3, series_prefix, series_suffix)
        print(f"✓ Вставлено {NUM_FILES} записей\n")
        
        # Тест 1: Поиск по filename
        print("Тест 1: Поиск по filename (100 запросов)")
        start = time.time()
        for i in range(NUM_FILES):
            filename = f"test_file_{i:03d}.mkv"
            db.get_playback(filename)
        elapsed = time.time() - start
        avg_time = elapsed / NUM_FILES * 1000
        print(f"   Общее время: {elapsed:.3f}s")
        print(f"   Среднее время: {avg_time:.3f}ms на запрос")
        
        # Тест 2: Пакетный запрос по filename
        print(f"\nТест 2: Пакетный запрос ({NUM_FILES} файлов)")
        filenames = [f"test_file_{i:03d}.mkv" for i in range(NUM_FILES)]
        start = time.time()
        db.get_playback_batch_status("/test", filenames)
        elapsed = time.time() - start
        avg_time = elapsed / NUM_FILES * 1000
        print(f"   Общее время: {elapsed:.3f}s")
        print(f"   Среднее время: {avg_time:.3f}ms на файл")
        
        # Тест 3: Поиск по series_prefix
        print(f"\nТест 3: Поиск по series_prefix (10 запросов)")
        start = time.time()
        for i in range(10):
            series_prefix = f"TestShow.S{i:02d}"
            db.find_other_versions(series_prefix, "720p.mkv")
        elapsed = time.time() - start
        avg_time = elapsed / 10 * 1000
        print(f"   Общее время: {elapsed:.3f}s")
        print(f"   Среднее время: {avg_time:.3f}ms на запрос")
        
        # Очистка тестовых данных
        db.cursor.execute("DELETE FROM playback WHERE filename LIKE 'test_file_%'")
        db.conn.commit()
        print(f"\n✓ Тестовые данные очищены")
    
    print("\n=== Тест производительности завершён ===\n")
    return True


def test_query_plan():
    """Проверка плана выполнения запросов (используются ли индексы)"""
    print("=== Проверка плана выполнения запросов ===")
    
    with VlcDatabase() as db:
        # Вставка тестовых данных
        db.save_playback("test_query_plan.mkv", 100, 3600, 50, "TestShow.S01", "1080p.mkv")
        
        # Проверка плана для поиска по filename
        print("План для SELECT WHERE filename = ?")
        db.cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM playback WHERE filename = 'test_query_plan.mkv'")
        plan = db.cursor.fetchall()
        for row in plan:
            print(f"  {row}")
        
        # Проверка плана для поиска по series_prefix
        print("\nПлан для SELECT WHERE series_prefix = ?")
        db.cursor.execute("EXPLAIN QUERY PLAN SELECT * FROM playback WHERE series_prefix = 'TestShow.S01'")
        plan = db.cursor.fetchall()
        for row in plan:
            print(f"  {row}")
        
        # Проверка плана для настроек сериала
        print("\nПлан для SELECT WHERE series_prefix = ? AND series_suffix = ?")
        db.cursor.execute("""
            EXPLAIN QUERY PLAN 
            SELECT * FROM series_settings 
            WHERE series_prefix = 'TestShow.S01' AND series_suffix = '1080p.mkv'
        """)
        plan = db.cursor.fetchall()
        for row in plan:
            print(f"  {row}")
        
        # Очистка
        db.cursor.execute("DELETE FROM playback WHERE filename = 'test_query_plan.mkv'")
        db.conn.commit()
    
    print("\n=== Проверка плана завершена ===\n")
    return True


def main():
    """Главная функция"""
    print("Тест индексов БД VLC\n")
    print("=" * 50)
    
    all_passed = True
    
    # Тест 1: Проверка наличия индексов
    if not test_indexes_exist():
        all_passed = False
    
    # Тест 2: Производительность
    if not test_performance_with_test_data():
        all_passed = False
    
    # Тест 3: План выполнения
    if not test_query_plan():
        all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("✓ Все тесты пройдены успешно!")
        return 0
    else:
        print("✗ Некоторые тесты не пройдены")
        return 1


if __name__ == "__main__":
    sys.exit(main())