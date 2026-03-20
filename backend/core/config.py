"""
core/config.py
--------------
Reads environment variables from the .env file.
Using a class means the rest of the app imports settings
from one place instead of calling os.environ everywhere.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # PostgreSQL connection string
    # Format: postgresql://username:password@host:port/database_name
    DATABASE_URL: str = "postgresql://smarthire:smarthire123@localhost:5432/smarthire"

    # Secret key used to sign JWT tokens.
    # Change this to a long random string in production.
    SECRET_KEY: str = "change-this-to-a-long-random-secret-in-production"

    # JWT algorithm and token lifetime
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    class Config:
        # If a .env file exists in the project root, load variables from it.
        # This means you can override any value without editing this file.
        env_file = ".env"


settings = Settings()
