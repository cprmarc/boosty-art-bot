from typing import List, Dict, Any
from playwright.async_api import async_playwright

URL = "https://www.bet365.com/#/AC/B1/C1/D13/E181/F43/"

async def fetch_events() -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.goto(URL, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")

        # Ezek a szelektorok a bet365 gyakori változásai miatt csak kiindulópontok
        groups = await page.query_selector_all("div.gl-MarketGroupContainer")
        for g in groups[:5]:
            title_el = await g.query_selector("div.scores")
            odds_els = await g.query_selector_all("span.odds")
            if not title_el or len(odds_els) != 2:
                continue
            title = (await title_el.inner_text()).strip()
            p1, p2 = [s.strip() for s in title.replace("–", " v ").split(" v ")[:2]]
            o1 = float((await odds_els[0].inner_text()).replace(",", "."))
            o2 = float((await odds_els[1].inner_text()).replace(",", "."))
            events.append({
                "event": f"{p1} - {p2}",
                "market": "Match Winner",
                "bookmaker": "Bet365",
                "odds": {p1: o1, p2: o2}
            })
        await browser.close()
    return events
