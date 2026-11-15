from __future__ import annotations

import re
from collections import defaultdict

from alleyfinder.db import DB_PATH, load_mentions, load_shops, replace_shortlist
from alleyfinder.pipeline.common import ProgressFn, emit, normalize, normalize_city

KEEP_N = 30
MALL_WORDS = (
    "万达", "商场", "购物中心", "商超", "超市", "美食广场",
    "美食街", "百货", "国金天地", "汉街万达",
)
CHAIN_WORDS = ("总店", "小吃城")
BAD_TYPES = ("快餐厅", "生活服务场所")


def names_match(raw: str, poi: str) -> bool:
    a = normalize(re.sub(r"(总店|分店|店|馆|酒楼)$", "", raw))
    b = normalize(re.sub(r"(总店|分店|店|馆|酒楼).*$", "", poi))
    if len(a) < 2 or len(b) < 2:
        return False
    return a in b or b in a


def drop_reason(city: str, shop: dict, texts: str) -> str | None:
    cityname = shop.get("cityname") or ""
    if cityname and city not in cityname:
        return f"非目标城市:{cityname}"
    if not names_match(shop["name_raw"], shop["name"]):
        return f"店名对不上:{shop['name_raw']} → {shop['name']}"
    for word in MALL_WORDS:
        if word in texts:
            return f"商超/商场:{word}"
    for word in CHAIN_WORDS:
        if word in (shop.get("name_raw") or "") or word in (shop.get("name") or ""):
            return f"连锁痕迹:{word}"
    poi_type = shop.get("type") or ""
    for word in BAD_TYPES:
        if word in poi_type:
            return f"类型不符:{poi_type}"
    return None


def screen_shops(
    city: str,
    *,
    keep_n: int = KEEP_N,
    progress: ProgressFn = None,
) -> list[dict]:
    name = normalize_city(city)
    shops = load_shops(name)
    if not shops:
        raise RuntimeError(f"缺少 {name} 的 POI 匹配结果，请先跑 POI 匹配")

    mentions_by_name: dict[str, list[dict]] = defaultdict(list)
    for row in load_mentions(name):
        mentions_by_name[normalize(row.get("name") or "")].append(row)

    emit(progress, "screening", f"初筛 {len(shops)} 家")
    merged: dict[str, dict] = {}
    for shop in shops:
        poi_id = shop.get("poi_id") or ""
        hits = mentions_by_name.get(normalize(shop.get("name_raw") or ""), [])
        blob = " ".join(
            [
                shop.get("name_raw") or "",
                shop.get("name") or "",
                shop.get("address") or "",
                *[str(m.get("evidence") or "") for m in hits],
                *[str((m.get("shop") or {}).get("address_hint") or "") for m in hits],
            ]
        )
        if poi_id in merged:
            merged[poi_id]["mention_count"] += len(hits)
            merged[poi_id]["name_raws"].append(shop["name_raw"])
            continue
        merged[poi_id] = {
            **shop,
            "name_raws": [shop["name_raw"]],
            "mention_count": len(hits) or 1,
            "blob": blob,
        }

    kept = []
    dropped = []
    for item in merged.values():
        reason = drop_reason(name, item, item["blob"])
        row = {k: v for k, v in item.items() if k != "blob"}
        if reason:
            row["drop_reason"] = reason
            dropped.append(row)
        else:
            kept.append(row)
    kept.sort(key=lambda x: x["mention_count"], reverse=True)
    shortlist = kept[:keep_n]
    replace_shortlist(name, shortlist, dropped)

    print(f"合并后 {len(merged)} 家")
    print(f"剔除 {len(dropped)} 家，进入短名单 {len(shortlist)} 家")
    print("— 剔除 —")
    for row in dropped:
        print(f"  {row['name_raw']} | {row['drop_reason']}")
    print("— 短名单 —")
    for row in shortlist:
        print(f"  ×{row['mention_count']} {row['name']} | {row['address']}")
    print(f"短名单：{DB_PATH} shortlist/{name}")
    return shortlist
