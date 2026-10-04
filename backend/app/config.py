from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/medflow"
    
    # Make AWS keys optional so the app doesn't crash if they are missing locally
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region_name: str = "us-east-1"
    jwt_secret_key: str = "temporary-dev-key-for-medflow-local-only"
    
    # extra="ignore" prevents crashes if your .env file has variables not listed here
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
