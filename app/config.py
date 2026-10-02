from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/chat_api"
    cors_origins: list[str] = ["*"]

    api_key: str

    llm_base_url: str = "http://localhost:1234/v1"
    llm_api_key: str = "lm-studio"
    llm_model: str = "google/gemma-4-e4b"
    llm_timeout_s: float = 30.0

    llm_fallback_base_url: str = "http://localhost:11434/v1"
    llm_fallback_api_key: str = "ollama"
    llm_fallback_model: str = "llama3.2"

    llm_fallback2_base_url: str = "http://localhost:11434/v1"
    llm_fallback2_api_key: str = "ollama"
    llm_fallback2_model: str = "llama3.2:1b"

settings = Settings()
