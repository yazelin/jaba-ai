"""Jaba AI - LINE 群組點餐系統"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio

from app.config import settings
from app.routers import (
    public_router,
    board_router,
    admin_router,
    line_webhook_router,
    line_admin_router,
    chat_router,
)

# 設定 logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("jaba")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    from app.services.scheduler import start_scheduler, stop_scheduler
    from app.broadcast import register_broadcasters

    logger.info("Starting Jaba AI...")

    # 註冊廣播函數（供其他模組使用）
    register_broadcasters(
        order_update=broadcast_order_update,
        chat_message=broadcast_chat_message,
        session_status=broadcast_session_status,
        payment_update=broadcast_payment_update,
        store_change=broadcast_store_change,
        application_update=broadcast_application_update,
        group_update=broadcast_group_update,
    )

    # 自動建立初始管理員
    await _init_super_admin()

    # 啟動定時任務排程器
    start_scheduler()

    yield

    # 停止排程器
    stop_scheduler()
    logger.info("Shutting down Jaba AI...")


async def _init_super_admin():
    """檢查並建立初始超級管理員"""
    from app.database import get_db_context
    from app.repositories.system_repo import SuperAdminRepository

    async with get_db_context() as session:
        repo = SuperAdminRepository(session)
        count = await repo.count()

        if count == 0:
            # 沒有管理員，建立初始管理員
            username = settings.init_admin_username
            password = settings.init_admin_password

            if username and password:
                await repo.create(username, password)
                await session.commit()
                logger.info(f"Created initial super admin: {username}")
            else:
                logger.warning("No initial admin credentials configured")
        else:
            logger.info(f"Found {count} existing super admin(s)")


# 建立 FastAPI 應用程式
app = FastAPI(
    title="Jaba AI",
    description="LINE 群組點餐系統",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
)
socket_app = socketio.ASGIApp(sio, app)

# 掛載路由
app.include_router(public_router)
app.include_router(board_router)
app.include_router(admin_router)
app.include_router(line_webhook_router)
app.include_router(line_admin_router)
app.include_router(chat_router)

# 掛載靜態檔案（CSS、圖片、JS 等資源）
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/images", StaticFiles(directory="static/images"), name="images")
app.mount("/js", StaticFiles(directory="static/js"), name="js")


# HTML 頁面路由（不需要 /static 前綴）
@app.get("/board.html")
async def serve_board():
    """看板頁面"""
    from fastapi.responses import FileResponse
    return FileResponse("static/board.html")


@app.get("/admin.html")
async def serve_admin():
    """超級管理員頁面"""
    from fastapi.responses import FileResponse
    return FileResponse("static/admin.html")


@app.get("/line-admin.html")
async def serve_line_admin():
    """LINE 管理員頁面"""
    from fastapi.responses import FileResponse
    return FileResponse("static/line-admin.html")


# Socket.IO 事件
@sio.event
async def connect(sid, environ):
    """客戶端連接"""
    logger.info(f"Socket.IO client connected: {sid}")


@sio.event
async def disconnect(sid):
    """客戶端斷開"""
    logger.info(f"Socket.IO client disconnected: {sid}")


@sio.event
async def join_board(sid, data):
    """加入看板房間"""
    group_id = data.get("group_id", "all")
    room = f"board:{group_id}"
    await sio.enter_room(sid, room)
    logger.info(f"Client {sid} joined room {room}")


@sio.event
async def leave_board(sid, data):
    """離開看板房間"""
    group_id = data.get("group_id", "all")
    room = f"board:{group_id}"
    await sio.leave_room(sid, room)
    logger.info(f"Client {sid} left room {room}")


@sio.event
async def join_admin(sid):
    """加入超管房間（接收申請更新）"""
    await sio.enter_room(sid, "admin")
    logger.info(f"Client {sid} joined admin room")


# 健康檢查
@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy"}


# 根路徑重導向到看板頁面
@app.get("/")
async def root():
    """重導向到看板頁面"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/board.html")


# Socket.IO 廣播函數（供其他模組使用）
async def broadcast_order_update(group_id: str, data: dict):
    """廣播訂單更新"""
    await sio.emit("order_update", data, room=f"board:{group_id}")
    await sio.emit("order_update", data, room="board:all")


async def broadcast_chat_message(group_id: str, data: dict):
    """廣播聊天訊息"""
    await sio.emit("chat_message", data, room=f"board:{group_id}")
    await sio.emit("chat_message", data, room="board:all")


async def broadcast_session_status(group_id: str, data: dict):
    """廣播 Session 狀態變更（開單/收單）"""
    await sio.emit("session_status", data, room=f"board:{group_id}")
    await sio.emit("session_status", data, room="board:all")


async def broadcast_payment_update(group_id: str, data: dict):
    """廣播付款狀態變更"""
    await sio.emit("payment_update", data, room=f"board:{group_id}")
    await sio.emit("payment_update", data, room="board:all")


async def broadcast_store_change(group_id: str, data: dict):
    """廣播今日店家變更"""
    await sio.emit("store_change", data, room=f"board:{group_id}")
    await sio.emit("store_change", data, room="board:all")


async def broadcast_application_update(room: str, data: dict):
    """廣播群組申請更新（給超管後台）"""
    await sio.emit("application_update", data, room="admin")


async def broadcast_group_update(room: str, data: dict):
    """廣播群組更新（給超管後台，如成員變化）"""
    await sio.emit("group_update", data, room="admin")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:socket_app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=True,
    )
