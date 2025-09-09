# scrapers/tippmixpro.py
from typing import List, Dict, Any
from playwright.async_api import async_playwright

BASE_URL = "https://www.tippmixpro.hu/hu/fogadas/i/fogadas"

def _norm(txt: str) -> float:
    return float(txt.replace("\xa0","").replace(",",".").strip())

def _split(title: str):
    t = title.replace("–","-").replace("—","-")
    if " - " in t:
        a,b = t.split(" - ",1)
        return a.strip(), b.strip()
    return t.strip(), "Másik"

async def _collect_from_page(page) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    # próbálunk sokféle elrendezést lefedni
    rows = await page.query_selector_all(
        "div.match-event, div.event-row, li:has(.odd), li:has(.odd-value), div:has(> .match-name)"
    )
    for r in rows:
        title_el = await r.query_selector(".match-name, .event-name, .name, .title, a")
        odd_els  = await r.query_selector_all(".odd-value, .odds, .odd, span:has-text('.')")

        if not title_el or len(odd_els) < 2:
            continue

        try:
            title = (await title_el.inner_text()).strip()
            o1 = _norm(await odd_els[0].inner_text())
            o2 = _norm(await odd_els[1].inner_text())
        except:
            continue

        p1, p2 = _split(title)
        market = "Match Winner" if ("tenisz" in (await page.title()).lower()) else "1X2"
        out.append({
            "event": f"{p1} - {p2}",
            "market": market,
            "bookmaker": "Tippmixpro",
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
            "Accept-Language": "hu-HU,hu;q=0.9,en;q=0.8"
        })

        for url in targets:
            try:
                await page.goto(url, timeout=90000)
                # cookie/consent
                for t in ("Elfogadom", "Rendben", "OK"):
                    try:
                        await page.get_by_text(t, exact=False).first.click(timeout=2000); break
                    except: pass

                # görgessünk le többször, hogy betöltsön mindent
                for _ in range(8):
                    await page.mouse.wheel(0, 2000)
                    await page.wait_for_timeout(600)

                events.extend(await _collect_from_page(page))
            except Exception:
                continue

        await browser.close()
    return events
