import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
 
import trafilatura
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

def env(name:str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"缺少有效配置：{name}（请检查 .env）")
    return value

def show_response_error(response: requests.Response) -> None:
    body = (response.text or "").strip()[:800]
    raise RuntimeError(f"API 错误：{response.status_code}\n{body}")

def chat(messages:list[ChatCompletionMessageParam]) -> str:
    client = OpenAI(api_key=env("deepseek_api_key"), base_url=env("deepseek_api_url"))
    reply = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        response_format={"type": "json_object"}
    )
    return (reply.choices[0].message.content or "").strip()

def search_web(query:str,count:int=10) -> list[dict]:
    url = env("bocha_api_url")
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {env("bocha_api_key")}",
            "Content-Type": "application/json"
        },
        json={
            "query": query, 
            "count": count,
            "freshness": "noLimit",
            "summary": True
        },
        timeout=30
    )
    if response.status_code >= 400:
        show_response_error(response)
    
    pages=(
        response.json()
        .get("data", {})
        .get("webPages", {})
        .get("value", [])
    )
    results = []
    for page in pages:
        link = page.get("url")
        if not link:
            continue
        results.append({
            "title": page.get("name") or page.get("title") or f"(无标题)",
            "url": link,
            "summary": page.get("summary") or f"(无摘要)",
            "snippet": page.get("snippet") or f"(无摘要)",
            "published_at": page.get("publishedAt") or f"(无发布时间)",
        })
    return results

def search_poi(keywords:str,city:str) ->list[dict]:
    url = env("gaode_api_url")
    response = requests.get(
        url,
        params={
            "key": env("gaode_api_key"),
            "keywords": keywords,
            "city": city,
            "citylimit": "true",
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
    results = []
    for point in points:
        results.append({
            "id": point.get("id") or "",
            "name": point.get("name"),
            "address":point.get("address") or "",
            "location":point.get("location") or "",
            "district":point.get("adname") or "",
            "cityname":point.get("cityname") or "",
            "type":point.get("type") or "",
        })
    return results


SKIP_HOSTS = (
    "douyin.com",
    "iesdouyin.com",
    "xiaohongshu.com",
    "xhslink.com",
    "xhs.com",
    # 深筛实测多次请求均抽不出正文（JS 空壳 / 登录墙）
    "ditu.so.com",
    "map.so.com",
    "chachaba.com",
    "dianping.com",
    "mafengwo.cn",
    "11467.com",
    "toutiao.com",
    "laowusk.com",
)

def _host_skipped(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == h or host.endswith("." + h) for h in SKIP_HOSTS)

def fetch_text(url: str) -> str:
    if not url or _host_skipped(url):
        return ""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            },
            allow_redirects=True,
        )
        if response.status_code >= 400 or not response.text:
            return ""
        text = trafilatura.extract(
            response.text,
            url=url,
            include_comments=True,
            include_tables=False,
        )
    except Exception:
        return ""
    text = (text or "").strip()
    # 登录墙、JS 空壳往往只有几十个字，当失败
    return text if len(text) >= 80 else ""