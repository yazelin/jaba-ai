"""規則解析器測試

寫法取自實際群組訊息，人名換成通用稱呼。菜單是店家公開菜單的節錄。
"""
import pytest

from app.services.order_parser import (
    AddItem,
    CancelAll,
    ChooseCandidate,
    CopyLast,
    Menu,
    MenuEntry,
    ReduceItem,
    SwitchOption,
    has_quantity_mark,
    is_restatement,
    looks_like_chatter,
    normalize_text,
    parse_message,
)


def _menu(rows):
    return Menu([MenuEntry(str(i), n, p, c) for i, (c, n, p) in enumerate(rows)])


# 便當與單點同名
JIAXIANG = _menu([
    ("便當", "炸雞腿", 125), ("便當", "古早味排骨", 110), ("便當", "蔥爆豬", 105),
    ("便當", "鯖魚便當", 105), ("便當", "鱈魚飯", 105), ("便當", "鹹豬肉", 105),
    ("便當", "蔥油雞", 105), ("便當", "宮保雞丁", 105), ("便當", "紅燒焢肉", 105),
    ("便當", "高粱酒香腸", 105),
    ("單點類", "炸雞腿", 80), ("單點類", "鯖魚", 60), ("單點類", "鱈魚", 60),
    ("單點類", "古早味排骨", 70), ("單點類", "鹹豬肉", 60), ("單點類", "高粱酒香腸", 35),
])
# 飯/麵 二選一
LIANG = _menu([
    ("招牌商品", "炸排骨飯/麵", 125), ("人氣商品", "椒麻雞飯/麵", 138),
    ("人氣商品", "炸雞腿飯/麵", 128), ("主餐", "椒鹽雞塊飯/麵", 95),
    ("主餐", "玫瑰油雞飯/麵", 128), ("主餐", "控肉飯/麵", 99),
    ("主餐", "炸紅糟肉飯/麵", 105), ("湯品", "味噌湯", 20),
])
CHICKEN = _menu([
    ("便當類", "雞腿飯", 130), ("便當類", "雞肉飯", 110), ("便當類", "黯然飯", 105),
    ("便當類", "雞滷飯", 85), ("便當類", "銷魂飯", 75), ("便當類", "雙饗銷魂飯", 115),
    ("便當類", "燒肉飯", 100), ("去骨雞肉切盤", "雞腿(小)", 100), ("其他", "燒肉", 55),
])
TANJI = _menu([
    ("便當", "炸雞腿飯", 110), ("便當", "炸排骨飯", 100), ("便當", "滷雞腿飯", 110),
    ("便當", "滷排骨飯", 100), ("便當", "宮保雞丁飯", 100), ("便當", "魚排飯", 100),
])


def adds(result):
    return [(o.entry.name, o.quantity, o.proxy) for o in result.ops if isinstance(o, AddItem)]


def one_add(text, menu):
    r = parse_message(text, menu)
    assert r is not None, text
    a = adds(r)
    assert len(a) == 1, (text, a)
    return a[0]


# ---------- 正規化 ----------

@pytest.mark.parametrize("raw,expected", [
    ("@jaba 呷爸 菜單", "菜單"),
    ("@呷爸 help", "help"),
    ("@jaba 呷爸 help", "help"),
    ("椒鹽雞塊飯/麵（飯）", "椒鹽雞塊飯/麵(飯)"),
    ("  開單 ", "開單"),
])
def test_normalize(raw, expected):
    assert normalize_text(raw) == expected


def test_normalize_with_line_mention_span():
    assert normalize_text("@呷爸 今日", [(0, 3)]) == "今日"


def test_chatter():
    assert looks_like_chatter("@某同事 110", mentions_others=True)
    assert looks_like_chatter("http://jaba.ui/", mentions_others=False)
    assert looks_like_chatter("各位同事，" + "飲水機" * 20, mentions_others=False)
    assert not looks_like_chatter("炸排骨+1", mentions_others=False)


# ---------- 點餐 ----------

