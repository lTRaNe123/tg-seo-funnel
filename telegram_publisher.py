import asyncio
import json
import os
import time
from typing import List, Optional

import httpx

TELEGRAM_API = "https://api.telegram.org"

def _split_4096(text: str, limit: int = 4096) -> List[str]:
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for para in text.split("\n"):
        add = para + "\n"
        if len(cur) + len(add) > limit:
            parts.append(cur.rstrip())
            cur = add
        else:
            cur += add
    if cur.strip():
        parts.append(cur.rstrip())
    return parts

async def _send_message(client: httpx.AsyncClient, token: str, chat_id: str, text: str) -> None:
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    while True:
        r = await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }, timeout=30.0)

        data = r.json()
        if data.get("ok") is True:
            return

        # 429 Too Many Requests -> retry_after в parameters
        err_code = data.get("error_code")
        if err_code == 429:
            retry_after = 1
            params = data.get("parameters") or {}
            retry_after = int(params.get("retry_after") or retry_after)
            await asyncio.sleep(retry_after + 0.25)
            continue

        # transient network-ish errors
        desc = data.get("description") or str(data)
        raise RuntimeError(f"Telegram API error: {err_code} {desc}")

async def publish_posts(
    posts_path: str,
    token: str,
    channel: str,
    rate_per_min: float = 26,
    limit: Optional[int] = None,
) -> None:
    """
    Публикация постов из JSONL.
    rate_per_min — целевой темп (постов/мин). При 429 скрипт сам ждёт retry_after.
    """
    if not token or not channel:
        raise ValueError("token/channel are required")

    # читаем посты
    posts = []
    with open(posts_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            posts.append(json.loads(line))

    if limit is not None:
        posts = posts[:limit]

    period = 60.0 / float(rate_per_min)
    next_tick = time.monotonic()

    async with httpx.AsyncClient() as client:
        for i, obj in enumerate(posts, start=1):
            text = (obj.get("tg_post") or "").strip()
            if not text:
                continue

            # pacing
            now = time.monotonic()
            if now < next_tick:
                await asyncio.sleep(next_tick - now)

            chunks = _split_4096(text)
            for c in chunks:
                await _send_message(client, token, channel, c)

            next_tick += period
            print(f"Posted {i}/{len(posts)}: {obj.get('slug')}")
