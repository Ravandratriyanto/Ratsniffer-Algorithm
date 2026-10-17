import json, time, sys, csv, re, urllib.request

API = "https://public-api.prozorro.gov.ua/api/2.5"
COMPETITIVE = {"aboveThresholdUA", "aboveThresholdEU", "aboveThreshold", "open"}
AWARDED = {"active.awarded", "complete"}
UA = {"User-Agent": "research/1.0"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def norm(s):
    return re.sub(r"[«»\"'’`]", "", re.sub(r"\s+", " ", (s or "")).strip().lower())

def load_cartels(path="data/amcu_cartels.csv"):
    out = []
    for r in csv.DictReader(open(path, encoding="utf-8")):
        uk = (r.get("firm_uk") or "").strip()
        if uk:
            out.append((norm(uk), r["cartel"], r["firm_en"]))
    return out

def match_cartels(names, cartels):
    ns = [norm(n) for n in names if n]
    return sorted({f"{cartel}::{en}" for key, cartel, en in cartels if any(key in n for n in ns)})

def bidder(b):
    td = (b.get("tenderers") or [{}])[0]
    return td.get("name") or (td.get("identifier") or {}).get("legalName"), (td.get("identifier") or {}).get("id")

def winner_edrpou(awards, lot=None):
    for a in awards:
        if a.get("status") == "active" and (lot is None or a.get("lotID") == lot):
            return ((a.get("suppliers") or [{}])[0].get("identifier") or {}).get("id")
    return None

def records(t, cartels):
    bids, lots, awards = t.get("bids") or [], t.get("lots") or [], t.get("awards") or []
    cpv = next((i.get("classification", {}).get("id") for i in (t.get("items") or [])), None)
    base = dict(tender_id=t.get("id"), tenderID=t.get("tenderID"), cpv=cpv,
                buyer=(t.get("procuringEntity") or {}).get("name"), date=t.get("date"))
    out = []
    def pack(lid, est, amts, names, eds, win):
        out.append({**base, "lot_id": lid, "estimate": est, "bids": amts, "names": names,
                    "bidders": eds, "winner": win, "cartel_hits": match_cartels(names, cartels)})
    if lots:
        est = {l["id"]: (l.get("value") or {}).get("amount") for l in lots}
        agg = {}
        for b in bids:
            nm, ed = bidder(b)
            for lv in (b.get("lotValues") or []):
                amt = (lv.get("initialValue") or lv.get("value") or {}).get("amount")
                if amt is None: continue
                g = agg.setdefault(lv.get("relatedLot"), {"a": [], "n": [], "e": []})
                g["a"].append(amt); g["n"].append(nm); g["e"].append(ed)
        for lid, g in agg.items():
            pack(lid, est.get(lid), g["a"], g["n"], g["e"], winner_edrpou(awards, lid))
    else:
        amts, names, eds = [], [], []
        for b in bids:
            amt = (b.get("initialValue") or b.get("value") or {}).get("amount")
            if amt is None: continue
            nm, ed = bidder(b); amts.append(amt); names.append(nm); eds.append(ed)
        if amts:
            pack(None, (t.get("value") or {}).get("amount"), amts, names, eds, winner_edrpou(awards))
    return out

def main(start="2025-01-01", limit=100000, out="data/prozorro_ua.ndjson"):
    cartels = load_cartels()
    print(f"{len(cartels)} cartel firm-keys loaded; feed starts {start}")
    url = f"{API}/tenders?offset={start}&opt_fields=procurementMethodType%2Cstatus"
    scanned = fetched = wrote = hits = 0
    with open(out, "w", encoding="utf-8") as fh:
        while url and scanned < limit:
            page = get(url)
            data = page.get("data") or []
            if not data:
                break
            for m in data:
                scanned += 1
                if m.get("procurementMethodType") not in COMPETITIVE or m.get("status") not in AWARDED:
                    continue
                try:
                    t = get(f"{API}/tenders/{m['id']}")["data"]
                except Exception as e:
                    print("skip", m.get("id"), e); continue
                fetched += 1
                for rec in records(t, cartels):
                    if len(rec["bids"]) >= 2:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); wrote += 1
                        if rec["cartel_hits"]: hits += 1
                time.sleep(0.15)
            print(f"scanned {scanned}  fetched {fetched}  wrote {wrote}  cartel-tagged {hits}")
            url = (page.get("next_page") or {}).get("uri")
    print(f"done: {wrote} multi-bid records ({hits} cartel-tagged) -> {out}")

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else "2025-01-01"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100000
    main(start, limit)
