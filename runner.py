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
ONLY_NOTIFY_ON_SUREBETS = os.environ.get("ONLY_NOTIFY_ON_SUREBETS", "1") == "1"
VERBOSE = os.environ.get("VERBOSE", "1") == "1"

def _parse_url_list(key: str):
    raw = os.environ.get(key, "").strip()
    return [u.strip() for u in raw.split(",") if u.strip()]

TIPPMIX_URLS = _parse_url_list("TIPPMIX_URLS")
VEGAS_URLS   = _parse_url_list("VEGAS_URLS")
BET365_URLS  = _parse_url_list("BET365_URLS")

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=data, timeout=30).raise_for_status()

def format_alert(arb):
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
        lines.append(f"Ajánlott tételosztás (összesen {int(TOTAL_STAKE)}):")
        for a in arb["allocation"]:
            lines.append(f"• {a['outcome']}: {a['stake']} → kifizetés {a['expected_payout']} (profit {a['expected_profit']})")
    return "\n".join(lines)

def format_diag(counts, top, limit=5):
    lines = []
    lines.append("ℹ️ Diagnosztika:")
    for k in ("tippmixpro","vegas","bet365"):
        lines.append(f"- {k}: {counts.get(k,0)} esemény")
    lines.append("")
    lines.append("Top marginok (nem biztos, hogy surebet):")
    shown = 0
    for a in sorted(top, key=lambda x: x["margin_pct"], reverse=True):
        if shown >= limit: break
        lines.append(f"• {a['event']} | {a['market']} | margin: {a['margin_pct']}%")
        shown += 1
    if shown == 0:
        lines.append("• Nincs értékelhető margin.")
    return "\n".join(lines)

async def main():
    events = []
    counts = {"tippmixpro":0,"vegas":0,"bet365":0}

    try:
        t = await fetch_tippmixpro(TIPPMIX_URLS)
        counts["tippmixpro"] = len(t); events.extend(t)
    except Exception as e:
        send_telegram(f"⚠️ Scraper hiba (Tippmixpro): {e}")

    try:
        v = await fetch_vegas(VEGAS_URLS)
        counts["vegas"] = len(v); events.extend(v)
    except Exception as e:
        send_telegram(f"⚠️ Scraper hiba (Vegas.hu): {e}")

    try:
        b = await fetch_bet365(BET365_URLS)
        counts["bet365"] = len(b); events.extend(b)
    except Exception as e:
        send_telegram(f"⚠️ Scraper hiba (Bet365): {e}")

    if not events:
        if not ONLY_NOTIFY_ON_SUREBETS:
            send_telegram("ℹ️ Nincs elérhető odds (scraperek üresek).")
        return

    arbs = find_surebets(events, stake=TOTAL_STAKE)
    found = False
    for arb in arbs:
        if arb["is_surebet"]:
            found = True
            send_telegram(format_alert(arb))

    if not found:
        if VERBOSE:
            send_telegram(format_diag(counts, arbs))
        elif not ONLY_NOTIFY_ON_SUREBETS:
            send_telegram("ℹ️ Most nincs surebet.")

if __name__ == "__main__":
    asyncio.run(main())