@pytest.mark.parametrize("text,menu,expected", [
    ("炸排骨+1", TANJI, ("炸排骨飯", 1, "")),
    ("炸排骨飯", TANJI, ("炸排骨飯", 1, "")),
    ("炸排骨飯+", TANJI, ("炸排骨飯", 1, "")),
    ("炸雞腿+1...", TANJI, ("炸雞腿飯", 1, "")),
    ("宮本雞丁飯", TANJI, ("宮保雞丁飯", 1, "")),
    ("銷魂飯*5", CHICKEN, ("銷魂飯", 5, "")),
    ("黯然", CHICKEN, ("黯然飯", 1, "")),
    ("雙饗銷魂飯 $105+1", CHICKEN, ("雙饗銷魂飯", 1, "")),
    ("燒肉飯", CHICKEN, ("燒肉飯", 1, "")),
    ("雞腿飯", CHICKEN, ("雞腿飯", 1, "")),
    ("古早味排骨 x4", JIAXIANG, ("古早味排骨", 4, "")),
    ("古早味排骨飯*1", JIAXIANG, ("古早味排骨", 1, "")),
    ("排骨便當", JIAXIANG, ("古早味排骨", 1, "")),
    (" 蔥爆豬 $105 +1", JIAXIANG, ("蔥爆豬", 1, "")),
    ("蔥爆豬 便當 $105 +1", JIAXIANG, ("蔥爆豬", 1, "")),
    ("紅燒焢肉 $105 +1", JIAXIANG, ("紅燒焢肉", 1, "")),
    ("鯖魚便當*1", JIAXIANG, ("鯖魚便當", 1, "")),
    ("控肉販", LIANG, ("控肉飯/麵", 1, "")),
    ("椒麻雞飯+1", LIANG, ("椒麻雞飯/麵", 1, "")),
    ("玫瑰油雞腿飯+1", LIANG, ("玫瑰油雞飯/麵", 1, "")),
    ("椒鹽雞飯*2", LIANG, ("椒鹽雞塊飯/麵", 2, "")),
    ("雞塊飯", LIANG, ("椒鹽雞塊飯/麵", 1, "")),
    ("椒鹽雞塊飯/麵（飯）", LIANG, ("椒鹽雞塊飯/麵", 1, "")),
    ("椒鹽雞塊飯/麵 $95（飯）", LIANG, ("椒鹽雞塊飯/麵", 1, "")),
    ("紅糟肉飯*3(老闆)", LIANG, ("炸紅糟肉飯/麵", 3, "老闆")),
    ("椒鹽雞塊*3 (老闆)", LIANG, ("椒鹽雞塊飯/麵", 3, "老闆")),
    ("炸雞腿飯（同事A）*1", TANJI, ("炸雞腿飯", 1, "同事A")),
    ("同事B:古早味排骨*1", JIAXIANG, ("古早味排骨", 1, "同事B")),
    ("同事C：銷魂飯 $70", CHICKEN, ("銷魂飯", 1, "同事C")),
    ("我要雞腿飯", CHICKEN, ("雞腿飯", 1, "")),
    ("再加一個黯然飯", CHICKEN, ("黯然飯", 1, "")),
    ("我追加3個椒鹽雞塊飯", LIANG, ("椒鹽雞塊飯/麵", 3, "")),
])
def test_single_add(text, menu, expected):
    assert one_add(normalize_text(text), menu) == expected


def test_default_bento_over_single_item():
    r = parse_message("炸雞腿+1", JIAXIANG)
    add = r.ops[0]
    assert add.entry.category == "便當" and add.entry.price == 125
    assert add.defaulted
    assert JIAXIANG.display(add.entry) == "炸雞腿（便當）"


def test_explicit_single_item():
    r = parse_message("單點炸雞腿", JIAXIANG) or parse_message("炸雞腿單點", JIAXIANG)
    assert r is not None
    assert r.ops[0].entry.price == 80


def test_rice_default_and_noodle():
    rice = parse_message("炸雞腿", LIANG).ops[0]
    assert rice.defaulted and LIANG.display(rice.entry, rice.choice) == "炸雞腿飯"
    noodle = parse_message("炸雞腿麵", LIANG).ops[0]
    assert not noodle.defaulted and LIANG.display(noodle.entry, noodle.choice) == "炸雞腿麵"


@pytest.mark.parametrize("text,menu,expected", [
    ("黯然飯*1\n銷魂飯*1", CHICKEN, [("黯然飯", 1, ""), ("銷魂飯", 1, "")]),
    ("黯然飯 *3+銷魂飯 *1", CHICKEN, [("黯然飯", 3, ""), ("銷魂飯", 1, "")]),
    ("黯然*6 銷魂飯*1", CHICKEN, [("黯然飯", 6, ""), ("銷魂飯", 1, "")]),
    ("炸雞腿飯+1 炸排骨飯+3", TANJI, [("炸雞腿飯", 1, ""), ("炸排骨飯", 3, "")]),
    ("玫瑰油雞+味噌湯", LIANG, [("玫瑰油雞飯/麵", 1, ""), ("味噌湯", 1, "")]),
    ("銷魂飯(小李)*1  黯然飯(小金)*1", CHICKEN, [("銷魂飯", 1, "小李"), ("黯然飯", 1, "小金")]),
    ("炸雞腿*1\n鹹豬肉*4", JIAXIANG, [("炸雞腿", 1, ""), ("鹹豬肉", 4, "")]),
])
def test_multi_add(text, menu, expected):
    r = parse_message(normalize_text(text), menu)
    assert r is not None and adds(r) == expected


def test_ambiguous_asks():
    r = parse_message("雞腿飯", TANJI)
    assert r.needs_choice
    assert {e.name for e in r.candidates} == {"炸雞腿飯", "滷雞腿飯"}


def test_choice_reply_only_when_awaiting():
    assert isinstance(parse_message("2", TANJI, awaiting_choice=True).ops[0], ChooseCandidate)
    assert parse_message("2", TANJI) is None


