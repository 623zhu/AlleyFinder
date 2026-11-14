from pathlib import Path
import argparse
import json
import re
import time

from alleyfinder.clients import chat, fetch_text, search_web
from alleyfinder.prompts.review import SYSTEM_PROMPT, page_kind_and_body, user_prompt

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "spike_wuhan" / "shortlist.jsonl"
OUT_DIR = ROOT / "data" / "spike_wuhan"
reviews_path = OUT_DIR / "reviews.jsonl"
ranked_path = OUT_DIR / "ranked.jsonl"
drop_path = OUT_DIR / "deep_dropped.jsonl"
CITY = "武汉"
KEEP_N = 10


def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text or "", flags=re.UNICODE).lower()


def shop_aliases(shop: dict) -> list[str]:
    names: list[str] = []
    for value in [shop.get("name_raw"), shop.get("name"), *(shop.get("name_raws") or [])]:
        text = (value or "").strip()
        if text and text not in names:
            names.append(text)
    return names


def pages_about_shop(pages: list[dict], names: list[str]) -> list[dict]:
    keys = [normalize(n) for n in names if n]
    hit = []
    for page in pages:
        blob = normalize((page.get("title") or "") + (page.get("summary") or page.get("snippet") or ""))
        if any(k and k in blob for k in keys):
            hit.append(page)
    return hit


def fill_page_text(pages: list[dict]) -> None:
    for page in pages:
        url = page.get("url") or ""
        page["text"] = fetch_text(url)
        time.sleep(0.2)


def page_sources(pages: list[dict]) -> list[dict]:
    sources = []
    for page in pages:
        kind, body = page_kind_and_body(page)
        sources.append({
            "url": page.get("url") or "",
            "title": page.get("title") or "",
            "kind": kind,
            "n_chars": len(body),
        })
    return sources


def extract_review(shop: dict, pages: list[dict]) -> dict:
    raw = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(
            CITY,
            shop.get("name") or "",
            shop.get("address") or "",
            shop.get("district") or "",
            pages,
            aliases=shop_aliases(shop),
        )},
    ])
    return json.loads(raw)


def grounded_evidence(review: dict, pages: list[dict]) -> list[dict]:
    raw = review.get("evidence") or []
    out: list[dict] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, str):
            quote = item.strip()
            source = None
        elif isinstance(item, dict):
            quote = str(item.get("quote") or "").strip()
            raw_source = item.get("source")
            try:
                source = int(raw_source) if raw_source is not None else None
            except (TypeError, ValueError):
                source = None
        else:
            continue
        if len(quote) < 8:
            continue
        needle = normalize(quote)
        if not needle:
            continue

        candidates: list[dict] = []
        if isinstance(source, int) and 1 <= source <= len(pages):
            candidates.append(pages[source - 1])
        candidates.extend(pages)

        matched = None
        for page in candidates:
            _, body = page_kind_and_body(page)
            if needle in normalize(body):
                matched = page
                break
        if not matched:
            continue
        url = matched.get("url") or ""
        key = normalize(quote) + "|" + url
        if key in seen:
            continue
        seen.add(key)
        out.append({"quote": quote, "url": url})
        if len(out) >= 4:
            break
    return out


def tidy_review(review: dict, pages: list[dict]) -> dict:
    dishes = [str(x).strip() for x in (review.get("dishes") or []) if str(x).strip()]
    keywords = [str(x).strip() for x in (review.get("keywords") or []) if str(x).strip()]
    review["dishes"] = dishes[:3]
    review["keywords"] = keywords[:5]
    review["evidence"] = grounded_evidence(review, pages)
    review["reason"] = str(review.get("reason") or "").strip()
    return review


def drop_reason(review: dict, pages: list[dict], extract_failed: bool = False) -> str | None:
    if not pages:
        return "没有搜到相关材料"
    if extract_failed or not review:
        return "口碑抽取失败"
    if review.get("about_this_shop") is False:
        return "材料不是在说这家店"
    if review.get("closed_hint"):
        return "疑似关店"
    if review.get("is_chain_or_mall"):
        return "连锁或商场店"
    if review.get("is_ad_like") and not review.get("is_old_shop"):
        return "广告/探店痕迹且无老店信号"
    if not review.get("evidence"):
        return "没有可核验的证据"
    return None


