import glob, json, re

def num(x): return (x.get("netAmountEur") or x.get("netAmount")) if isinstance(x,dict) else None
def up(s): return re.sub(r"[^A-Z0-9 ]"," ",(s or "").upper())

CASES = [
    ("Butimanu-Brazi", lambda ti,bu,yr: "BUTIMANU" in ti and 2008 <= yr <= 2010),
    ("Giurgiu-Ruse",   lambda ti,bu,yr: "GIURGIU" in ti and "RUSE" in ti and 2010 <= yr <= 2012),
    ("APIA-IT",        lambda ti,bu,yr: "APIA" in bu and ("INFORMATIC" in ti or "SISTEM" in ti) and 2007 <= yr <= 2009),
]

def main():
    hits = {c[0]: [] for c in CASES}
    for f in sorted(glob.glob("data/data-ro-20*.ndjson")):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            t = json.loads(line)
            lots = t.get("lots") or []
            nb = sum(len(l.get("bids") or []) for l in lots)
            if nb == 0: continue
            try: yr = int(t.get("tenderYear"))
            except (TypeError, ValueError): continue
            ti = up(t.get("title")); bu = up((t.get("buyers") or [{}])[0].get("name"))
            for name, rule in CASES:
                if rule(ti, bu, yr):
                    est, fin = num(t.get("estimatedPrice")), num(t.get("finalPrice"))
                    prem = fin/est if (est and fin and est > 0) else None
                    single = int(nb == 1); nonopen = 0 if t.get("procedureType") == "OPEN" else 1
                    wpf = int(prem is not None and prem >= 0.98)
                    winners = {bd["name"] for l in lots for b in (l.get("bids") or [])
                               if b.get("isWinning") for bd in (b.get("bidders") or []) if bd.get("name")}
                    hits[name].append({"title": t.get("title"), "year": yr,
                                       "buyer": (t.get("buyers") or [{}])[0].get("name"),
                                       "nbids": nb, "proc": t.get("procedureType"),
                                       "prem": round(prem, 3) if prem else None,
                                       "flags": single + nonopen + wpf, "winner": sorted(winners)})
    for name, _ in CASES:
        print(f"\n=== {name}: {len(hits[name])} candidate tender(s) ===")
        for h in hits[name][:25]:
            print(f"  {h['year']}  nbids={h['nbids']}  proc={h['proc']}  prem={h['prem']}  flags={h['flags']}/3")
            print(f"     buyer:  {h['buyer']}")
            print(f"     title:  {(h['title'] or '')[:90]}")
            print(f"     winner: {h['winner']}")
def bid_count(lots):
    bcs = [l.get("bids.Count") for l in lots if isinstance(l.get("bidsCount"), (int, float))]
    return max(bcs) if bsc else None
if __name__ == "__main__":
    main()
