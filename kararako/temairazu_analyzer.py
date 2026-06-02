# -*- coding: utf-8 -*-
"""
temairazu_analyzer.py
手間いらず 予約データ分析モジュール
"""

import csv, io, re, json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"

def read_csv(path):
    raw = path.read_bytes()
    for enc in ("cp932", "shift_jis", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc, errors="strict")
            rows = list(csv.DictReader(io.StringIO(text)))
            if rows: return rows
        except (UnicodeDecodeError, UnicodeError): continue
    return list(csv.DictReader(io.StringIO(raw.decode("cp932", errors="replace"))))

def find_files(data_dir=None):
    d = Path(data_dir) if data_dir else DATA_DIR
    return sorted(d.glob("temairazu_stay_*.csv")), sorted(d.glob("temairazu_pickup_*.csv"))

def pint(s):
    try: return int(str(s).replace(",","").strip())
    except: return 0

def parse_date(s):
    if not s: return None
    try: return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
    except: return None

def extract_prefecture(addr):
    if not addr: return "不明"
    addr = str(addr).strip().lstrip("〒").strip()
    addr = re.sub(r"^[\d\-]+\s*", "", addr)
    m = re.match(r"(北海道|東京都|大阪府|京都府|.{2,3}県)", addr)
    return m.group(1) if m else "不明"

def infer_travel_type(row):
    adults = pint(row.get("大人人数", 0))
    children = pint(row.get("子供人数", 0))
    male = pint(row.get("男性人数", 0))
    female = pint(row.get("女性人数", 0))
    rooms = max(1, pint(row.get("部屋数", 1)))
    if adults == 1 and children == 0: return "一人旅"
    elif adults == 2 and children == 0:
        if male == 0 and female == 2: return "女子旅"
        elif male == 2 and female == 0: return "男性2名"
        else: return "夫婦・カップル"
    elif children > 0: return "ファミリー"
    elif adults >= 3:
        return "グループ（複数室）" if rooms >= 2 else "グループ"
    else: return "その他"

