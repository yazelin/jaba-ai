"""歷史重播：用新的規則解析器重跑過去的點餐訊息，和實際存下的訂單比對

只讀不寫（整段在唯讀交易裡）。資料庫連線沿用 DB_HOST、DB_PORT 等環境變數。
報告含真實姓名與訊息，請輸出到 repo 以外的地方，不要 commit。

用法：
    DB_HOST=192.168.11.11 uv run python scripts/replay_history.py > /tmp/replay.txt
    DB_HOST=... uv run python scripts/replay_history.py --since 2026-06-01

規則解析不了的訊息在正式環境會交給 AI，這裡只列出來，不模擬 AI。
菜單用的是目前的菜單；店家改過菜名時，舊訊息可能對不到。
"""
import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.services.order_parser import (  # noqa: E402
    AddItem, CancelAll, ChooseCandidate, CopyLast, Menu, MenuEntry, ReduceItem,
    SetOrder, SwitchOption, _base, is_restatement, looks_like_chatter, normalize_text, parse_message,
)


async def load(conn, since):
    menus: dict[str, Menu] = {}
    rows = (await conn.execute(text("""
        select m.store_id, i.id, i.name, i.price, c.name
        from menu_items i join menu_categories c on c.id = i.category_id join menus m on m.id = c.menu_id
        order by c.sort_order, i.sort_order
    """))).all()
    by_store = defaultdict(list)
    for store_id, iid, name, price, cat in rows:
        by_store[str(store_id)].append(MenuEntry(str(iid), name, float(price), cat or ""))
    menus = {k: Menu(v) for k, v in by_store.items()}

    msgs = (await conn.execute(text("""
        with st as (
          select distinct on (session_id) session_id, store_id from orders order by session_id, created_at
        )
        select c.session_id, st.store_id, c.created_at, coalesce(u.display_name, '?'), c.role, c.content
        from chat_messages c
        join st on st.session_id = c.session_id
        left join users u on u.id = c.user_id
        where c.role = 'user' and c.created_at >= :since
        order by c.created_at
    """), {"since": since})).all()

    stored = (await conn.execute(text("""
        select o.session_id, coalesce(u.display_name, '?'), i.name, i.quantity, coalesce(i.note, '')
        from order_items i join orders o on o.id = i.order_id left join users u on u.id = o.user_id
        join order_sessions s on s.id = o.session_id where s.started_at >= :since
    """), {"since": since})).all()
    return menus, msgs, stored


def _key(menu: Menu, op: AddItem) -> tuple[str, str]:
    return _base(menu.display(op.entry, op.choice).split("（")[0]), op.proxy


def simulate(menu: Menu, orders: dict, who: str, ops, last_item: dict) -> None:
    mine: Counter = orders[who]
    # 與正式流程相同的重列判斷
    if ops and all(isinstance(o, AddItem) for o in ops):
        existing = {k: v for k, v in mine.items() if v}
        adds = [(*_key(menu, o), o.quantity, o.additive) for o in ops]
        if is_restatement(existing, adds):
            mine.clear()
    for op in ops:
        if isinstance(op, AddItem):
            key = _key(menu, op)
            mine[key] += op.quantity
            last_item[who] = key
            last_item["_any"] = (who, key)
        elif isinstance(op, ReduceItem):
            if op.query is None:
                key = last_item.get(who)
            else:
                cands = [k for k in mine if _base(op.query) in k[0] or k[0] in _base(op.query)]
                key = cands[0] if cands else None
            if key and key in mine:
                mine[key] = 0 if op.quantity is None else max(0, mine[key] - op.quantity)
        elif isinstance(op, CancelAll):
            mine.clear()
        elif isinstance(op, CopyLast):
            any_last = last_item.get("_any")
            if any_last and any_last[0] != who:
                mine[(any_last[1][0], "")] += op.quantity
        elif isinstance(op, SetOrder):
            mine.clear()
            simulate(menu, orders, who, op.items, last_item)
        elif isinstance(op, (SwitchOption, ChooseCandidate)):
            pass


def normalize_stored(name: str, note: str) -> tuple[str, str]:
    # 舊資料：「炸排骨飯/麵」＋ note「飯」；新資料：「炸排骨飯」
    if name.endswith("飯/麵"):
        name = name[:-3] + (note if note in ("飯", "麵") else "飯")
        note = ""
    name = name.split("（")[0]
    return _base(name), ("" if note in ("飯", "麵") else note)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2025-01-01")
    args = ap.parse_args()

    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        await conn.execute(text("set transaction read only"))
        from datetime import datetime
        menus, msgs, stored = await load(conn, datetime.fromisoformat(args.since))
        await conn.rollback()
    await engine.dispose()

    sim: dict[str, dict] = defaultdict(lambda: defaultdict(Counter))
    last: dict[str, dict] = defaultdict(dict)
    unparsed: dict[str, list] = defaultdict(list)
    stats = Counter()
    for session_id, store_id, created_at, who, _role, content in msgs:
        sid = str(session_id)
        menu = menus.get(str(store_id))
        txt = normalize_text(content)
        if not menu or looks_like_chatter(txt, False):
            stats["略過"] += 1
            continue
        res = parse_message(txt, menu)
        if res is None or res.needs_choice:
            stats["交給 AI" if res is None else "需要選擇"] += 1
            unparsed[sid].append(f"{created_at:%m-%d %H:%M} {who}：{txt[:40]}")
            continue
        stats["規則處理"] += 1
        simulate(menu, sim[sid], who, res.ops, last[sid])

    actual: dict[str, dict] = defaultdict(lambda: defaultdict(Counter))
    for session_id, who, name, qty, note in stored:
        actual[str(session_id)][who][normalize_stored(name, note)] += qty

    print("訊息統計：", dict(stats))
    sessions = sorted(set(sim) | set(actual), key=lambda s: min(
        (m[2] for m in msgs if str(m[0]) == s), default=None) or "")
    diff_count = 0
    for sid in sessions:
        lines = []
        for who in sorted(set(sim[sid]) | set(actual[sid])):
            a = {k: v for k, v in actual[sid][who].items() if v}
            b = {k: v for k, v in sim[sid][who].items() if v}
            if a != b:
                fmt = lambda d: "、".join(f"{n}{'(' + p + ')' if p else ''}×{q}" for (n, p), q in sorted(d.items())) or "（無）"
                lines.append(f"  {who}\n    實際存下：{fmt(a)}\n    新流程　：{fmt(b)}")
        if lines:
            diff_count += 1
            first = next((m[2] for m in msgs if str(m[0]) == sid), None)
            print(f"\n== {first:%Y-%m-%d} session {sid[:8]}" if first else f"\n== session {sid[:8]}")
            print("\n".join(lines))
            if unparsed[sid]:
                print("  交給 AI 的訊息：\n    " + "\n    ".join(unparsed[sid]))
    print(f"\n有差異的點餐：{diff_count} / {len(sessions)}")


if __name__ == "__main__":
    asyncio.run(main())
