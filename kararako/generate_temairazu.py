# -*- coding: utf-8 -*-
"""
generate_temairazu.py
手間いらず 予約分析ダッシュボード生成

使い方:
  python3 generate_temairazu.py                     # カレントの data/ を探索
  python3 generate_temairazu.py --hotel /path/to/hotel  # 指定フォルダの data/ を探索
  python3 generate_temairazu.py --no-open           # ブラウザを開かない

data/ フォルダの命名規則:
  Stay:   temairazu_stay_YYYYMM.csv   (例: temairazu_stay_202605.csv)
  Pickup: temairazu_pickup_YYYYMM.csv (例: temairazu_pickup_202605.csv)
  毎月2枚ずつ追加していくだけで、自動的に全月が統合されます。
"""
import sys
import json
import argparse
import webbrowser
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from temairazu_analyzer import load_temairazu_data

OUTPUT_DIR = Path(__file__).parent / "output"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hotel", type=str, default=None,
                        help="ホテルフォルダのパス（data/ サブフォルダを探索）")
    parser.add_argument("--no-open", action="store_true",
                        help="ブラウザを自動で開かない")
    args = parser.parse_args()

    print("=" * 50)
    print("  手間いらず 予約分析ダッシュボード生成")
    print("=" * 50)

    print("\n[1/2] データ読み込み中...")
    try:
        data = load_temairazu_data(args.hotel)
    except FileNotFoundError as e:
        print(f"\nエラー: {e}")
        args.no_open or input("\nEnterキーで終了...")
        return

    m_count = len(data["months"])
    d_count = sum(len(v) for v in data["daily"].values())
    r_count = sum(len(v) for v in data["room"].values())
    p_count = len(data["pickup"])
    print(f"  月次: {m_count}ヶ月  Daily: {d_count}件  Room: {r_count}件  Pickup: {p_count}日")

    print("\n[2/2] ダッシュボード生成中...")
    out_dir = Path(args.hotel) / "output" if args.hotel else OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(build_html(data), encoding="utf-8")
    print(f"  出力: {out}")

    print("\n✓ 完了！")
    if not args.no_open:
        print("ブラウザで開きます...")
        webbrowser.open(out.as_uri())
        input("\nEnterキーで終了...")


# ========================================================================
# HTML 生成
# ========================================================================

def build_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False, default=str)
    return html_head(data) + html_body(data) + \
        f"\n<script>\nconst DATA = {data_json};\n{make_js()}\n</script>\n</body>\n</html>"


