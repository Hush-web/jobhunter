import os
import sqlite3
import requests


def format_digest(rows: list[sqlite3.Row]) -> str:
    if not rows:
        return "No new matches today."
    lines = [f"🎯 {len(rows)} new matches\n"]
    for r in rows:
        lines.append(
            f"[{r['score']}] {r['title']} — {r['company']}\n"
            f"     {r['source']} · {r['location'] or 'n/a'}\n"
            f"     {r['url']}\n"
        )
    return "\n".join(lines)


def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    # Telegram has a 4096-char limit per message
    for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)]:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": chunk, "disable_web_page_preview": True},
            timeout=15,
        )