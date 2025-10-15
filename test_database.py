from app.database import create_tables, SessionLocal, engine

def test_database_connection():
    try:
        # Пытаемся подключиться к БД
        with engine.connect() as connection:
            print("✅ Успешное подключение к PostgreSQL!")
        
        # Создаем таблицы
        create_tables()
        print("✅ Таблицы успешно созданы!")
        
        # Проверяем существование таблиц
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Созданные таблицы: {tables}")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")

if __name__ == "__main__":
    test_database_connection()