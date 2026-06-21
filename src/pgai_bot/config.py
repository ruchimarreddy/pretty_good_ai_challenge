from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Twilio credentials
    twilio_account_sid: str = Field(alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(alias="TWILIO_FROM_NUMBER")

    # Public webhook URL, usually from ngrok
    public_base_url: str = Field(alias="PUBLIC_BASE_URL")

    # Challenge target number
    target_number: str = Field(default="+18054398008", alias="TARGET_NUMBER")

    # Twilio voice settings
    call_language: str = Field(default="en-US", alias="CALL_LANGUAGE")
    voice_name: str = Field(default="Polly.Joanna", alias="VOICE_NAME")
    female_voice_name: str = Field(default="Polly.Joanna", alias="FEMALE_VOICE_NAME")
    male_voice_name: str = Field(default="Polly.Matthew", alias="MALE_VOICE_NAME")

    # Free/local patient-agent settings using Ollama
    llm_backend: str = Field(default="ollama", alias="LLM_BACKEND")
    ollama_url: str = Field(default="http://localhost:11434", alias="OLLAMA_URL")
    ollama_model: str = Field(default="llama3.1:latest", alias="OLLAMA_MODEL")
    llm_timeout_seconds: int = Field(default=18, alias="LLM_TIMEOUT_SECONDS")

    # Local output directories
    transcripts_path: str = Field(default="transcripts", alias="TRANSCRIPTS_DIR")
    recordings_path: str = Field(default="recordings", alias="RECORDINGS_DIR")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def transcripts_dir(self) -> Path:
        path = Path(self.transcripts_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def recordings_dir(self) -> Path:
        path = Path(self.recordings_path)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()