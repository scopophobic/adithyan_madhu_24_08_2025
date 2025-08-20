import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    def __init__(self):
        print("Loaded environment variables:")
        print(f"  POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
        print(f"  POSTGRES_PASSWORD: {os.getenv('POSTGRES_PASSWORD')}")
        print(f"  POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
        print(f"  POSTGRES_SERVER: {os.getenv('POSTGRES_SERVER')}")
        print(f"  POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}")

    PROJECT_NAME: str = "Data Logger API"
    POSTGRES_USER: str = os.getenv("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", 5432)

    DATABASE_URL: str = (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
        f"{POSTGRES_SERVER}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )

settings = Settings()
