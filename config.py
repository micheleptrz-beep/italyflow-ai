# -*- coding: utf-8 -*-
"""
ItalyFlow AI - Configuration v3.1
Aggiunto: Visual Identity settings
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # === Branding ===
    APP_NAME: str = "ItalyFlow AI"
    APP_TAGLINE: str = "Compliance, engineered for export."
    APP_VERSION: str = "3.1.0"

    # === Core ===
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # === API Keys ===
    GOOGLE_API_KEY: str
    SECRET_KEY: str = "change-me-in-production"

    # === Database ===
    DATABASE_URL: str = "sqlite:///./italyflow.db"

    # === Gemini / LLM ===
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    GEMINI_TIMEOUT_S: int = 30
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_MAX_OUTPUT_TOKENS: int = 4000
    GEMINI_TEMPERATURE: float = 0.1

    # === Upload & Limits ===
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_CONTENT_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
    ]
    RATE_LIMIT_PER_MINUTE: int = 10
    MAX_MARKETS_PER_AUDIT: int = 10

    # === Dashboard (v3.0) ===
    DASHBOARD_CACHE_TTL_S: int = 60
    SPARKLINE_DAYS: int = 30
    HEATMAP_MIN_AUDITS: int = 1

    # === Product Categories ===
    PRODUCT_CATEGORIES: list[str] = [
        "Olio & Condimenti",
        "Vino & Spirits",
        "Pasta & Cereali",
        "Formaggi & Latticini",
        "Salumi & Carni",
        "Conserve & Sottoli",
        "Dolci & Bakery",
        "Frutta & Verdura",
        "Caffe & Bevande",
        "Altro",
    ]

    # === Visual Identity (v3.1) ===
    VISUAL_CACHE_TTL_S: int = 300  # 5 min cache per asset selection
    HERO_MOBILE_WIDTH: int = 720
    HERO_TABLET_WIDTH: int = 1080
    HERO_DESKTOP_WIDTH: int = 1920
    HERO_4K_WIDTH: int = 3840
    HERO_QUALITY: int = 80  # JPEG/WebP quality
    HERO_BLUR_PLACEHOLDER_WIDTH: int = 32  # tiny blur-up
    ENABLE_PARALLAX: bool = True
    ENABLE_SEASONAL_ROTATION: bool = True
    ENABLE_TIME_AWARENESS: bool = True

    # === CORS ===
    ALLOWED_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
