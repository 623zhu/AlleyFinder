import json
from pathlib import Path
from collections import defaultdict
import re


ROOT = Path(__file__).resolve().parents[1]
MENTIONS = ROOT / "data" / "spike_wuhan" / "mentions.jsonl"
SHOPS = ROOT / "data" / "spike_wuhan" / "shops.jsonl"
OUT = ROOT / "data" / "spike_wuhan" / "shortlist.jsonl"
DROP_LOG = ROOT / "data" / "spike_wuhan" / "screen_dropped.jsonl"
KEEP_N = 30
CITY = "武汉"
WUHAN_DISTRICTS = {
    "江岸区", "江汉区", "硚口区", "汉阳区", "武昌区",
    "青山区", "洪山区", "蔡甸区", "江夏区", "黄陂区",
    "新洲区", "东西湖区", "汉南区",
}
MALL_WORDS = (
    "万达", "商场", "购物中心", "商超", "超市", "美食广场",
    "美食街", "百货", "国金天地", "汉街万达",
)
CHAIN_WORDS = ("总店", "小吃城")
BAD_TYPES = ("快餐厅", "生活服务场所")

def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text or "", flags=re.UNICODE).lower()

def names_match(raw: str, poi: str) -> bool:
    a = normalize(re.sub(r"(总店|分店|店|馆|酒楼)$", "", raw))
    b = normalize(re.sub(r"(总店|分店|店|馆|酒楼).*$", "", poi))
    if len(a) < 2 or len(b) < 2:
        return False
    return a in b or b in a

def drop_reason(shop: dict, texts: str) -> str | None:
    cityname = shop.get("cityname") or ""
    if cityname and CITY not in cityname:
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


def main() -> None:
    shops = []
    with SHOPS.open(encoding="utf-8") as f:
        for line in f:
            shops.append(json.loads(line))
    mentions_by_name: dict[str, list[dict]] = defaultdict(list)
    with MENTIONS.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            mentions_by_name[normalize(row.get("name") or "")].append(row)
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
        reason = drop_reason(item, item["blob"])
        row = {k: v for k, v in item.items() if k != "blob"}
        if reason:
            row["drop_reason"] = reason
            dropped.append(row)
        else:
            kept.append(row)
    kept.sort(key=lambda x: x["mention_count"], reverse=True)
    shortlist = kept[:KEEP_N]
    with OUT.open("w", encoding="utf-8") as f:
        for row in shortlist:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with DROP_LOG.open("w", encoding="utf-8") as f:
        for row in dropped:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"合并后 {len(merged)} 家")
    print(f"剔除 {len(dropped)} 家，进入短名单 {len(shortlist)} 家")
    print("— 剔除 —")
    for row in dropped:
        print(f"  {row['name_raw']} | {row['drop_reason']}")
    print("— 短名单 —")
    for row in shortlist:
        print(f"  ×{row['mention_count']} {row['name']} | {row['address']}")
    print(f"短名单：{OUT}")
    print(f"剔除日志：{DROP_LOG}")

if __name__ == "__main__":
    main()