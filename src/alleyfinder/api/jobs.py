from __future__ import annotations

import threading

from alleyfinder.city import normalize_city
from alleyfinder.db import city_has_ranking, get_job, upsert_job
from alleyfinder.pipeline.run import run_pipeline

_lock = threading.Lock()
_threads: dict[str, threading.Thread] = {}


def _payload(city: str, row: dict | None) -> dict:
    if row:
        return {
            "city": row["city"],
            "status": row["status"],
            "stage": row.get("stage") or "",
            "message": row.get("message") or "",
            "error": row.get("error"),
        }
    if city_has_ranking(city):
        return {
            "city": city,
            "status": "done",
            "stage": "done",
            "message": "榜单已生成",
            "error": None,
        }
    return {
        "city": city,
        "status": "idle",
        "stage": "",
        "message": "",
        "error": None,
    }


def _in_flight(city: str) -> bool:
    thread = _threads.get(city)
    if thread is None:
        return False
    return thread.is_alive() or thread.ident is None


def _reconcile(city: str) -> dict | None:
    if city_has_ranking(city):
        row = get_job(city)
        if row and row["status"] == "done":
            return row
        return upsert_job(city, status="done", stage="done", message="榜单已生成")

    row = get_job(city)
    if row and row["status"] in ("queued", "running") and not _in_flight(city):
        return upsert_job(
            city,
            status="error",
            stage="error",
            message="探巷中断，请再试一次",
            error="探巷中断，请再试一次",
        )
    return row


def start_job(city: str) -> dict:
    name = normalize_city(city)
    if not name:
        raise ValueError("城市名不能为空")

    with _lock:
        row = _reconcile(name)
        if city_has_ranking(name):
            return _payload(name, row)
        if row and row["status"] in ("queued", "running") and _in_flight(name):
            return _payload(name, row)

        thread = threading.Thread(
            target=_run_job,
            args=(name,),
            name=f"alley-{name}",
            daemon=True,
        )
        _threads[name] = thread
        upsert_job(name, status="queued", stage="queued", message="排队探巷…")
        thread.start()
        return _payload(name, get_job(name))


def read_job(city: str) -> dict:
    name = normalize_city(city)
    if not name:
        raise ValueError("城市名不能为空")
    return _payload(name, _reconcile(name))


def _run_job(city: str) -> None:
    upsert_job(city, status="running", stage="searching", message=f"开始探 {city}")

    def progress(stage: str, message: str = "") -> None:
        upsert_job(
            city,
            status="running",
            stage=stage,
            message=message or stage,
        )

    try:
        run_pipeline(city, progress=progress)
        upsert_job(city, status="done", stage="done", message="榜单已生成")
    except Exception as exc:
        upsert_job(
            city,
            status="error",
            stage="error",
            message="探巷失败",
            error=str(exc).strip()[:500] or "探巷失败",
        )
