from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration for the Freelance Hunter Bot.
    Pydantic automatically reads these from the .env file.
    """
    groq_api_key: str
    sqlite_db_path: str = "freelance_hunter.db"
    chroma_db_path: str = "./chroma_data"
    
    # This tells Pydantic to look for a file named .env
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

# We instantiate it once here, so we can just import `settings` anywhere in our app.
settings = Settings()