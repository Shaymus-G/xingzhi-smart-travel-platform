from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME:str="XingZhi Backend"
    DEBUG:bool=True

    MYSQL_HOST:str
    MYSQL_PORT:int
    MYSQL_USER:str
    MYSQL_PASSWORD:str
    MYSQL_DATABASE:str

    SECRET_KEY:str

    model_config = SettingsConfigDict(
        env_file=".env",
        encoding="utf-8"
    )

settings=Settings()