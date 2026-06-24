from pydantic_settings import BaseSettings

class Settings (BaseSettings):
    GEMINI_API_KEY: str
    # AWS
    AWS_SECRET_KEY: str
    AWS_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str
    # Redis
    REDIS_HOST:str
    REDIS_PORT:int

    #  async pg
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str

    class Config:
        env_file= ".env"
        env_file_encoding= "utf-8"
        extra= "ignore"
 
settings = Settings()
