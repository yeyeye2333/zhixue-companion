from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MiniMax 大模型
    minimax_api_key: str = ""
    minimax_group_id: str = ""
    minimax_model: str = "abab6.5s-chat"

    # JWT 鉴权
    secret_key: str = "change_this_to_a_long_random_string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 小时

    # 数据库
    database_url: str = "sqlite:///./zhixue.db"

    # 文件存储
    upload_dir: str = "./uploads"
    log_dir: str = "./logs"

    # 文件上传限制
    max_upload_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_extensions: list[str] = ["pdf", "txt", "doc", "docx"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
