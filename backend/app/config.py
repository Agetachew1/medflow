from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/medflow"
    
    
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region_name: str = "us-east-1"
    jwt_secret_key: str = "43fde73cb34a4bf85a413f7d1dfe33cced712bb73272e5a10caa83d8ce40119a"
    
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    
    frontend_origin: str = "http://localhost:5173,http://localhost:5174"
    db_echo: bool = False
    s3_bucket: str | None = None

settings = Settings()