@pytest.mark.parametrize("text", [
    "帶骨牛小排飯", "滿漢全席", "我不用", "回公司的路上", "是不是有漲價了？",
    "便當來了~可以自己到前面拿", "炸排骨+100", "雙饗銷魂飯是什麼",
])
def test_unparsed_goes_to_ai(text, ):
    menu = CHICKEN if "銷魂" in text else (JIAXIANG if "便當" in text else TANJI)
    assert parse_message(normalize_text(text), menu) is None


# ---------- 減少、取消、改 ----------

def reduce_ops(text, menu=CHICKEN):
    r = parse_message(normalize_text(text), menu)
    assert r is not None, text
    return [(o.query, o.quantity, o.proxy) for o in r.ops if isinstance(o, ReduceItem)]


@pytest.mark.parametrize("text,expected", [
    ("少一個蔥油雞", [("蔥油雞", 1, "")]),
    ("炸排骨少3個", [("炸排骨", 3, "")]),
    ("銷魂飯少兩個", [("銷魂飯", 2, "")]),
    ("少雞滷飯 x3 $255\n銷魂飯 *1", [("雞滷飯", 3, ""), ("銷魂飯", 1, "")]),
    ("取消一個雞腿飯", [("雞腿飯", 1, "")]),
    ("取消 黯然飯", [("黯然飯", None, "")]),
    ("我不要炸雞腿飯了", [("炸雞腿飯", None, "")]),
    ("椒鹽雞飯不要了", [("椒鹽雞飯", None, "")]),
    ("再少一個排骨飯", [("排骨飯", 1, "")]),
    ("少一個炸雞腿飯（同事A)", [("炸雞腿飯", 1, "同事A")]),
    ("-2", [(None, 2, "")]),
])
def test_reduce(text, expected):
    assert reduce_ops(text) == expected


def test_cancel_all():
    for t in ["取消", "幫我取消", "不要了", "算了"]:
        assert isinstance(parse_message(t, CHICKEN).ops[0], CancelAll), t


def test_change_with_old_item():
    r = parse_message("蔥油雞*3改蔥爆豬*3", JIAXIANG)
    assert isinstance(r.ops[0], ReduceItem) and r.ops[0].query == "蔥油雞" and r.ops[0].quantity == 3
    assert adds(r) == [("蔥爆豬", 3, "")]


def test_change_last_item():
    r = parse_message("改炸雞腿", TANJI)
    assert r.ops[0] == ReduceItem(None, None, "")
    assert adds(r) == [("炸雞腿飯", 1, "")]


def test_copy_and_option_replies():
    assert parse_message("+1", TANJI).ops == [CopyLast(1)]
    assert parse_message("我也要", TANJI).ops == [CopyLast(1)]
    assert parse_message("飯啦..", TANJI).ops == [SwitchOption("飯")]
    assert parse_message("便當啦", TANJI).ops == [SwitchOption("便當")]
    assert parse_message("單點", TANJI).ops == [SwitchOption("單點")]


def test_quantity_mark():
    assert has_quantity_mark("炸排骨+1")
    assert has_quantity_mark("銷魂飯*5")
    assert not has_quantity_mark("家香味")
    assert not has_quantity_mark("梁社漢菜單")


def test_additive_flag():
    assert parse_message("再加一個黯然飯", CHICKEN).ops[0].additive
    assert parse_message("我追加3個椒鹽雞塊飯", LIANG).ops[0].additive
    assert not parse_message("黯然飯+1", CHICKEN).ops[0].additive


def test_filler_na_wo_yao():
    assert one_add("那我要雞腿飯好了", CHICKEN) == ("雞腿飯", 1, "")


@pytest.mark.parametrize("existing,adds,expected", [
    # 重傳同一則
    ({("古早味排骨（便當）", ""): 4}, [("古早味排骨（便當）", "", 4, False)], True),
    # 重貼整份清單（06-08）
    ({("黯然飯", ""): 3, ("雞滷飯", ""): 3, ("銷魂飯", ""): 1},
     [("雞滷飯", "", 3, False), ("銷魂飯", "", 1, False), ("黯然飯", "", 3, False)], True),
    # 數量不同 → 追加（08-13「銷魂飯」之後「銷魂飯*3」是再點 3 份）
    ({("銷魂飯", ""): 1}, [("銷魂飯", "", 3, False)], False),
    # 重貼時多了新品項 → 原本的不重複，新的照加
    ({("黯然飯", ""): 3}, [("黯然飯", "", 3, False), ("雞肉飯", "", 1, False)], True),
    # 點了別的品項 → 追加
    ({("黯然飯", ""): 6}, [("銷魂飯", "", 1, False)], False),
    # 數量比原本少 → 追加（「炸排骨*3」後「炸排骨*2」不是改成 2）
    ({("炸排骨飯", ""): 3}, [("炸排骨飯", "", 2, False)], False),
    # 明講再加
    ({("黯然飯", ""): 1}, [("黯然飯", "", 1, True)], False),
    # 代訂對象不同 → 追加
    ({("銷魂飯", ""): 1}, [("銷魂飯", "小李", 1, False)], False),
    ({}, [("銷魂飯", "", 1, False)], False),
])
def test_restatement(existing, adds, expected):
    assert is_restatement(existing, adds) is expected
