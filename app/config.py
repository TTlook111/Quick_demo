"""应用配置 - 从 .env 文件加载"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    if not OPENAI_API_KEY:
        print("❌ 错误: OPENAI_API_KEY 未配置！请复制 .env.example 为 .env 并填入你的 API Key")
        sys.exit(1)
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/demo.db")

    # 安全配置
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", "100"))
    QUERY_TIMEOUT: int = int(os.getenv("QUERY_TIMEOUT", "10"))

    # 输入限制
    MAX_QUESTION_LENGTH: int = int(os.getenv("MAX_QUESTION_LENGTH", "500"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "1"))


settings = Settings()
