# runner.py
import os
import asyncio
import requests
import difflib

from arb import find_surebets
from scrapers.tippmixpro import fetch_events as fetch_tippmixpro
from scrapers.vegas import fetch_events as fetch_vegas
from scrapers.bet365 import fetch_events as fetch_bet365

# --- ENV (kényelmi, de alapból mindig küldünk üzenetet) ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
TOTAL_STAKE = float(os.environ.get("TOTAL_STAKE", "10000"))
# ha akarod, beállíthatod, de a fájl alapból MINDIG küld üzenetet:
ONLY_NOTIFY_ON_SUREBETS = os.environ.get("ONLY_NOTIFY_ON_SUREBETS", "0") == "1"
VERBOSE = os.environ.get("VERBOSE", "1") == "1"
SPORTS = [s.strip().lower() for s in os.environ.get("SPORTS", "tenisz,labdarúgás").split(",")]

# --- segédfüggvények ---
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=data, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print("Telegram send error:", e)

def _norm_name(s: str) -> str:
    return (s or "").lower().replace("–", "-").replace("—", "-").replace(" vs ", " - ").replace(" v ", " - ").strip()

def _similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm_name(a), _norm_name(b)).ratio()

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

def format_diag(source_counts, arbs, agg_count=None, limit=5):
    scored = sorted(arbs, key=lambda x: x["margin_pct"], reverse=True)
    lines = []
    lines.append("ℹ️ Diagnosztika:")
    if agg_count is not None:
        lines.append(f"- Agg. cél-meccsek: {agg_count}")
    lines.append(f"- Tippmixpro események: {source_counts.get('tippmixpro', 0)}")
    lines.append(f"- Vegas.hu események:   {source_counts.get('vegas', 0)}")
    lines.append(f"- Bet365 események:     {source_counts.get('bet365', 0)}")
    lines.append("")
    lines.append("Top marginok (legjobb → gyengébb):")
    shown = 0
    for a in scored:
        if shown >= limit:
            break
        lines.append(f"• {a['event']} | {a['market']} | margin: {a['margin_pct']}%")
        shown += 1
    if shown == 0:
        lines.append("• Nincs értékelhető margin.")
    return "\n".join(lines)

# --- fő futtatás ---
async def main():
    events = []
    source_counts = {"tippmixpro": 0, "vegas": 0, "bet365": 0}

    # Tippmixpro
    try:
        t = await fetch_tippmixpro(SPORTS)
        source_counts["tippmixpro"] = len(t)
        events.extend(t)
    except Exception as e:
        # Ha a scraper hibázik, jelzi, de továbbmegyünk
        send_telegram(f"⚠️ Scraper hiba (Tippmixpro): {e}")

    # Vegas.hu
    try:
        v = await fetch_vegas(SPORTS)
        source_counts["vegas"] = len(v)
        events.extend(v)
    except Exception as e:
        send_telegram(f"⚠️ Scraper hiba (Vegas.hu): {e}")

    # Bet365
    try:
        b = await fetch_bet365(SPORTS)
        source_counts["bet365"] = len(b)
        events.extend(b)
    except Exception as e:
        send_telegram(f"⚠️ Scraper hiba (Bet365): {e}")

    # Ha egyáltalán nincs esemény, küldünk erről is üzenetet
    if not events:
        send_telegram("ℹ️ Figyelem — a scraperek egyáltalán nem találtak eseményt.")
        # küldjük a részletes diagnosztikát is (ha van értelme)
        send_telegram(format_diag(source_counts, [], agg_count=0, limit=5))
        return

    # arbitrázs számítás a begyűjtött eseményeken
    arbs = find_surebets(events, stake=TOTAL_STAKE)

    found = False
    for arb in arbs:
        if arb["is_surebet"]:
            found = True
            send_telegram(format_alert(arb, TOTAL_STAKE))

    # ha nem találtunk surebetet, akkor is küldünk diagnosztikát + "nincs surebet" üzenetet
    if not found:
        send_telegram("ℹ️ Most nincs surebet.")
        # küldjük a diagnosztikát (top 5 margin), ez mindig hasznos
        send_telegram(format_diag(source_counts, arbs, agg_count=0, limit=5))

if __name__ == "__main__":
    asyncio.run(main())
