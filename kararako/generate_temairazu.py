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
:root{{--bg:#0f1117;--sf:#181c25;--bd:rgba(255,255,255,0.07);--tx:#e8eaf0;--mu:#7a7f8e;--ac:#4f8ef7;--up:#34c98e;--dn:#f75f5f;--wn:#f7a34f;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Noto Sans JP',sans-serif;background:var(--bg);color:var(--tx);font-size:13px;line-height:1.6;}}
a{{color:var(--ac);text-decoration:none;}}
.header{{background:linear-gradient(135deg,#1a1f2e 0%,#0f1117 100%);border-bottom:1px solid var(--bd);padding:16px 24px;position:sticky;top:0;z-index:100;}}
.header h1{{font-size:17px;font-weight:500;letter-spacing:.5px;}}
.header .sub{{color:var(--mu);font-size:11px;margin-top:3px;font-family:'DM Mono',monospace;}}
.top-controls{{display:flex;align-items:center;gap:12px;margin-top:8px;flex-wrap:wrap;}}
.top-controls label{{font-size:11px;color:var(--mu);}}
.top-controls select,.top-controls button{{background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:4px 10px;border-radius:6px;font-size:11px;cursor:pointer;font-family:inherit;}}
.top-controls select:hover,.top-controls button:hover{{border-color:var(--ac);}}
.nav{{display:flex;gap:2px;padding:8px 24px 0;flex-wrap:wrap;border-bottom:1px solid var(--bd);background:var(--bg);position:sticky;top:72px;z-index:99;}}
.nav-tab{{background:none;border:none;color:var(--mu);padding:7px 12px;font-size:11.5px;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit;transition:all .15s;white-space:nowrap;}}
.nav-tab:hover{{color:var(--tx);}}
.nav-tab.active{{color:var(--ac);border-bottom-color:var(--ac);font-weight:500;}}
.month-bar{{display:flex;gap:4px;padding:8px 24px;background:var(--bg);border-bottom:1px solid var(--bd);flex-wrap:wrap;align-items:center;}}
.month-bar .label{{font-size:11px;color:var(--mu);margin-right:8px;}}
.month-btn{{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:4px 12px;border-radius:6px;font-size:11px;cursor:pointer;font-family:inherit;}}
.month-btn:hover{{border-color:var(--ac);color:var(--tx);}}
.month-btn.active{{background:var(--ac);color:#fff;border-color:var(--ac);}}
.container{{max-width:1400px;margin:0 auto;padding:16px 24px 60px;}}
.section{{display:none;animation:fadeIn .25s ease;}}
.section.active{{display:block;}}
@keyframes fadeIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:20px;}}
.kpi{{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:14px;position:relative;overflow:hidden;}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;}}
.kpi.blue::before{{background:var(--ac);}}.kpi.green::before{{background:var(--up);}}.kpi.orange::before{{background:var(--wn);}}.kpi.red::before{{background:var(--dn);}}
.kpi .label{{font-size:10px;color:var(--mu);text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;}}
.kpi .value{{font-size:20px;font-weight:500;font-family:'DM Mono',monospace;}}
.kpi .unit{{font-size:11px;color:var(--mu);margin-left:2px;}}
.card{{background:var(--sf);border:1px solid var(--bd);border-radius:8px;padding:16px;margin-bottom:14px;}}
.card h3{{font-size:13px;font-weight:500;margin-bottom:12px;display:flex;align-items:center;gap:8px;}}
.card h3 .badge{{font-size:10px;background:var(--ac);color:#fff;padding:1px 7px;border-radius:10px;font-weight:400;}}
table{{width:100%;border-collapse:collapse;font-size:12px;}}
th{{text-align:left;padding:6px 8px;border-bottom:2px solid var(--bd);color:var(--mu);font-weight:500;font-size:10.5px;white-space:nowrap;position:sticky;top:0;background:var(--sf);}}
td{{padding:5px 8px;border-bottom:1px solid var(--bd);}}
tr:hover td{{background:rgba(79,142,247,0.03);}}
.num{{text-align:right;font-family:'DM Mono',monospace;font-size:11.5px;}}
.up{{color:var(--up);}}.dn{{color:var(--dn);}}
.chart-wrap{{position:relative;height:300px;margin:8px 0;}}
.chart-wrap.tall{{height:400px;}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;}}
.grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;}}
@media(max-width:900px){{.grid-2,.grid-3{{grid-template-columns:1fr;}}}}
.pill{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:500;}}
.pill-blue{{background:rgba(79,142,247,.15);color:var(--ac);}}.pill-green{{background:rgba(52,201,142,.15);color:var(--up);}}
.pill-red{{background:rgba(247,95,95,.15);color:var(--dn);}}.pill-orange{{background:rgba(247,163,79,.15);color:var(--wn);}}
.scroll-table{{max-height:500px;overflow-y:auto;}}
.scroll-table::-webkit-scrollbar{{width:5px;}}.scroll-table::-webkit-scrollbar-thumb{{background:var(--bd);border-radius:3px;}}
.bar-bg{{height:5px;border-radius:3px;background:var(--bd);overflow:hidden;margin-top:3px;}}
.bar-fill{{height:100%;border-radius:3px;}}
.filter-row{{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center;}}
.filter-row label{{font-size:11px;color:var(--mu);}}
.filter-row select,.filter-row input,.filter-row button{{background:var(--sf);border:1px solid var(--bd);color:var(--tx);padding:4px 8px;border-radius:6px;font-size:11px;font-family:inherit;}}
.toggle-btn{{background:var(--sf);border:1px solid var(--bd);color:var(--mu);padding:3px 10px;border-radius:6px;font-size:10.5px;cursor:pointer;font-family:inherit;}}
.toggle-btn.active{{background:rgba(79,142,247,.15);color:var(--ac);border-color:var(--ac);}}
.no-data{{text-align:center;padding:40px;color:var(--mu);font-size:12px;}}
.footer{{text-align:center;padding:20px;color:var(--mu);font-size:10px;border-top:1px solid var(--bd);margin-top:20px;}}
@media print{{.header,.nav,.month-bar{{position:static;}}.section{{display:block!important;page-break-before:always;}}}}
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
const CH_COLORS={'一休.com':'#f59e0b','楽天トラベル':'#ef4444','じゃらん':'#22c55e','るるぶトラベル':'#3b82f6','予約プロクロス':'#a78bfa','Booking.com':'#06b6d4','Relux':'#ec4899','ツアービルダー':'#f97316','JALパック':'#14b8a6','e宿':'#8b5cf6','自社':'#a78bfa'};
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

function showTab(name,el){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if(el)el.classList.add('active');
  else document.querySelectorAll('.nav-tab').forEach(t=>{if(t.textContent.trim()===name)t.classList.add('active');});
  curTab=name;
  document.getElementById('monthBar').style.display=noMonthBar.includes(name)?'none':'';
  const tm=tabMonths[name]||DATA.default_month;
  document.querySelectorAll('.month-btn').forEach(x=>x.classList.toggle('active',x.textContent===tm));
  drawTab(name);
}
function switchAllTabs(m){
  monthTabs.forEach(t=>{tabMonths[t]=m;});
  document.querySelectorAll('.month-btn').forEach(x=>x.classList.toggle('active',x.textContent===m));
  const sel=document.getElementById('global-month-select');if(sel)sel.value=m;
  drawTab(curTab);
}
function printAll(){document.querySelectorAll('.section').forEach(s=>s.classList.add('active'));setTimeout(()=>{window.print();},300);}
function drawTab(name){
  const m=tabMonths[name]||DATA.default_month;
  switch(name){
    case'monthly':drawMonthly(m);break;case'yoy':drawYoY();break;case'daily':drawDaily(m);break;
    case'room':drawRoom(m);break;case'room_monthly':drawRoomMonthly();break;case'plan':drawPlan(m);break;
    case'cancel':drawCancel(m);break;case'pickup':drawPickup();break;case'leadtime':drawLeadtime();break;
    case'pref':drawPref(m);break;case'pref_monthly':drawPrefMonthly();break;case'travel':drawTravel(m);break;
  }
}

function drawMonthly(m){const el=document.getElementById('tab-monthly');const md=DATA.monthly[m];if(!md){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const dd=DATA.daily[m]||[];const chRevMap={};dd.forEach(d=>{const tr=d.rooms;Object.entries(d.channels).forEach(([ch,rooms])=>{if(!chRevMap[ch])chRevMap[ch]={rooms:0,revenue:0,rn:0,persons:0};chRevMap[ch].rooms+=rooms;chRevMap[ch].revenue+=tr>0?Math.round(d.revenue*rooms/tr):0;chRevMap[ch].rn+=rooms;chRevMap[ch].persons+=tr>0?Math.round(d.persons*rooms/tr):0;});});const chList=Object.entries(chRevMap).sort((a,b)=>b[1].revenue-a[1].revenue).map(([ch,d])=>({name:ch,rooms:d.rooms,rn:d.rn,revenue:d.revenue,persons:d.persons,adr:d.rn>0?Math.round(d.revenue/d.rn):0}));const totalRev=chList.reduce((a,c)=>a+c.revenue,0);let chRows=chList.map(c=>`<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${chColor(c.name)};margin-right:6px"></span>${c.name}</td><td class="num">${fmt(c.rooms)}</td><td class="num">${fmt(c.rn)}</td><td class="num">${fmtY(c.revenue)}</td><td class="num">${fmtY(c.adr)}</td><td class="num">${fmt(c.persons)}</td><td class="num">${pct(c.revenue,totalRev)}%</td></tr>`).join('');el.innerHTML=`<div class="kpi-row"><div class="kpi blue"><div class="label">売上合計</div><div class="value">${(md.revenue/10000).toFixed(0)}<span class="unit">万円</span></div></div><div class="kpi green"><div class="label">予約件数</div><div class="value">${fmt(md.rooms)}<span class="unit">件</span></div></div><div class="kpi blue"><div class="label">室泊数 RN</div><div class="value">${fmt(md.rn)}<span class="unit">RN</span></div></div><div class="kpi orange"><div class="label">ADR</div><div class="value">${fmt(md.adr)}<span class="unit">円</span></div></div><div class="kpi green"><div class="label">人泊単価</div><div class="value">${fmt(md.per_person)}<span class="unit">円</span></div></div><div class="kpi red"><div class="label">キャンセル率</div><div class="value">${md.cancel_rate}<span class="unit">%</span></div></div></div><div class="grid-2"><div class="card"><h3>チャネル別構成</h3><div class="chart-wrap"><canvas id="monthly-pie"></canvas></div></div><div class="card"><h3>チャネル別明細</h3><div class="scroll-table"><table><tr><th>チャネル</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">構成比</th></tr>${chRows}</table></div></div></div>`;const cData=chList.filter(c=>c.revenue>0);makeChart('monthly-pie',{type:'doughnut',data:{labels:cData.map(c=>c.name),datasets:[{data:cData.map(c=>c.revenue),backgroundColor:cData.map(c=>chColor(c.name)),borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#e8eaf0',font:{size:11},padding:8}},tooltip:{callbacks:{label:ctx=>ctx.label+': \u00a5'+fmt(ctx.raw)+' ('+pct(ctx.raw,totalRev)+'%)'}}}}});}

function drawYoY(){const el=document.getElementById('tab-yoy');const allMonths=DATA.months;const yoyMonths=Object.keys(DATA.yoy||{});if(!yoyMonths.length){el.innerHTML=`<div class="card"><h3>前年同日対比</h3><div class="no-data">前年データが蓄積されると、前年同曜日比較が表示されます。<br>手間いらずの前年CSVを追加することで利用可能になります。</div></div>`;return;}if(!window._yoyMonth)window._yoyMonth=yoyMonths[yoyMonths.length-1];const ym=window._yoyMonth;const cd=DATA.yoy[ym]||[];let monthBtns=yoyMonths.map(m=>`<button class="toggle-btn ${ym===m?'active':''}" onclick="window._yoyMonth='${m}';drawYoY()">${m}</button>`).join('');const totalCur=cd.reduce((a,d)=>a+d.revenue,0);const totalPy=cd.reduce((a,d)=>a+d.py_revenue,0);const diffPct=totalPy?((totalCur-totalPy)/totalPy*100).toFixed(1):'-';let rows=cd.map(d=>{const isWe=d.dow==='土'||d.dow==='日';const rdiff=d.py_revenue?((d.revenue-d.py_revenue)/d.py_revenue*100).toFixed(1):'-';return`<tr style="${isWe?'background:rgba(79,142,247,.03)':''}"><td>${d.date} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td><td class="num">${fmtY(d.revenue)}</td><td class="num">${fmtY(d.py_revenue)}</td><td class="num ${Number(rdiff)>0?'up':'dn'}">${rdiff}%</td><td class="num">${d.rooms}</td><td class="num">${d.py_rooms}</td><td class="num">${fmtY(d.adr)}</td><td class="num">${fmtY(d.py_adr)}</td></tr>`;}).join('');el.innerHTML=`<div class="filter-row"><label>表示月：</label>${monthBtns}</div><div class="kpi-row"><div class="kpi blue"><div class="label">今年 売上</div><div class="value">${(totalCur/10000).toFixed(0)}<span class="unit">万円</span></div></div><div class="kpi green"><div class="label">前年 売上</div><div class="value">${(totalPy/10000).toFixed(0)}<span class="unit">万円</span></div></div><div class="kpi ${Number(diffPct)>=0?'green':'red'}"><div class="label">前年比</div><div class="value">${diffPct}<span class="unit">%</span></div></div></div><div class="card"><h3>日別売上（今年 vs 前年同曜日）</h3><div class="chart-wrap tall"><canvas id="yoy-chart"></canvas></div></div><div class="card"><h3>日別明細（前年同曜日比較）</h3><div class="scroll-table"><table><tr><th>日付</th><th class="num">今年売上</th><th class="num">前年売上</th><th class="num">前年比</th><th class="num">今年室数</th><th class="num">前年室数</th><th class="num">今年ADR</th><th class="num">前年ADR</th></tr>${rows}</table></div></div>`;makeChart('yoy-chart',{type:'bar',data:{labels:cd.map(d=>d.date.slice(5)+' '+d.dow),datasets:[{label:'今年',data:cd.map(d=>d.revenue),backgroundColor:'rgba(79,142,247,.6)',borderRadius:3},{label:'前年',data:cd.map(d=>d.py_revenue),backgroundColor:'rgba(255,255,255,.15)',borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{labels:{color:'#e8eaf0'}}},scales:{x:{ticks:{color:'#7a7f8e',font:{size:9}}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}}}}});}

function drawDaily(m){const el=document.getElementById('tab-daily');const dd=DATA.daily[m]||[];if(!dd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}let rows=dd.map(d=>{const isWe=d.dow==='土'||d.dow==='日';return`<tr style="${isWe?'background:rgba(79,142,247,.03)':''}"><td>${d.date} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td><td class="num">${d.rooms}</td><td class="num">${d.rn}</td><td class="num">${fmtY(d.revenue)}</td><td class="num">${fmtY(d.adr)}</td><td class="num">${d.persons}</td><td class="num">${fmtY(d.per_person)}</td></tr>`;}).join('');el.innerHTML=`<div class="card"><h3>日別売上（${m}）</h3><div class="chart-wrap tall"><canvas id="daily-chart"></canvas></div></div><div class="card"><h3>日別明細</h3><div class="scroll-table"><table><tr><th>日付</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">人泊単価</th></tr>${rows}</table></div></div>`;makeChart('daily-chart',{type:'bar',data:{labels:dd.map(d=>d.date.slice(5)+' '+d.dow),datasets:[{type:'bar',label:'売上',data:dd.map(d=>d.revenue),backgroundColor:dd.map(d=>(d.dow==='土'||d.dow==='日')?'rgba(247,163,79,.6)':'rgba(79,142,247,.6)'),borderRadius:3,yAxisID:'y'},{type:'line',label:'ADR',data:dd.map(d=>d.adr),borderColor:'#f59e0b',backgroundColor:'transparent',pointRadius:2,tension:.3,yAxisID:'y1'}]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},scales:{x:{ticks:{color:'#7a7f8e',font:{size:10}}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y1:{position:'right',grid:{display:false},ticks:{color:'#f59e0b',callback:v=>'\u00a5'+fmt(v)}}},plugins:{legend:{labels:{color:'#e8eaf0'}}}}});}

function drawRoom(m){const el=document.getElementById('tab-room');const rd=DATA.room[m]||[];if(!rd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const totalRev=rd.reduce((a,r)=>a+r.revenue,0);let rows=rd.map(r=>`<tr><td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.name}</td><td class="num">${r.rooms}</td><td class="num">${r.rn}</td><td class="num">${fmtY(r.revenue)}</td><td class="num">${fmtY(r.adr)}</td><td class="num">${r.persons}</td><td class="num">${pct(r.revenue,totalRev)}%<div class="bar-bg"><div class="bar-fill" style="width:${(r.revenue/totalRev*100).toFixed(0)}%;background:var(--ac)"></div></div></td></tr>`).join('');el.innerHTML=`<div class="card"><h3>室タイプ別 明細（${m}）</h3><div class="scroll-table"><table><tr><th>室タイプ</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">構成比</th></tr>${rows}</table></div></div><div class="grid-2"><div class="card"><h3>室タイプ別 売上</h3><div class="chart-wrap"><canvas id="room-rev"></canvas></div></div><div class="card"><h3>室タイプ別 ADR</h3><div class="chart-wrap"><canvas id="room-adr"></canvas></div></div></div>`;const colors=['#4f8ef7','#f59e0b','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4','#f97316','#14b8a6','#8b5cf6'];makeChart('room-rev',{type:'bar',data:{labels:rd.map(r=>r.name.length>14?r.name.slice(0,14)+'…':r.name),datasets:[{data:rd.map(r=>r.revenue),backgroundColor:rd.map((_,i)=>colors[i%colors.length]),borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y:{ticks:{color:'#e8eaf0',font:{size:10}}}}}});const sorted=[...rd].sort((a,b)=>b.adr-a.adr);makeChart('room-adr',{type:'bar',data:{labels:sorted.map(r=>r.name.length>14?r.name.slice(0,14)+'…':r.name),datasets:[{data:sorted.map(r=>r.adr),backgroundColor:sorted.map((_,i)=>`hsl(${210+i*25},65%,55%)`),borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>'\u00a5'+fmt(v)}},y:{ticks:{color:'#e8eaf0',font:{size:10}}}}}});}

function drawRoomMonthly(){const el=document.getElementById('tab-room_monthly');const allMonths=DATA.months;const rmData=DATA.room_monthly||{};const yoyMonths=Object.keys(rmData);if(!yoyMonths.length){const roomSet=new Set();allMonths.forEach(m=>{(DATA.room[m]||[]).forEach(r=>roomSet.add(r.name));});const roomNames=[...roomSet];let thMonths=allMonths.map(m=>`<th class="num" colspan="3" style="text-align:center;border-bottom:1px solid var(--bd)">${m}</th>`).join('');let thSub=allMonths.map(()=>`<th class="num">室数</th><th class="num">売上</th><th class="num">ADR</th>`).join('');let rows=roomNames.map(name=>{let cells=allMonths.map(m=>{const rd=(DATA.room[m]||[]).find(r=>r.name===name);if(!rd)return`<td class="num">-</td><td class="num">-</td><td class="num">-</td>`;return`<td class="num">${rd.rooms}</td><td class="num">${fmtY(rd.revenue)}</td><td class="num">${fmtY(rd.adr)}</td>`;}).join('');return`<tr><td style="white-space:nowrap;max-width:200px;overflow:hidden;text-overflow:ellipsis">${name}</td>${cells}</tr>`;}).join('');let totalCells=allMonths.map(m=>{const rd=DATA.room[m]||[];const tRooms=rd.reduce((a,r)=>a+r.rooms,0);const tRev=rd.reduce((a,r)=>a+r.revenue,0);const tRn=rd.reduce((a,r)=>a+r.rn,0);return`<td class="num" style="font-weight:500">${tRooms}</td><td class="num" style="font-weight:500">${fmtY(tRev)}</td><td class="num" style="font-weight:500">${tRn?fmtY(Math.round(tRev/tRn)):'-'}</td>`;}).join('');el.innerHTML=`<div class="card"><h3>室タイプ別 月次推移</h3><div class="scroll-table" style="overflow-x:auto"><table><tr><th rowspan="2" style="min-width:160px">室タイプ</th>${thMonths}</tr><tr>${thSub}</tr>${rows}<tr style="border-top:2px solid var(--bd)"><td style="font-weight:500">合計</td>${totalCells}</tr></table></div></div>`;return;}if(!window._rmMonth)window._rmMonth=yoyMonths[yoyMonths.length-1];const ym=window._rmMonth;const rd=rmData[ym]||[];let monthBtns=yoyMonths.map(m=>`<button class="toggle-btn ${ym===m?'active':''}" onclick="window._rmMonth='${m}';drawRoomMonthly()">${m}</button>`).join('');let rows2=rd.map(r=>{const rDiff=r.py_rooms?((r.rooms-r.py_rooms)/r.py_rooms*100).toFixed(1):'-';const aDiff=r.py_adr?((r.adr-r.py_adr)/r.py_adr*100).toFixed(1):'-';return`<tr><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.name}</td><td class="num">${r.rooms}</td><td class="num">${r.py_rooms||'-'}</td><td class="num ${Number(rDiff)>=0?'up':'dn'}">${rDiff}%</td><td class="num">${fmtY(r.adr)}</td><td class="num">${r.py_adr?fmtY(r.py_adr):'-'}</td><td class="num ${Number(aDiff)>=0?'up':'dn'}">${aDiff}%</td></tr>`;}).join('');el.innerHTML=`<div class="filter-row"><label>表示月：</label>${monthBtns}</div><div class="card"><h3>室タイプ別 前年比較（${ym}）</h3><div class="scroll-table"><table><tr><th>室タイプ</th><th class="num">今年室数</th><th class="num">前年室数</th><th class="num">室数比</th><th class="num">今年ADR</th><th class="num">前年ADR</th><th class="num">ADR比</th></tr>${rows2}</table></div></div><div class="grid-2"><div class="card"><h3>室タイプ別 室数比較</h3><div class="chart-wrap"><canvas id="rm-rooms"></canvas></div></div><div class="card"><h3>室タイプ別 ADR比較</h3><div class="chart-wrap"><canvas id="rm-adr"></canvas></div></div></div>`;const labels=rd.map(r=>r.name.length>12?r.name.slice(0,12)+'…':r.name);makeChart('rm-rooms',{type:'bar',data:{labels,datasets:[{label:'今年',data:rd.map(r=>r.rooms),backgroundColor:'rgba(79,142,247,.6)',borderRadius:3},{label:'前年',data:rd.map(r=>r.py_rooms),backgroundColor:'rgba(255,255,255,.15)',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#e8eaf0'}}},scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}},y:{ticks:{color:'#e8eaf0',font:{size:10}}}}}});makeChart('rm-adr',{type:'bar',data:{labels,datasets:[{label:'今年',data:rd.map(r=>r.adr),backgroundColor:'rgba(52,201,142,.6)',borderRadius:3},{label:'前年',data:rd.map(r=>r.py_adr),backgroundColor:'rgba(255,255,255,.15)',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#e8eaf0'}}},scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>'\u00a5'+fmt(v)}},y:{ticks:{color:'#e8eaf0',font:{size:10}}}}}});}

function drawPlan(m){const el=document.getElementById('tab-plan');const pd=DATA.plan[m]||[];if(!pd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}let rows=pd.map((p,i)=>`<tr><td>${i+1}</td><td style="max-width:350px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${p.full_name}">${p.name}</td><td class="num">${p.count}</td><td class="num">${fmtY(p.revenue)}</td><td class="num">${fmtY(p.avg_price)}</td><td class="num">${p.persons}</td><td><span class="pill pill-blue">${p.top_channel}</span></td></tr>`).join('');el.innerHTML=`<div class="card"><h3>プラン一覧 <span class="badge">${pd.length}プラン</span></h3><div class="scroll-table"><table><tr><th>#</th><th>プラン名</th><th class="num">件数</th><th class="num">売上</th><th class="num">平均単価</th><th class="num">人数</th><th>主要CH</th></tr>${rows}</table></div></div>`;}

function drawCancel(m){const el=document.getElementById('tab-cancel');const cc=DATA.cancel_channels[m]||[];const cd=DATA.cancel[m]||[];if(!cc.length){el.innerHTML='<div class="no-data">この月のキャンセルデータはありません</div>';return;}const totalCancel=cc.reduce((a,c)=>a+c.cancel,0);const totalLost=cc.reduce((a,c)=>a+c.revenue_lost,0);const totalAll=cc.reduce((a,c)=>a+c.total,0);let chRows=cc.map(c=>`<tr><td><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${chColor(c.name)};margin-right:6px"></span>${c.name}</td><td class="num">${c.cancel}</td><td class="num">${c.total}</td><td class="num ${c.rate>50?'dn':c.rate>30?'':'up'}">${c.rate}%</td><td class="num">${fmtY(c.revenue_lost)}</td></tr>`).join('');let detRows=cd.slice(0,50).map(c=>`<tr><td><span class="pill pill-blue">${c.channel}</span></td><td>${c.ci_date}</td><td>${c.cancel_date||'-'}</td><td>${c.book_date||'-'}</td><td class="num">${fmtY(c.revenue)}</td><td>${c.room}</td><td class="num">${c.adults}</td></tr>`).join('');el.innerHTML=`<div class="kpi-row"><div class="kpi red"><div class="label">キャンセル数</div><div class="value">${totalCancel}<span class="unit">件</span></div></div><div class="kpi orange"><div class="label">キャンセル率</div><div class="value">${pct(totalCancel,totalAll)}<span class="unit">%</span></div></div><div class="kpi red"><div class="label">損失売上</div><div class="value">${(totalLost/10000).toFixed(0)}<span class="unit">万円</span></div></div></div><div class="grid-2"><div class="card"><h3>チャネル別キャンセル数</h3><div class="chart-wrap"><canvas id="cancel-bar"></canvas></div></div><div class="card"><h3>チャネル別キャンセル率</h3><div class="chart-wrap"><canvas id="cancel-rate"></canvas></div></div></div><div class="card"><h3>キャンセル詳細</h3><div class="scroll-table"><table><tr><th>チャネル</th><th>CI日</th><th>キャンセル日</th><th>予約日</th><th class="num">金額</th><th>室タイプ</th><th class="num">大人</th></tr>${detRows}</table></div></div>`;makeChart('cancel-bar',{type:'bar',data:{labels:cc.map(c=>c.name),datasets:[{label:'キャンセル',data:cc.map(c=>c.cancel),backgroundColor:'rgba(247,95,95,.7)',borderRadius:3},{label:'成立',data:cc.map(c=>c.total-c.cancel),backgroundColor:'rgba(52,201,142,.5)',borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#e8eaf0'}}},scales:{x:{stacked:true,ticks:{color:'#7a7f8e'}},y:{stacked:true,grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}}}}});makeChart('cancel-rate',{type:'bar',data:{labels:cc.map(c=>c.name),datasets:[{data:cc.map(c=>c.rate),backgroundColor:cc.map(c=>c.rate>50?'rgba(247,95,95,.7)':c.rate>30?'rgba(247,163,79,.7)':'rgba(52,201,142,.5)'),borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#7a7f8e'}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>v+'%'}}}}});}

let pickupMetric='rooms';let pickupPeriod='all';let pickupMaCh='__all__';
function drawPickup(){const el=document.getElementById('tab-pickup');const allCh=DATA.pickup_channels;let metricBtns=['rooms','rn','revenue','persons'].map(m=>`<button class="toggle-btn ${pickupMetric===m?'active':''}" onclick="pickupMetric='${m}';drawPickup()">${{rooms:'室数',rn:'RN',revenue:'売上',persons:'人数'}[m]}</button>`).join('');let periodBtns=[['all','全期間'],['30','直近30日'],['60','直近60日'],['90','直近90日'],['180','直近180日']].map(([v,l])=>`<button class="toggle-btn ${pickupPeriod===v?'active':''}" onclick="pickupPeriod='${v}';drawPickup()">${l}</button>`).join('');let maChBtns=`<button class="toggle-btn ${pickupMaCh==='__all__'?'active':''}" onclick="pickupMaCh='__all__';drawPickup()">全体</button>`;maChBtns+=allCh.map(ch=>`<button class="toggle-btn ${pickupMaCh===ch?'active':''}" onclick="pickupMaCh='${ch}';drawPickup()">${ch}</button>`).join('');const today=DATA.pickup.length?DATA.pickup[DATA.pickup.length-1].date:'';const cutoff=pickupPeriod==='all'?'':(() => {const d=new Date(today);d.setDate(d.getDate()-Number(pickupPeriod));return d.toISOString().slice(0,10);})();const filteredPickup=DATA.pickup.filter(p=>!cutoff||p.date>=cutoff);const dailyAgg=filteredPickup.map(p=>{const agg={date:p.date,dow:p.dow,channels:{}};let total=0,cancelTotal=0;allCh.forEach(ch=>{let val=0,cancelVal=0;const chData=p.channels[ch]||{};Object.entries(chData).forEach(([cm,d])=>{val+=d[pickupMetric]||0;cancelVal+=d.cancel||0;});agg.channels[ch]=val;total+=val;cancelTotal+=cancelVal;});agg.total=total;agg.cancel=cancelTotal;agg.net=total-cancelTotal;return agg;});let rows=dailyAgg.map(d=>{const isWe=d.dow==='土'||d.dow==='日';return`<tr style="${isWe?'background:rgba(79,142,247,.03)':''}"><td>${d.date.slice(5)} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td><td class="num">${fmt(d.total)}</td><td class="num ${d.net<0?'dn':'up'}">${d.net>=0?'+':''}${d.net}</td>${allCh.map(ch=>`<td class="num">${d.channels[ch]||'-'}</td>`).join('')}</tr>`;}).join('');el.innerHTML=`<div class="card"><h3>受信日別 チャネル別 販売室数</h3><div class="filter-row"><label>表示指標：</label>${metricBtns}<label style="margin-left:12px">期間：</label>${periodBtns}</div><div class="chart-wrap tall"><canvas id="pickup-stack"></canvas></div></div><div class="card"><h3>移動平均トレンド</h3><div class="filter-row" style="flex-wrap:wrap"><label>チャネル：</label>${maChBtns}</div><div class="grid-2"><div class="chart-wrap tall"><canvas id="pickup-ma7"></canvas></div><div class="chart-wrap tall"><canvas id="pickup-ma30"></canvas></div></div></div><div class="card"><h3>Pickup明細</h3><div class="scroll-table"><table><tr><th>受信日</th><th class="num">合計</th><th class="num">ネット</th>${allCh.map(ch=>`<th class="num">${ch}</th>`).join('')}</tr>${rows}</table></div></div>`;const datasets=allCh.map(ch=>({label:ch,data:dailyAgg.map(d=>d.channels[ch]||0),backgroundColor:chColor(ch),borderRadius:1}));makeChart('pickup-stack',{type:'bar',data:{labels:dailyAgg.map(d=>d.date.slice(5)+' '+d.dow),datasets},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#e8eaf0',font:{size:10}}}},scales:{x:{stacked:true,ticks:{color:'#7a7f8e',font:{size:9}}},y:{stacked:true,grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}}}}});function ma(arr,n){return arr.map((_,i)=>{if(i<n-1)return null;const s=arr.slice(i-n+1,i+1);return Math.round(s.reduce((a,b)=>a+b,0)/n);});}let maData;if(pickupMaCh==='__all__'){maData=dailyAgg.map(d=>d.total);}else{maData=dailyAgg.map(d=>d.channels[pickupMaCh]||0);}const maLabel=pickupMaCh==='__all__'?'全体':pickupMaCh;makeChart('pickup-ma7',{type:'line',data:{labels:dailyAgg.map(d=>d.date.slice(5)),datasets:[{label:maLabel+' 日次',data:maData,borderColor:'rgba(255,255,255,.2)',pointRadius:1,tension:.2},{label:'7日MA',data:ma(maData,7),borderColor:'#4f8ef7',pointRadius:0,tension:.4,borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#e8eaf0'}},title:{display:true,text:'7日移動平均',color:'#e8eaf0',font:{size:12}}},scales:{x:{ticks:{color:'#7a7f8e',font:{size:9}}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}}}}});makeChart('pickup-ma30',{type:'line',data:{labels:dailyAgg.map(d=>d.date.slice(5)),datasets:[{label:maLabel+' 日次',data:maData,borderColor:'rgba(255,255,255,.2)',pointRadius:1,tension:.2},{label:'30日MA',data:ma(maData,30),borderColor:'#f59e0b',pointRadius:0,tension:.4,borderWidth:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#e8eaf0'}},title:{display:true,text:'30日移動平均',color:'#e8eaf0',font:{size:12}}},scales:{x:{ticks:{color:'#7a7f8e',font:{size:9}}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}}}}});}

function drawLeadtime(){const el=document.getElementById('tab-leadtime');el.innerHTML=`<div class="kpi-row"><div class="kpi blue"><div class="label">平均リードタイム</div><div class="value">${DATA.leadtime_stats.avg}<span class="unit">日</span></div></div><div class="kpi green"><div class="label">中央値</div><div class="value">${DATA.leadtime_stats.median}<span class="unit">日</span></div></div></div><div class="card"><h3>リードタイム分布（日別・0〜180日）</h3><div class="chart-wrap tall"><canvas id="lt-chart"></canvas></div></div>`;makeChart('lt-chart',{type:'bar',data:{labels:DATA.leadtime.map(d=>d.days),datasets:[{data:DATA.leadtime.map(d=>d.count),backgroundColor:'rgba(79,142,247,.5)',borderRadius:1}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#7a7f8e',callback:function(v,i){return i%15===0?i+'日':'';}}},y:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}}}}});}

function drawPref(m){const el=document.getElementById('tab-pref');const pd=DATA.prefecture[m]||[];if(!pd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const totalCount=pd.reduce((a,p)=>a+p.count,0);const top15=pd.slice(0,15);const top15rev=[...pd].sort((a,b)=>b.revenue-a.revenue).slice(0,15);let rows=pd.map((p,i)=>`<tr><td>${i+1}</td><td>${p.name}</td><td class="num">${p.count}</td><td class="num">${fmtY(p.revenue)}</td><td class="num">${fmtY(p.avg_price)}</td><td class="num">${p.persons}</td><td class="num">${pct(p.count,totalCount)}%<div class="bar-bg"><div class="bar-fill" style="width:${Math.min(100,p.count/totalCount*200)}%;background:var(--ac)"></div></div></td></tr>`).join('');el.innerHTML=`<div class="grid-2"><div class="card"><h3>居住地 TOP15（件数）</h3><div class="chart-wrap tall"><canvas id="pref-cnt"></canvas></div></div><div class="card"><h3>居住地 TOP15（売上）</h3><div class="chart-wrap tall"><canvas id="pref-rev"></canvas></div></div></div><div class="card"><h3>居住地 明細 <span class="badge">${pd.length}地域</span></h3><div class="scroll-table"><table><tr><th>#</th><th>都道府県</th><th class="num">件数</th><th class="num">売上</th><th class="num">平均単価</th><th class="num">人数</th><th class="num">構成比</th></tr>${rows}</table></div></div>`;makeChart('pref-cnt',{type:'bar',data:{labels:top15.map(p=>p.name),datasets:[{data:top15.map(p=>p.count),backgroundColor:'rgba(79,142,247,.6)',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}},y:{ticks:{color:'#e8eaf0'}}}}});makeChart('pref-rev',{type:'bar',data:{labels:top15rev.map(p=>p.name),datasets:[{data:top15rev.map(p=>p.revenue),backgroundColor:'rgba(52,201,142,.6)',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y:{ticks:{color:'#e8eaf0'}}}}});}

function drawPrefMonthly(){const el=document.getElementById('tab-pref_monthly');const allMonths=DATA.months;const prefTotals={};allMonths.forEach(m=>{(DATA.prefecture[m]||[]).forEach(p=>{prefTotals[p.name]=(prefTotals[p.name]||0)+p.count;});});const top10=Object.entries(prefTotals).sort((a,b)=>b[1]-a[1]).slice(0,10).map(e=>e[0]);const colors=['#4f8ef7','#f59e0b','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4','#f97316','#14b8a6','#8b5cf6'];el.innerHTML=`<div class="card"><h3>都道府県 月次構成（件数 TOP10）</h3><div class="chart-wrap tall"><canvas id="pref-monthly-chart"></canvas></div></div>`;const datasets=top10.map((name,i)=>({label:name,data:allMonths.map(m=>{const p=(DATA.prefecture[m]||[]).find(x=>x.name===name);return p?p.count:0;}),backgroundColor:colors[i%colors.length]}));makeChart('pref-monthly-chart',{type:'bar',data:{labels:allMonths,datasets},options:{responsive:true,maintainAspectRatio:false,scales:{x:{stacked:true,ticks:{color:'#7a7f8e'}},y:{stacked:true,grid:{color:'rgba(255,255,255,.05)'},ticks:{color:'#7a7f8e'}}},plugins:{legend:{position:'bottom',labels:{color:'#e8eaf0',font:{size:10}}}}}});}

function drawTravel(m){const el=document.getElementById('tab-travel');const td=DATA.travel[m]||[];if(!td.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const colors=['#4f8ef7','#f59e0b','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4'];el.innerHTML=`<div class="grid-2"><div class="card"><h3>旅行動態別 件数</h3><div class="chart-wrap"><canvas id="travel-cnt"></canvas></div></div><div class="card"><h3>旅行動態別 売上</h3><div class="chart-wrap"><canvas id="travel-rev"></canvas></div></div></div><div class="card"><h3>旅行動態 明細</h3><div class="scroll-table"><table><tr><th>旅行動態</th><th class="num">件数</th><th class="num">売上</th><th class="num">平均単価</th><th class="num">人数</th><th class="num">構成比</th></tr>${td.map(t=>{const total=td.reduce((a,x)=>a+x.count,0);return`<tr><td>${t.name}</td><td class="num">${t.count}</td><td class="num">${fmtY(t.revenue)}</td><td class="num">${fmtY(t.count?Math.round(t.revenue/t.count):0)}</td><td class="num">${t.persons}</td><td class="num">${pct(t.count,total)}%</td></tr>`;}).join('')}</table></div></div><p style="color:var(--mu);font-size:10px;margin-top:8px">※ 旅行動態は大人人数・子供人数・男女人数から推定しています</p>`;makeChart('travel-cnt',{type:'doughnut',data:{labels:td.map(t=>t.name),datasets:[{data:td.map(t=>t.count),backgroundColor:colors,borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#e8eaf0'}}}}});makeChart('travel-rev',{type:'doughnut',data:{labels:td.map(t=>t.name),datasets:[{data:td.map(t=>t.revenue),backgroundColor:colors,borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#e8eaf0'}},tooltip:{callbacks:{label:ctx=>ctx.label+': \u00a5'+fmt(ctx.raw)}}}}});}

showTab('monthly',document.querySelector('.nav-tab'));
switchAllTabs(DATA.default_month);
"""

if __name__ == "__main__":
    main()
