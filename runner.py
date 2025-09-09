import os
import asyncio
import requests

from arb import find_surebets
from scrapers.tippmixpro import fetch_events as fetch_tippmixpro
from scrapers.vegas import fetch_events as fetch_vegas
from scrapers.bet365 import fetch_events as fetch_bet365

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
TOTAL_STAKE = float(os.environ.get("TOTAL_STAKE", "10000"))

def format_alert(arb, total_stake: float) -> str:
    lines = []
    lines.append("✅ SUREBET TALÁLVA!")
    lines.append(f"Meccs: {arb['event']}")
    lines.append(f"Piac: {arb['market']}")
    lines.append(f"Margin: +{arb['margin_pct']}%")
    lines.append("")
    lines.append("Legjobb oddsok:")
    for outcome, data in arb["best_table"].items():
        lines.append(f"• {outcome}: {data['odd']} @ {data['bookmaker']}")
    if arb["allocation"]:
        lines.append("")
        lines.append(f"Ajánlott tételosztás (összesen {int(total_stake)}):")
        for a in arb["allocation"]:
            lines.append(f"• {a['outcome']}: {a['stake']} → kifizetés {a['expected_payout']} (profit {a['expected_profit']})")
    return "\n".join(lines)

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data, timeout=30).raise_for_status()

async def main():
    events = []
    for fetch in (fetch_tippmixpro, fetch_vegas, fetch_bet365):
        try:
            events.extend(await fetch())
        except Exception as e:
            send_telegram(f"ℹ️ Scraper hiba: {fetch.__module__}: {e}")

    if not events:
        send_telegram("ℹ️ Nincs elérhető odds (scraper üres).")
        return

    arbs = find_surebets(events, stake=TOTAL_STAKE)

    found = False
    for arb in arbs:
        if arb["is_surebet"]:
            found = True
            send_telegram(format_alert(arb, TOTAL_STAKE))

    if not found:
        send_telegram("ℹ️ Most nincs surebet.")

if __name__ == "__main__":
    asyncio.run(main())
