from pathlib import Path

from dotenv import load_dotenv
import requests
import os
from openai import OpenAI
import sys

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def env(name:str) -> str:
    value = os.getenv(name, "").strip()
    if value and "*" not in value:
        return value
    raise RuntimeError(f"缺少有效配置：{name}（请检查 .env）")

def show_response_error(response: requests.Response) -> None:
    body = (response.text or "").strip()[:800]
    raise RuntimeError(f"API 错误：{response.status_code}\n{body}")

def test_bocha() -> str:
    url = env("bocha_api_url")
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {env("bocha_api_key")}",
            "Content-Type": "application/json"
            },
         json={"query": "武汉美食","freshness": "noLimit","summary": True,"count": 1},
         timeout=30
        )
    if response.status_code >= 400:
        show_response_error(response)
    result = response.json().get("data", {}).get("webPages", {}).get("value") or []
    if not result:
        raise RuntimeError("请求成功但是结果为空")
    title = result[0].get("name") or result[0].get("title") or f"(无标题)"
    return f"搜索到{len(result)}条结果：第一条:{title}"

def test_deepseek() -> str:
    client = OpenAI(api_key=env("deepseek_api_key"), base_url=env("deepseek_api_url"))
    reply = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "只回复：ok"}],
        max_tokens=16,
    )
    text = (reply.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("模型没有返回内容")
    return f"模型回复：{text}"

def test_gaode() -> str:
    url = env("gaode_api_url")
    response = requests.get(
        url,
        params={
            "key": env("gaode_api_key"),
            "keywords": "武汉美食",
            "city": "武汉",
            "output": "json",
        },
        timeout=30
    )
    if response.status_code >= 400:
        show_response_error(response)
    payload = response.json()
    if str(payload.get("status")) != "1":
        raise RuntimeError(f"高德业务失败：{payload.get('info')} ({payload.get('infocode')})")
    points = payload.get("pois") or []
    if not points:
        raise RuntimeError("请求成功但是没有POI")
    return f"搜索到{len(points)}条结果：第一条:{points[0].get('name')}"

def main() -> int:
    tests = [
        ("博查", test_bocha),
        ("DeepSeek", test_deepseek),
        ("高德", test_gaode),
    ]
    failed = 0
    for name, fn in tests:
        try:
            print(f"[通过] {name}：{fn()}")
        except Exception as exc:
            failed += 1
            print(f"[失败] {name}：{exc}")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
