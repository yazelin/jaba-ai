"""群組點餐：規則解析後的訂單寫入、確認訊息、自動開單與補單

LineService 繼承這個 mixin。這裡的方法都假設呼叫端已經取得群組鎖。
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage
from app.models.group import Group
from app.models.menu import Menu as MenuModel, MenuCategory, MenuItem
from app.models.order import Order, OrderItem, OrderSession
from app.models.user import User
from app.repositories.order_repo import TW_TZ, get_today_tw
from app.services.order_parser import (
    AddItem,
    CancelAll,
    ChooseCandidate,
    CopyLast,
    Menu,
    MenuEntry,
    ParseResult,
    ReduceItem,
    SetOrder,
    SwitchOption,
    is_restatement,
)

logger = logging.getLogger("jaba.ordering")

# 同一群組一次處理一則訊息。
# ponytail: 單一行程內的 asyncio.Lock；改成多個 worker 時要換成 PostgreSQL advisory lock
_group_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


def group_lock(line_group_id: str) -> asyncio.Lock:
    return _group_locks[line_group_id]


# 等使用者從候選品項中選一個：(group_id, user_id) -> (候選, 待套用的點餐, 到期時間)
# ponytail: 存在記憶體，服務重啟就忘記，使用者重打一次品項即可
_pending_choices: dict[tuple[str, str], tuple[list[MenuEntry], AddItem, float]] = {}
_CHOICE_TTL = 600

# 開單前提醒過的群組（同一天只提醒一次）
_reminded_today: dict[str, str] = {}

PENDING_ROLE = "pending"


def _now_tw() -> datetime:
    return datetime.now(TW_TZ)


class GroupOrderingMixin:
    """需要 LineService 的 session、各 repository"""

    # ---------- 菜單 ----------

    async def _load_menu(self, today_stores: list) -> tuple[Menu, dict[str, UUID]]:
        """今日菜單索引，以及品項 id 對應的店家 id"""
        entries: list[MenuEntry] = []
        store_of: dict[str, UUID] = {}
        for ts in today_stores:
            result = await self.session.execute(
                select(MenuItem, MenuCategory.name)
                .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
                .join(MenuModel, MenuCategory.menu_id == MenuModel.id)
                .where(MenuModel.store_id == ts.store_id)
                .where(MenuItem.is_available.is_(True))
                .order_by(MenuCategory.sort_order, MenuItem.sort_order)
            )
            for item, cat_name in result.all():
                entries.append(MenuEntry(str(item.id), item.name, float(item.price), cat_name or ""))
                store_of[str(item.id)] = ts.store_id
        return Menu(entries), store_of

    # ---------- 自動結單 ----------

    async def _close_stale_session(self, group: Group, active: Optional[OrderSession]) -> Optional[OrderSession]:
        """進行中的單不是今天開的就結束，回傳結束後仍有效的 session（可能為 None）"""
        if not active:
            return None
        started = active.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=TW_TZ)
        if started.astimezone(TW_TZ).date() >= get_today_tw():
            return active
        logger.info(f"Auto-closing stale session {active.id} (started {started})")
        await self.session_repo.end_session(active, None)
        await self.session.commit()
        return None

    # ---------- 開單與補單 ----------

    async def _open_session(self, user: User, group: Group, today_stores: list) -> OrderSession:
        from app.broadcast import emit_session_status, flush_events

        new_session = await self.session_repo.start_session(group.id, user.id)
        store_names = "、".join(ts.store.name for ts in today_stores if ts.store)
        await self.chat_repo.add_message(
            role="system",
            content=f"=== 新的點餐開始 ===\n今日店家：{store_names}\n由 {user.display_name} 發起",
            group_id=group.id,
            session_id=new_session.id,
        )
        await self.session.commit()
        await emit_session_status(str(group.id), {
            "group_id": str(group.id),
            "session_id": str(new_session.id),
            "status": "ordering",
            "started_by": user.display_name,
        })
        await flush_events()
        return new_session

    async def _apply_buffered_orders(self, group: Group, session: OrderSession, today_stores: list) -> str:
        """把今天開單前暫存的點餐補進訂單，回傳要附在開單訊息後的說明"""
        today = get_today_tw()
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.group_id == group.id, ChatMessage.role == PENDING_ROLE)
            .options(selectinload(ChatMessage.user))
            .order_by(ChatMessage.created_at)
        )
        pending = [m for m in result.scalars().all()
                   if m.created_at.astimezone(TW_TZ).date() == today]
        if not pending:
            return ""

        from app.services.order_parser import parse_message
        menu, store_of = await self._load_menu(today_stores)
        applied, failed = [], []
        for msg in pending:
            msg.role = "user"
            msg.session_id = session.id
            res = parse_message(msg.content, menu)
            if not res or res.needs_choice or not msg.user:
                failed.append(f"{msg.user.display_name if msg.user else '?'}：{msg.content}")
                continue
            _, err = await self._apply_ops(msg.user, group, session, res, menu, store_of)
            if err:
                failed.append(f"{msg.user.display_name}：{msg.content}")
            else:
                applied.append(msg.user)
        await self.session.commit()
        _reminded_today.pop(str(group.id), None)

        lines = []
        seen = set()
        for u in applied:
            if u.id in seen:
                continue
            seen.add(u.id)
            lines.append(await self._confirm_line(u, session))
        out = []
        if lines:
            out.append("已補上開單前的點餐：\n" + "\n".join(lines))
        if failed:
            out.append("下面這幾則看不懂，請本人再點一次：\n" + "\n".join(failed))
        return "\n\n".join(out)

    async def _buffer_before_open(self, user: User, group: Group, text: str) -> Optional[str]:
        """今日店家還沒設定時，先存下點餐訊息；同一天只提醒一次"""
        await self.chat_repo.add_message(role=PENDING_ROLE, content=text, group_id=group.id, user_id=user.id)
        await self.session.commit()
        key, today = str(group.id), str(get_today_tw())
        if _reminded_today.get(key) == today:
            return None
        _reminded_today[key] = today
        return "還沒選今天的店家，先幫大家記著。管理員選好店家後，剛剛的點餐會自動補上。"

    # ---------- 套用操作 ----------

    async def _user_order(self, user: User, session: OrderSession) -> Optional[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.session_id == session.id, Order.user_id == user.id)
            .options(selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def _apply_ops(
        self,
        user: User,
        group: Group,
        session: OrderSession,
        res: ParseResult,
        menu: Menu,
        store_of: dict[str, UUID],
    ) -> tuple[bool, Optional[str]]:
        """套用規則解析結果

        回傳 (訂單是否變動, 要直接回給使用者的訊息)。訊息不為 None 時不另外產生確認行。
        """
        key = (str(group.id), str(user.id))
        changed = False

        if res.needs_choice:
            _pending_choices[key] = (res.candidates, res.pending_add, time.time() + _CHOICE_TTL)
            opts = "\n".join(
                f"{i}. {menu.display(e)} ${int(e.price)}" for i, e in enumerate(res.candidates, 1)
            )
            # 前面已經解析好的品項先寫入
            if res.ops:
                changed, _ = await self._apply_ops(user, group, session, ParseResult(ops=res.ops), menu, store_of)
            return changed, f"「{res.ambiguous_query}」是哪一個？回數字就好：\n{opts}"

        # 把原本點的再列一次（重傳、重貼整份）→ 整份取代，不重複追加
        self._last_restated = False
        if res.ops and all(isinstance(o, AddItem) for o in res.ops):
            order = await self._user_order(user, session)
            if order and order.items:
                existing: dict = {}
                for it in order.items:
                    k = (it.name, it.note or "")
                    existing[k] = existing.get(k, 0) + it.quantity
                adds = [(menu.display(o.entry, o.choice), o.proxy, o.quantity, o.additive) for o in res.ops]
                if is_restatement(existing, adds):
                    msg_counts: dict = {}
                    for name, proxy, qty, _ in adds:
                        msg_counts[(name, proxy)] = msg_counts.get((name, proxy), 0) + qty
                    if msg_counts == existing:
                        self._last_restated = True
                        return False, None
                    res = ParseResult(ops=[SetOrder(list(res.ops))])

        for op in res.ops:
            if isinstance(op, ChooseCandidate):
                pend = _pending_choices.pop(key, None)
                if not pend or pend[2] < time.time() or not (1 <= op.index <= len(pend[0])):
                    return changed, None if changed else ""
                cands, add, _ = pend
                add.entry = cands[op.index - 1]
                op = add
            if isinstance(op, AddItem):
                await self._add_item(user, session, op, menu, store_of)
                changed = True
            elif isinstance(op, ReduceItem):
                msg = await self._reduce_item(user, session, op, menu)
                if msg is None:
                    changed = True
                elif msg:
                    return changed, msg
            elif isinstance(op, CancelAll):
                order = await self._user_order(user, session)
                if order:
                    await self.order_repo.delete(order)
                    changed = True
            elif isinstance(op, CopyLast):
                msg = await self._copy_last(user, session, op.quantity)
                if msg:
                    return changed, msg
                changed = True
            elif isinstance(op, SwitchOption):
                changed = await self._switch_option(user, session, op.option, menu) or changed
                if not changed:
                    # 「飯」「便當」只是確認預設，回目前內容即可
                    return False, None
            elif isinstance(op, SetOrder):
                order = await self._user_order(user, session)
                if order:
                    await self.order_repo.delete(order)
                    await self.session.flush()
                for add in op.items:
                    await self._add_item(user, session, add, menu, store_of)
                changed = True

        await self.session.flush()
        return changed, None

    async def _add_item(self, user: User, session: OrderSession, add: AddItem, menu: Menu, store_of: dict) -> None:
        entry = add.entry
        order = await self._user_order(user, session)
        if not order:
            order = Order(session_id=session.id, user_id=user.id, store_id=store_of[entry.item_id])
            order = await self.order_repo.create(order)
            await self.session.refresh(order, ["items"])
        name = menu.display(entry, add.choice)
        note = add.proxy or ""
        price = Decimal(str(entry.price))
        for item in order.items:
            if item.name == name and (item.note or "") == note and item.unit_price == price:
                item.quantity += add.quantity
                item.subtotal = item.unit_price * item.quantity
                break
        else:
            item = OrderItem(
                order_id=order.id,
                menu_item_id=UUID(entry.item_id),
                name=name,
                quantity=add.quantity,
                unit_price=price,
                subtotal=price * add.quantity,
                note=note,
                options={"choice": add.choice} if add.choice else {},
            )
            self.session.add(item)
            order.items.append(item)
        await self.session.flush()
        await self.order_repo.calculate_total(order)

    async def _reduce_item(self, user: User, session: OrderSession, op: ReduceItem, menu: Menu) -> Optional[str]:
        """減少本人的品項；成功回傳 None，找不到回傳說明"""
        order = await self._user_order(user, session)
        if not order or not order.items:
            return ""  # 沒東西可減，安靜略過（例如「改」之前根本沒點）
        items = sorted(order.items, key=lambda i: i.created_at or datetime.min.replace(tzinfo=TW_TZ))

        if op.query is None:
            target = items[-1]
        else:
            pool = [i for i in items if (i.note or "") == op.proxy] if op.proxy else items
            if op.proxy and not pool:
                pool = items
            own = Menu([MenuEntry(str(i.id), i.name, float(i.unit_price), "") for i in pool])
            mr = own.match(op.query)
            if not mr.ok and not op.proxy:
                # 同名多筆時優先自己的（沒有代訂備註）
                own = Menu([MenuEntry(str(i.id), i.name, float(i.unit_price), "") for i in pool if not i.note])
                mr = own.match(op.query)
            if not mr.ok:
                names = "、".join(self._item_text(i) for i in items)
                return f"你目前點的是：{names}，沒有對到「{op.query}」，要減哪一個？"
            target = next(i for i in items if str(i.id) == mr.entry.item_id)

        if op.quantity is None or op.quantity >= target.quantity:
            await self.session.delete(target)
            order.items.remove(target)
        else:
            target.quantity -= op.quantity
            target.subtotal = target.unit_price * target.quantity
        await self.session.flush()
        if order.items:
            await self.order_repo.calculate_total(order)
        else:
            await self.order_repo.delete(order)
        return None

    async def _copy_last(self, user: User, session: OrderSession, quantity: int) -> Optional[str]:
        result = await self.session.execute(
            select(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.session_id == session.id, Order.user_id != user.id)
            .order_by(OrderItem.created_at.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        if not last:
            return "目前還沒有人點，直接說要吃什麼就好～"
        src_order = await self.session.get(Order, last.order_id)
        order = await self._user_order(user, session)
        if not order:
            order = await self.order_repo.create(Order(session_id=session.id, user_id=user.id, store_id=src_order.store_id))
            await self.session.refresh(order, ["items"])
        for item in order.items:
            if item.name == last.name and not item.note and item.unit_price == last.unit_price:
                item.quantity += quantity
                item.subtotal = item.unit_price * item.quantity
                break
        else:
            item = OrderItem(
                order_id=order.id, menu_item_id=last.menu_item_id, name=last.name,
                quantity=quantity, unit_price=last.unit_price,
                subtotal=last.unit_price * quantity, note="", options=last.options or {},
            )
            self.session.add(item)
            order.items.append(item)
        await self.session.flush()
        await self.order_repo.calculate_total(order)
        return None

    async def _switch_option(self, user: User, session: OrderSession, option: str, menu: Menu) -> bool:
        """把本人最後一項換成「麵」或「單點」等選項，有變動回傳 True"""
        order = await self._user_order(user, session)
        if not order or not order.items:
            return False
        last = max(order.items, key=lambda i: i.created_at or datetime.min.replace(tzinfo=TW_TZ))
        entry = next((e for e in menu.entries if last.menu_item_id and e.item_id == str(last.menu_item_id)), None)
        if not entry:
            return False

        if option in ("飯", "麵") and entry.has_rice_noodle_choice:
            new_name = menu.display(entry, option)
            if new_name == last.name:
                return False
            last.name = new_name
            last.options = {**(last.options or {}), "choice": option}
        elif option in ("便當", "單點"):
            want = (lambda c: "單點" in c) if option == "單點" else (lambda c: "便當" in c)
            if want(entry.category):
                return False
            alt = next((e for e in menu.entries if e.name == entry.name and want(e.category)), None)
            if not alt:
                return False
            last.menu_item_id = UUID(alt.item_id)
            last.name = menu.display(alt)
            last.unit_price = Decimal(str(alt.price))
            last.subtotal = last.unit_price * last.quantity
        else:
            return False
        await self.session.flush()
        await self.order_repo.calculate_total(order)
        return True

    # ---------- 確認訊息 ----------

    @staticmethod
    def _item_text(item: OrderItem) -> str:
        text = f"{item.name}×{item.quantity}"
        if item.note:
            text += f"（{item.note}）"
        return text

    async def _confirm_line(self, user: User, session: OrderSession, notes: Optional[list[str]] = None) -> str:
        """本人目前的訂單，一行；內容取自資料庫"""
        order = await self._user_order(user, session)
        name = user.display_name or "你"
        if not order or not order.items:
            return f"{name}：目前沒有點餐"
        items = sorted(order.items, key=lambda i: i.created_at or datetime.min.replace(tzinfo=TW_TZ))
        text = f"{name}：{'、'.join(self._item_text(i) for i in items)}，小計 ${int(order.total_amount)}"
        if notes:
            text += "\n" + "\n".join(notes)
        return text

    def _default_notes(self, res: ParseResult, menu: Menu) -> list[str]:
        if getattr(self, "_last_restated", False):
            first = next((o for o in res.ops if isinstance(o, AddItem)), None)
            hint = f"「再加一個{first.entry.name.replace('飯/麵', '飯')}」" if first else "「再加一個」"
            return [f"（跟你原本點的一樣，沒有重複加。要多一份請打{hint}）"]
        notes = set()
        for op in res.ops:
            if isinstance(op, AddItem) and op.defaulted:
                if op.entry.has_rice_noodle_choice:
                    notes.add("（沒講就照飯算，要麵說「麵」）")
                elif menu.is_duplicated(op.entry):
                    notes.add("（沒講就照便當算，要單點說「單點」）")
        return sorted(notes)

    # ---------- 價格更新日期 ----------

    PRICE_STALE_DAYS = 90

    async def _price_note(self, store_id) -> str:
        """「價格 2026/05/29 更新」；超過三個月加一句提醒"""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.max(MenuItem.updated_at))
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
            .join(MenuModel, MenuCategory.menu_id == MenuModel.id)
            .where(MenuModel.store_id == store_id)
        )
        last = result.scalar()
        if not last:
            return ""
        last = last.astimezone(TW_TZ)
        note = f"價格 {last:%Y/%m/%d} 更新"
        if (_now_tw() - last).days > self.PRICE_STALE_DAYS:
            note += "，超過三個月，價格可能變了（管理員可打「改價 品項 金額」）"
        return note

    # ---------- 改價 ----------

    async def _update_item_price(self, group: Group, today_stores: list, query: str, price: int) -> str:
        menu, _ = await self._load_menu(today_stores)
        mr = menu.match(query)
        if mr.ambiguous:
            names = "、".join(menu.display(e) for e in mr.candidates)
            return f"「{query}」對到好幾個：{names}，請打完整名稱"
        if not mr.ok:
            return f"今日菜單找不到「{query}」"
        entry = mr.entry
        item = await self.session.get(MenuItem, UUID(entry.item_id))
        old = int(item.price)
        item.price = Decimal(price)  # updated_at 由欄位的 onupdate 自動更新

        # 今天還開著的單，這個品項一起改價
        active = await self.session_repo.get_active_session(group.id)
        touched = 0
        if active:
            res = await self.session.execute(
                select(OrderItem).join(Order, OrderItem.order_id == Order.id)
                .where(Order.session_id == active.id, OrderItem.menu_item_id == item.id)
            )
            orders = set()
            for oi in res.scalars().all():
                oi.unit_price = Decimal(price)
                oi.subtotal = oi.unit_price * oi.quantity
                orders.add(oi.order_id)
                touched += 1
            await self.session.flush()
            for oid in orders:
                await self.order_repo.calculate_total(await self.session.get(Order, oid))
        await self.session.commit()
        extra = f"，目前訂單中 {touched} 筆一起改了" if touched else ""
        return f"已把 {menu.display(entry)} 從 ${old} 改成 ${price}{extra}"

    # ---------- 收款 ----------

    async def _latest_session(self, group: Group) -> Optional[OrderSession]:
        result = await self.session.execute(
            select(OrderSession)
            .where(OrderSession.group_id == group.id)
            .order_by(OrderSession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _mark_paid_by_name(self, group: Group, name: str) -> str:
        session = await self._latest_session(group)
        if not session:
            return "還沒有任何點餐紀錄"
        full = await self.session_repo.get_with_orders(session.id)
        orders = [o for o in full.orders if o.user and name in (o.user.display_name or "")]
        if not orders:
            return f"這次點餐找不到「{name}」"
        if len(orders) > 1:
            return f"「{name}」對到好幾個人：{'、'.join(o.user.display_name for o in orders)}，請打完整名稱"
        order = orders[0]
        order.payment_status = "paid"
        order.paid_amount = order.total_amount
        order.paid_at = _now_tw()
        await self.session.commit()
        return f"{order.user.display_name} ${int(order.total_amount)} 已付\n\n" + await self._unpaid_summary(group)

    async def _unpaid_summary(self, group: Group) -> str:
        session = await self._latest_session(group)
        if not session:
            return "還沒有任何點餐紀錄"
        full = await self.session_repo.get_with_orders(session.id)
        unpaid = [o for o in full.orders if o.payment_status != "paid" and o.total_amount > 0]
        if not unpaid:
            return "這次點餐都收齊了"
        lines = [f"{o.user.display_name if o.user else '?'} ${int(o.total_amount)}" for o in unpaid]
        total = sum(int(o.total_amount) for o in unpaid)
        return f"還沒付（共 ${total}）：\n" + "\n".join(lines)
