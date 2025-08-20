from app.database import engine
from sqlalchemy import text

def test_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connected successfully:", result.scalar())
    except Exception as e:
        print("❌ Database connection failed:", e)

if __name__ == "__main__":
    test_connection()
