from typing import List, Dict, Any, Iterable
from playwright.async_api import async_playwright

BASE_URL = "https://www.bet365.com/#/AS/B1/"

def _norm_num(txt: str) -> float:
    return float(txt.replace("\xa0", "").replace(",", ".").strip())

def _split_title(title: str):
    t = title.replace("–", "-").replace("—", "-")
    parts = [p.strip() for p in t.split(" v ")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return title.strip(), "Másik"

async def fetch_events(sports: Iterable[str]) -> List[Dict[str, Any]]:
    wanted = {s.lower() for s in sports}
    out: List[Dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8"
        })

        await page.goto(BASE_URL, timeout=90000)
        await page.wait_for_load_state("domcontentloaded")

        # próbáljunk átugrani a nyitó overlay-t, ha van
        try:
            await page.get_by_text("Accept All Cookies", exact=False).click(timeout=3000)
        except:
            pass

        # bet365-ön a sports menü dinamikusan generált — sportokra szűrünk
        for sport in ("Soccer", "Tennis"):
            if sport.lower() not in wanted and sport != "Soccer":
                continue

            try:
                await page.get_by_text(sport, exact=False).first.click(timeout=5000)
            except:
                continue

            await page.wait_for_timeout(2000)

            rows = await page.query_selector_all("div.scores-row, div.sip-MarketGroup")
            taken = 0
            for row in rows:
                if taken >= 20:
                    break
                title_el = await row.query_selector("div.scores, span.sip-MarketFixtureDetails_Team")
                odd_els = await row.query_selector_all("span.sip-ParticipantOddsOnly80_Odds")

                if not title_el or len(odd_els) < 2:
                    continue

                title = (await title_el.inner_text()).strip()
                p1, p2 = _split_title(title)

                try:
                    o1 = _norm_num(await odd_els[0].inner_text())
                    o2 = _norm_num(await odd_els[1].inner_text())
                except:
                    continue

                market = "Match Winner" if sport.lower() == "tennis" else "1X2"
                odds = {p1: o1, p2: o2}
                out.append({
                    "event": f"{p1} - {p2}",
                    "market": market,
                    "bookmaker": "Bet365",
                    "odds": odds
                })
                taken += 1

        await browser.close()
    return out
