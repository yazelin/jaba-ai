"""設定管理模組"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """應用程式設定"""

    # 資料庫
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5433"))
    db_name: str = os.getenv("DB_NAME", "jaba_ai")
    db_user: str = os.getenv("DB_USER", "jaba_ai")
    db_password: str = os.getenv("DB_PASSWORD", "jaba_ai_secret")

    # 應用程式
    app_port: int = int(os.getenv("APP_PORT", "8089"))

    # 初始超級管理員（第一次啟動時自動建立）
    init_admin_username: str = os.getenv("INIT_ADMIN_USERNAME", "admin")
    init_admin_password: str = os.getenv("INIT_ADMIN_PASSWORD", "admin123")

    # LINE Bot
    line_channel_secret: str = os.getenv("LINE_CHANNEL_SECRET", "")
    line_channel_access_token: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    # 安全設定
    security_ban_threshold: int = int(os.getenv("SECURITY_BAN_THRESHOLD", "5"))

    # AI 對話設定
    chat_history_limit: int = int(os.getenv("CHAT_HISTORY_LIMIT", "40"))  # 傳給 AI 的對話歷史筆數

    @property
    def database_url(self) -> str:
        """取得資料庫連線字串"""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_sync(self) -> str:
        """取得同步資料庫連線字串（用於 Alembic）"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
