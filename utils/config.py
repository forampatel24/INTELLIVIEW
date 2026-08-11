from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    default_ai_provider: str = "gemini"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4"

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "intellivue"

    jwt_secret: str = "change_me_to_a_long_random_string"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 7

    resume_provider: str = ""
    question_provider: str = ""
    evaluation_provider: str = ""
    behavior_provider: str = ""
    feedback_provider: str = ""

    @property
    def task_providers(self) -> dict[str, str]:
        return {
            "resume_analysis": self.resume_provider or self.default_ai_provider,
            "question_generation": self.question_provider or self.default_ai_provider,
            "answer_evaluation": self.evaluation_provider or self.default_ai_provider,
            "behavior_analysis": self.behavior_provider or self.default_ai_provider,
            "feedback_generation": self.feedback_provider or self.default_ai_provider,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
