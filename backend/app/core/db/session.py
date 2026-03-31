from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://Yuussuke:bulagpt@postgres:5432/bulagpt"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)