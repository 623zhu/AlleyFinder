from pathlib import Path
import argparse
from alleyfinder.clients import search_web, chat
from alleyfinder.prompts.extract import SYSTEM_PROMPT, user_prompt
import json
import csv
import re

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "spike_wuhan"
CITY = "武汉"
QUERIES = [
    "武汉 苍蝇馆子",
    "武汉 热干面 老店",
    "武汉 本地人 推荐 小吃",
    "武汉 巷子 美食",
    "武汉 开了十几年 餐馆",
]

# 文本归一化 去标点，空白，符号，转小写
def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text or "", flags=re.UNICODE).lower()

# 大模型结构化解析函数。
def extract_shops(city: str, title: str, url: str, text: str) -> list[dict]:
    raw = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(city, title, url, text)},
    ])
    payload = json.loads(raw)
    shops = payload.get("shops") or []
    return shops if isinstance(shops, list) else []

def main() -> None:
    ## 脚本命令增加命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract-n", type=int, default=20, help="送给模型的文档数")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    pages: list[dict] = []
    seen: set[str] = set()
    for query in QUERIES:
        print(f"搜索：{query}")
        for page in search_web(query, count=5):
            url = page["url"]
            if url in seen:
                continue
            seen.add(url)
            pages.append(page)
    print(f"去重后 {len(pages)} 篇")

    mentions_path = OUT_DIR / "mentions.jsonl"
    review_path = OUT_DIR / "review.csv"
    ok = 0
    bad = 0

    with mentions_path.open("w", encoding="utf-8") as jf, review_path.open(
        "w", encoding="utf-8", newline=""
    ) as cf:
        writer = csv.DictWriter(
            cf,
            fieldnames=["name", "evidence_ok", "evidence", "title", "url"],
        )
        writer.writeheader()

        for page in pages[: args.extract_n]:
            text = page.get("summary") or page.get("snippet") or ""
            source = normalize(page["title"] + text)
            try:
                shops = extract_shops(CITY, page["title"], page["url"], text)
            except Exception as exc:
                print(f"抽取失败 {page['url']}: {exc}")
                continue

            for shop in shops:
                name = str(shop.get("name") or "").strip()
                evidence = str(shop.get("evidence") or "").strip()
                if not name:
                    continue
                evidence_ok = bool(
                    evidence
                    and normalize(evidence) in source
                    and normalize(name) in source
                )
                if evidence_ok:
                    ok += 1
                else:
                    bad += 1
                row = {
                    "name": name,
                    "evidence": evidence,
                    "evidence_ok": evidence_ok,
                    "title": page["title"],
                    "url": page["url"],
                    "shop": shop,
                }
                jf.write(json.dumps(row, ensure_ascii=False) + "\n")
                writer.writerow({
                    "name": name,
                    "evidence_ok": evidence_ok,
                    "evidence": evidence,
                    "title": page["title"],
                    "url": page["url"],
                })
    print(f"证据通过 {ok} 条，失败 {bad} 条")
    print(f"明细：{mentions_path}")
    print(f"人工核对：{review_path}")

if __name__ == "__main__":
    main()