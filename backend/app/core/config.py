from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──
    DATABASE_URL: str

    # ── Supabase Auth ──
    SUPABASE_JWT_SECRET: str
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""

    # ── App ──
    APP_NAME: str = "Smart Learning Support System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── CORS ──
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Server ──
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
