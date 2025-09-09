from typing import Dict, List, Any

def find_surebets(events: List[Dict[str, Any]], stake: float = 10000.0):
    index = {}
    for e in events:
        key = (e["event"], e.get("market", "Match Winner"))
        if key not in index:
            index[key] = {}
        for outcome, odd in e["odds"].items():
            cur = index[key].get(outcome)
            if not cur or odd > cur["odd"]:
                index[key][outcome] = {"odd": float(odd), "bookmaker": e["bookmaker"]}

    out = []
    for (event_name, market), outcomes in index.items():
        if len(outcomes) < 2:
            continue
        inv_sum = sum(1.0 / v["odd"] for v in outcomes.values())
        is_arb = inv_sum < 1.0
        margin = round((1.0 - inv_sum) * 100, 2)
        plan = []
        if is_arb:
            for name, v in outcomes.items():
                stake_i = round(stake * ((1.0 / v["odd"]) / inv_sum), 2)
                expected_payout = round(stake_i * v["odd"], 2)
                plan.append({
                    "outcome": name,
                    "odd": v["odd"],
                    "bookmaker": v["bookmaker"],
                    "stake": stake_i,
                    "expected_payout": expected_payout,
                    "expected_profit": round(expected_payout - stake, 2)
                })

        out.append({
            "event": event_name,
            "market": market,
            "is_surebet": is_arb,
            "margin_pct": margin,
            "allocation": plan,
            "best_table": {k: {"odd": v["odd"], "bookmaker": v["bookmaker"]} for k,v in outcomes.items()}
        })
    return out
