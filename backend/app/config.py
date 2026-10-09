from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:password@127.0.0.1:5432/medflow"
    
    
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region_name: str = "us-east-1"
    jwt_secret_key: str = "43fde73cb34a4bf85a413f7d1dfe33cced712bb73272e5a10caa83d8ce40119a"
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=7, gt=0)
    
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    
    
    frontend_origin: str = "http://localhost:5173,http://localhost:5174"
    db_echo: bool = False
    s3_bucket: str | None = None

    @model_validator(mode="after")
    def validate_token_lifetimes(self) -> "Settings":
        if self.access_token_expire_minutes >= self.refresh_token_expire_days * 24 * 60:
            raise ValueError("Access-token lifetime must be shorter than refresh-token lifetime")
        return self

settings = Settings()
