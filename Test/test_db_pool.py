#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тесты для vlc_db.py с пулом соединений
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from vlc_db import VlcDatabase, get_connection_pool, ConnectionPool


class TestVlcDatabase(unittest.TestCase):
    """Тесты для базы данных VLC"""
    
    def setUp(self):
        """Подготовка теста - создание временной базы данных"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = Path(self.temp_db.name)
        
        # Создаем экземпляр базы данных с временным путем
        self.db = VlcDatabase(self.db_path)
        
        # Инициализируем базу данных
        with self.db as db:
            db.init_db()
    
    def tearDown(self):
        """Очистка после теста"""
        if self.db_path.exists():
            self.db_path.unlink()
    
    def test_connection_pool_creation(self):
        """Тест создания пула соединений"""
        pool = get_connection_pool()
        self.assertIsInstance(pool, ConnectionPool)
        self.assertEqual(pool.min_connections, 2)
        self.assertLessEqual(pool.current_size, pool.max_connections)
    
    def test_database_initialization(self):
        """Тест инициализации базы данных"""
        with self.db as db:
            # Проверяем, что таблицы существуют
            cursor = db.conn.cursor()
            
            # Проверяем таблицу playback
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='playback'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Проверяем таблицу series_settings
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='series_settings'")
            self.assertIsNotNone(cursor.fetchone())
    
    def test_save_and_get_playback(self):
        """Тест сохранения и получения прогресса воспроизведения"""
        filename = "test_video.mp4"
        position = 100
        duration = 1000
        percent = 10
        
        with self.db as db:
            # Сохраняем прогресс
            success = db.save_playback(filename, position, duration, percent)
            self.assertTrue(success)
            
            # Получаем сохраненные данные
            result = db.get_playback(filename)
            self.assertIsNotNone(result)
            self.assertEqual(result[0], position)  # position
            self.assertEqual(result[1], duration)  # duration
            self.assertEqual(result[2], percent)   # percent
    
    def test_playback_percent(self):
        """Тест получения процента воспроизведения"""
        filename = "test_video2.mp4"
        percent = 25
        
        with self.db as db:
            # Сохраняем данные
            db.save_playback(filename, 250, 1000, percent)
            
            # Получаем процент
            retrieved_percent = db.get_playback_percent(filename)
            self.assertEqual(retrieved_percent, percent)
    
    def test_playback_status(self):
        """Тест получения статуса воспроизведения"""
        # Тест для статуса 'partial' (1-89%)
        filename_partial = "partial_video.mp4"
        with self.db as db:
            db.save_playback(filename_partial, 500, 1000, 45)  # 45% - статус 'partial'
            status = db.get_playback_status(filename_partial)
            self.assertEqual(status, 'partial')
            
            # Тест для статуса 'watched' (90-100%)
            filename_watched = "watched_video.mp4"
            db.save_playback(filename_watched, 950, 1000, 95)  # 95% - статус 'watched'
            status = db.get_playback_status(filename_watched)
            self.assertEqual(status, 'watched')
            
            # Тест для статуса None (0%)
            filename_not_started = "not_started_video.mp4"
            db.save_playback(filename_not_started, 0, 1000, 0)  # 0% - статус None
            status = db.get_playback_status(filename_not_started)
            self.assertIsNone(status)
    
    def test_series_settings(self):
        """Тест сохранения и получения настроек сериалов"""
        series_prefix = "Test.Series.S01"
        series_suffix = "1080p.mkv"
        
        with self.db as db:
            # Сохраняем настройки
            success = db.save_series_settings(series_prefix, series_suffix, 
                                            autoplay=True, skip_intro=True, skip_outro=False,
                                            intro_start=30, intro_end=90, credits_duration=120)
            self.assertTrue(success)
            
            # Получаем настройки
            settings = db.get_series_settings(series_prefix, series_suffix)
            self.assertIsNotNone(settings)
            self.assertEqual(settings[0], 1)  # autoplay
            self.assertEqual(settings[1], 1)  # skip_intro
            self.assertEqual(settings[2], 0)  # skip_outro
            self.assertEqual(settings[3], '30')  # intro_start
            self.assertEqual(settings[4], '90')  # intro_end
            self.assertEqual(settings[5], '120')  # credits_duration
    
    def test_batch_operations(self):
        """Тест пакетных операций"""
        with self.db as db:
            # Сохраняем несколько записей
            test_files = [("test1.mp4", 100, 1000, 10), 
                         ("test2.mp4", 500, 1000, 50),
                         ("test3.mp4", 900, 1000, 90)]
            
            for filename, pos, dur, pct in test_files:
                db.save_playback(filename, pos, dur, pct)
            
            # Тестируем пакетное получение статусов
            filenames = [f[0] for f in test_files]
            statuses = db.get_playback_batch_status("", filenames)
            
            self.assertEqual(len(statuses), len(filenames))
            self.assertIn("test1.mp4", statuses)
            self.assertIn("test2.mp4", statuses)
            self.assertIn("test3.mp4", statuses)
    
    def test_concurrent_access(self):
        """Тест многопоточного доступа к базе данных"""
        import threading
        import time
        
        results = []
        
        def access_db(thread_id):
            """Функция для доступа к базе данных из потока"""
            try:
                with self.db as db:
                    filename = f"thread_video_{thread_id}.mp4"
                    success = db.save_playback(filename, thread_id * 100, 1000, thread_id * 10)
                    if success:
                        percent = db.get_playback_percent(filename)
                        results.append((thread_id, percent))
            except Exception as e:
                results.append((thread_id, f"Error: {str(e)}"))
        
        # Создаем и запускаем несколько потоков
        threads = []
        for i in range(5):
            thread = threading.Thread(target=access_db, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Проверяем, что все потоки успешно выполнили операции
        self.assertEqual(len(results), 5)
        for thread_id, result in results:
            self.assertIsInstance(result, int)  # percent должен быть числом


def run_tests():
    """Запуск тестов"""
    print("Запуск тестов для vlc_db.py с пулом соединений...")
    
    # Создаем тестовый набор
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestVlcDatabase)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Возвращаем результат
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)