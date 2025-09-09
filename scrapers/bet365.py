# scrapers/bet365.py
from typing import List, Dict, Any
from playwright.async_api import async_playwright

BASE_URL = "https://www.bet365.com/#/AS/B1/"

def _norm(txt: str) -> float:
    return float(txt.replace("\xa0","").replace(",",".").strip())

def _split(title: str):
    t = title.replace("–","-").replace("—","-").replace(" v "," - ")
    if " - " in t:
        a,b = t.split(" - ",1)
        return a.strip(), b.strip()
    return t.strip(), "Másik"

async def _collect_from_page(page) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # bet365 gyakran változik — több szelektort próbálunk
    rows = await page.query_selector_all("div.scores-row, div.sip-MarketGroup, div.gl-MarketGroupContainer")
    for r in rows:
        title_el = await r.query_selector("div.scores, span.sip-MarketFixtureDetails_Team, div:has(span.sip-MarketFixtureDetails_Team)")
        odd_els  = await r.query_selector_all("span.sip-ParticipantOddsOnly80_Odds, span.gl-Participant_Odds")
        if not title_el or len(odd_els) < 2:
            continue
        try:
            title = (await title_el.inner_text()).strip()
            o1 = _norm(await odd_els[0].inner_text())
            o2 = _norm(await odd_els[1].inner_text())
        except:
            continue

        p1, p2 = _split(title)
        market = "Match Winner" if " - " in title else "1X2"
        out.append({
            "event": f"{p1} - {p2}",
            "market": market,
            "bookmaker": "Bet365",
            "odds": {p1: o1, p2: o2}
        })
    return out

async def fetch_events(urls: List[str]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    targets = urls or [BASE_URL]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.set_extra_http_headers({
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            "Accept-Language": "en-GB,en;q=0.9,hu-HU;q=0.6"
        })

        for url in targets:
            try:
                await page.goto(url, timeout=90000)
                # cookie / consent
                for t in ("Accept All Cookies", "I Agree", "OK"):
                    try:
                        await page.get_by_text(t, exact=False).first.click(timeout=2000); break
                    except: pass

                for _ in range(8):
                    await page.mouse.wheel(0, 2000)
                    await page.wait_for_timeout(700)

                events.extend(await _collect_from_page(page))
            except Exception:
                continue

        await browser.close()
    return events
