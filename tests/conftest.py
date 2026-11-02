"""測試設定

整合測試需要一個空的 PostgreSQL（不要指到正式資料庫）：
    docker run -d --name jaba-test-db -e POSTGRES_USER=jaba_ai \
      -e POSTGRES_PASSWORD=jaba_ai_secret -e POSTGRES_DB=jaba_ai_test \
      -p 55433:5432 postgres:16-alpine
    DB_PORT=55433 DB_NAME=jaba_ai_test uv run alembic upgrade head
連不上時整合測試會自動略過，只跑解析器測試。
"""
import os

# 必須在 import app 之前設定，app.config 在 import 時讀環境變數
os.environ.setdefault("DB_PORT", os.getenv("TEST_DB_PORT", "55433"))
os.environ.setdefault("DB_NAME", os.getenv("TEST_DB_NAME", "jaba_ai_test"))
os.environ.setdefault("LINE_CHANNEL_SECRET", "test")
os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "test")
os.environ.pop("ADMIN_LINE_USER_ID", None)

assert os.environ["DB_NAME"] != "jaba_ai", "測試不能指到正式資料庫"
