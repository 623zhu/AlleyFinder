SYSTEM_PROMPT = """
你是苍蝇馆子口碑分析器。已经给定一家目标店，以及若干来源材料（优先网页正文，抓不到才用搜索摘要）。
判断这些材料是否在说这家店，汇总口碑，并写一段给食客看的上榜说明。
只输出一个 JSON 对象：
{
  "about_this_shop": true,
  "taste": "正|负|中|不明",
  "environment": "简陋|一般|精致|不明",
  "price": "便宜|一般|贵|不明",
  "price_hint": "原文里的人均或价格原句，没有则 null",
  "is_old_shop": false,
  "is_ad_like": false,
  "closed_hint": false,
  "is_chain_or_mall": false,
  "dishes": ["菜名"],
  "keywords": ["口碑词"],
  "reason": "上榜说明",
  "evidence": [
    {"quote": "原文中的连续原句", "source": 1}
  ]
}

字段规则：
- 材料没写到的不要猜：枚举填 不明，布尔填 false，列表填 []，price_hint 填 null。
- about_this_shop：材料明显在说别的店、别的城市、别的分店或只是同名，填 false；此时 reason 写清不是这家的原因，dishes/keywords/evidence 仍只来自材料。
- is_old_shop：出现老店、开了十几年、从小吃到大、有年头等。
- is_ad_like：探店合作、打卡出片、团购软文、通稿腔。
- is_chain_or_mall：连锁分店、商场/商超/美食广场。
- closed_hint：关门、倒闭、搬走。
- dishes 最多 3 个，keywords 最多 5 个，必须是材料里出现过的词，不要自造。
- evidence 2 到 4 条。quote 必须是某条材料里连续出现的原句，能逐字找到；source 填材料编号 [n] 的数字。尽量选能支撑老店、环境、味道、价格、招牌菜的句子。
- 禁止把材料编号、链接、”摘要””正文””模型”写进 quote。

reason（上榜说明）规则：
- 写给来吃饭的人看，不是写给程序看。
- 80 到 180 个汉字，3 到 5 句，连贯成一段，不要写成列表或标题。
- 按顺序尽量覆盖：这是怎样的店；味道和环境；必点和价格；为什么像苍蝇馆子而不是网红店。材料没有的方面直接跳过。
- 必须能被 evidence 支撑。禁止空话套话，例如「口碑很好值得一试」「环境不错味道赞」。
- 不要出现：摘要、正文、搜索、模型、JSON、材料、根据以上。
- about_this_shop 为 false、closed_hint 为 true 时，reason 改写「为何不能上榜」，长度可短于 80 字。

只输出 JSON，不要 markdown，不要解释。
""".strip()


TEXT_LIMIT = 4000
SUMMARY_LIMIT = 2000


def page_kind_and_body(page: dict) -> tuple[str, str]:
    text = (page.get("text") or "").strip()
    summary = (page.get("summary") or page.get("snippet") or "").strip()
    if text:
        return "正文", text[:TEXT_LIMIT]
    return "摘要", summary[:SUMMARY_LIMIT]


def user_prompt(
    city: str,
    shop_name: str,
    address: str,
    district: str,
    pages: list[dict],
    aliases: list[str] | None = None,
) -> str:
    blocks = []
    for i, page in enumerate(pages, 1):
        kind, body = page_kind_and_body(page)
        if not body:
            body = "（无内容）"
        published = page.get("published_at") or ""
        blocks.append(
            f"[{i}] 类型：{kind}\n"
            f"标题：{page.get('title') or ''}\n"
            f"链接：{page.get('url') or ''}\n"
            f"时间：{published}\n"
            f"内容：{body}"
        )
    materials = "\n\n".join(blocks) or "（无搜索结果）"
    alias_text = "、".join(a for a in (aliases or []) if a) or shop_name
    return f"""
城市：{city}
目标店名（高德）：{shop_name}
别名：{alias_text}
地址：{address}
行政区：{district}

说明：类型为「正文」的是网页抽出的原文；类型为「摘要」的是搜索引擎转述，可信度较低。请优先根据正文判断。evidence.quote 必须来自对应编号的「内容」字段。

材料：
{materials}
"""