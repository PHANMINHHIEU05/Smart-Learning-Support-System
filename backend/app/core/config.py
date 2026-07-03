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

    # ── Internal Service Authentication ──
    AI_WORKER_INTERNAL_TOKEN: str = "dev-internal-token"

    # ── Vocabulary Providers ──
    MERRIAM_WEBSTER_LEARNERS_API_KEY: str = ""
    MERRIAM_WEBSTER_LEARNERS_API_BASE_URL: str = "https://www.dictionaryapi.com/api/v3/references/learners/json"
    DICTIONARY_API_BASE_URL: str = "https://api.dictionaryapi.dev"
    TRANSLATION_API_BASE_URL: str = "https://api.mymemory.translated.net"
    VOCABULARY_HTTP_TIMEOUT_SECONDS: float = 6.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
