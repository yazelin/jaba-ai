"""群組點餐整合測試：真的資料庫、假的 LINE 與 AI

每個案例都對應一個實際發生過的狀況（見 openspec/changes/update-group-ordering-reliability）。
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text

from app.database import async_session_factory, engine
from app.models.group import Group, GroupAdmin
from app.models.menu import Menu, MenuCategory, MenuItem
from app.models.order import Order, OrderItem, OrderSession
from app.models.store import Store
from app.models.user import User
from app.repositories.order_repo import TW_TZ
from app.services import group_ordering
from app.services.line_service import LineService


async def _db_available() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1 from ai_prompts limit 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.asyncio

GID = "Ctestgroup"
ADMIN, A, B = "Uadmin", "Ua", "Ub"
NAMES = {ADMIN: "管理員", A: "同事A", B: "同事B"}


@pytest.fixture(autouse=True)
async def clean_db():
    if not await _db_available():
        pytest.skip("測試資料庫未啟動")
    async with async_session_factory() as db:
        for t in ["order_items", "orders", "chat_messages", "order_sessions", "group_today_stores",
                  "group_admins", "group_members", "menu_items", "menu_categories", "menus",
                  "stores", "groups", "users", "ai_logs"]:
            await db.execute(text(f"DELETE FROM {t}"))
        users = {k: User(line_user_id=k, display_name=v) for k, v in NAMES.items()}
        db.add_all(users.values())
        group = Group(line_group_id=GID, name="測試群", status="active", group_code="1234")
        db.add(group)
        await db.flush()
        db.add(GroupAdmin(group_id=group.id, user_id=users[ADMIN].id))
        _add_store(db, "家香味排骨便當", {
            "便當": [("炸雞腿", 125), ("古早味排骨", 110), ("蔥油雞", 105), ("蔥爆豬", 105), ("宮保雞丁", 105)],
            "單點類": [("炸雞腿", 80), ("古早味排骨", 70)],
        })
        _add_store(db, "梁社漢", {
            "主餐": [("玫瑰油雞飯/麵", 128), ("椒鹽雞塊飯/麵", 95), ("控肉飯/麵", 99)],
            "湯品": [("味噌湯", 20)],
        })
        _add_store(db, "土雞肉飯", {
            "便當類": [("雞肉飯", 110), ("黯然飯", 105), ("雞滷飯", 85), ("銷魂飯", 75)],
        })
        await db.commit()
    group_ordering._pending_choices.clear()
    group_ordering._reminded_today.clear()
    yield


def _add_store(db, name, cats):
    store = Store(name=name, scope="global", is_active=True)
    menu = Menu(store=store)
    for i, (cat, items) in enumerate(cats.items()):
        c = MenuCategory(menu=menu, name=cat, sort_order=i)
        for j, (n, p) in enumerate(items):
            MenuItem(category=c, name=n, price=Decimal(p), sort_order=j, variants=[])
    db.add(store)


class Chat:
    def __init__(self):
        self.ai_response = {"message": "", "actions": []}
        self.ai_calls = 0

    async def say(self, who, text, mentions_others=False, spans=None):
        out = []
        async with async_session_factory() as db:
            svc = LineService(db)

            async def fake_reply(token, msg):
                out.append(msg)

            async def fake_chat(**kwargs):
                self.ai_calls += 1
                return dict(self.ai_response)

            svc.reply_message = fake_reply
            svc.get_group_name = AsyncMock(return_value="測試群")
            svc.get_group_member_profile = AsyncMock(return_value={"display_name": NAMES.get(who, who)})
            svc.ai_service.chat = fake_chat
            await svc.handle_message(who, GID, text, "token", spans, mentions_others)
            await db.commit()
        return out[0] if out else None


async def items_of(who) -> list[tuple[str, int, str]]:
    async with async_session_factory() as db:
        res = await db.execute(
            select(OrderItem.name, OrderItem.quantity, OrderItem.note)
            .join(Order).join(OrderSession).join(User, Order.user_id == User.id)
            .where(User.line_user_id == who, OrderSession.status == "ordering")
            .order_by(OrderItem.created_at, OrderItem.name)
        )
        return [(n, q, note or "") for n, q, note in res.all()]


async def open_sessions() -> int:
    async with async_session_factory() as db:
        res = await db.execute(select(OrderSession).where(OrderSession.status == "ordering"))
        return len(res.scalars().all())


# ---------- 開單 ----------

async def test_store_name_opens_session():
    chat = Chat()
    reply = await chat.say(ADMIN, "家香味")
    assert "今天吃 家香味排骨便當" in reply
    assert await open_sessions() == 1


async def test_store_menu_phrase_opens_session():
    chat = Chat()
    reply = await chat.say(ADMIN, "梁社漢菜單")
    assert "今天吃 梁社漢" in reply and "玫瑰油雞" in reply


async def test_please_open():
    chat = Chat()
    await chat.say(ADMIN, "加 家香味")
    assert "開始群組點餐" in await chat.say(A, "請開單")


async def test_mention_prefix_stripped():
    chat = Chat()
    reply = await chat.say(A, "@jaba 呷爸 help")
    assert "呷爸" in reply and "可用指令" in reply


# ---------- 點餐 ----------

async def test_rule_order_and_confirm_line():
    chat = Chat()
    await chat.say(ADMIN, "家香味")
    reply = await chat.say(A, "古早味排骨+1")
    assert reply.startswith("同事A：古早味排骨（便當）×1，小計 $110")
    assert "照便當算" in reply
    assert chat.ai_calls == 0


async def test_rice_default_no_question():
    chat = Chat()
    await chat.say(ADMIN, "梁社漢")
    reply = await chat.say(A, "玫瑰油雞+1")
    assert "玫瑰油雞飯×1" in reply and "要麵說「麵」" in reply
    reply = await chat.say(A, "麵")
    assert "玫瑰油雞麵×1" in reply


async def test_switch_to_single_item():
    chat = Chat()
    await chat.say(ADMIN, "家香味")
    await chat.say(A, "炸雞腿")
    reply = await chat.say(A, "單點")
    assert "炸雞腿（單點）×1，小計 $80" in reply


async def test_proxy_and_multiline():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(ADMIN, "銷魂飯*1(小李)\n黯然飯*1(小金)\n雞滷飯*3(老闆)\n銷魂飯*1")
    assert sorted(await items_of(ADMIN)) == sorted([
        ("銷魂飯", 1, "小李"), ("黯然飯", 1, "小金"), ("雞滷飯", 3, "老闆"), ("銷魂飯", 1, ""),
    ])


async def test_same_item_merges_quantity():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "銷魂飯+1")
    await chat.say(A, "再加一個銷魂飯")
    assert await items_of(A) == [("銷魂飯", 2, "")]  # 同品項合併成一列


async def test_ambiguous_asks_then_choose():
    chat = Chat()
    await chat.say(ADMIN, "家香味")
    async with async_session_factory() as db:  # 加一個會撞名的品項
        cat = (await db.execute(select(MenuCategory).where(MenuCategory.name == "便當"))).scalar_one()
        db.add(MenuItem(category_id=cat.id, name="滷雞腿", price=Decimal(110), sort_order=9, variants=[]))
        await db.commit()
    reply = await chat.say(A, "雞腿*2")
    assert "回數字" in reply and "1. 炸雞腿（便當） $125" in reply and "2. 滷雞腿 $110" in reply
    reply = await chat.say(A, "2")
    assert reply.startswith("同事A：滷雞腿×2，小計 $220")


async def test_copy_last():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "黯然飯")
    await chat.say(B, "+1")
    assert await items_of(B) == [("黯然飯", 1, "")]


# ---------- 減少、取消、改 ----------

async def test_0608_reduce_two_lines():
    """06-08：「少雞滷飯 x3／銷魂飯 *1」要兩項都減"""
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(ADMIN, "黯然飯*3")
    await chat.say(ADMIN, "雞滷飯*3\n銷魂飯*1")
    reply = await chat.say(ADMIN, "少雞滷飯 x3 $255\n銷魂飯 *1")
    assert await items_of(ADMIN) == [("黯然飯", 3, "")]
    assert "黯然飯×3，小計 $315" in reply


async def test_reduce_matches_own_items():
    chat = Chat()
    await chat.say(ADMIN, "家香味")
    await chat.say(A, "炸雞腿*1")
    await chat.say(A, "取消一個雞腿")
    assert await items_of(A) == []


async def test_change_item():
    chat = Chat()
    await chat.say(ADMIN, "家香味")
    await chat.say(A, "蔥油雞*3")
    await chat.say(A, "蔥油雞*3改蔥爆豬*3")
    assert await items_of(A) == [("蔥爆豬", 3, "")]


async def test_cancel_all():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "銷魂飯*2")
    reply = await chat.say(A, "取消")
    assert "目前沒有點餐" in reply and await items_of(A) == []


# ---------- AI 路徑的安全規則 ----------

async def test_ai_cancel_without_cancel_word_is_blocked():
    """06-08：AI 把「改點」當成整筆取消再重點"""
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "黯然飯*3")
    chat.ai_response = {"message": "好", "actions": [
        {"type": "group_cancel_order", "data": {}},
    ]}
    await chat.say(A, "我想想要不要換別的口味")
    assert await items_of(A) == [("黯然飯", 3, "")]


async def test_ai_cancel_plus_create_becomes_set():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "黯然飯*3")
    chat.ai_response = {"message": "改好了", "actions": [
        {"type": "group_cancel_order", "data": {}},
        {"type": "group_create_order", "data": {"items": [{"name": "雞滷飯", "quantity": 2}]}},
    ]}
    reply = await chat.say(A, "我整份換成兩個雞滷飯好了")
    assert await items_of(A) == [("雞滷飯", 2, "")]
    assert reply.startswith("同事A：雞滷飯×2")  # 回覆取自資料庫，不是 AI 的「改好了」


async def test_ai_unknown_item_not_written():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    chat.ai_response = {"message": "", "actions": [
        {"type": "group_create_order", "data": {"items": [{"name": "牛肉麵", "quantity": 1}]}},
    ]}
    reply = await chat.say(A, "我想吃有牛的")
    assert "找不到「牛肉麵」" in reply and await items_of(A) == []


async def test_ai_error_message_is_friendly():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    chat.ai_response = {"message": "呷爸的 AI 暫時連不上，請稍後再試。", "actions": [],
                        "_error": "Failed to authenticate: OAuth session expired"}
    reply = await chat.say(A, "我想吃有雞的")
    assert "OAuth" not in reply and "固定格式的點餐" in reply


# ---------- 不漏單 ----------

async def test_order_before_open_with_store_auto_opens():
    chat = Chat()
    await chat.say(ADMIN, "加 土雞肉飯")
    # 「加 店名」不開單；這時有人直接點
    async with async_session_factory() as db:
        await db.execute(text("DELETE FROM order_sessions"))
        await db.commit()
    reply = await chat.say(A, "銷魂飯+1")
    assert reply.startswith("已用 土雞肉飯 開單")
    assert await items_of(A) == [("銷魂飯", 1, "")]


async def test_0804_orders_before_store_are_buffered():
    """08-04：開單前點的 6 筆全掉了"""
    chat = Chat()
    first = await chat.say(A, "古早味排骨飯+1")
    assert "先幫大家記著" in first
    assert await chat.say(B, "宮保雞丁 +1") is None  # 同一天只提醒一次
    reply = await chat.say(ADMIN, "家香味")
    assert "已補上開單前的點餐" in reply
    assert await items_of(A) == [("古早味排骨（便當）", 1, "")]
    assert await items_of(B) == [("宮保雞丁", 1, "")]


async def test_1102_stale_session_auto_closed():
    """11-02：9/22 的梁社漢單沒關，今天打「家香味」被當成點餐"""
    chat = Chat()
    await chat.say(ADMIN, "梁社漢")
    async with async_session_factory() as db:
        s = (await db.execute(select(OrderSession))).scalar_one()
        s.started_at = datetime.now(TW_TZ) - timedelta(days=41)
        await db.commit()
    reply = await chat.say(ADMIN, "家香味")
    assert "今天吃 家香味排骨便當" in reply
    reply = await chat.say(A, "炸排骨飯+1")  # 家香味沒有炸排骨飯 → 不能寫進舊的梁社漢單
    assert await open_sessions() == 1


async def test_admin_store_change_blocked_when_orders_exist():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "銷魂飯")
    reply = await chat.say(ADMIN, "家香味")
    assert "要換店請先「結單」" in reply


async def test_admin_ordering_item_named_like_store():
    """管理員在土雞肉飯點「雞肉飯」不能被當成換店"""
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(ADMIN, "雞肉飯*1")
    assert await items_of(ADMIN) == [("雞肉飯", 1, "")]


async def test_chatter_ignored_without_ai():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    assert await chat.say(ADMIN, "@同事A 110", mentions_others=True) is None
    assert await chat.say(A, "便當來了~可以自己到前面拿") is None  # 交給 AI，AI 不回
    assert chat.ai_calls == 1
    assert await chat.say(A, "http://jaba.ui/") is None


# ---------- 改價、收款 ----------

async def test_update_price_updates_open_orders():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "銷魂飯")
    reply = await chat.say(ADMIN, "改價 銷魂飯 80")
    assert "從 $75 改成 $80" in reply and "1 筆一起改了" in reply
    assert "小計 $80" in await chat.say(A, "飯")


async def test_payment_flow():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "銷魂飯")
    await chat.say(B, "黯然飯")
    end = await chat.say(ADMIN, "結單")
    assert "已付 名字" in end
    reply = await chat.say(ADMIN, "已付 同事A")
    assert "同事A $75 已付" in reply and "同事B $105" in reply
    assert "都收齊了" in (await chat.say(ADMIN, "已付 同事B"))


async def test_concurrent_orders_all_saved():
    import asyncio
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await asyncio.gather(*(chat.say(u, "銷魂飯+1") for u in (A, B, ADMIN)))
    for u in (A, B, ADMIN):
        assert await items_of(u) == [("銷魂飯", 1, "")]


# ---------- 重傳、重列 ----------

async def test_resend_does_not_duplicate():
    """07-13「奇怪，怎麼老漏單」：機器人慢，同一則再傳一次"""
    chat = Chat()
    await chat.say(ADMIN, "家香味")
    await chat.say(A, "古早味排骨飯*1")
    reply = await chat.say(A, "古早味排骨飯*1")
    assert await items_of(A) == [("古早味排骨（便當）", 1, "")]
    assert "沒有重複加" in reply and "再加一個古早味排骨" in reply


async def test_explicit_add_more():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "黯然飯")
    await chat.say(A, "再加一個黯然飯")
    assert await items_of(A) == [("黯然飯", 2, "")]


async def test_0608_full_sequence():
    """06-08 完整重現：先點、改點、重貼整份、再減，最後只剩黯然飯×3"""
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(ADMIN, "黯然飯*3")
    await chat.say(ADMIN, "雞滷飯*3\n銷魂飯*1")
    await chat.say(ADMIN, "雞滷飯 x3\n銷魂飯 *1\n黯然飯*3")
    await chat.say(ADMIN, "少雞滷飯 x3 $255\n銷魂飯 *1")
    await chat.say(ADMIN, "雞肉飯*1")
    assert sorted(await items_of(ADMIN)) == [("雞肉飯", 1, ""), ("黯然飯", 3, "")]


async def test_different_quantity_adds():
    """08-13：「銷魂飯」之後「銷魂飯*3」是再幫別人點 3 份"""
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "銷魂飯")
    reply = await chat.say(A, "銷魂飯*3")
    assert await items_of(A) == [("銷魂飯", 4, "")]
    assert "銷魂飯×4" in reply  # 確認行顯示總數，點錯可以馬上改


async def test_repost_with_new_item_adds_only_new():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(A, "黯然飯*3")
    await chat.say(A, "黯然飯*3\n雞肉飯*1")
    assert sorted(await items_of(A)) == [("雞肉飯", 1, ""), ("黯然飯", 3, "")]


# ---------- 店名打錯字（11-02 早上「家鄉味菜單」） ----------

async def test_store_menu_phrase_exact_store():
    chat = Chat()
    reply = await chat.say(ADMIN, "家香味菜單")
    assert "今天吃 家香味排骨便當" in reply


async def test_store_name_typo_with_menu_suffix():
    chat = Chat()
    reply = await chat.say(ADMIN, "家鄉味菜單")
    assert "今天吃 家香味排骨便當" in reply


async def test_unknown_store_with_menu_suffix_lists_stores():
    chat = Chat()
    reply = await chat.say(ADMIN, "麥當勞菜單")
    assert "找不到「麥當勞」" in reply and "家香味排骨便當" in reply
    assert await open_sessions() == 0


async def test_typo_without_suffix_stays_silent():
    """沒有「菜單」「開單」結尾，可能只是聊天，不猜"""
    chat = Chat()
    assert await chat.say(ADMIN, "家鄉味") is None
    assert await open_sessions() == 0


async def test_typo_during_stale_session():
    """完整重現 11-02：舊單沒關、管理員打錯字的「家鄉味菜單」"""
    chat = Chat()
    await chat.say(ADMIN, "梁社漢")
    async with async_session_factory() as db:
        s = (await db.execute(select(OrderSession))).scalar_one()
        s.started_at = datetime.now(TW_TZ) - timedelta(days=41)
        await db.commit()
    reply = await chat.say(ADMIN, "家鄉味菜單")
    assert "今天吃 家香味排骨便當" in reply
    assert await open_sessions() == 1


# ---------- 價格更新日期 ----------

async def test_price_date_shown_and_stale_warning():
    chat = Chat()
    async with async_session_factory() as db:  # 家香味的價格停在 2025-12-24
        await db.execute(text(
            "UPDATE menu_items SET updated_at = '2025-12-24 10:00+08' WHERE category_id IN ("
            " SELECT c.id FROM menu_categories c JOIN menus m ON m.id = c.menu_id"
            " JOIN stores s ON s.id = m.store_id WHERE s.name = '家香味排骨便當')"
        ))
        await db.commit()
    opened = await chat.say(ADMIN, "家香味")
    assert "價格 2025/12/24 更新，超過三個月" in opened
    await chat.say(A, "蔥油雞")
    end = await chat.say(ADMIN, "結單")
    assert "家香味排骨便當：價格 2025/12/24 更新" in end


async def test_price_update_refreshes_date():
    chat = Chat()
    await chat.say(ADMIN, "土雞肉飯")
    await chat.say(ADMIN, "改價 銷魂飯 80")
    menu = await chat.say(A, "菜單")
    assert f"價格 {datetime.now(TW_TZ):%Y/%m/%d} 更新" in menu and "超過三個月" not in menu
