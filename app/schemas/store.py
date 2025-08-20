import os
from sqlalchemy import create_engine


LOCAL_DB_URL = "postgresql://store_admin:store1978@localhost:5432/resturant_db"
DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DB_URL)

engine = create_engine(DATABASE_URL)