def html_head(data):
    hotel = data["hotel_name"]
    gen_at = data["generated_at"]
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{hotel}｜予約分析</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');
:root{{--bg:#faf8f4;--sf:#f5f1ea;--bd:rgba(44,36,24,0.12);--tx:#2c2418;--mu:#9a8e7e;--ac:#8b6914;--up:#2d7a2d;--dn:#c03030;--wn:#b07828;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Noto Sans JP',sans-serif;background:var(--bg);color:var(--tx);font-size:13px;line-height:1.6;}}
a{{color:var(--ac);text-decoration:none;}}
.header{{background:linear-gradient(135deg,#f5f0e8 0%,#faf8f4 100%);border-bottom:1px solid var(--bd);padding:16px 24px;position:sticky;top:0;z-index:100;}}
.header h1{{font-size:17px;font-weight:500;letter-spacing:.5px;}}
.header .sub{{color:var(--mu);font-size:11px;margin-top:3px;font-family:'DM Mono',monospace;}}
.top-controls{{display:flex;align-items:center;gap:12px;margin-top:8px;flex-wrap:wrap;}}
.top-controls label{{font-size:11px;color:var(--mu);}}
.top-controls select,.top-controls button{{background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:4px 10px;border-radius:6px;font-size:11px;cursor:pointer;font-family:inherit;}}
.top-controls select:hover,.top-controls button:hover{{border-color:var(--ac);}}
.nav{{display:flex;gap:2px;padding:8px 24px 0;flex-wrap:wrap;border-bottom:1px solid var(--bd);background:#f5f1ea;position:sticky;top:72px;z-index:99;}}
.nav-tab{{background:none;border:none;color:var(--mu);padding:7px 12px;font-size:11.5px;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit;transition:all .15s;white-space:nowrap;}}
.nav-tab:hover{{color:var(--tx);}}
.nav-tab.active{{color:#8b6914;border-bottom-color:#8b6914;font-weight:500;}}
.month-bar{{display:flex;gap:4px;padding:8px 24px;background:var(--bg);border-bottom:1px solid var(--bd);flex-wrap:wrap;align-items:center;}}
.month-bar .label{{font-size:11px;color:var(--mu);margin-right:8px;}}
.month-btn{{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:4px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-family:inherit;}}
.month-btn:hover{{border-color:var(--ac);color:var(--tx);}}
.month-btn.active{{background:#8b6914;color:#faf8f4;border-color:var(--ac);}}
.container{{max-width:1400px;margin:0 auto;padding:16px 24px 60px;}}
.section{{display:none;animation:fadeIn .25s ease;}}
.section.active{{display:block;}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:20px;}}
.kpi{{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:14px;position:relative;overflow:hidden;}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;}}
.kpi.blue::before{{background:#3366aa;}}.kpi.green::before{{background:#2d7a2d;}}.kpi.orange::before{{background:#b07828;}}.kpi.red::before{{background:#c03030;}}
.kpi .label{{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;}}
.kpi .value{{font-size:20px;font-weight:500;font-family:'DM Mono',monospace;}}
.kpi .unit{{font-size:11px;color:var(--mu);margin-left:2px;}}
.card{{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:16px;margin-bottom:14px;}}
.card h3{{font-size:13px;font-weight:500;margin-bottom:12px;display:flex;align-items:center;gap:8px;}}
.card h3 .badge{{font-size:10px;background:#8b6914;color:#faf8f4;padding:1px 7px;border-radius:10px;font-weight:400;}}
table{{width:100%;border-collapse:collapse;font-size:12px;}}
th{{text-align:left;padding:6px 8px;border-bottom:2px solid var(--bd);color:var(--mu);font-weight:500;font-size:10.5px;white-space:nowrap;position:sticky;top:0;background:var(--sf);}}
td{{padding:5px 8px;border-bottom:1px solid var(--bd);}}
tr:hover td{{background:rgba(139,105,20,0.04);}}
.num{{text-align:right;font-family:'DM Mono',monospace;font-size:11.5px;}}
.up{{color:var(--up);}}.dn{{color:var(--dn);}}
.chart-wrap{{position:relative;height:300px;margin:8px 0;}}
.chart-wrap.tall{{height:400px;}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;}}
.grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;}}
@media(max-width:900px){{.grid-2,.grid-3{{grid-template-columns:1fr;}}}}
.pill{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:500;}}
.pill-blue{{background:rgba(139,105,20,.12);color:#8b6914;}}.pill-green{{background:rgba(45,122,45,.12);color:#2d7a2d;}}
.pill-red{{background:rgba(192,48,48,.12);color:#c03030;}}.pill-orange{{background:rgba(176,120,40,.12);color:#b07828;}}
.scroll-table{{max-height:500px;overflow-y:auto;}}
.scroll-table::-webkit-scrollbar{{width:5px;}}.scroll-table::-webkit-scrollbar-thumb{{background:rgba(44,36,24,.2);border-radius:3px;}}
.bar-bg{{height:5px;border-radius:3px;background:var(--bd);overflow:hidden;margin-top:3px;}}
.bar-fill{{height:100%;border-radius:3px;}}
.filter-row{{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center;}}
.filter-row label{{font-size:11px;color:var(--mu);}}
.filter-row select,.filter-row input,.filter-row button{{background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:4px 8px;border-radius:6px;font-size:11px;font-family:inherit;}}
.toggle-btn{{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:3px 10px;border-radius:6px;font-size:10.5px;cursor:pointer;font-family:inherit;}}
.toggle-btn.active{{background:rgba(139,105,20,.12);color:#8b6914;border-color:#8b6914;}}
.no-data{{text-align:center;padding:40px;color:var(--mu);font-size:12px;}}
.footer{{text-align:center;padding:20px;color:var(--mu);font-size:10px;border-top:1px solid var(--bd);margin-top:20px;}}
@media print{{.header,.nav,.month-bar{{position:static;}}.section{{display:block!important;page-break-before:always;}}body{{background:#fff;}}}}
</style>
</head>
<body>
"""


def html_body(data):
    hotel = data["hotel_name"]
    gen_at = data["generated_at"]
    months = data["months"]

    tab_defs = [
        ("monthly", "月別実績"), ("yoy", "前年同日対比"), ("daily", "Daily"),
        ("room", "Room"), ("room_monthly", "Room月次"), ("plan", "Plan"),
        ("cancel", "キャンセル"), ("pickup", "Pickup"), ("leadtime", "Leadtime"),
        ("pref", "都道府県"), ("pref_monthly", "都道府県月次"), ("travel", "旅行動態"),
    ]

    nav = "".join(
        f'<button class="nav-tab" onclick="showTab(\'{t}\',this)">{l}</button>'
        for t, l in tab_defs
    )
    month_btns = "".join(
        f'<button class="month-btn" onclick="switchAllTabs(\'{m}\')">{m}</button>'
        for m in months
    )
    month_opts = "".join(f'<option value="{m}">{m}</option>' for m in months)
    sections = "\n".join(f'<div class="section" id="tab-{t}"></div>' for t, _ in tab_defs)

    return f"""
<div class="header">
<div style="display:flex;justify-content:space-between;align-items:flex-start">
<div>
<h1>{hotel}｜予約分析ダッシュボード</h1>
<div class="sub">source: 手間いらず 予約CSV ／ 生成: {gen_at}</div>
</div>
<div class="top-controls">
<label>全タブ切替：</label>
<select id="global-month-select" onchange="switchAllTabs(this.value)">{month_opts}</select>
<button onclick="printAll()">&#x1F5A8; 全ページ印刷</button>
</div>
</div>
</div>
<div class="nav">{nav}</div>
<div class="month-bar" id="monthBar"><span class="label">表示月：</span>{month_btns}</div>
<div class="container" id="content">
{sections}
<div class="footer">{hotel}様｜予約分析ダッシュボード 手間いらず予約CSV → temairazu_stay / temairazu_pickup</div>
</div>
"""


def make_js():
    """ダッシュボード描画ロジック（JavaScript文字列を返す）。"""
    # build_v2.py の JS をそのまま埋め込む
    # DATA は呼び出し元で注入済み
    return JS_CODE


# ========================================================================
# JavaScript (TLリンカーン版と同一構造)
# ========================================================================

JS_CODE = r"""
// Channel grouping
function groupCh(c){
  if(c==='一休.com'||c==='楽天トラベル'||c==='じゃらん'||c==='Booking.com')return c;
  if(c==='予約プロクロス'||c==='自社')return '自社';
  return 'その他';
}
// Physical room count from name (count ・-separated names after ｜)
function physicalRooms(name){
  const p=name.split('｜');
  if(p.length<2)return 1;
  return p[1].split('・').length;
}
// Days in month
function daysInMonth(ym){
  const[y,m]=ym.split('-').map(Number);
  return new Date(y,m,0).getDate();
}
const CH_COLORS={'一休.com':'#d4870a','楽天トラベル':'#ef4444','じゃらん':'#22c55e','るるぶトラベル':'#3b82f6','予約プロクロス':'#a78bfa','Booking.com':'#06b6d4','Relux':'#ec4899','ツアービルダー':'#f97316','JALパック':'#14b8a6','e宿':'#8b5cf6','自社':'#a78bfa'};
function chColor(c){return CH_COLORS[c]||'#64748b';}
function fmt(n){if(n==null)return'-';return Number(n).toLocaleString();}
function fmtY(n){return'\u00a5'+fmt(n);}
function pct(a,b){return b?(a/b*100).toFixed(1):'-';}
const monthTabs=['monthly','daily','room','plan','cancel','pref','travel'];
const noMonthBar=['yoy','room_monthly','pref_monthly'];
let tabMonths={};monthTabs.forEach(t=>{tabMonths[t]=DATA.default_month;});
let curTab='monthly';
const charts={};
function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id];}}
function makeChart(id,cfg){destroyChart(id);const c=document.getElementById(id);if(!c)return null;charts[id]=new Chart(c,cfg);return charts[id];}
function showTab(name,el){document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));document.querySelectorAll('.nav-tab').forEach(t=>t.classList.remove('active'));document.getElementById('tab-'+name).classList.add('active');if(el)el.classList.add('active');curTab=name;document.getElementById('monthBar').style.display=noMonthBar.includes(name)?'none':'';const tm=tabMonths[name]||DATA.default_month;document.querySelectorAll('.month-btn').forEach(x=>x.classList.toggle('active',x.textContent===tm));drawTab(name);}
function switchAllTabs(m){monthTabs.forEach(t=>{tabMonths[t]=m;});document.querySelectorAll('.month-btn').forEach(x=>x.classList.toggle('active',x.textContent===m));const sel=document.getElementById('global-month-select');if(sel)sel.value=m;drawTab(curTab);}
function printAll(){document.querySelectorAll('.section').forEach(s=>s.classList.add('active'));setTimeout(()=>{window.print();},300);}
function drawTab(name){const m=tabMonths[name]||DATA.default_month;switch(name){case'monthly':drawMonthly(m);break;case'yoy':drawYoY();break;case'daily':drawDaily(m);break;case'room':drawRoom(m);break;case'room_monthly':drawRoomMonthly();break;case'plan':drawPlan(m);break;case'cancel':drawCancel(m);break;case'pickup':drawPickup();break;case'leadtime':drawLeadtime();break;case'pref':drawPref(m);break;case'pref_monthly':drawPrefMonthly();break;case'travel':drawTravel(m);break;}}

let rangeMode=false;let rangeFrom='';let rangeTo='';
function drawMonthly(m){const el=document.getElementById('tab-monthly');
  const allM=DATA.months;
  if(!rangeFrom)rangeFrom=allM[0];
  if(!rangeTo)rangeTo=allM[allM.length-1];
  let fromOpts=allM.map(mm=>`<option value="${mm}" ${rangeFrom===mm?'selected':''}>${mm}</option>`).join('');
  let toOpts=allM.map(mm=>`<option value="${mm}" ${rangeTo===mm?'selected':''}>${mm}</option>`).join('');
  let rangeUI=`<div class="filter-row" style="margin-bottom:12px">
    <button class="toggle-btn ${!rangeMode?'active':''}" onclick="rangeMode=false;drawMonthly(tabMonths.monthly)">月別</button>
    <button class="toggle-btn ${rangeMode?'active':''}" onclick="rangeMode=true;drawMonthly(tabMonths.monthly)">期間指定</button>
    ${rangeMode?`<select onchange="rangeFrom=this.value;drawMonthly(tabMonths.monthly)" style="margin-left:8px">${fromOpts}</select>
    <span style="color:var(--mu);font-size:11px">〜</span>
    <select onchange="rangeTo=this.value;drawMonthly(tabMonths.monthly)">${toOpts}</select>`:''}
  </div>`;

  // Determine which months to aggregate
  const targetMonths=rangeMode?allM.filter(mm=>mm>=rangeFrom&&mm<=rangeTo):[m];
  const label=rangeMode?`${rangeFrom} 〜 ${rangeTo}`:m;

  // Aggregate monthly data
  let aRev=0,aRooms=0,aRn=0,aPersons=0,aCancel=0,aTotal=0;
  targetMonths.forEach(mm=>{
    const md=DATA.monthly[mm];if(!md)return;
    aRev+=md.revenue;aRooms+=md.rooms;aRn+=md.rn;aPersons+=md.persons;aCancel+=md.cancel;aTotal+=md.total;
  });
  const aAdr=aRn?Math.round(aRev/aRn):0;
  const aPerPerson=aPersons?Math.round(aRev/aPersons):0;
  const aCancelRate=aTotal?((aCancel/aTotal)*100).toFixed(1):0;

  // Aggregate channel data from daily
  const chRevMap={};
  targetMonths.forEach(mm=>{
    (DATA.daily[mm]||[]).forEach(d=>{const tr=d.rooms;Object.entries(d.channels).forEach(([ch,rooms])=>{
      if(!chRevMap[ch])chRevMap[ch]={rooms:0,revenue:0,rn:0,persons:0};
      chRevMap[ch].rooms+=rooms;chRevMap[ch].revenue+=tr>0?Math.round(d.revenue*rooms/tr):0;
      chRevMap[ch].rn+=rooms;chRevMap[ch].persons+=tr>0?Math.round(d.persons*rooms/tr):0;
    });});
  });
  const chList=Object.entries(chRevMap).sort((a,b)=>b[1].revenue-a[1].revenue).map(([ch,d])=>({name:ch,rooms:d.rooms,rn:d.rn,revenue:d.revenue,persons:d.persons,adr:d.rn>0?Math.round(d.revenue/d.rn):0}));
  const totalRev=chList.reduce((a,c)=>a+c.revenue,0);
  let chRows=chList.map(c=>`<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${chColor(c.name)};margin-right:6px"></span>${c.name}</td><td class="num">${fmt(c.rooms)}</td><td class="num">${fmt(c.rn)}</td><td class="num">${fmtY(c.revenue)}</td><td class="num">${fmtY(c.adr)}</td><td class="num">${fmt(c.persons)}</td><td class="num">${pct(c.revenue,totalRev)}%</td></tr>`).join('');
  el.innerHTML=rangeUI+`<div class="kpi-row"><div class="kpi blue"><div class="label">売上合計</div><div class="value">${(aRev/10000).toFixed(0)}<span class="unit">万円</span></div></div><div class="kpi green"><div class="label">予約件数</div><div class="value">${fmt(aRooms)}<span class="unit">件</span></div></div><div class="kpi blue"><div class="label">室泊数 RN</div><div class="value">${fmt(aRn)}<span class="unit">RN</span></div></div><div class="kpi orange"><div class="label">ADR</div><div class="value">${fmt(aAdr)}<span class="unit">円</span></div></div><div class="kpi green"><div class="label">人泊単価</div><div class="value">${fmt(aPerPerson)}<span class="unit">円</span></div></div><div class="kpi red"><div class="label">キャンセル率</div><div class="value">${aCancelRate}<span class="unit">%</span></div></div></div><div class="grid-2"><div class="card"><h3>チャネル別構成${rangeMode?' ('+label+')':''}</h3><div class="chart-wrap"><canvas id="monthly-pie"></canvas></div></div><div class="card"><h3>チャネル別明細</h3><div class="scroll-table"><table><tr><th>チャネル</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">構成比</th></tr>${chRows}</table></div></div></div>`;
  const cData=chList.filter(c=>c.revenue>0);
  makeChart('monthly-pie',{type:'doughnut',data:{labels:cData.map(c=>c.name),datasets:[{data:cData.map(c=>c.revenue),backgroundColor:cData.map(c=>chColor(c.name)),borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#2c2418',font:{size:11},padding:8}},tooltip:{callbacks:{label:ctx=>ctx.label+': \u00a5'+fmt(ctx.raw)+' ('+pct(ctx.raw,totalRev)+'%)'}}}}});}

/* ========== YOY: 先行予約 同日対比（テーブル形式） ========== */
function calcPosition(baseDate){
  // baseDate以前に受信した予約を、宿泊月×チャネル別に集計
  const br=DATA.bookings_raw;
  const baseYear=parseInt(baseDate.slice(0,4));
  const result={};// {ci_month: {ch: {rooms,rn,rev,ppl}}}
  br.forEach(b=>{
    if(b.bd<=baseDate && b.k===0){
      const ci=b.ci;// "YYYY-MM"
      if(!result[ci])result[ci]={};
      if(!result[ci][b.ch])result[ci][b.ch]={rooms:0,rn:0,rev:0,ppl:0};
      const d=result[ci][b.ch];
      d.rooms+=b.rooms;d.rn+=b.rn;d.rev+=b.rev;d.ppl+=b.ppl;
    }
  });
  return result;
}
function drawYoY(){
  const el=document.getElementById('tab-yoy');
  const br=DATA.bookings_raw;
  if(!br||!br.length){el.innerHTML='<div class="no-data">予約データがありません</div>';return;}
  const allDates=[...new Set(br.map(b=>b.bd))].sort();
  const latestDate=allDates[allDates.length-1];
  if(!window._yoyBase)window._yoyBase=latestDate;
  const base=window._yoyBase;
  const baseYear=parseInt(base.slice(0,4));
  const baseMM=base.slice(5,7);
  const prevBase=(baseYear-1)+base.slice(4);

  // Calc positions
  const cur=calcPosition(base);
  const prev=calcPosition(prevBase);

  // Stay months: from base month forward 6 months (current year)
  const stayMonths=[];
  for(let i=0;i<8;i++){
    let mm=parseInt(baseMM)+i;
    let yy=baseYear;
    if(mm>12){mm-=12;yy+=1;}
    stayMonths.push(yy+'-'+String(mm).padStart(2,'0'));
  }

  // Collect all channels
  const chSet=new Set();
  stayMonths.forEach(sm=>{
    if(cur[sm])Object.keys(cur[sm]).forEach(c=>chSet.add(c));
    const pSm=(baseYear-1)+sm.slice(4);
    if(prev[pSm])Object.keys(prev[pSm]).forEach(c=>chSet.add(c));
  });
  const channels=[...chSet].sort();

  // Build table per stay month
  let tables='';
  stayMonths.forEach(sm=>{
    const pSm=(baseYear-1)+sm.slice(4);
    const curM=cur[sm]||{};
    const prevM=prev[pSm]||{};
    // Totals
    let tCur={rooms:0,rn:0,rev:0,ppl:0};
    let tPrev={rooms:0,rn:0,rev:0,ppl:0};
    channels.forEach(ch=>{
      const c=curM[ch]||{rooms:0,rn:0,rev:0,ppl:0};
      const p=prevM[ch]||{rooms:0,rn:0,rev:0,ppl:0};
      tCur.rooms+=c.rooms;tCur.rn+=c.rn;tCur.rev+=c.rev;tCur.ppl+=c.ppl;
      tPrev.rooms+=p.rooms;tPrev.rn+=p.rn;tPrev.rev+=p.rev;tPrev.ppl+=p.ppl;
    });
    if(tCur.rev===0&&tPrev.rev===0)return;// skip empty months

    function diffVal(a,b){const d=a-b;return`<span class="${d>=0?'up':'dn'}">${d>=0?'+':''}${fmt(d)}</span>`;}
    function diffValY(a,b){const d=a-b;return`<span class="${d>=0?'up':'dn'}">${d>=0?'+':''}${fmtY(d)}</span>`;}
    function adr(rev,rn){return rn?Math.round(rev/rn):0;}
    function pprice(rev,ppl){return ppl?Math.round(rev/ppl):0;}
    function companion(ppl,rooms){return rooms?(ppl/rooms).toFixed(2):'-';}

    let rows=channels.map(ch=>{
      const c=curM[ch]||{rooms:0,rn:0,rev:0,ppl:0};
      const p=prevM[ch]||{rooms:0,rn:0,rev:0,ppl:0};
      return`<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${chColor(ch)};margin-right:4px"></span>${ch}</td>
        <td class="num">${fmtY(c.rev)}</td><td class="num" style="color:var(--mu)">${fmtY(p.rev)}</td><td class="num">${diffValY(c.rev,p.rev)}</td>
        <td class="num">${c.rooms}</td><td class="num" style="color:var(--mu)">${p.rooms}</td><td class="num">${diffVal(c.rooms,p.rooms)}</td>
        <td class="num">${fmtY(adr(c.rev,c.rn))}</td><td class="num" style="color:var(--mu)">${fmtY(adr(p.rev,p.rn))}</td><td class="num">${diffValY(adr(c.rev,c.rn),adr(p.rev,p.rn))}</td>
        <td class="num">${c.ppl}</td><td class="num" style="color:var(--mu)">${p.ppl}</td>
        <td class="num">${fmtY(pprice(c.rev,c.ppl))}</td><td class="num" style="color:var(--mu)">${fmtY(pprice(p.rev,p.ppl))}</td><td class="num">${diffValY(pprice(c.rev,c.ppl),pprice(p.rev,p.ppl))}</td>
        <td class="num">${companion(c.ppl,c.rooms)}</td></tr>`;
    }).join('');
    // Total row
    rows+=`<tr style="border-top:2px solid var(--bd);font-weight:500"><td>合計</td>
      <td class="num">${fmtY(tCur.rev)}</td><td class="num" style="color:var(--mu)">${fmtY(tPrev.rev)}</td><td class="num">${diffValY(tCur.rev,tPrev.rev)}</td>
      <td class="num">${tCur.rooms}</td><td class="num" style="color:var(--mu)">${tPrev.rooms}</td><td class="num">${diffVal(tCur.rooms,tPrev.rooms)}</td>
      <td class="num">${fmtY(adr(tCur.rev,tCur.rn))}</td><td class="num" style="color:var(--mu)">${fmtY(adr(tPrev.rev,tPrev.rn))}</td><td class="num">${diffValY(adr(tCur.rev,tCur.rn),adr(tPrev.rev,tPrev.rn))}</td>
      <td class="num">${tCur.ppl}</td><td class="num" style="color:var(--mu)">${tPrev.ppl}</td>
      <td class="num">${fmtY(pprice(tCur.rev,tCur.ppl))}</td><td class="num" style="color:var(--mu)">${fmtY(pprice(tPrev.rev,tPrev.ppl))}</td><td class="num">${diffValY(pprice(tCur.rev,tCur.ppl),pprice(tPrev.rev,tPrev.ppl))}</td>
      <td class="num">${companion(tCur.ppl,tCur.rooms)}</td></tr>`;

    tables+=`<div class="card"><h3>宿泊月：${sm}（前年：${pSm}）</h3>
      <div class="scroll-table" style="overflow-x:auto"><table>
        <tr><th>チャネル</th><th class="num">売上今年</th><th class="num">売上前年</th><th class="num">差</th>
        <th class="num">室数今</th><th class="num">室数前</th><th class="num">差</th>
        <th class="num">ADR今</th><th class="num">ADR前</th><th class="num">差</th>
        <th class="num">人数今</th><th class="num">人数前</th>
        <th class="num">客単価今</th><th class="num">客単価前</th><th class="num">差</th>
        <th class="num">同伴</th></tr>
        ${rows}
      </table></div></div>`;
  });

  el.innerHTML=`
  <div class="filter-row">
    <label>基準日：</label>
    <input type="date" value="${base}" onchange="window._yoyBase=this.value;drawYoY()" style="color:var(--tx)">
    <button class="toggle-btn" onclick="drawYoY()">表示</button>
  </div>
  <p style="color:var(--mu);font-size:11px;margin-bottom:12px">${base}時点 vs ${prevBase}時点の先行予約残高を比較</p>
  ${tables||'<div class="no-data">該当データがありません</div>'}`;
}

function drawDaily(m){const el=document.getElementById('tab-daily');const dd=DATA.daily[m]||[];if(!dd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}let rows=dd.map(d=>{const isWe=d.dow==='土'||d.dow==='日';return`<tr style="${isWe?'background:rgba(139,105,20,.04)':''}"><td>${d.date} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td><td class="num">${d.rooms}</td><td class="num">${d.rn}</td><td class="num">${fmtY(d.revenue)}</td><td class="num">${fmtY(d.adr)}</td><td class="num">${d.persons}</td><td class="num">${fmtY(d.per_person)}</td></tr>`;}).join('');el.innerHTML=`<div class="card"><h3>日別売上（${m}）</h3><div class="chart-wrap tall"><canvas id="daily-chart"></canvas></div></div><div class="card"><h3>日別明細</h3><div class="scroll-table"><table><tr><th>日付</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">人泊単価</th></tr>${rows}</table></div></div>`;makeChart('daily-chart',{type:'bar',data:{labels:dd.map(d=>d.date.slice(5)+' '+d.dow),datasets:[{type:'bar',label:'売上',data:dd.map(d=>d.revenue),backgroundColor:dd.map(d=>(d.dow==='土'||d.dow==='日')?'rgba(176,120,40,.5)':'rgba(139,105,20,.55)'),borderRadius:3,yAxisID:'y'},{type:'line',label:'ADR',data:dd.map(d=>d.adr),borderColor:'#d4870a',backgroundColor:'transparent',pointRadius:2,tension:.3,yAxisID:'y1'}]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},scales:{x:{ticks:{color:'#9a8e7e',font:{size:10}}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y1:{position:'right',grid:{display:false},ticks:{color:'#d4870a',callback:v=>'\u00a5'+fmt(v)}}},plugins:{legend:{labels:{color:'#2c2418'}}}}});}

function drawRoom(m){const el=document.getElementById('tab-room');const rd=DATA.room[m]||[];
  const prevM=(parseInt(m.slice(0,4))-1)+m.slice(4);const prd=DATA.room[prevM]||[];
  const prevMap={};prd.forEach(r=>{prevMap[r.name]=r;});if(!rd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const totalRev=rd.reduce((a,r)=>a+r.revenue,0);const dim=daysInMonth(m);const pdim=daysInMonth(prevM);
  let rows=rd.map(r=>{const pr=physicalRooms(r.name);const occ=pr*dim>0?(r.rn/(pr*dim)*100).toFixed(1):'-';
    const pv=prevMap[r.name]||{rooms:0,rn:0,revenue:0,adr:0,persons:0};
    const pOcc=pr*pdim>0?(pv.rn/(pr*pdim)*100).toFixed(1):'-';
    const adrDiff=r.adr-(pv.adr||0);
    return`<tr><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.name}</td><td class="num">${pr}</td><td class="num">${r.rooms}</td><td class="num" style="color:var(--mu)">${pv.rooms||'-'}</td><td class="num">${r.rn}</td><td class="num ${Number(occ)>=80?'up':Number(occ)<40?'dn':''}">${occ}%</td><td class="num" style="color:var(--mu)">${pOcc!=='-'?pOcc+'%':'-'}</td><td class="num">${fmtY(r.revenue)}</td><td class="num" style="color:var(--mu)">${pv.revenue?fmtY(pv.revenue):'-'}</td><td class="num">${fmtY(r.adr)}</td><td class="num" style="color:var(--mu)">${pv.adr?fmtY(pv.adr):'-'}</td><td class="num ${adrDiff>=0?'up':'dn'}">${adrDiff>=0?'+':''}${fmtY(adrDiff)}</td><td class="num">${r.persons}</td><td class="num">${pct(r.revenue,totalRev)}%</td></tr>`;}).join('');el.innerHTML=`<div class="card"><h3>室タイプ別 明細（${m}）</h3><div class="scroll-table"><table><tr><th>室タイプ</th><th class="num">物理室</th><th class="num">室数</th><th class="num">PY室数</th><th class="num">RN</th><th class="num">稼働率</th><th class="num">PY稼</th><th class="num">売上</th><th class="num">PY売上</th><th class="num">ADR</th><th class="num">PY ADR</th><th class="num">差</th><th class="num">人数</th><th class="num">構成比</th></tr>${rows}</table></div></div><div class="grid-2"><div class="card"><h3>室タイプ別 売上</h3><div class="chart-wrap"><canvas id="room-rev"></canvas></div></div><div class="card"><h3>室タイプ別 ADR</h3><div class="chart-wrap"><canvas id="room-adr"></canvas></div></div></div>`;const colors=['#3366aa','#d4870a','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4','#f97316','#14b8a6','#8b5cf6'];makeChart('room-rev',{type:'bar',data:{labels:rd.map(r=>r.name.length>14?r.name.slice(0,14)+'…':r.name),datasets:[{data:rd.map(r=>r.revenue),backgroundColor:rd.map((_,i)=>colors[i%colors.length]),borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y:{ticks:{color:'#2c2418',font:{size:10}}}}}});const sorted=[...rd].sort((a,b)=>b.adr-a.adr);makeChart('room-adr',{type:'bar',data:{labels:sorted.map(r=>r.name.length>14?r.name.slice(0,14)+'…':r.name),datasets:[{data:sorted.map(r=>r.adr),backgroundColor:sorted.map((_,i)=>`hsl(${210+i*25},65%,55%)`),borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'\u00a5'+fmt(v)}},y:{ticks:{color:'#2c2418',font:{size:10}}}}}});}

/* ========== ROOM MONTHLY: 年タブ + 12ヶ月テーブル + 前年比較 ========== */
function drawRoomMonthly(){
  const el=document.getElementById('tab-room_monthly');
  const years=DATA.years||[];
  if(!years.length){el.innerHTML='<div class="no-data">データがありません</div>';return;}
  if(!window._rmYear)window._rmYear=years[years.length-1];
  const yr=window._rmYear;
  const prevYr=String(Number(yr)-1);
  let yearBtns=years.map(y=>`<button class="toggle-btn ${yr===y?'active':''}" onclick="window._rmYear='${y}';drawRoomMonthly()">${y}</button>`).join('');
  const mm12=['01','02','03','04','05','06','07','08','09','10','11','12'];
  // Collect all room names for this year
  const roomSet=new Set();
  mm12.forEach(mm=>{const ym=yr+'-'+mm;(DATA.room[ym]||[]).forEach(r=>roomSet.add(r.name));});
  mm12.forEach(mm=>{const ym=prevYr+'-'+mm;(DATA.room[ym]||[]).forEach(r=>roomSet.add(r.name));});
  const roomNames=[...roomSet];
  // Build table header: room | Jan(rooms,ADR,py_rooms,py_ADR,diff) | Feb... 
  let thMonths=mm12.map(mm=>`<th class="num" colspan="4" style="text-align:center;border-bottom:1px solid var(--bd);border-left:2px solid var(--bd)">${Number(mm)}月</th>`).join('');
  let thSub=mm12.map(()=>`<th class="num" style="border-left:2px solid var(--bd)">稼働率</th><th class="num">PY稼</th><th class="num">ADR</th><th class="num">PY ADR</th>`).join('');
  let rows=roomNames.map(name=>{
    let cells=mm12.map(mm=>{
      const ym=yr+'-'+mm;const pyYm=prevYr+'-'+mm;
      const c=(DATA.room[ym]||[]).find(r=>r.name===name);
      const p=(DATA.room[pyYm]||[]).find(r=>r.name===name);
      const dim2=daysInMonth(yr+'-'+mm);const pr2=physicalRooms(name);
      const occC=c&&pr2?((c.rn/(pr2*dim2))*100).toFixed(0)+'%':'-';
      const occP=p&&pr2?((p.rn/(pr2*daysInMonth(prevYr+'-'+mm)))*100).toFixed(0)+'%':'-';
      const ca=c?fmtY(c.adr):'-';const pa=p?fmtY(p.adr):'-';
      const occVal=parseFloat(occC);const occStyle=occVal<40&&occVal>0?'background:rgba(192,48,48,.12);color:#c03030;font-weight:500':'';
      return`<td class="num" style="border-left:2px solid var(--bd);${occStyle}">${occC}</td><td class="num" style="color:var(--mu)">${occP}</td><td class="num">${ca}</td><td class="num" style="color:var(--mu)">${pa}</td>`;
    }).join('');
    return`<tr><td style="white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis;position:sticky;left:0;background:var(--sf);z-index:1">${name}</td>${cells}</tr>`;
  }).join('');
  // Totals
  let totalCells=mm12.map(mm=>{
    const ym=yr+'-'+mm;const pyYm=prevYr+'-'+mm;
    const rd=DATA.room[ym]||[];const prd=DATA.room[pyYm]||[];
    const tR=rd.reduce((a,r)=>a+r.rooms,0);const tRev=rd.reduce((a,r)=>a+r.revenue,0);const tRn=rd.reduce((a,r)=>a+r.rn,0);
    const pR=prd.reduce((a,r)=>a+r.rooms,0);const pRev=prd.reduce((a,r)=>a+r.revenue,0);const pRn=prd.reduce((a,r)=>a+r.rn,0);
    const totalPhys=roomNames.reduce((a,n)=>a+physicalRooms(n),0);
      const dim3=daysInMonth(yr+'-'+mm);const pdim3=daysInMonth(prevYr+'-'+mm);
      const tOcc=totalPhys*dim3?(tRn/(totalPhys*dim3)*100).toFixed(0)+'%':'-';
      const pOcc=totalPhys*pdim3?(pRn/(totalPhys*pdim3)*100).toFixed(0)+'%':'-';
      return`<td class="num" style="font-weight:500;border-left:2px solid var(--bd)">${tOcc}</td><td class="num" style="color:var(--mu)">${pOcc}</td><td class="num" style="font-weight:500">${tRn?fmtY(Math.round(tRev/tRn)):'-'}</td><td class="num" style="color:var(--mu)">${pRn?fmtY(Math.round(pRev/pRn)):'-'}</td>`;
  }).join('');
  el.innerHTML=`<div class="filter-row"><label>年：</label>${yearBtns}<span style="color:var(--mu);font-size:10px;margin-left:12px">※ PY = 前年(${prevYr}年)</span></div>
  <div class="card"><h3>室タイプ別 月次推移（${yr}年 vs ${prevYr}年）</h3>
    <div class="scroll-table" style="overflow-x:auto"><table style="min-width:1600px">
      <tr><th rowspan="2" style="min-width:140px;position:sticky;left:0;background:var(--sf);z-index:1">室タイプ</th>${thMonths}</tr>
      <tr>${thSub}</tr>${rows}
      <tr style="border-top:2px solid var(--bd)"><td style="font-weight:500;position:sticky;left:0;background:var(--sf);z-index:1">合計</td>${totalCells}</tr>
    </table></div></div>`;
}

function drawPlan(m){const el=document.getElementById('tab-plan');const pd=DATA.plan[m]||[];if(!pd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}let rows=pd.map((p,i)=>`<tr><td>${i+1}</td><td style="max-width:350px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${p.full_name}">${p.name}</td><td class="num">${p.count}</td><td class="num">${fmtY(p.revenue)}</td><td class="num">${fmtY(p.avg_price)}</td><td class="num">${p.persons}</td><td><span class="pill pill-blue">${p.top_channel}</span></td></tr>`).join('');el.innerHTML=`<div class="card"><h3>プラン一覧 <span class="badge">${pd.length}プラン</span></h3><div class="scroll-table"><table><tr><th>#</th><th>プラン名</th><th class="num">件数</th><th class="num">売上</th><th class="num">平均単価</th><th class="num">人数</th><th>主要CH</th></tr>${rows}</table></div></div>`;}

function drawCancel(m){const el=document.getElementById('tab-cancel');const cc=DATA.cancel_channels[m]||[];const cd=DATA.cancel[m]||[];if(!cc.length){el.innerHTML='<div class="no-data">この月のキャンセルデータはありません</div>';return;}const totalCancel=cc.reduce((a,c)=>a+c.cancel,0);const totalLost=cc.reduce((a,c)=>a+c.revenue_lost,0);const totalAll=cc.reduce((a,c)=>a+c.total,0);let chRows=cc.map(c=>`<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${chColor(c.name)};margin-right:6px"></span>${c.name}</td><td class="num">${c.cancel}</td><td class="num">${c.total}</td><td class="num ${c.rate>50?'dn':c.rate>30?'':'up'}">${c.rate}%</td><td class="num">${fmtY(c.revenue_lost)}</td></tr>`).join('');let detRows=cd.slice(0,50).map(c=>`<tr><td><span class="pill pill-blue">${c.channel}</span></td><td>${c.ci_date}</td><td>${c.cancel_date||'-'}</td><td>${c.book_date||'-'}</td><td class="num">${fmtY(c.revenue)}</td><td>${c.room}</td><td class="num">${c.adults}</td></tr>`).join('');el.innerHTML=`<div class="kpi-row"><div class="kpi red"><div class="label">キャンセル数</div><div class="value">${totalCancel}<span class="unit">件</span></div></div><div class="kpi orange"><div class="label">キャンセル率</div><div class="value">${pct(totalCancel,totalAll)}<span class="unit">%</span></div></div><div class="kpi red"><div class="label">損失売上</div><div class="value">${(totalLost/10000).toFixed(0)}<span class="unit">万円</span></div></div></div><div class="grid-2"><div class="card"><h3>チャネル別キャンセル数</h3><div class="chart-wrap"><canvas id="cancel-bar"></canvas></div></div><div class="card"><h3>チャネル別キャンセル率</h3><div class="chart-wrap"><canvas id="cancel-rate"></canvas></div></div></div><div class="card"><h3>キャンセル詳細</h3><div class="scroll-table"><table><tr><th>チャネル</th><th>CI日</th><th>キャンセル日</th><th>予約日</th><th class="num">金額</th><th>室タイプ</th><th class="num">大人</th></tr>${detRows}</table></div></div>`;makeChart('cancel-bar',{type:'bar',data:{labels:cc.map(c=>c.name),datasets:[{label:'キャンセル',data:cc.map(c=>c.cancel),backgroundColor:'rgba(192,48,48,.65)',borderRadius:3},{label:'成立',data:cc.map(c=>c.total-c.cancel),backgroundColor:'rgba(45,122,45,.45)',borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#2c2418'}}},scales:{x:{stacked:true,ticks:{color:'#9a8e7e'}},y:{stacked:true,grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}}}}});makeChart('cancel-rate',{type:'bar',data:{labels:cc.map(c=>c.name),datasets:[{data:cc.map(c=>c.rate),backgroundColor:cc.map(c=>c.rate>50?'rgba(192,48,48,.65)':c.rate>30?'rgba(176,120,40,.65)':'rgba(45,122,45,.45)'),borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#9a8e7e'}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>v+'%'}}}}});}

/* ========== PICKUP: 期間フィルタ + MA切替 + 前年対比 ========== */
let pickupMetric='rooms';let pickupPeriod='90';let pickupMaCh='__all__';let pickupMA7=true;let pickupMA30=true;let pickupShowPY=false;
function drawPickup(){
  const el=document.getElementById('tab-pickup');const allCh=DATA.pickup_channels;
  const mainCh=['自社','一休.com','じゃらん','楽天トラベル','Booking.com','その他'];
  let metricBtns=['rooms','rn','revenue','persons'].map(m=>`<button class="toggle-btn ${pickupMetric===m?'active':''}" onclick="pickupMetric='${m}';drawPickup()">${{rooms:'室数',rn:'RN',revenue:'売上',persons:'人数'}[m]}</button>`).join('');
  let periodBtns=[['all','全期間'],['30','直近30日'],['60','直近60日'],['90','直近90日'],['180','直近180日']].map(([v,l])=>`<button class="toggle-btn ${pickupPeriod===v?'active':''}" onclick="pickupPeriod='${v}';drawPickup()">${l}</button>`).join('');
  let maChBtns=`<button class="toggle-btn ${pickupMaCh==='__all__'?'active':''}" onclick="pickupMaCh='__all__';drawPickup()">全体</button>`;
  maChBtns+=mainCh.map(ch=>`<button class="toggle-btn ${pickupMaCh===ch?'active':''}" onclick="pickupMaCh='${ch}';drawPickup()">${ch}</button>`).join('');
  let maBtns=`<button class="toggle-btn ${pickupMA7?'active':''}" onclick="pickupMA7=!pickupMA7;drawPickup()">7日MA</button>`;
  maBtns+=`<button class="toggle-btn ${pickupMA30?'active':''}" onclick="pickupMA30=!pickupMA30;drawPickup()">30日MA</button>`;
  let pyBtn=`<button class="toggle-btn ${pickupShowPY?'active':''}" onclick="pickupShowPY=!pickupShowPY;drawPickup()">前年対比</button>`;
  // Filter by period
  const today=DATA.pickup.length?DATA.pickup[DATA.pickup.length-1].date:'';
  const cutoff=pickupPeriod==='all'?'':(()=>{const d=new Date(today);d.setDate(d.getDate()-Number(pickupPeriod));return d.toISOString().slice(0,10);})();
  const filtered=DATA.pickup.filter(p=>!cutoff||p.date>=cutoff);
  // Aggregate
  const dailyAgg=filtered.map(p=>{const agg={date:p.date,dow:p.dow,channels:{}};let total=0,cancelTotal=0;allCh.forEach(ch=>{let val=0,cv=0;const cd=p.channels[ch]||{};Object.entries(cd).forEach(([cm,d])=>{val+=d[pickupMetric]||0;cv+=d.cancel||0;});agg.channels[ch]=val;total+=val;cancelTotal+=cv;});agg.total=total;agg.cancel=cancelTotal;agg.net=total-cancelTotal;return agg;});
  const groupedAgg=dailyAgg.map(d=>{const g={};mainCh.forEach(mc=>{g[mc]=0;});
    Object.entries(d.channels).forEach(([ch,val])=>{const gc=groupCh(ch);g[gc]=(g[gc]||0)+val;});return g;});
  
  // PY data (same dates -1 year)
  let pyAgg=[];
  if(pickupShowPY){
    const pyLookup={};DATA.pickup.forEach(p=>{pyLookup[p.date]=p;});
    pyAgg=dailyAgg.map(d=>{const pyDate=(parseInt(d.date.slice(0,4))-1)+d.date.slice(4);const pp=pyLookup[pyDate];if(!pp)return{total:0,channels:{}};let total=0;const chData={};allCh.forEach(ch=>{let val=0;const cd=pp?pp.channels[ch]||{}:{};Object.entries(cd).forEach(([cm,dd])=>{val+=dd[pickupMetric]||0;});chData[ch]=val;total+=val;});return{total,channels:chData};});
  }
  // Table
  let rows=dailyAgg.map((d,i)=>{const isWe=d.dow==='土'||d.dow==='日';return`<tr style="${isWe?'background:rgba(139,105,20,.04)':''}"><td>${d.date.slice(5)} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td><td class="num">${fmt(d.total)}</td><td class="num ${d.net<0?'dn':'up'}">${d.net>=0?'+':''}${d.net}</td>${mainCh.map(ch=>`<td class="num">${groupedAgg[i]?.[ch]||'-'}</td>`).join('')}</tr>`;}).join('');
  el.innerHTML=`
  <div class="card"><h3>受信日別 チャネル別 販売室数</h3>
    <div class="filter-row"><label>表示指標：</label>${metricBtns}</div>
    <div class="filter-row"><label>期間：</label>${periodBtns}</div>
    <div class="chart-wrap tall"><canvas id="pickup-stack"></canvas></div>
  </div>
  <div class="card"><h3>移動平均トレンド</h3>
    <div class="filter-row" style="flex-wrap:wrap"><label>チャネル：</label>${maChBtns}</div>
    <div class="filter-row"><label>MA：</label>${maBtns}${pyBtn}</div>
    <div class="chart-wrap tall"><canvas id="pickup-ma"></canvas></div>
  </div>
  <div class="card"><h3>Pickup明細</h3><div class="scroll-table"><table>
    <tr><th>受信日</th><th class="num">合計</th><th class="num">ネット</th>${mainCh.map(ch=>`<th class="num">${ch}</th>`).join('')}</tr>${rows}</table></div></div>`;
  // Stacked bar
  const datasets=mainCh.map(ch=>({label:ch,data:groupedAgg.map(d=>d[ch]||0),backgroundColor:chColor(ch),borderRadius:1,hidden:true}));
  makeChart('pickup-stack',{type:'bar',data:{labels:dailyAgg.map(d=>d.date.slice(5)+' '+d.dow),datasets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#2c2418',font:{size:10}},onClick:function(e,item,legend){const idx=item.datasetIndex;const ci=legend.chart;ci.data.datasets.forEach((ds,i)=>{const meta=ci.getDatasetMeta(i);meta.hidden=i===idx?!meta.hidden:true;});ci.update();}}},scales:{x:{stacked:true,ticks:{color:'#9a8e7e',font:{size:9}}},y:{stacked:true,grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}}}}});
  // MA chart
  function ma(arr,n){return arr.map((_,i)=>{if(i<n-1)return null;const s=arr.slice(i-n+1,i+1);return Math.round(s.reduce((a,b)=>a+b,0)/n);});}
  let maData=pickupMaCh==='__all__'?dailyAgg.map(d=>d.total):groupedAgg.map(d=>d[pickupMaCh]||0);
  const maLabel=pickupMaCh==='__all__'?'全体':pickupMaCh;
  const maSets=[{label:maLabel+' 日次',data:maData,borderColor:'rgba(44,36,24,.15)',pointRadius:1,tension:.2}];
  if(pickupMA7)maSets.push({label:'7日MA',data:ma(maData,7),borderColor:'#3366aa',pointRadius:0,tension:.4,borderWidth:2});
  if(pickupMA30)maSets.push({label:'30日MA',data:ma(maData,30),borderColor:'#d4870a',pointRadius:0,tension:.4,borderWidth:2});
  if(pickupShowPY&&pyAgg.length){
    let pyRaw=pickupMaCh==='__all__'?pyAgg.map(p=>p.total):pyAgg.map(p=>{if(!p.channels)return 0;let s=0;Object.entries(p.channels).forEach(([ch,v])=>{if(groupCh(ch)===pickupMaCh)s+=v;});return s;});let pyData=pyRaw;
    // Apply same MA to PY data
    if(pickupMA30&&!pickupMA7)pyData=ma(pyData,30);
    else if(pickupMA7&&!pickupMA30)pyData=ma(pyData,7);
    else if(pickupMA7&&pickupMA30)pyData=ma(pyData,30);
    maSets.push({label:'前年'+(pickupMA30?' 30日MA':pickupMA7?' 7日MA':''),data:pyData,borderColor:'#f75f5f',borderDash:[5,3],pointRadius:0,tension:.3,borderWidth:1.5});
  }
  makeChart('pickup-ma',{type:'line',data:{labels:dailyAgg.map(d=>d.date.slice(5)),datasets:maSets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#2c2418'}}},scales:{x:{ticks:{color:'#9a8e7e',font:{size:9}}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}}}}});
}

function drawLeadtime(){const el=document.getElementById('tab-leadtime');el.innerHTML=`<div class="kpi-row"><div class="kpi blue"><div class="label">平均リードタイム</div><div class="value">${DATA.leadtime_stats.avg}<span class="unit">日</span></div></div><div class="kpi green"><div class="label">中央値</div><div class="value">${DATA.leadtime_stats.median}<span class="unit">日</span></div></div></div><div class="card"><h3>リードタイム分布（日別・0〜180日）</h3><div class="chart-wrap tall"><canvas id="lt-chart"></canvas></div></div>`;makeChart('lt-chart',{type:'bar',data:{labels:DATA.leadtime.map(d=>d.days),datasets:[{data:DATA.leadtime.map(d=>d.count),backgroundColor:'rgba(139,105,20,.45)',borderRadius:1}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#9a8e7e',callback:function(v,i){return i%15===0?i+'日':'';}}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}}}}});}

function drawPref(m){const el=document.getElementById('tab-pref');const pd=DATA.prefecture[m]||[];if(!pd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const totalCount=pd.reduce((a,p)=>a+p.count,0);const top15=pd.slice(0,15);const top15rev=[...pd].sort((a,b)=>b.revenue-a.revenue).slice(0,15);let rows=pd.map((p,i)=>`<tr><td>${i+1}</td><td>${p.name}</td><td class="num">${p.count}</td><td class="num">${fmtY(p.revenue)}</td><td class="num">${fmtY(p.avg_price)}</td><td class="num">${p.persons}</td><td class="num">${pct(p.count,totalCount)}%<div class="bar-bg"><div class="bar-fill" style="width:${Math.min(100,p.count/totalCount*200)}%;background:var(--ac)"></div></div></td></tr>`).join('');el.innerHTML=`<div class="grid-2"><div class="card"><h3>居住地 TOP15（件数）</h3><div class="chart-wrap tall"><canvas id="pref-cnt"></canvas></div></div><div class="card"><h3>居住地 TOP15（売上）</h3><div class="chart-wrap tall"><canvas id="pref-rev"></canvas></div></div></div><div class="card"><h3>居住地 明細 <span class="badge">${pd.length}地域</span></h3><div class="scroll-table"><table><tr><th>#</th><th>都道府県</th><th class="num">件数</th><th class="num">売上</th><th class="num">平均単価</th><th class="num">人数</th><th class="num">構成比</th></tr>${rows}</table></div></div>`;makeChart('pref-cnt',{type:'bar',data:{labels:top15.map(p=>p.name),datasets:[{data:top15.map(p=>p.count),backgroundColor:'rgba(139,105,20,.55)',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}},y:{ticks:{color:'#2c2418'}}}}});makeChart('pref-rev',{type:'bar',data:{labels:top15rev.map(p=>p.name),datasets:[{data:top15rev.map(p=>p.revenue),backgroundColor:'rgba(52,201,142,.6)',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y:{ticks:{color:'#2c2418'}}}}});}

function drawPrefMonthly(){const el=document.getElementById('tab-pref_monthly');const allMonths=DATA.months;const prefTotals={};allMonths.forEach(m=>{(DATA.prefecture[m]||[]).forEach(p=>{prefTotals[p.name]=(prefTotals[p.name]||0)+p.count;});});const top10=Object.entries(prefTotals).sort((a,b)=>b[1]-a[1]).slice(0,10).map(e=>e[0]);const colors=['#3366aa','#d4870a','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4','#f97316','#14b8a6','#8b5cf6'];el.innerHTML=`<div class="card"><h3>都道府県 月次構成（件数 TOP10）</h3><div class="chart-wrap tall"><canvas id="pref-monthly-chart"></canvas></div></div>`;const datasets=top10.map((name,i)=>({label:name,data:allMonths.map(m=>{const p=(DATA.prefecture[m]||[]).find(x=>x.name===name);return p?p.count:0;}),backgroundColor:colors[i%colors.length]}));makeChart('pref-monthly-chart',{type:'bar',data:{labels:allMonths,datasets},options:{responsive:true,maintainAspectRatio:false,scales:{x:{stacked:true,ticks:{color:'#9a8e7e'}},y:{stacked:true,grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}}},plugins:{legend:{position:'bottom',labels:{color:'#2c2418',font:{size:10}}}}}});}

function drawTravel(m){const el=document.getElementById('tab-travel');const td=DATA.travel[m]||[];if(!td.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const colors=['#3366aa','#d4870a','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4'];el.innerHTML=`<div class="grid-2"><div class="card"><h3>旅行動態別 件数</h3><div class="chart-wrap"><canvas id="travel-cnt"></canvas></div></div><div class="card"><h3>旅行動態別 売上</h3><div class="chart-wrap"><canvas id="travel-rev"></canvas></div></div></div><div class="card"><h3>旅行動態 明細</h3><div class="scroll-table"><table><tr><th>旅行動態</th><th class="num">件数</th><th class="num">売上</th><th class="num">平均単価</th><th class="num">人数</th><th class="num">構成比</th></tr>${td.map(t=>{const total=td.reduce((a,x)=>a+x.count,0);return`<tr><td>${t.name}</td><td class="num">${t.count}</td><td class="num">${fmtY(t.revenue)}</td><td class="num">${fmtY(t.count?Math.round(t.revenue/t.count):0)}</td><td class="num">${t.persons}</td><td class="num">${pct(t.count,total)}%</td></tr>`;}).join('')}</table></div></div><p style="color:var(--mu);font-size:10px;margin-top:8px">※ 旅行動態は大人人数・子供人数・男女人数から推定しています</p>`;makeChart('travel-cnt',{type:'doughnut',data:{labels:td.map(t=>t.name),datasets:[{data:td.map(t=>t.count),backgroundColor:colors,borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#2c2418'}}}}});makeChart('travel-rev',{type:'doughnut',data:{labels:td.map(t=>t.name),datasets:[{data:td.map(t=>t.revenue),backgroundColor:colors,borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#2c2418'}},tooltip:{callbacks:{label:ctx=>ctx.label+': \u00a5'+fmt(ctx.raw)}}}}});}

showTab('monthly',document.querySelector('.nav-tab'));
switchAllTabs(DATA.default_month);

"""

if __name__ == "__main__":
    main()
