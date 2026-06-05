from pydantic_settings import BaseSettings

class Settings (BaseSettings):
    GEMINI_API_KEY: str
    AWS_SECRET_KEY: str
    AWS_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET: str

    class Config:
        env_file= ".env"
        env_file_encoding= "utf-8"
        extra= "ignore"
 
settings = Settings()
