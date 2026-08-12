"""应用配置 - 从 .env 文件加载"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/demo.db")

    # 安全配置
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "100"))
    QUERY_TIMEOUT: int = int(os.getenv("QUERY_TIMEOUT", "10"))


settings = Settings()
