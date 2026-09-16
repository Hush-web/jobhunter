import os
import sqlite3
import time
import requests

MAX_LEN = 4000


def _format_row(r: sqlite3.Row) -> str:
    score = r["score"]
    title = r["title"]
    company = r["company"] or ""
    loc = r["location"] or "n/a"
    url = r["url"]

    head = f"*[{score}] {title}*"
    if company:
        head += f"\n{company}"
    head += f"\n`{r['source']} · {loc}`"
    head += f"\n{url}"
    return head


def format_digest(rows: list[sqlite3.Row], max_items: int = 15) -> str:
    if not rows:
        return "No new matches today."
    lines = [f"*{len(rows)} new matches*", ""]
    for r in rows[:max_items]:
        lines.append(_format_row(r))
        lines.append("")
    if len(rows) > max_items:
        lines.append(f"...and {len(rows) - max_items} more.")
    return "\n".join(lines)


def _send(token: str, chat_id: str, text: str) -> bool:
    ok = True
    for chunk in [text[i:i + MAX_LEN] for i in range(0, len(text), MAX_LEN)]:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            if resp.status_code != 200:
                # Retry without markdown if formatting broke
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk,
                          "disable_web_page_preview": True},
                    timeout=20,
                )
            time.sleep(0.5)
        except Exception:
            ok = False
    return ok


def send_digest(rows: list[sqlite3.Row]) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    public_id = os.getenv("TELEGRAM_PUBLIC_CHAT_ID")

    if not token:
        print("TELEGRAM_BOT_TOKEN not set — skipping Telegram.")
        return

    if not rows:
        return

    text = format_digest(rows)

    if chat_id:
        if _send(token, chat_id, text):
            print(f"Sent {len(rows)} jobs to personal chat")
        else:
            print("Failed to send to personal chat")

    if public_id:
        if _send(token, public_id, text):
            print(f"Sent {len(rows)} jobs to public channel")
        else:
            print("Failed to send to public channel")
