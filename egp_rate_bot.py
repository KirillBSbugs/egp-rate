#!/usr/bin/env python3
import os
import sys

import requests

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL = os.environ["CHANNEL"]
API = f"https://api.telegram.org/bot{TOKEN}"
ID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "msg_id.txt")


def rate_yahoo() -> float:
    def px(pair):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair}=X"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        return float(r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"])
    return px("USDRUB") / px("USDEGP")


def rate_erapi() -> float:
    r = requests.get("https://open.er-api.com/v6/latest/EGP", timeout=15)
    r.raise_for_status()
    return float(r.json()["rates"]["RUB"])


def get_rate() -> float:
    for source in (rate_yahoo, rate_erapi):
        try:
            value = source()
            if value > 0:
                return value
        except Exception as e:
            print(f"{source.__name__} упал: {e}", file=sys.stderr)
    raise RuntimeError("ни один источник курса не ответил")


def build_text(rate: float) -> str:
    return f"1 EGP = {rate:.2f} ₽"


def load_message_id():
    env = os.environ.get("MESSAGE_ID")
    if env:
        return int(env)
    if os.path.exists(ID_FILE):
        return int(open(ID_FILE).read().strip())
    return None


def save_message_id(message_id: int) -> None:
    with open(ID_FILE, "w") as f:
        f.write(str(message_id))


def send(text: str) -> int:
    r = requests.post(
        f"{API}/sendMessage",
        json={"chat_id": CHANNEL, "text": text, "parse_mode": "Markdown"},
        timeout=15,
    )
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    return data["result"]["message_id"]


def edit(message_id: int, text: str) -> None:
    r = requests.post(
        f"{API}/editMessageText",
        json={
            "chat_id": CHANNEL,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown",
        },
        timeout=15,
    )
    data = r.json()
    if data.get("ok"):
        print("отредактировано")
        return
    desc = str(data.get("description", ""))
    if "message is not modified" in desc:
        print("курс не изменился — правка не нужна")
        return
    if "message to edit not found" in desc:
        new_id = send(text)
        save_message_id(new_id)
        print(f"старый пост не найден, создан новый: {new_id}")
        return
    raise RuntimeError(data)


def main() -> None:
    text = build_text(get_rate())
    message_id = load_message_id()
    if message_id is None:
        message_id = send(text)
        save_message_id(message_id)
        print(f"MESSAGE_ID = {message_id}  <-- запомни это значение")
    else:
        edit(message_id, text)


if __name__ == "__main__":
    main()
