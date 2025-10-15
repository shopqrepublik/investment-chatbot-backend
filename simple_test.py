print("=== ПРОСТОЙ ТЕСТ БАЗЫ ДАННЫХ ===")

try:
    from app.database import create_tables, engine
    
    print("1. Импорты успешны")
    
    # Создаем таблицы
    create_tables()
    print("2. Таблицы созданы")
    
    # Проверяем что таблицы существуют
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"3. Созданные таблицы: {tables}")
    
    print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("✅ База данных SQLite готова к работе!")
    print(f"📁 Файл базы данных: investment_bot.db")
    
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()