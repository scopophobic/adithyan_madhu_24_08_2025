#!/usr/bin/env python3
"""
Test script for app/config.py
"""

def test_config():
    try:
        # Import the config
        from app.config import settings
        
        print("✅ Config imported successfully!")
        print(f"Project Name: {settings.PROJECT_NAME}")
        print(f"Database URL: {settings.DATABASE_URL}")
        
        # Test environment variables
        print("\nEnvironment Variables:")
        print(f"POSTGRES_USER: {settings.POSTGRES_USER}")
        print(f"POSTGRES_PASSWORD: {'*' * len(settings.POSTGRES_PASSWORD) if settings.POSTGRES_PASSWORD else 'None'}")
        print(f"POSTGRES_DB: {settings.POSTGRES_DB}")
        print(f"POSTGRES_SERVER: {settings.POSTGRES_SERVER}")
        print(f"POSTGRES_PORT: {settings.POSTGRES_PORT}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_config()


