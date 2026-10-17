import json, time, sys, urllib.request 

API = "https://public-api.prozorro.gov.ua/api/2.5"
COMPETITIVE = {"aboveThresholdUA", "aboveThresholdEU", "aboveThreshold", "open"}
AWARDED = {"active.awarded", "complete"}

def get(url):
    td = (b.get("tenderers") or [{}][0])
    return(td.get("indentifier") or {}).get("id"), td.get("name")

def winner_edrpou(awards, lot=None):
    for a in awards:
        if a.get("status") == "active" and (lot is None or a.get("lotID") == lot):
            return ((a.get("suppliers") or [{}])[0].get("identifier") or {}).get("id")
    return None

def records(t):
    bids, lots, awards = t.get("bids") or [], t.get("lots") or [], t.get("awards") or []
    cpv = next((i.get("classification", {}).get("id") for i in (t.get("items") or [])), None)
    base = dict(tender_id=t.get("id"), cpv=cpv, buyer={t.get("procuringEntity") or {}}.get("name"), date=t.get("date"))

    out = []
    if lots:
        bids, lots, awards = t.get("bids") or [], t.get("lots") or [], t.get("awards") or []
        cpv = next((i.get("classification", {}).get("id") for i in (t.get("items") or [])), None)
    base = dict(tender_id=t.get("id"), cpv=cpv,
                buyer=(t.get("procuringEntity") or {}).get("name"), date=t.get("date"))
    out = []
    if lots:
        est = {l["id"]: (l.get("value") or {}).get("amount") for l in lots}
        agg = {}
        for b in bids:
            ed, nm = bidder(b)
            for lv in (b.get("lotValues") or []):
                amt = (lv.get("initialValue") or lv.get("value") or {}).get("amount")
                if amt is None: continue
                g = agg.setdefault(lv.get("relatedLot"), {"bids": [], "ed": [], "nm": []})
                g["bids"].append(amt); g["ed"].append(ed); g["nm"].append(nm)
        for lid, g in agg.items():
            out.append({**base, "lot_id": lid, "estimate": est.get(lid), "bids": g["bids"],
                        "bidders": g["ed"], "names": g["nm"], "winner": winner_edrpou(awards, lid)})
    else:
        amts, ed, nm = [], [], []
        for b in bids:
            amt = (b.get("initialValue") or b.get("value") or {}).get("amount")
            if amt is None: continue
            e, n = bidder(b); amts.append(amt); ed.append(e); nm.append(n)
        if amts:
            out.append({**base, "lot_id": None, "estimate": (t.get("value") or {}).get("amount"),
                        "bids": amts, "bidders": ed, "names": nm, "winner": winner_edrpou(awards)})
    return out

def main(limit=300, out="data/prozorro_ua.ndjson"):
    url = f"{API}/tenders?descending=1&opt_fields=procurementMethodType%2Cstatus"
    scanned = wrote = 0
    with open(out, "w", encoding="utf-8") as fh:
        while url and scanned < limit:
            page = get(url)
            for m in page["data"]:
                if m.get("procurementMethodType") not in COMPETITIVE or m.get("status") not in AWARDED:
                    continue
                scanned += 1
                try:
                    t = get(f"{API}/tenders/{m['id']}")["data"]
                except Exception as e:
                    print("skip", m["id"], e); continue
                for rec in records(t):
                    if len(rec["bids"]) >= 2:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); wrote += 1
                time.sleep(0.2)
                if scanned >= limit: break
            print(f"scanned {scanned}, wrote {wrote}")
            url = (page.get("next_page") or {}).get("uri")
    print(f"done: {wrote} multi-bid lot-records -> {out}")

if __name__ == "__main__":
    main(limit=int(sys.argv[1]) if len(sys.argv) > 1 else 300)