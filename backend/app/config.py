from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_image_bucket: str = "item-images"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    first_admin_username: str = "admin"
    first_admin_email: str = "admin@example.com"
    first_admin_password: str = "changeme"

    class Config:
        env_file = ".env"


settings = Settings()
