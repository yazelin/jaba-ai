"""群組點餐訊息規則解析器

純函式模組：輸入訊息文字與今日菜單，輸出結構化的訂單操作。
不碰資料庫、不呼叫 AI，方便測試與歷史重播。

解析不了就回傳 None，交給 AI 處理。
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional, Union


# ========== 菜單 ==========

# 類別優先順序：使用者沒指定時，便當類優先於單點類
_LOW_PRIORITY_CATEGORY = ("單點", "其他", "小菜", "配菜", "湯", "切盤", "飲料", "特價")


def category_rank(category: str) -> int:
    if "便當" in category:
        return 0
    if any(k in category for k in _LOW_PRIORITY_CATEGORY):
        return 2
    return 1


@dataclass(frozen=True)
class MenuEntry:
    """菜單上一個可點的品項"""
    item_id: str
    name: str            # 菜單上的原始名稱，如「炸排骨飯/麵」
    price: float
    category: str = ""

    @property
    def rank(self) -> int:
        return category_rank(self.category)

    @property
    def has_rice_noodle_choice(self) -> bool:
        return self.name.endswith("飯/麵")


# 比對用的同音、錯字對照（只用在比對，不改顯示名稱）
_CHAR_MAP = str.maketrans({
    "焢": "控", "爌": "控",
    "販": "飯",
    "増": "噌", "增": "噌",
    "臺": "台",
})
_WORD_MAP = [
    ("宮本", "宮保"),
    ("梁酒", "高粱酒"),
]


def _key(s: str) -> str:
    """比對用正規化：去空白、錯字對照"""
    s = re.sub(r"\s+", "", s).translate(_CHAR_MAP)
    for wrong, right in _WORD_MAP:
        s = s.replace(wrong, right)
    return s


def _base(s: str) -> str:
    """去掉結尾的飯、麵、便當，取得菜色本體"""
    s = _key(s)
    s = re.sub(r"(飯/麵|飯麵|便當|飯|麵)$", "", s)
    return s


def display_name(entry: MenuEntry, choice: Optional[str], duplicated: bool) -> str:
    """訂單上顯示的品項名稱"""
    name = entry.name
    if entry.has_rice_noodle_choice:
        name = name[: -len("飯/麵")] + (choice if choice in ("飯", "麵") else "飯")
    if duplicated and entry.category:
        short = "單點" if "單點" in entry.category else entry.category
        name = f"{name}（{short}）"
    return name


class Menu:
    """今日菜單索引"""

    def __init__(self, entries: list[MenuEntry]):
        self.entries = entries
        names = [e.name for e in entries]
        self._dup_names = {n for n in names if names.count(n) > 1}

    def is_duplicated(self, entry: MenuEntry) -> bool:
        return entry.name in self._dup_names

    def display(self, entry: MenuEntry, choice: Optional[str] = None) -> str:
        return display_name(entry, choice, self.is_duplicated(entry))

    def match(self, query: str, category_hint: Optional[str] = None) -> "MatchResult":
        """把使用者寫的品項名稱對到菜單

        比對順序：菜色本體相同 → 菜單本體包含輸入（唯一）→ 輸入包含菜單本體（取最長）
        同一層有多個候選時，用類別優先順序挑；還是多個就回傳候選讓使用者選。
        """
        q = _key(query)
        qb = _base(query)
        if not qb:
            return MatchResult()

        pool = self.entries
        if category_hint:
            hinted = [e for e in pool if category_hint in e.category]
            if hinted:
                pool = hinted

        tiers = [
            [e for e in pool if _key(e.name) == q or _base(e.name) == qb],
            [e for e in pool if qb in _base(e.name)],
        ]
        # 輸入比菜名長時（如「玫瑰油雞腿」對「玫瑰油雞」），最多容許多 2 個字，
        # 避免「雙饗銷魂飯是什麼」這類問句被當成點餐
        contained = [
            e for e in pool
            if _base(e.name) and _base(e.name) in qb and len(qb) - len(_base(e.name)) <= 2
        ]
        if contained:
            longest = max(len(_base(e.name)) for e in contained)
            tiers.append([e for e in contained if len(_base(e.name)) == longest])

        for cands in tiers:
            if not cands:
                continue
            picked = _pick(cands)
            if picked:
                return MatchResult(entry=picked)
            return MatchResult(candidates=_unique_by_display(cands, self))
        return MatchResult()


def _pick(cands: list[MenuEntry]) -> Optional[MenuEntry]:
    if len(cands) == 1:
        return cands[0]
    best = min(e.rank for e in cands)
    top = [e for e in cands if e.rank == best]
    return top[0] if len(top) == 1 else None


def _unique_by_display(cands: list[MenuEntry], menu: Menu) -> list[MenuEntry]:
    seen, out = set(), []
    for e in sorted(cands, key=lambda e: e.rank):
        d = menu.display(e)
        if d not in seen:
            seen.add(d)
            out.append(e)
    return out


@dataclass
class MatchResult:
    entry: Optional[MenuEntry] = None
    candidates: list[MenuEntry] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.entry is not None

    @property
    def ambiguous(self) -> bool:
        return self.entry is None and len(self.candidates) > 1


# ========== 操作 ==========

@dataclass
class AddItem:
    entry: MenuEntry
    quantity: int = 1
    proxy: str = ""            # 代訂對象
    choice: Optional[str] = None  # 飯或麵；None 表示用預設
    defaulted: bool = False    # 是否用了預設選項（回覆時提示）
    additive: bool = False     # 明講「再加」「追加」，一定是追加，不當成重列


@dataclass
class ReduceItem:
    """減少本人已點的品項；比對對象是本人訂單，不是菜單"""
    query: Optional[str]        # None 表示「本人最後點的那項」
    quantity: Optional[int]     # None 表示全部
    proxy: str = ""


@dataclass
class CancelAll:
    pass


@dataclass
class CopyLast:
    quantity: int = 1


@dataclass
class SwitchOption:
    """把本人最後一項改成另一個選項，如「單點」「麵」"""
    option: str


@dataclass
class ChooseCandidate:
    index: int


@dataclass
class SetOrder:
    """以清單取代本人整份訂單"""
    items: list[AddItem]


Op = Union[AddItem, ReduceItem, CancelAll, CopyLast, SwitchOption, ChooseCandidate, SetOrder]


@dataclass
class ParseResult:
    ops: list[Op] = field(default_factory=list)
    # 品項有多個候選時，只回傳第一個需要使用者選的
    ambiguous_query: str = ""
    candidates: list[MenuEntry] = field(default_factory=list)
    pending_add: Optional[AddItem] = None  # 選完候選後要套用的數量、代訂

    @property
    def needs_choice(self) -> bool:
        return bool(self.candidates)


# ========== 文字正規化 ==========

_BOT_MENTION = re.compile(r"^\s*@\s*(jaba\s*呷爸|呷爸|jaba)\s*", re.IGNORECASE)


def normalize_text(text: str, bot_mention_spans: Optional[list[tuple[int, int]]] = None) -> str:
    """去掉提及呷爸的標記、全形轉半形、去頭尾空白

    bot_mention_spans: LINE webhook 提供的 (index, length)，isSelf 的那幾段
    """
    if bot_mention_spans:
        for idx, length in sorted(bot_mention_spans, reverse=True):
            text = text[:idx] + " " + text[idx + length:]
    text = _BOT_MENTION.sub("", text)
    # NFKC：全形英數、符號轉半形（中文標點的（）：也會轉成 ():）
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


_URL = re.compile(r"https?://", re.IGNORECASE)


def looks_like_chatter(text: str, mentions_others: bool) -> bool:
    """明顯不是點餐、也不用問 AI 的訊息"""
    if mentions_others or text.startswith("@"):
        return True
    if _URL.search(text):
        return True
    if len(text) > 60:
        return True
    return False


# ========== 數量 ==========

_CN_NUM = {"一": 1, "二": 2, "兩": 2, "倆": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
MAX_QTY = 20


def _num(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    if s.isdigit():
        return int(s)
    return _CN_NUM.get(s)


_NUM = r"(\d+|[一二兩倆三四五六七八九十])"
_UNIT = r"(?:個|份|盒|碗|杯)?"
_OPTION_WORDS = {"飯", "麵", "便當", "單點"}

# 句子開頭的贅字（不影響意思）
_FILLERS = re.compile(
    r"^(那|那我|我今天也要吃便當|我想訂一個|我想訂|我要點|幫我點|我也要|我要|要|點|再來|再)+"
)
_ADDITIVE = re.compile(r"^(我)?(再|追加|多加|加點|加)")


# ========== 單一品項片段 ==========

_SEG_QTY_TAIL = re.compile(rf"\s*(?:[+*xX×]\s*{_NUM}\s*{_UNIT}|\+)\s*$")
_SEG_QTY_HEAD = re.compile(rf"^(?:再多加|多加|追加|再加|加|再)?\s*{_NUM}\s*{_UNIT}(?=\D)")
_PAREN = re.compile(r"\(([^()]{1,10})\)")
_PRICE = re.compile(r"\$\s*\d+|\d+\s*元")


@dataclass
class _Seg:
    name: str
    quantity: int
    explicit_qty: bool
    proxy: str
    option: Optional[str]
    additive: bool = False


def _parse_segment(seg: str, line_proxy: str) -> Optional[_Seg]:
    seg = _PRICE.sub("", seg).strip().rstrip(".。~～!！")
    seg = re.sub(r"好了$", "", seg)
    additive = bool(_ADDITIVE.match(seg))
    proxy = line_proxy
    option = None

    # 括號：選項或代訂對象
    for m in _PAREN.finditer(seg):
        inner = m.group(1).strip()
        if inner in _OPTION_WORDS:
            option = inner
        elif inner:
            proxy = inner
    seg = _PAREN.sub("", seg).strip()

    seg = _FILLERS.sub("", re.sub(r"^我", "", seg)).strip()
    m = re.match(r"^(單點|便當)(?=.{2,})", seg)
    if m:
        option, seg = m.group(1), seg[m.end():]

    qty, explicit = 1, False
    m = _SEG_QTY_TAIL.search(seg)
    if m:
        n = _num(m.group(1)) if m.group(1) else 1
        qty, explicit = (n if n is not None else 1), True
        seg = seg[: m.start()].strip()
    else:
        m = _SEG_QTY_HEAD.search(seg)
        if m:
            qty, explicit = _num(m.group(1)) or 1, True
            seg = seg[m.end():].strip()

    seg = _FILLERS.sub("", seg).strip()
    # 結尾的「便當」「單點」當作選項
    m = re.search(r"(便當|單點)$", seg)
    if m and len(seg) > 2:
        option = option or m.group(1)

    if not seg or len(seg) > 14:
        return None
    if not re.fullmatch(r"[一-鿿A-Za-z/]+", seg):
        return None
    return _Seg(seg, qty, explicit, proxy, option, additive)


def _split_segments(line: str) -> list[str]:
    """一行拆成多個品項片段

    「+」後面接數字是數量，後面接品項是分隔。
    數量、選項、代訂括號若被空白隔開，併回前一段。
    """
    line = re.sub(r"\+(?=\s*[^\d\s])", " ", line)
    raw = [t for t in re.split(r"[\s,、]+", line) if t]
    out: list[str] = []
    for t in raw:
        attach = (
            re.fullmatch(rf"(?:[+*xX×]\s*{_NUM}?\s*{_UNIT})", t)
            or t in _OPTION_WORDS
            or re.fullmatch(r"\([^()]{1,10}\)", t)
            or _PRICE.fullmatch(t)
        )
        if attach and out:
            out[-1] += t
        else:
            out.append(t)
    return out


# ========== 整則訊息 ==========

_CANCEL_ALL = re.compile(r"^(幫我)?(取消|全部取消|取消全部|取消訂單)$|^(我)?(不要了|不用了|算了)$")
_COPY = re.compile(rf"^(\+\s*{_NUM}?|我也要|同上|跟單)$")
_MINUS = re.compile(rf"^-\s*{_NUM}$")
_REDUCE_HEAD = re.compile(rf"^(?:再)?(?:少|減|取消|扣)\s*{_NUM}?\s*{_UNIT}\s*(.+)$")
_REDUCE_TAIL = re.compile(rf"^(.+?)\s*(?:少|減|取消)\s*{_NUM}?\s*{_UNIT}$")
_REDUCE_X = re.compile(rf"^(?:少|減)\s*(.+?)\s*[*xX×]\s*{_NUM}$")
_NOT_WANT = re.compile(r"^(?:我)?不要(.+?)了?$")
_NOT_WANT_TAIL = re.compile(r"^(.+?)不要了?$")
_CHANGE = re.compile(r"^(.*?)\s*改\s*(?:成|為|點)?\s*(.+)$")
_OPTION_REPLY = re.compile(r"^(飯|麵|便當|單點)[啦喔呀丫]*(好了)?\.*$|^要(便當|單點)$")
_CHOICE_REPLY = re.compile(r"^(\d)$")
_HAS_QTY_MARK = re.compile(rf"[+*xX×]\s*{_NUM}|\d+\s*{_UNIT}\S")


def has_quantity_mark(text: str) -> bool:
    return bool(_HAS_QTY_MARK.search(text))


def parse_message(text: str, menu: Menu, *, awaiting_choice: bool = False) -> Optional[ParseResult]:
    """解析一則群組訊息

    回傳 None 表示規則看不懂，交給 AI。
    """
    text = text.strip()
    if not text:
        return None

    if awaiting_choice:
        m = _CHOICE_REPLY.match(text)
        if m:
            return ParseResult(ops=[ChooseCandidate(int(m.group(1)))])

    one_line = re.sub(r"\s+", "", text)
    if _CANCEL_ALL.match(one_line):
        return ParseResult(ops=[CancelAll()])
    m = _COPY.match(one_line)
    if m:
        return ParseResult(ops=[CopyLast(_num(m.group(2)) or 1)])
    m = _MINUS.match(one_line)
    if m:
        return ParseResult(ops=[ReduceItem(query=None, quantity=_num(m.group(1)))])
    m = _OPTION_REPLY.match(one_line)
    if m:
        return ParseResult(ops=[SwitchOption(m.group(1) or m.group(3))])

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    result = ParseResult()
    inherit = False
    for line in lines:
        kind = _parse_line(line, menu, result, inherit_reduce=inherit)
        if kind is None:
            return None
        inherit = kind == "reduce_head"
        if result.needs_choice:
            break
    return result if (result.ops or result.needs_choice) else None


def _resolve(seg: _Seg, menu: Menu, result: ParseResult) -> Optional[AddItem]:
    """片段對到菜單；多候選時寫進 result 並回傳 None"""
    hint = "單點" if seg.option == "單點" else ("便當" if seg.option == "便當" else None)
    name = seg.name
    if seg.option in ("便當", "單點") and name.endswith(seg.option) and len(name) > 2:
        stripped = name[: -len(seg.option)]
        # 「鯖魚便當」本身就是菜單品項時保留原名
        if not menu.match(name).ok or seg.option == "單點":
            name = stripped
    mr = menu.match(name, category_hint=hint)
    choice = None
    if seg.option in ("飯", "麵"):
        choice = seg.option
    elif seg.name.endswith("麵"):
        choice = "麵"
    elif seg.name.endswith("飯"):
        choice = "飯"

    add = AddItem(entry=None, quantity=seg.quantity, proxy=seg.proxy, choice=choice,  # type: ignore[arg-type]
                  additive=seg.additive)
    if mr.ambiguous:
        result.ambiguous_query = seg.name
        result.candidates = mr.candidates
        result.pending_add = add
        return None
    if not mr.ok:
        return False  # type: ignore[return-value]
    add.entry = mr.entry
    add.defaulted = (
        (mr.entry.has_rice_noodle_choice and choice is None)
        or (menu.is_duplicated(mr.entry) and hint is None)
    )
    return add


def _old_query(raw: str, line_proxy: str) -> tuple[Optional[str], Optional[int], str]:
    """「改」「少」左邊的品項；回傳 (品項, 數量, 代訂)。品項為 None 表示沒寫"""
    seg = _parse_segment(raw, line_proxy) if raw else None
    if not seg:
        return None, None, line_proxy
    return seg.name, (seg.quantity if seg.explicit_qty else None), seg.proxy


def _parse_line(line: str, menu: Menu, result: ParseResult, inherit_reduce: bool = False) -> Optional[str]:
    """解析一行

    回傳 None 表示看不懂；成功時回傳這行的種類（"add"、"reduce_head"、"reduce"、"change"），
    「少雞滷飯 x3」下一行沒寫動詞的品項沿用減少。
    """
    line = _PRICE.sub(" ", line).strip()
    line_proxy = ""
    m = re.match(r"^([^\s:()]{1,8})\s*:\s*(.+)$", line)
    if m:
        line_proxy, line = m.group(1), m.group(2)

    compact = re.sub(r"\s+", "", line)

    # 改：「蔥油雞*3改蔥爆豬*3」「改炸雞腿」
    m = _CHANGE.match(compact)
    if m and "改" in compact:
        old, new = _FILLERS.sub("", m.group(1)), m.group(2)
        new_res = ParseResult()
        if _parse_line(new, menu, new_res) not in ("add",) or not (new_res.ops or new_res.needs_choice):
            return None
        name, qty, proxy = _old_query(old, line_proxy)
        if old and name is None:
            return None
        result.ops.append(ReduceItem(name, qty, proxy))
        if new_res.needs_choice:
            result.candidates = new_res.candidates
            result.ambiguous_query = new_res.ambiguous_query
            result.pending_add = new_res.pending_add
        result.ops.extend(new_res.ops)
        return "change"

    # 減少、取消單一品項
    patterns = (
        (_REDUCE_X, 1, 2, "reduce_head"),
        (_REDUCE_HEAD, 2, 1, "reduce_head"),
        (_REDUCE_TAIL, 1, 2, "reduce"),
        (_NOT_WANT, 1, None, "reduce"),
        (_NOT_WANT_TAIL, 1, None, "reduce"),
    )
    for pat, name_g, qty_g, kind in patterns:
        m = pat.match(compact)
        if not m:
            continue
        seg = _parse_segment(m.group(name_g), line_proxy)
        if not seg:
            return None
        qty = _num(m.group(qty_g)) if qty_g else None
        if qty is None and seg.explicit_qty:
            qty = seg.quantity
        result.ops.append(ReduceItem(seg.name, qty, seg.proxy))
        return kind

    segs = _split_segments(line)
    if not segs:
        return None

    # 沿用上一行的「少」
    if inherit_reduce:
        for raw in segs:
            seg = _parse_segment(raw, line_proxy)
            if not seg:
                return None
            result.ops.append(ReduceItem(seg.name, seg.quantity if seg.explicit_qty else None, seg.proxy))
        return "reduce_head"

    # 一般點餐：一或多個品項
    for raw in segs:
        seg = _parse_segment(raw, line_proxy)
        if not seg:
            return None
        if seg.quantity < 1 or seg.quantity > MAX_QTY:
            return None
        add = _resolve(seg, menu, result)
        if add is None:          # 多候選，等使用者選
            return "add"
        if add is False:         # 對不到菜單
            return None
        result.ops.append(add)
    return "add"


# ========== 重列判斷 ==========

def is_restatement(existing: dict, adds: list) -> bool:
    """這則點餐是不是把自己原本點的再列一次

    existing: {(品項顯示名稱, 代訂): 數量}，本人目前的訂單
    adds: [(品項顯示名稱, 代訂, 數量, 是否明講追加)]，這則訊息

    原本點的每一項都出現在這則訊息、而且數量完全相同 → 視為重列（不重複加）。
    歷史上「機器人沒回就再傳一次」「把整份清單重貼」都是這種情況。
    數量不同就當追加：「銷魂飯」之後「銷魂飯*3」實際是再幫別人點 3 份（08-13），
    少算比多算嚴重，而且確認行會顯示總數，點錯可以馬上改。
    明講「再加」「追加」的永遠是追加。
    """
    if not existing or not adds or any(a[3] for a in adds):
        return False
    msg: dict = {}
    for name, proxy, qty, _ in adds:
        msg[(name, proxy)] = msg.get((name, proxy), 0) + qty
    return all(msg.get(k) == q for k, q in existing.items())
