import json, sys
from pyproc import Lpse, JenisPengadaan

HOST = sys.argv[1] if len(sys.argv) > 1 else "lkpp"
YEAR = int(sys.argv[2]) if len(sys.argv) > 2 else 2023

def summarize(tag, pkt):
    meta = {k: v for k, v in pkt.items() if k != "data"}
    rows = pkt.get("data") or []
    print(f"[{tag}] meta={meta}  data_rows={len(rows)}")
    return rows

with Lpse(HOST) as lpse:
    rows = summarize("tahun+barang", lpse.get_paket_tender(tahun=YEAR, kategori=JenisPengadaan.PENGADAAN_BARANG))
    if not rows:
        rows = summarize("tahun only", lpse.get_paket_tender(tahun=YEAR))
    if not rows:
        rows = summarize("konstruksi", lpse.get_paket_tender(tahun=YEAR, kategori=JenisPengadaan.PEKERJAAN_KONSTRUKSI))
    if not rows:
        rows = summarize("no filter", lpse.get_paket_tender())
    if not rows:
        print("\nno packages on this host/params. Try another host: lkpp, jakarta, pu, kemenkeu, kemenkes")
        sys.exit(0)
    print("\nfirst row:", rows[0])
    pid = rows[0][0]
    print("sample package id:", pid)
    detil = lpse.detil_paket_tender(pid)
    print("\ndetail methods:", [m for m in dir(detil) if not m.startswith("_")])
    for meth in ("get_pengumuman", "get_peserta", "get_hasil_evaluasi", "get_pemenang"):
        if not hasattr(detil, meth):
            print(f"\n{meth}: NOT on detail object"); continue
        print(f"\n=== {meth}() ===")
        print(json.dumps(getattr(detil, meth)(), indent=2, ensure_ascii=False)[:2500])