def analyze(stay_files, pickup_files):
    all_stay = []
    for f in stay_files:
        rows = read_csv(f)
        print(f"    {f.name}: {len(rows)}件")
        all_stay.extend(rows)
    all_pickup = []
    for f in pickup_files:
        rows = read_csv(f)
        print(f"    {f.name}: {len(rows)}件")
        all_pickup.extend(rows)

    hotel_name = "（施設名未設定）"
    for r in all_stay:
        n = r.get("施設名", "").strip()
        if n: hotel_name = n; break

    active = [r for r in all_stay if r.get("予約区分", "") != "キャンセル"]
    cancels = [r for r in all_stay if r.get("予約区分", "") == "キャンセル"]

    # ── 先行予約同日対比 用の生データ（pickupベース） ──
    # pickupデータ：受信日ベースなので将来月のCIデータを含む
    # 予約番号ベースで最新状態のみ保持（同一予約の変更・キャンセルを反映）
    booking_latest = {}
    for r in all_pickup:
        bd = r.get("予約日時", "")[:10]
        ci = r.get("チェックイン日", "")[:7]
        resv_no = r.get("予約番号", "")
        if not bd or not ci: continue
        entry = {
            "bd": bd, "ci": ci,
            "ch": r.get("予約サイト名", "不明"),
            "rooms": max(1, pint(r.get("部屋数", 1))),
            "rn": max(1, pint(r.get("部屋数", 1))) * max(1, pint(r.get("泊数", 1))),
            "rev": pint(r.get("合計料金", 0)),
            "ppl": pint(r.get("大人人数", 0)) + pint(r.get("子供人数", 0)),
            "k": 1 if r.get("予約区分", "") == "キャンセル" else 0,
        }
        if resv_no:
            # 同一予約番号は最新（受信日が遅い方）を採用
            if resv_no not in booking_latest or bd >= booking_latest[resv_no]["bd"]:
                booking_latest[resv_no] = entry
        else:
            # 予約番号なしはそのまま追加（ユニークキー生成）
            booking_latest[f"_no_{len(booking_latest)}_{bd}_{ci}"] = entry
    bookings_raw = list(booking_latest.values())

    # ── MONTHLY ──
    by_month_a = defaultdict(list)
    by_month_c = defaultdict(list)
    for r in active:
        ym = r.get("チェックイン日", "")[:7]
        if ym: by_month_a[ym].append(r)
    for r in cancels:
        ym = r.get("チェックイン日", "")[:7]
        if ym: by_month_c[ym].append(r)
    all_yms = sorted(set(list(by_month_a.keys()) + list(by_month_c.keys())))
    monthly = {}
    for ym in all_yms:
        ra, rc = by_month_a.get(ym, []), by_month_c.get(ym, [])
        rev = sum(pint(r.get("合計料金", 0)) for r in ra)
        rooms = sum(max(1, pint(r.get("部屋数", 1))) for r in ra)
        rn = sum(max(1, pint(r.get("部屋数", 1))) * max(1, pint(r.get("泊数", 1))) for r in ra)
        persons = sum(pint(r.get("大人人数", 0)) + pint(r.get("子供人数", 0)) for r in ra)
        total = len(ra) + len(rc)
        monthly[ym] = {"revenue": rev, "rooms": rooms, "rn": rn, "persons": persons,
            "adr": round(rev / rn) if rn else 0, "per_person": round(rev / persons) if persons else 0,
            "cancel": len(rc), "total": total,
            "cancel_rate": round(len(rc) / total * 100, 1) if total else 0}

    # ── DAILY ──
    daily = defaultdict(list)
    daily_raw = defaultdict(lambda: defaultdict(lambda: {"rooms":0,"rn":0,"revenue":0,"persons":0,"channels":{}}))
    for r in active:
        ci = r.get("チェックイン日", "")[:10]
        if not ci: continue
        ym = ci[:7]; ch = r.get("予約サイト名", "不明")
        rooms = max(1, pint(r.get("部屋数", 1))); nights = max(1, pint(r.get("泊数", 1)))
        rev = pint(r.get("合計料金", 0)); ppl = pint(r.get("大人人数", 0)) + pint(r.get("子供人数", 0))
        d = daily_raw[ym][ci]; d["rooms"]+=rooms; d["rn"]+=rooms*nights; d["revenue"]+=rev; d["persons"]+=ppl
        d["channels"][ch] = d["channels"].get(ch, 0) + rooms
    for ym in sorted(daily_raw.keys()):
        for dt in sorted(daily_raw[ym].keys()):
            dd = daily_raw[ym][dt]
            dow_dt = parse_date(dt)
            dow = ["月","火","水","木","金","土","日"][dow_dt.weekday()] if dow_dt else ""
            daily[ym].append({"date":dt,"dow":dow,"rooms":dd["rooms"],"rn":dd["rn"],"revenue":dd["revenue"],"persons":dd["persons"],
                "adr":round(dd["revenue"]/dd["rn"]) if dd["rn"] else 0,"per_person":round(dd["revenue"]/dd["persons"]) if dd["persons"] else 0,"channels":dd["channels"]})

    # ── ROOM ──
    room = defaultdict(list)
    room_raw = defaultdict(lambda: defaultdict(lambda: {"rooms":0,"rn":0,"revenue":0,"persons":0}))
    for r in active:
        ym = r.get("チェックイン日", "")[:7]
        rt = re.sub(r"【温泉半露天風呂付】", "", r.get("部屋名称", "不明")).strip()
        rooms = max(1, pint(r.get("部屋数", 1))); nights = max(1, pint(r.get("泊数", 1)))
        rev = pint(r.get("合計料金", 0)); ppl = pint(r.get("大人人数", 0)) + pint(r.get("子供人数", 0))
        d = room_raw[ym][rt]; d["rooms"]+=rooms; d["rn"]+=rooms*nights; d["revenue"]+=rev; d["persons"]+=ppl
    for ym in sorted(room_raw.keys()):
        for rt in sorted(room_raw[ym].keys(), key=lambda x: -room_raw[ym][x]["revenue"]):
            d = room_raw[ym][rt]
            room[ym].append({"name":rt,"rooms":d["rooms"],"rn":d["rn"],"revenue":d["revenue"],"persons":d["persons"],
                "adr":round(d["revenue"]/d["rn"]) if d["rn"] else 0})

    # ── PLAN ──
    plan = defaultdict(list)
    plan_raw = defaultdict(lambda: defaultdict(lambda: {"count":0,"revenue":0,"persons":0,"channels":Counter()}))
    for r in active:
        ym = r.get("チェックイン日", "")[:7]; p = r.get("プラン名称", "不明")
        rev = pint(r.get("合計料金", 0)); ppl = pint(r.get("大人人数", 0)) + pint(r.get("子供人数", 0))
        ch = r.get("予約サイト名", "不明")
        d = plan_raw[ym][p]; d["count"]+=1; d["revenue"]+=rev; d["persons"]+=ppl; d["channels"][ch]+=1
    for ym in sorted(plan_raw.keys()):
        for p in sorted(plan_raw[ym].keys(), key=lambda x: -plan_raw[ym][x]["revenue"]):
            d = plan_raw[ym][p]
            plan[ym].append({"name":p[:80],"full_name":p,"count":d["count"],"revenue":d["revenue"],
                "avg_price":round(d["revenue"]/d["count"]) if d["count"] else 0,"persons":d["persons"],
                "top_channel":d["channels"].most_common(1)[0][0] if d["channels"] else ""})

    # ── CANCEL ──
    cancel = defaultdict(list)
    cancel_by_ch = defaultdict(lambda: defaultdict(lambda: {"cancel":0,"total":0,"revenue_lost":0}))
    for r in all_stay:
        ym = r.get("チェックイン日", "")[:7]; ch = r.get("予約サイト名", "")
        cancel_by_ch[ym][ch]["total"]+=1
        if r.get("予約区分", "") == "キャンセル":
            cancel_by_ch[ym][ch]["cancel"]+=1
            cancel_by_ch[ym][ch]["revenue_lost"]+=pint(r.get("合計料金", 0))
            cancel[ym].append({"channel":ch,"ci_date":r.get("チェックイン日","")[:10],"cancel_date":r.get("キャンセル日時","")[:10],
                "book_date":r.get("予約日時","")[:10],"revenue":pint(r.get("合計料金",0)),
                "room":re.sub(r"【温泉半露天風呂付】","",r.get("部屋名称","")).strip(),"plan":r.get("プラン名称","")[:50],"adults":pint(r.get("大人人数",0))})
    cancel_channels = {}
    for ym in cancel_by_ch:
        cancel_channels[ym] = []
        for ch in sorted(cancel_by_ch[ym].keys(), key=lambda x: -cancel_by_ch[ym][x]["cancel"]):
            d = cancel_by_ch[ym][ch]
            cancel_channels[ym].append({"name":ch,"cancel":d["cancel"],"total":d["total"],
                "rate":round(d["cancel"]/d["total"]*100,1) if d["total"] else 0,"revenue_lost":d["revenue_lost"]})

    # ── PICKUP ──
    pickup = []
    pickup_detail = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {"rooms":0,"rn":0,"revenue":0,"persons":0,"cancel_rooms":0})))
    for r in all_pickup:
        book_dt = r.get("予約日時","")[:10]
        if not book_dt: continue
        ch = r.get("予約サイト名","不明"); ci_month = r.get("チェックイン日","")[:7]
        kubun = r.get("予約区分",""); rooms = max(1,pint(r.get("部屋数",1))); nights = max(1,pint(r.get("泊数",1)))
        rev = pint(r.get("合計料金",0)); ppl = pint(r.get("大人人数",0)) + pint(r.get("子供人数",0))
        d = pickup_detail[book_dt][ch][ci_month]
        if kubun == "キャンセル": d["cancel_rooms"]+=rooms
        else: d["rooms"]+=rooms; d["rn"]+=rooms*nights; d["revenue"]+=rev; d["persons"]+=ppl
    all_pickup_channels = set()
    all_cin_months = set()
    for dt in sorted(pickup_detail.keys()):
        entry = {"date":dt,"dow":["月","火","水","木","金","土","日"][parse_date(dt).weekday()] if parse_date(dt) else "","channels":{}}
        for ch in pickup_detail[dt]:
            all_pickup_channels.add(ch)
            entry["channels"][ch] = {}
            for cm in pickup_detail[dt][ch]:
                all_cin_months.add(cm)
                d = pickup_detail[dt][ch][cm]
                entry["channels"][ch][cm] = {"rooms":d["rooms"],"rn":d["rn"],"revenue":d["revenue"],"persons":d["persons"],"cancel":d["cancel_rooms"]}
        pickup.append(entry)

    # ── LEADTIME ──
    lt_data = []
    for r in all_pickup:
        if r.get("予約区分","") == "キャンセル": continue
        book_dt = parse_date(r.get("予約日時","")[:10]); ci_dt = parse_date(r.get("チェックイン日",""))
        if not book_dt or not ci_dt: continue
        lt = (ci_dt - book_dt).days
        if lt >= 0: lt_data.append(lt)
    lt_dist = Counter(min(d, 180) for d in lt_data)
    leadtime = [{"days":d,"count":lt_dist.get(d,0)} for d in range(181)]

    # ── PREFECTURE ──
    prefecture = defaultdict(list)
    pref_raw = defaultdict(lambda: defaultdict(lambda: {"count":0,"revenue":0,"persons":0}))
    for r in active:
        ym = r.get("チェックイン日","")[:7]; pref = extract_prefecture(r.get("住所",""))
        rev = pint(r.get("合計料金",0)); ppl = pint(r.get("大人人数",0)) + pint(r.get("子供人数",0))
        d = pref_raw[ym][pref]; d["count"]+=1; d["revenue"]+=rev; d["persons"]+=ppl
    for ym in sorted(pref_raw.keys()):
        for p in sorted(pref_raw[ym].keys(), key=lambda x: -pref_raw[ym][x]["count"]):
            d = pref_raw[ym][p]
            prefecture[ym].append({"name":p,"count":d["count"],"revenue":d["revenue"],"persons":d["persons"],
                "avg_price":round(d["revenue"]/d["count"]) if d["count"] else 0})

    # ── TRAVEL ──
    travel = defaultdict(list)
    travel_raw = defaultdict(lambda: defaultdict(lambda: {"count":0,"revenue":0,"persons":0}))
    for r in active:
        ym = r.get("チェックイン日","")[:7]; t = infer_travel_type(r)
        rev = pint(r.get("合計料金",0)); ppl = pint(r.get("大人人数",0)) + pint(r.get("子供人数",0))
        d = travel_raw[ym][t]; d["count"]+=1; d["revenue"]+=rev; d["persons"]+=ppl
    for ym in sorted(travel_raw.keys()):
        for t in sorted(travel_raw[ym].keys(), key=lambda x: -travel_raw[ym][x]["count"]):
            d = travel_raw[ym][t]
            travel[ym].append({"name":t,"count":d["count"],"revenue":d["revenue"],"persons":d["persons"]})

    # ── 年リスト ──
    years = sorted(set(ym[:4] for ym in all_yms))

    now = datetime.now()
    return {
        "hotel_name": hotel_name,
        "cur_year": now.year,
        "generated_at": now.strftime("%Y年%m月%d日 %H:%M"),
        "months": all_yms,
        "years": years,
        "default_month": all_yms[-1] if all_yms else "",
        "monthly": monthly,
        "daily": dict(daily),
        "room": dict(room),
        "plan": dict(plan),
        "cancel": dict(cancel),
        "cancel_channels": cancel_channels,
        "bookings_raw": bookings_raw,
        "pickup": pickup,
        "pickup_channels": sorted(list(all_pickup_channels)),
        "pickup_cin_months": sorted(list(all_cin_months)),
        "leadtime": leadtime,
        "leadtime_stats": {"avg": round(sum(lt_data)/len(lt_data),1) if lt_data else 0,
                           "median": sorted(lt_data)[len(lt_data)//2] if lt_data else 0},
        "prefecture": dict(prefecture),
        "travel": dict(travel),
    }

def load_temairazu_data(hotel_dir=None):
    global DATA_DIR
    if hotel_dir: DATA_DIR = Path(hotel_dir) / "data"
    stay_files, pickup_files = find_files()
    if not stay_files:
        raise FileNotFoundError(f"手間いらず Stay CSV が見つかりません\n  探索先: {DATA_DIR}")
    print(f"  Stay CSV:")
    if pickup_files: print(f"  Pickup CSV:")
    return analyze(stay_files, pickup_files)

if __name__ == "__main__":
    data = load_temairazu_data()
    print(f"\n施設名: {data['hotel_name']}")
    print(f"月数: {len(data['months'])}")
    print(f"年: {data['years']}")
    print(f"bookings_raw: {len(data['bookings_raw'])}件")
