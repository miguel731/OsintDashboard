import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./osint.db")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
    HIBP_API_KEY = os.getenv("HIBP_API_KEY", "")
    SPIDERFOOT_URL = os.getenv("SPIDERFOOT_URL", "")
    TZ = os.getenv("TZ", "UTC")

settings = Settings()