def score(shop: dict, review: dict, n_pages: int) -> float:
    s = 0.0
    s += min(shop.get("mention_count") or 0, 3)
    s += min(n_pages, 5) * 0.4
    if review.get("taste") == "正":
        s += 2
    if review.get("environment") in ("简陋", "一般"):
        s += 1.5
    if review.get("environment") == "精致":
        s -= 1.5
    if review.get("is_old_shop"):
        s += 2
    if review.get("price") == "便宜":
        s += 1
    if review.get("price") == "贵":
        s -= 1.5
    if review.get("is_ad_like"):
        s -= 1
    return s


def card_row(row: dict) -> dict:
    review = row.get("review") or {}
    return {
        "name": row.get("name"),
        "name_raw": row.get("name_raw"),
        "poi_id": row.get("poi_id"),
        "address": row.get("address"),
        "district": row.get("district"),
        "cityname": row.get("cityname"),
        "type": row.get("type"),
        "lng": row.get("lng"),
        "lat": row.get("lat"),
        "score": row.get("score"),
        "reason": review.get("reason") or "",
        "dishes": review.get("dishes") or [],
        "keywords": review.get("keywords") or [],
        "evidence": review.get("evidence") or [],
        "taste": review.get("taste"),
        "environment": review.get("environment"),
        "price": review.get("price"),
        "price_hint": review.get("price_hint"),
        "is_old_shop": review.get("is_old_shop"),
        "n_pages": row.get("n_pages"),
        "n_body": row.get("n_body"),
        "n_summary": row.get("n_summary"),
        "urls": row.get("urls"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只处理前 N 家，0 表示全部")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    shops = []
    with IN.open(encoding="utf-8") as f:
        for line in f:
            shops.append(json.loads(line))
    if args.limit and args.limit > 0:
        shops = shops[: args.limit]

    kept = []
    dropped = []

    with reviews_path.open("w", encoding="utf-8") as f:
        for shop in shops:
            name = shop.get("name_raw") or shop.get("name") or ""
            query = f"{name} {CITY} 评价"
            print(f"正在搜索：{query}")

            try:
                pages = search_web(query, 8)
            except Exception as exc:
                print(f"搜索失败：{exc}")
                pages = []
            time.sleep(0.3)

            hit = pages_about_shop(pages, shop_aliases(shop))
            if hit:
                print(f"  命中 {len(hit)} 条，抓取正文…")
                fill_page_text(hit)

            sources = page_sources(hit)
            n_body = sum(1 for s in sources if s["kind"] == "正文")
            n_summary = sum(1 for s in sources if s["kind"] == "摘要")
            if hit:
                print(f"  正文 {n_body} / 摘要 {n_summary}")

            extract_failed = False
            if hit:
                try:
                    review = tidy_review(extract_review(shop, hit), hit)
                except Exception as exc:
                    print(f"抽取失败 {name}: {exc}")
                    review = {}
                    extract_failed = True
            else:
                review = {}

            reason = drop_reason(review, hit, extract_failed=extract_failed)
            n_pages = len(hit)
            row = {
                **shop,
                "query": query,
                "n_pages": n_pages,
                "n_body": n_body,
                "n_summary": n_summary,
                "urls": [p.get("url") for p in hit],
                "sources": sources,
                "review": review,
            }
            if reason:
                row["drop_reason"] = reason
                dropped.append(row)
                print(f"[剔除] {name} | {reason}")
            else:
                row["score"] = score(shop, review, n_pages)
                kept.append(row)
                preview = (review.get("reason") or "")[:40]
                print(f"[留下] {name} | {row['score']:.1f} | 正文{n_body}/{n_pages} | {preview}")

            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()

    kept.sort(key=lambda x: x["score"], reverse=True)
    ranked = kept[:KEEP_N]

    with ranked_path.open("w", encoding="utf-8") as f:
        for row in ranked:
            f.write(json.dumps(card_row(row), ensure_ascii=False) + "\n")
    with drop_path.open("w", encoding="utf-8") as f:
        for row in dropped:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"短名单 {len(shops)} 家，剔除 {len(dropped)}，留下 {len(kept)}，榜单 {len(ranked)}")
    print("— 剔除 —")
    for row in dropped:
        print(f"  {row.get('name_raw')} | {row['drop_reason']}")
    print("— 榜单 —")
    for i, row in enumerate(ranked, 1):
        card = card_row(row)
        print(
            f"  {i}. {card['score']:.1f}  {card.get('name')} | "
            f"正文{card.get('n_body')}/{card.get('n_pages')} | {card.get('address')}"
        )
        print(f"     {card.get('reason')}")
    print(f"口碑明细：{reviews_path}")
    print(f"榜单：{ranked_path}")
    print(f"剔除日志：{drop_path}")


if __name__ == "__main__":
    main()
