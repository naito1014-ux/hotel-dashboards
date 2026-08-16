# -*- coding: utf-8 -*-
"""
generate_temairazu.py
手間いらず 予約分析ダッシュボード生成

使い方:
  python3 generate_temairazu.py                     # カレントの data/ を探索
  python3 generate_temairazu.py --hotel /path/to/hotel  # 指定フォルダの data/ を探索
  python3 generate_temairazu.py --no-open           # ブラウザを開かない
  python3 generate_temairazu.py --facility kararako # 掲載順位・クチコミのタブを付ける

data/ フォルダの命名規則:
  Stay:   temairazu_stay_YYYYMM.csv   (例: temairazu_stay_202605.csv)
  Pickup: temairazu_pickup_YYYYMM.csv (例: temairazu_pickup_202605.csv)
  毎月2枚ずつ追加していくだけで、自動的に全月が統合されます。

■ --facility を使うときだけ hotel_report_master 側に依存する（2026-08-15 追加）
  掲載順位・売上ランキング・クチコミは hotel_report_master が収集し、
  dashboard パッケージが Python/CSS/HTML/JS の4層を持っている。--facility を
  渡すとそれを読み込んでタブを3つ足す。
  渡さなければ従来どおり、この1本と temairazu_analyzer.py と
  data/ だけで完結する（依存は増えない）。

  ★ --facility を使う場合は venv の python で実行すること ★
  読み込む先で PyYAML（config.yml の読み取り）が要る。システムの python3 には
  入っていないため、--facility 付きでは動かない。--facility 無しなら従来どおり
  システム python でも動く。dashboard の読み込みは --facility 指定時だけに
  遅らせてあるので、無指定の実行が依存で失敗することはない。
      ./venv/bin/python3 generate_temairazu.py --facility kararako --no-open
      （venv は hotel_report_master/venv）
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

# --facility 指定時にだけ読み込む dashboard パッケージ。無指定なら None のまま
_DASHBOARD = None


def _master_dir() -> Path:
    """hotel_report_master を相対で解決する。

    絶対パスを直書きしない。両リポジトリは AIレポート/ 直下の兄弟なので、
    このファイル(<AIレポート>/hotel-dashboards/<施設>/generate_temairazu.py)
    から2つ上がると AIレポート/ になる。
    """
    master = Path(__file__).resolve().parents[2] / "hotel_report_master"
    if not master.is_dir():
        raise SystemExit(
            f"\nエラー: hotel_report_master が見つかりません\n"
            f"  探した場所: {master}\n"
            f"  この生成器の場所: {Path(__file__).resolve()}\n"
            f"  hotel-dashboards と hotel_report_master が AIレポート/ 直下に\n"
            f"  並んでいる前提です。片方だけ移動していないか確認してください。\n"
            f"  （--facility を付けない実行なら master は不要です）"
        )
    return master


def _dashboard():
    """dashboard パッケージを遅延で読み込む。何が無いかを必ず明示して落ちる。"""
    global _DASHBOARD
    if _DASHBOARD is not None:
        return _DASHBOARD
    master = _master_dir()
    pkg = master / "dashboard" / "__init__.py"
    if not pkg.exists():
        raise SystemExit(
            f"\nエラー: dashboard パッケージが見つかりません\n"
            f"  探した場所: {pkg}\n"
            f"  hotel_report_master 側が古い可能性があります。"
        )
    if str(master) not in sys.path:
        sys.path.insert(0, str(master))
    try:
        import dashboard as _d
    except ImportError as e:
        raise SystemExit(
            f"\nエラー: dashboard の読み込みに失敗しました: {e}\n"
            f"  読み込み元: {master}\n"
            f"  PyYAML が要ります。hotel_report_master/venv の python で\n"
            f"  実行してください:\n"
            f"    {master / 'venv/bin/python3'} {Path(__file__).name} --facility <id>"
        )
    _DASHBOARD = _d
    return _DASHBOARD


def load_dashboard_data(facility_id: str) -> dict:
    """掲載順位・クチコミを hotel_report_master から読む。

    ★ 使うのは収集データの3系統だけ ★
    load_context() は report_dir_name から既存CSVの置き場も解決するが、
    その結果（ctx['paths']）には一切触らない。手間いらず系のデータは
    --hotel か自分の隣の data/ にあり、master 側を見に行ってはいけない。
    手間いらず系の config.yml は report_dir_name: null なので、参照すると
    master 自身にフォールバックして自分のデータを見失う。
    """
    d = _dashboard()
    from dashboard.context import load_context, FACILITIES_DIR

    cfg_path = FACILITIES_DIR / facility_id / "config.yml"
    if not cfg_path.exists():
        raise SystemExit(
            f"\nエラー: 施設マスタがありません\n"
            f"  探した場所: {cfg_path}\n"
            f"  facilities/ 配下のディレクトリ名を --facility に渡してください。"
        )
    ctx = load_context(facility_id)
    if ctx.get("config") is None:
        raise SystemExit(
            f"\nエラー: {cfg_path} を読めませんでした\n"
            f"  理由として記録されたもの:\n"
            + "".join(f"    - {n}\n" for n in ctx.get("notes") or ["(記録なし)"])
            + f"  PyYAML が無い場合もここに来ます。venv の python で実行してください。"
        )

    extra = {
        "listing_rank": d.listing_rank_payload(ctx),
        "reviews": d.reviews_payload(ctx),
        "sales_rank": d.sales_rank_payload(ctx),
    }
    lr_m = extra["listing_rank"].get("months") or []
    rv_m = extra["reviews"].get("months") or []
    sr_m = extra["sales_rank"].get("months") or []
    print(f"  掲載順位: {len(lr_m)}ヶ月"
          + (f"  {lr_m[0]} 〜 {lr_m[-1]}" if lr_m else "（未収集）"))
    print(f"  クチコミ: {len(rv_m)}ヶ月"
          + (f"  {rv_m[0]} 〜 {rv_m[-1]}" if rv_m else "（未収集）"))
    print(f"  売上ランキング: {len(sr_m)}ヶ月"
          + (f"  {sr_m[0]} 〜 {sr_m[-1]}" if sr_m else "（未収集）"))
    for n in ctx.get("notes") or []:
        print(f"  [note] {n}")
    return extra


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hotel", type=str, default=None,
                        help="ホテルフォルダのパス（data/ サブフォルダを探索）")
    parser.add_argument("--no-open", action="store_true",
                        help="ブラウザを自動で開かない")
    parser.add_argument("--facility", type=str, default=None,
                        help="施設ID（hotel_report_master/facilities/ 配下の名前）。"
                             "指定すると掲載順位・クチコミのタブが付く")
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

    # 掲載順位・売上ランキング・クチコミ（--facility 指定時のみ）。ここで読むのは
    # hotel_report_master 側の収集JSONだけで、上の手間いらずデータには触らない
    extra = load_dashboard_data(args.facility) if args.facility else None

    print("\n[2/2] ダッシュボード生成中...")
    out_dir = Path(args.hotel) / "output" if args.hotel else OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "index.html"
    out.write_text(build_html(data, extra), encoding="utf-8")
    print(f"  出力: {out}")

    print("\n✓ 完了！")
    if not args.no_open:
        print("ブラウザで開きます...")
        webbrowser.open(out.as_uri())
        input("\nEnterキーで終了...")


# ========================================================================
# HTML 生成
# ========================================================================

def build_html(data: dict, extra: dict = None) -> str:
    """extra は load_dashboard_data() の戻り（掲載順位・クチコミ）。無ければ None。

    temairazu_analyzer.py は触らずに、ここで data へ足す。analyzer は
    手間いらずCSVの集計だけを担当させ、影響範囲を広げない。
    """
    if extra:
        data.update(extra)

    # データが1ヶ月も無ければタブ自体を出さない。空タブが出ていると
    # 「データが消えた」ようにしか見えず、収集済みの施設と区別が付かない
    has_lr = bool((data.get("listing_rank") or {}).get("months"))
    has_rv = bool((data.get("reviews") or {}).get("months"))
    has_sr = bool((data.get("sales_rank") or {}).get("months"))

    data_json = json.dumps(data, ensure_ascii=False, default=str)
    return html_head(data, has_lr, has_rv, has_sr) + html_body(data, has_lr, has_rv, has_sr) + \
        f"\n<script>\nconst DATA = {data_json};\n{make_js(has_lr, has_rv, has_sr)}\n</script>\n</body>\n</html>"


def html_head(data, has_lr=False, has_rv=False, has_sr=False):
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
.kpi .py{{font-size:10px;color:var(--mu);margin-top:5px;font-family:'DM Mono',monospace;letter-spacing:.2px;}}
.kpi .py .d{{margin-left:6px;font-weight:500;}}
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
/* ── 月次レポート ── */
.rp-line{{font-size:12.5px;margin-bottom:6px;}}
.rp-line:last-child{{margin-bottom:0;}}
.rp-sub{{font-size:11px;color:var(--mu);margin:10px 0 6px;font-weight:500;}}
.rp-narr{{background:rgba(139,105,20,.06);border-left:3px solid var(--ac);padding:8px 10px;border-radius:0 6px 6px 0;font-size:11.5px;margin-top:10px;}}
.rp-ok{{color:var(--mu);font-size:11.5px;padding:6px 0;}}
.rp-factor{{display:flex;justify-content:space-between;align-items:center;padding:7px 10px;background:var(--bg);border:1px solid var(--bd);border-radius:6px;margin-bottom:6px;font-size:11.5px;}}
.rp-factor .lbl{{color:var(--mu);}}
.rp-factor .amt{{font-family:'DM Mono',monospace;font-weight:500;}}
.rp-metrics{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px;}}
.rp-cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px;}}
@media(max-width:900px){{.rp-cols,.rp-metrics{{grid-template-columns:1fr;}}}}
.rp-chrow{{display:flex;justify-content:space-between;align-items:center;padding:5px 0;border-bottom:1px solid var(--bd);font-size:11.5px;}}
.rp-chrow .amt{{font-family:'DM Mono',monospace;}}
.rp-day{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--bd);font-size:11.5px;font-family:'DM Mono',monospace;}}
.rp-day .wd{{color:var(--mu);margin-left:4px;}}
.rp-alert{{background:rgba(192,48,48,.07);border-left:3px solid var(--dn);padding:8px 10px;border-radius:0 6px 6px 0;font-size:11.5px;margin-bottom:6px;}}
.rp-alert.lv2{{background:rgba(176,120,40,.08);border-left-color:var(--wn);}}
.rp-alert.lv1{{background:rgba(44,36,24,.04);border-left-color:var(--mu);}}
.rp-lvtag{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:10px;font-weight:500;margin-right:6px;}}
.rp-lv3{{background:var(--dn);color:#faf8f4;}}
.rp-lv2{{background:var(--wn);color:#faf8f4;}}
.rp-lv1{{background:rgba(44,36,24,.12);color:var(--mu);}}
.rp-issue{{padding:7px 0 7px 20px;border-bottom:1px solid var(--bd);font-size:11.5px;position:relative;}}
.rp-issue:before{{content:'\\25B8';position:absolute;left:4px;color:var(--ac);}}
.rp-note{{font-size:10px;color:var(--mu);margin-top:8px;}}
.footer{{text-align:center;padding:20px;color:var(--mu);font-size:10px;border-top:1px solid var(--bd);margin-top:20px;}}
@media print{{.header,.nav,.month-bar{{position:static;}}.section{{display:block!important;page-break-before:always;}}body{{background:#fff;}}}}
{_dashboard().css() if (has_lr or has_rv or has_sr) else ''}
</style>
</head>
<body>
"""


def html_body(data, has_lr=False, has_rv=False, has_sr=False):
    hotel = data["hotel_name"]
    gen_at = data["generated_at"]
    months = data["months"]

    tab_defs = [
        ("report", "月次レポート"),
        ("monthly", "月別実績"), ("yoy", "前年同日対比"), ("daily", "Daily"),
        ("room", "Room"), ("room_monthly", "Room月次"), ("plan", "Plan"),
        ("cancel", "キャンセル"), ("pickup", "Pickup"), ("leadtime", "Leadtime"),
        ("pref", "都道府県"), ("pref_monthly", "都道府県月次"), ("travel", "旅行動態"),
    ]
    # 掲載順位・売上ランキング・クチコミは、データがある施設にだけ後ろへ足す。
    # ラベル・並び順とも dashboard.TABS を正とする（施設ごとに書き分けない）
    if has_lr or has_rv or has_sr:
        _shown = {'listing_rank': has_lr, 'reviews': has_rv, 'sales_rank': has_sr}
        tab_defs += [(k, label) for k, label in _dashboard().TABS if _shown.get(k)]

    nav = "".join(
        f'<button class="nav-tab" onclick="showTab(\'{t}\',this)">{l}</button>'
        for t, l in tab_defs
    )
    month_btns = "".join(
        f'<button class="month-btn" onclick="switchAllTabs(\'{m}\')">{m}</button>'
        for m in months
    )
    month_opts = "".join(f'<option value="{m}">{m}</option>' for m in months)
    # 既存13タブは中身が空の div で、JS が innerHTML で組み立てる。
    # 掲載順位・クチコミは静的HTMLを持つので、そのタブだけ中身入りにする。
    # 方式が違うだけで競合はしない（どちらも id="tab-<キー>" の div 1枚）
    static = (_dashboard().section_map(has_lr, has_rv, has_sr)
              if (has_lr or has_rv or has_sr) else {})
    sections = "\n".join(
        static.get(t) or f'<div class="section" id="tab-{t}"></div>'
        for t, _ in tab_defs
    )

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


def make_js(has_lr=False, has_rv=False, has_sr=False):
    """ダッシュボード描画ロジック（JavaScript文字列を返す）。"""
    # build_v2.py の JS をそのまま埋め込む
    # DATA は呼び出し元で注入済み
    if not (has_lr or has_rv or has_sr):
        return JS_CODE
    d = _dashboard()
    # js_prelude() は base（Chart.js の共通オプション）と mk()。
    # TL系は自前で持っているので使わないが、こちらは持っていないので足す。
    # charts は下の JS_CODE が `const charts={}` を持っているため入っていない。
    # base は drawYoY() 内のローカル `const base` と名前が同じだが、あちらは
    # 関数内宣言なので shadowing になるだけで壊れない。
    #
    # js() は掲載順位・クチコミの両方を必ず返す。片方のタブしか出さない場合も
    # 分割しないこと（クチコミJSが掲載順位の LR_OTA_NAME / LR_OTA_COLOR を
    # 参照しているため、欠けると ReferenceError でタブが白くなる）
    return JS_CODE + d.js_prelude() + d.js()


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
const monthTabs=['report','monthly','daily','room','plan','cancel','pref','travel'];
// 掲載順位・クチコミは自前の月切替を持つので、共通の月バーは出さない。
// タブを出していない施設でも配列に入れておくだけなら無害
const noMonthBar=['yoy','room_monthly','pref_monthly','listing_rank','sales_rank','reviews'];
let tabMonths={};monthTabs.forEach(t=>{tabMonths[t]=DATA.default_month;});
let curTab='monthly';
const charts={};
function destroyChart(id){if(charts[id]){charts[id].destroy();delete charts[id];}}
function makeChart(id,cfg){destroyChart(id);const c=document.getElementById(id);if(!c)return null;charts[id]=new Chart(c,cfg);return charts[id];}
function showTab(name,el){document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));document.querySelectorAll('.nav-tab').forEach(t=>t.classList.remove('active'));document.getElementById('tab-'+name).classList.add('active');if(el)el.classList.add('active');curTab=name;document.getElementById('monthBar').style.display=noMonthBar.includes(name)?'none':'';const tm=tabMonths[name]||DATA.default_month;document.querySelectorAll('.month-btn').forEach(x=>x.classList.toggle('active',x.textContent===tm));drawTab(name);}
function switchAllTabs(m){monthTabs.forEach(t=>{tabMonths[t]=m;});document.querySelectorAll('.month-btn').forEach(x=>x.classList.toggle('active',x.textContent===m));const sel=document.getElementById('global-month-select');if(sel)sel.value=m;drawTab(curTab);}
function printAll(){document.querySelectorAll('.section').forEach(s=>s.classList.add('active'));setTimeout(()=>{window.print();},300);}
function drawTab(name){const m=tabMonths[name]||DATA.default_month;switch(name){case'report':drawReport(m);break;case'monthly':drawMonthly(m);break;case'yoy':drawYoY();break;case'daily':drawDaily(m);break;case'room':drawRoom(m);break;case'room_monthly':drawRoomMonthly();break;case'plan':drawPlan(m);break;case'cancel':drawCancel(m);break;case'pickup':drawPickup();break;case'leadtime':drawLeadtime();break;case'pref':drawPref(m);break;case'pref_monthly':drawPrefMonthly();break;case'travel':drawTravel(m);break;
// 掲載順位・クチコミ。タブを出していない施設では描画関数自体が
// 埋め込まれないので、typeof で確かめてから呼ぶ
case'listing_rank':if(typeof drawListingRank==='function')drawListingRank();break;
case'sales_rank':if(typeof drawSalesRank==='function')drawSalesRank();break;
case'reviews':if(typeof drawReviews==='function')drawReviews();break;}}

let rangeMode=false;let rangeFrom='';let rangeTo='';

/* ========== 前年対比ヘルパー（月別実績タブ） ========== */
// CSVの月跨ぎ流入で数件だけ入っている端数月（例 2024-12）は「前年実績あり」と見なさない。
// 全月の室数の中央値の15%未満を端数月と判定（実データの最小月でも中央値の6割程度あるため安全）。
function fragmentMonths(){
  if(window._fragMo)return window._fragMo;
  const vals=DATA.months.map(mm=>(DATA.monthly[mm]||{}).rooms||0).slice().sort((a,b)=>a-b);
  const med=vals.length?vals[Math.floor(vals.length/2)]:0;
  window._fragMo=new Set(DATA.months.filter(mm=>((DATA.monthly[mm]||{}).rooms||0)<med*0.15));
  return window._fragMo;
}
function pyMonth(mm){return (Number(mm.slice(0,4))-1)+mm.slice(4);}
function hasPy(mm){const p=pyMonth(mm);return !!DATA.monthly[p]&&!fragmentMonths().has(p);}
// 前年比（％）。inv=true はキャンセル率のように「増加＝悪化」の指標
function pyDelta(cur,py,inv){
  if(py===null||py===undefined)return{txt:'-',cls:''};
  if(!py)return{txt:'-',cls:''};// 前年ゼロは率を出さず、新規/消失はピルで示す
  const d=(cur-py)/py*100;
  return{txt:(d>0?'+':'')+d.toFixed(1)+'%',cls:d>0?(inv?'dn':'up'):(d<0?(inv?'up':'dn'):'')};
}
// 前年差（ポイント）
function ptDelta(cur,py,inv){
  const d=cur-py;
  return{txt:(d>0?'+':'')+d.toFixed(1)+'pt',cls:d>0?(inv?'dn':'up'):(d<0?(inv?'up':'dn'):'')};
}
// チャネル別集計：monthly にチャネル内訳が無いため daily の室数比で按分。
// daily の channels は室数しか持たないので、売上・RN・人数はその日の室数シェアで按分する。
function aggChannels(months){
  const map={};
  months.forEach(mm=>{
    (DATA.daily[mm]||[]).forEach(d=>{const tr=d.rooms;Object.entries(d.channels).forEach(([ch,rooms])=>{
      if(!map[ch])map[ch]={rooms:0,revenue:0,rn:0,persons:0};
      map[ch].rooms+=rooms;map[ch].revenue+=tr>0?Math.round(d.revenue*rooms/tr):0;
      map[ch].rn+=tr>0?Math.round(d.rn*rooms/tr):0;map[ch].persons+=tr>0?Math.round(d.persons*rooms/tr):0;
    });});
  });
  return map;
}
function chStats(d){return{rooms:d.rooms,rn:d.rn,revenue:d.revenue,persons:d.persons,adr:d.rn>0?Math.round(d.revenue/d.rn):0};}
function chDot(n){return`<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${chColor(n)};margin-right:6px"></span>`;}
// 当年 / 前年 / 比 の3セル
function pyTrio(cur,py,fn){
  const d=pyDelta(cur,py,false);
  return`<td class="num" style="border-left:2px solid var(--bd)">${fn(cur)}</td>`+
    `<td class="num" style="color:var(--mu)">${py?fn(py):'-'}</td>`+
    `<td class="num ${d.cls}" style="font-size:10.5px">${d.txt}</td>`;
}

function drawMonthly(m){const el=document.getElementById('tab-monthly');
  const allM=DATA.months;
  if(!rangeFrom)rangeFrom=allM[0];
  if(!rangeTo)rangeTo=allM[allM.length-1];
  let fromOpts=allM.map(mm=>`<option value="${mm}" ${rangeFrom===mm?'selected':''}>${mm}</option>`).join('');
  let toOpts=allM.map(mm=>`<option value="${mm}" ${rangeTo===mm?'selected':''}>${mm}</option>`).join('');

  // Determine which months to aggregate
  const targetMonths=rangeMode?allM.filter(mm=>mm>=rangeFrom&&mm<=rangeTo):[m];
  const label=rangeMode?`${rangeFrom} 〜 ${rangeTo}`:m;

  // 前年対比の可否：対象月すべてに前年実績がある場合のみ表示（部分的な前年は歪むため出さない）
  const missPy=targetMonths.filter(mm=>!hasPy(mm));
  const showPy=targetMonths.length>0&&missPy.length===0;
  const pyMonths=showPy?targetMonths.map(pyMonth):[];
  const pyLabel=showPy?(rangeMode?`${pyMonth(rangeFrom)} 〜 ${pyMonth(rangeTo)}`:pyMonth(m)):'';
  const pyNote=showPy
    ?`<span style="font-size:10.5px;color:var(--mu);margin-left:8px">前年：${pyLabel}</span>`
    :`<span style="font-size:10.5px;color:var(--mu);margin-left:8px">前年データなし（${missPy.slice(0,3).join('・')}${missPy.length>3?' 他':''} の前年実績が未取込）</span>`;

  let rangeUI=`<div class="filter-row" style="margin-bottom:12px">
    <button class="toggle-btn ${!rangeMode?'active':''}" onclick="rangeMode=false;drawMonthly(tabMonths.monthly)">月別</button>
    <button class="toggle-btn ${rangeMode?'active':''}" onclick="rangeMode=true;drawMonthly(tabMonths.monthly)">期間指定</button>
    ${rangeMode?`<select onchange="rangeFrom=this.value;drawMonthly(tabMonths.monthly)" style="margin-left:8px">${fromOpts}</select>
    <span style="color:var(--mu);font-size:11px">〜</span>
    <select onchange="rangeTo=this.value;drawMonthly(tabMonths.monthly)">${toOpts}</select>`:''}
    ${pyNote}
  </div>`;

  // Aggregate monthly data
  let aRev=0,aRooms=0,aRn=0,aPersons=0,aCancel=0,aTotal=0;
  targetMonths.forEach(mm=>{
    const md=DATA.monthly[mm];if(!md)return;
    aRev+=md.revenue;aRooms+=md.rooms;aRn+=md.rn;aPersons+=md.persons;aCancel+=md.cancel;aTotal+=md.total;
  });
  const aAdr=aRn?Math.round(aRev/aRn):0;
  const aPerPerson=aPersons?Math.round(aRev/aPersons):0;
  const aCancelRate=aTotal?((aCancel/aTotal)*100).toFixed(1):0;

  // Aggregate previous-year monthly data
  let pRev=0,pRooms=0,pRn=0,pPersons=0,pCancel=0,pTotal=0;
  pyMonths.forEach(mm=>{
    const md=DATA.monthly[mm];if(!md)return;
    pRev+=md.revenue;pRooms+=md.rooms;pRn+=md.rn;pPersons+=md.persons;pCancel+=md.cancel;pTotal+=md.total;
  });
  const pAdr=pRn?Math.round(pRev/pRn):0;
  const pPerPerson=pPersons?Math.round(pRev/pPersons):0;
  const pCancelRateN=pTotal?(pCancel/pTotal)*100:0;

  // KPI cards (+ 前年 / 前年比)
  const kpis=[
    {c:'blue',l:'売上合計',v:(aRev/10000).toFixed(0),u:'万円',cur:aRev,py:pRev,f:x=>(x/10000).toFixed(0)+'万円'},
    {c:'green',l:'予約件数',v:fmt(aRooms),u:'件',cur:aRooms,py:pRooms,f:x=>fmt(x)+'件'},
    {c:'blue',l:'室泊数 RN',v:fmt(aRn),u:'RN',cur:aRn,py:pRn,f:x=>fmt(x)+'RN'},
    {c:'orange',l:'ADR',v:fmt(aAdr),u:'円',cur:aAdr,py:pAdr,f:x=>fmtY(x)},
    {c:'green',l:'人泊単価',v:fmt(aPerPerson),u:'円',cur:aPerPerson,py:pPerPerson,f:x=>fmtY(x)},
    {c:'red',l:'キャンセル率',v:aCancelRate,u:'%',cur:Number(aCancelRate),py:pCancelRateN,f:x=>x.toFixed(1)+'%',pt:true,inv:true},
  ];
  const kpiHtml=kpis.map(k=>{
    let py;
    if(showPy){
      const d=k.pt?ptDelta(k.cur,k.py,k.inv):pyDelta(k.cur,k.py,k.inv);
      py=`<div class="py">前年 ${k.f(k.py)}<span class="d ${d.cls}">${d.txt}</span></div>`;
    }else{
      py=`<div class="py">前年データなし</div>`;
    }
    return`<div class="kpi ${k.c}"><div class="label">${k.l}</div><div class="value">${k.v}<span class="unit">${k.u}</span></div>${py}</div>`;
  }).join('');

  // Aggregate channel data from daily
  const chMap=aggChannels(targetMonths);
  const pyChMap=showPy?aggChannels(pyMonths):{};
  const chList=Object.entries(chMap).sort((a,b)=>b[1].revenue-a[1].revenue).map(([ch,d])=>Object.assign({name:ch},chStats(d)));
  const totalRev=chList.reduce((a,c)=>a+c.revenue,0);
  const pyList=Object.entries(pyChMap).sort((a,b)=>b[1].revenue-a[1].revenue).map(([ch,d])=>Object.assign({name:ch},chStats(d)));
  const pyTotalRev=pyList.reduce((a,c)=>a+c.revenue,0);
  const lost=pyList.filter(c=>!chMap[c.name]);
  const ZERO={rooms:0,rn:0,revenue:0,persons:0,adr:0};

  let chRows,tableCard;
  if(showPy){
    const METRICS=['室数','RN','売上','ADR','人数'];
    const th1=METRICS.map(x=>`<th class="num" colspan="3" style="text-align:center;border-left:2px solid var(--bd)">${x}</th>`).join('');
    const th2=METRICS.map(()=>`<th class="num" style="border-left:2px solid var(--bd)">当年</th><th class="num">前年</th><th class="num">比</th>`).join('');
    chRows=chList.map(c=>{
      const p=pyChMap[c.name]?chStats(pyChMap[c.name]):ZERO;
      const tag=pyChMap[c.name]?'':` <span class="pill pill-green" style="margin-left:4px">新規</span>`;
      return`<tr><td style="white-space:nowrap">${chDot(c.name)}${c.name}${tag}</td>`+
        pyTrio(c.rooms,p.rooms,fmt)+pyTrio(c.rn,p.rn,fmt)+pyTrio(c.revenue,p.revenue,fmtY)+
        pyTrio(c.adr,p.adr,fmtY)+pyTrio(c.persons,p.persons,fmt)+
        `<td class="num">${pct(c.revenue,totalRev)}%</td></tr>`;
    }).join('');
    chRows+=lost.map(c=>`<tr style="opacity:.7"><td style="white-space:nowrap">${chDot(c.name)}${c.name} <span class="pill pill-red" style="margin-left:4px">消失</span></td>`+
      pyTrio(0,c.rooms,fmt)+pyTrio(0,c.rn,fmt)+pyTrio(0,c.revenue,fmtY)+
      pyTrio(0,c.adr,fmtY)+pyTrio(0,c.persons,fmt)+
      `<td class="num">-</td></tr>`).join('');
    tableCard=`<div class="card"><h3>チャネル別明細（前年対比）<span class="badge">${label} vs ${pyLabel}</span></h3>
      <div class="scroll-table" style="overflow-x:auto"><table style="min-width:1180px">
        <tr><th rowspan="2" style="min-width:150px">チャネル</th>${th1}<th rowspan="2" class="num">構成比</th></tr>
        <tr>${th2}</tr>${chRows}</table></div>
      <div style="font-size:10px;color:var(--mu);margin-top:8px">※ チャネル別の RN・売上・人数は Daily の室数比で按分した推計値です（日次で丸めるため月合計と最大数RN程度ずれます）。</div></div>`;
  }else{
    chRows=chList.map(c=>`<tr><td>${chDot(c.name)}${c.name}</td><td class="num">${fmt(c.rooms)}</td><td class="num">${fmt(c.rn)}</td><td class="num">${fmtY(c.revenue)}</td><td class="num">${fmtY(c.adr)}</td><td class="num">${fmt(c.persons)}</td><td class="num">${pct(c.revenue,totalRev)}%</td></tr>`).join('');
    tableCard=`<div class="card"><h3>チャネル別明細</h3><div class="scroll-table"><table><tr><th>チャネル</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">構成比</th></tr>${chRows}</table></div></div>`;
  }

  // Layout: 前年ありは 当年/前年の2円グラフ + 全幅テーブル、前年なしは従来どおり
  const pieCur=`<div class="card"><h3>チャネル別構成${showPy?'（'+label+'）':(rangeMode?' ('+label+')':'')}</h3><div class="chart-wrap"><canvas id="monthly-pie"></canvas></div></div>`;
  const layout=showPy
    ?`<div class="grid-2">${pieCur}<div class="card"><h3>チャネル別構成（前年：${pyLabel}）</h3><div class="chart-wrap"><canvas id="monthly-pie-py"></canvas></div></div></div>${tableCard}`
    :`<div class="grid-2">${pieCur}${tableCard}</div>`;

  el.innerHTML=rangeUI+`<div class="kpi-row">${kpiHtml}</div>`+layout;

  const cData=chList.filter(c=>c.revenue>0);
  makeChart('monthly-pie',{type:'doughnut',data:{labels:cData.map(c=>c.name),datasets:[{data:cData.map(c=>c.revenue),backgroundColor:cData.map(c=>chColor(c.name)),borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#2c2418',font:{size:11},padding:8}},tooltip:{callbacks:{label:ctx=>ctx.label+': ¥'+fmt(ctx.raw)+' ('+pct(ctx.raw,totalRev)+'%)'}}}}});
  if(showPy){
    const pData=pyList.filter(c=>c.revenue>0);
    makeChart('monthly-pie-py',{type:'doughnut',data:{labels:pData.map(c=>c.name),datasets:[{data:pData.map(c=>c.revenue),backgroundColor:pData.map(c=>chColor(c.name)),borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#2c2418',font:{size:11},padding:8}},tooltip:{callbacks:{label:ctx=>ctx.label+': ¥'+fmt(ctx.raw)+' ('+pct(ctx.raw,pyTotalRev)+'%)'}}}}});
  }else{destroyChart('monthly-pie-py');}
}

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

/* ========== DAILY: 前年同曜日合わせ比較 ==========
   前年の「同月・同回数目の同曜日」と比較する（今年の第2土曜 → 前年の第2土曜）。
   かららこの DATA.daily は月キー辞書で、予約ゼロ日は行そのものが存在しない。
   前年月が取込済み（hasPy）なら「行が無い＝予約ゼロ」とみなし売上0で比較する。 */
let dailyPY=true;
function toggleDailyPY(){dailyPY=!dailyPY;drawDaily(tabMonths.daily);}
// 前年同月の「k回目の同曜日」（無ければ null）
function pyNthWeekday(dateStr){
  const y=+dateStr.slice(0,4),mo=+dateStr.slice(5,7),da=+dateStr.slice(8,10);
  const g=new Date(y,mo-1,da).getDay();
  let k=0;for(let i=1;i<=da;i++)if(new Date(y,mo-1,i).getDay()===g)k++;
  const dimPrev=new Date(y-1,mo,0).getDate();
  let c=0;
  for(let i=1;i<=dimPrev;i++){
    if(new Date(y-1,mo-1,i).getDay()===g){c++;if(c===k)return (y-1)+'-'+String(mo).padStart(2,'0')+'-'+String(i).padStart(2,'0');}
  }
  return null;
}
function drawDaily(m){
  const el=document.getElementById('tab-daily');
  const dd=DATA.daily[m]||[];
  if(!dd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}
  const showPyMonth=hasPy(m),pm=pyMonth(m);
  // 前年月の日次売上マップ（行が無い日＝予約ゼロ）
  const pmap={};if(showPyMonth)(DATA.daily[pm]||[]).forEach(d=>{pmap[d.date]=d;});
  const pyOf={};let noCounter=0;
  dd.forEach(d=>{
    const pd=showPyMonth?pyNthWeekday(d.date):null;
    if(showPyMonth&&!pd)noCounter++;
    pyOf[d.date]={pd,row:pd?(pmap[pd]||null):null};
  });
  const on=dailyPY&&showPyMonth;
  const toggleUI=`<div class="filter-row" style="margin-bottom:12px">
    <button class="toggle-btn ${dailyPY?'active':''}" onclick="toggleDailyPY()">前年曜日合わせ</button>
    ${dailyPY?(showPyMonth
      ?`<span style="font-size:10.5px;color:var(--mu);margin-left:4px">前年 ${pm} と同曜日で比較${noCounter?`（前年に対応日なし ${noCounter}日）`:''}</span>`
      :`<span style="font-size:10.5px;color:var(--mu);margin-left:4px">この月は前年データがありません</span>`):''}
  </div>`;

  const SV=r=>r?r.revenue:0,RM=r=>r?r.rooms:0,RNv=r=>r?r.rn:0;
  // 「差」列は率ではなく実数差で表示する（前年に実績が無い日は '-' のまま）
  const ddiffY=(a,b)=>{if(!b)return'<td class="num">-</td>';const d=a-b;
    return`<td class="num ${d>=0?'up':'dn'}">${(d>=0?'+':'−')+fmtY(Math.abs(d))}</td>`;};
  const ddiffC=(a,b,u)=>{if(!b)return'<td class="num">-</td>';const d=a-b;
    return`<td class="num ${d>=0?'up':'dn'}">${(d>=0?'+':'−')+fmt(Math.abs(d))+u}</td>`;};

  let rows,head;
  if(on){
    head=`<tr><th>日付</th><th>前年同曜日</th><th class="num">室数</th><th class="num">前年</th><th class="num">差</th><th class="num">RN</th><th class="num">売上</th><th class="num">前年売上</th><th class="num">差</th><th class="num">ADR</th><th class="num">人数</th></tr>`;
    rows=dd.map(d=>{
      const isWe=d.dow==='土'||d.dow==='日',info=pyOf[d.date],p=info.row;
      // 前年月は取込済みなので、行が無い日は「予約ゼロ（売上0）」として比較する
      const cmp=info.pd!=null;
      const pv=SV(p);
      const sub=info.pd?`${info.pd.slice(5)}${p?'':' <span style="color:var(--mu)">(予約なし)</span>'}`
                       :'<span style="color:var(--mu)">対応日なし</span>';
      return`<tr style="${isWe?'background:rgba(139,105,20,.04)':''}${cmp?'':'opacity:.55'}">
        <td>${d.date} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td>
        <td style="color:var(--mu);font-size:11px">${sub}</td>
        <td class="num">${d.rooms}</td><td class="num" style="color:var(--mu)">${cmp?RM(p):'-'}</td>
        ${cmp?ddiffC(d.rooms,RM(p),'室'):'<td class="num">-</td>'}
        <td class="num">${d.rn}</td>
        <td class="num">${fmtY(d.revenue)}</td>
        <td class="num" style="color:var(--mu)">${cmp?fmtY(pv):'-'}</td>
        ${cmp?ddiffY(d.revenue,pv):'<td class="num">-</td>'}
        <td class="num">${fmtY(d.adr)}</td><td class="num">${d.persons}</td></tr>`;
    }).join('');
  }else{
    head=`<tr><th>日付</th><th class="num">室数</th><th class="num">RN</th><th class="num">売上</th><th class="num">ADR</th><th class="num">人数</th><th class="num">人泊単価</th></tr>`;
    rows=dd.map(d=>{const isWe=d.dow==='土'||d.dow==='日';
      return`<tr style="${isWe?'background:rgba(139,105,20,.04)':''}"><td>${d.date} <span class="pill ${isWe?'pill-orange':'pill-blue'}">${d.dow}</span></td><td class="num">${d.rooms}</td><td class="num">${d.rn}</td><td class="num">${fmtY(d.revenue)}</td><td class="num">${fmtY(d.adr)}</td><td class="num">${d.persons}</td><td class="num">${fmtY(d.per_person)}</td></tr>`;}).join('');
  }

  el.innerHTML=toggleUI+`<div class="card"><h3>日別売上（${m}）${on?`<span class="badge">前年 ${pm} 同曜日比較</span>`:''}</h3><div class="chart-wrap tall"><canvas id="daily-chart"></canvas></div></div>`
    +`<div class="card"><h3>日別明細</h3><div class="scroll-table" style="overflow-x:auto"><table${on?' style="min-width:900px"':''}>${head}${rows}</table></div>`
    +(on?`<div style="font-size:10px;color:var(--mu);margin-top:8px">※ 比較先は「前年同月の同回数目の同曜日」。前年に予約が無かった日は行が存在しないため売上0円として比較しています。前年に同回数目の同曜日が存在しない日（第5週など）は比較対象外です。</div>`:'')
    +`</div>`;

  const ds=on
    ?[{type:'bar',label:'前年同曜日',data:dd.map(d=>SV(pyOf[d.date].row)),backgroundColor:'rgba(44,36,24,.14)',borderRadius:3,yAxisID:'y'},
      {type:'bar',label:'今年',data:dd.map(d=>d.revenue),backgroundColor:dd.map(d=>{const i=pyOf[d.date];
        if(!i.pd)return'rgba(44,36,24,.30)';                              // 比較不可
        return d.revenue>=SV(i.row)?'rgba(45,122,45,.62)':'rgba(192,48,48,.62)';}),borderRadius:3,yAxisID:'y'}]
    :[{type:'bar',label:'売上',data:dd.map(d=>d.revenue),backgroundColor:dd.map(d=>(d.dow==='土'||d.dow==='日')?'rgba(176,120,40,.5)':'rgba(139,105,20,.55)'),borderRadius:3,yAxisID:'y'},
      {type:'line',label:'ADR',data:dd.map(d=>d.adr),borderColor:'#d4870a',backgroundColor:'transparent',pointRadius:2,tension:.3,yAxisID:'y1'}];
  const scales=on
    ?{x:{ticks:{color:'#9a8e7e',font:{size:10}}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'¥'+(v/10000).toFixed(0)+'万'}}}
    :{x:{ticks:{color:'#9a8e7e',font:{size:10}}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'¥'+(v/10000).toFixed(0)+'万'}},y1:{position:'right',grid:{display:false},ticks:{color:'#d4870a',callback:v=>'¥'+fmt(v)}}};
  makeChart('daily-chart',{data:{labels:dd.map(d=>d.date.slice(5)+' '+d.dow),datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},scales,plugins:{legend:{labels:{color:'#2c2418'}}}}});
}

function drawRoom(m){const el=document.getElementById('tab-room');const rd=DATA.room[m]||[];
  const prevM=(parseInt(m.slice(0,4))-1)+m.slice(4);const prd=DATA.room[prevM]||[];
  const prevMap={};prd.forEach(r=>{prevMap[r.name]=r;});if(!rd.length){el.innerHTML='<div class="no-data">この月のデータはありません</div>';return;}const totalRev=rd.reduce((a,r)=>a+r.revenue,0);const dim=daysInMonth(m);const pdim=daysInMonth(prevM);
  let rows=rd.map(r=>{const pr=physicalRooms(r.name);const occ=pr*dim>0?(r.rn/(pr*dim)*100).toFixed(1):'-';
    const pv=prevMap[r.name]||{rooms:0,rn:0,revenue:0,adr:0,persons:0};
    const pOcc=pr*pdim>0?(pv.rn/(pr*pdim)*100).toFixed(1):'-';
    const adrDiff=r.adr-(pv.adr||0);
    const revDiff=r.revenue-(pv.revenue||0);
    const comp=r.rooms?(r.persons/r.rooms).toFixed(2):'-';
    const pComp=pv.rooms?(pv.persons/pv.rooms).toFixed(2):'-';
    const compDiff=comp!=='-'&&pComp!=='-'?(parseFloat(comp)-parseFloat(pComp)).toFixed(2):'-';
    return`<tr><td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${r.name}</td><td class="num">${pr}</td><td class="num">${r.rooms}</td><td class="num" style="color:var(--mu)">${pv.rooms||'-'}</td><td class="num ${Number(occ)>=80?'up':Number(occ)<40?'dn':''}">${occ}%</td><td class="num" style="color:var(--mu)">${pOcc!=='-'?pOcc+'%':'-'}</td><td class="num">${fmtY(r.revenue)}</td><td class="num" style="color:var(--mu)">${pv.revenue?fmtY(pv.revenue):'-'}</td><td class="num ${revDiff>=0?'up':'dn'}">${revDiff>=0?'+':''}${fmtY(revDiff)}</td><td class="num">${fmtY(r.adr)}</td><td class="num" style="color:var(--mu)">${pv.adr?fmtY(pv.adr):'-'}</td><td class="num ${adrDiff>=0?'up':'dn'}">${adrDiff>=0?'+':''}${fmtY(adrDiff)}</td><td class="num">${comp}</td><td class="num" style="color:var(--mu)">${pComp}</td><td class="num ${compDiff!=='-'&&parseFloat(compDiff)>=0?'up':'dn'}">${compDiff!=='-'?(parseFloat(compDiff)>=0?'+':'')+compDiff:'-'}</td><td class="num">${pct(r.revenue,totalRev)}%</td></tr>`;}).join('');el.innerHTML=`<div class="card"><h3>室タイプ別 明細（${m}）</h3><div class="scroll-table"><table><tr><th>室タイプ</th><th class="num">物理室</th><th class="num">室数</th><th class="num">PY室数</th><th class="num">稼働率</th><th class="num">PY稼</th><th class="num">売上</th><th class="num">PY売上</th><th class="num">差</th><th class="num">ADR</th><th class="num">PY ADR</th><th class="num">差</th><th class="num">同伴</th><th class="num">PY同伴</th><th class="num">差</th><th class="num">構成比</th></tr>${rows}</table></div></div><div class="grid-2"><div class="card"><h3>室タイプ別 売上</h3><div class="chart-wrap"><canvas id="room-rev"></canvas></div></div><div class="card"><h3>室タイプ別 ADR</h3><div class="chart-wrap"><canvas id="room-adr"></canvas></div></div></div>`;const colors=['#3366aa','#d4870a','#22c55e','#ef4444','#a78bfa','#ec4899','#06b6d4','#f97316','#14b8a6','#8b5cf6'];makeChart('room-rev',{type:'bar',data:{labels:rd.map(r=>r.name.length>14?r.name.slice(0,14)+'…':r.name),datasets:[{data:rd.map(r=>r.revenue),backgroundColor:rd.map((_,i)=>colors[i%colors.length]),borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'\u00a5'+(v/10000).toFixed(0)+'万'}},y:{ticks:{color:'#2c2418',font:{size:10}}}}}});const sorted=[...rd].sort((a,b)=>b.adr-a.adr);makeChart('room-adr',{type:'bar',data:{labels:sorted.map(r=>r.name.length>14?r.name.slice(0,14)+'…':r.name),datasets:[{data:sorted.map(r=>r.adr),backgroundColor:sorted.map((_,i)=>`hsl(${210+i*25},65%,55%)`),borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e',callback:v=>'\u00a5'+fmt(v)}},y:{ticks:{color:'#2c2418',font:{size:10}}}}}});}

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
let pickupMetric='rooms';let pickupPeriod='90';let pickupMaCh='__all__';let pickupMA7=true;let pickupMA30=true;let pickupShowPY=false;let pickupChView='__all__';
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
    <div class="filter-row"><label>チャネル：</label><button class="toggle-btn ${pickupChView==='__all__'?'active':''}" onclick="pickupChView='__all__';drawPickup()">全体</button>${mainCh.map(ch=>`<button class="toggle-btn ${pickupChView===ch?'active':''}" onclick="pickupChView='${ch}';drawPickup()">${ch}</button>`).join('')}</div>
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
  let chartData;
  if(pickupChView==='__all__'){
    chartData=[{label:'全体',data:dailyAgg.map(d=>d.total),backgroundColor:'rgba(139,105,20,.45)',borderRadius:2}];
  } else {
    chartData=[{label:pickupChView,data:groupedAgg.map(d=>d[pickupChView]||0),backgroundColor:chColor(pickupChView),borderRadius:2}];
  }
  makeChart('pickup-stack',{type:'bar',data:{labels:dailyAgg.map(d=>d.date.slice(5)+' '+d.dow),datasets:chartData},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#2c2418'}}},scales:{x:{ticks:{color:'#9a8e7e',font:{size:9}}},y:{grid:{color:'rgba(44,36,24,.08)'},ticks:{color:'#9a8e7e'}}}}});
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

/* ========== 月次レポート（ルールベース自動生成） ==========
   TL系 drawReport の移植。かららこの DATA はフラット構造・英語キーのため読み替える。
   - 全体値   : TL total/total_py → DATA.monthly[月] / DATA.monthly[前年同月]
   - ADR      : md.adr（＝売上÷RN）。月別実績タブと同一定義
   - 同伴係数 : DATA に無いため persons/rooms で導出
   - チャネル : DATA に実測値が無いため aggChannels()（日次室数シェア按分）を当年・前年に同一適用
   ④⑤は TL系から変更（④＝前年同曜日比での前年割れ額、⑤＝稼働率の前年割れ連続性3段階）
*/
const RP_WD=['日','月','火','水','木','金','土'];
const RP_OCC={};                      // 月→{室タイプ:稼働率} のキャッシュ
function rpYoY(c,p){return p?(c/p-1)*100:null;}
function rpWord(p){return p==null?'前年データなし':(p>5?'増加':(p<-5?'減少':'横ばい'));}
function rpFmtP(p){return p==null?'—':(p>=0?'+':'')+p.toFixed(1)+'%';}
function rpCls(p){return p==null?'':(p>=0?'up':'dn');}
function rpChip(p){return p==null?'<span style="color:var(--mu)">前年データなし</span>'
  :`<span class="${rpCls(p)}">${rpFmtP(p)}（${rpWord(p)}）</span>`;}
function rpSgnY(v){return (v>=0?'+':'−')+fmtY(Math.abs(v));}
function rpPad(n){return String(n).padStart(2,'0');}
function rpDow(ds){const p=ds.split('-').map(Number);return new Date(p[0],p[1]-1,p[2]).getDay();}
function rpPrevMonth(ym){const y=Number(ym.slice(0,4)),mo=Number(ym.slice(5,7));const d=new Date(y,mo-2,1);
  return d.getFullYear()+'-'+rpPad(d.getMonth()+1);}
// データ最終日（これ以降の日付は「未到来／未取込」として集計対象外）
function rpMaxDate(){if(window._rpMaxD)return window._rpMaxD;let mx='';
  Object.keys(DATA.daily).forEach(k=>DATA.daily[k].forEach(d=>{if(d.date>mx)mx=d.date;}));
  window._rpMaxD=mx;return mx;}
// 室タイプ別 稼働率（drawRoom と同一ロジック：rn ÷（物理室数 × 当月日数））
function rpOccMap(ym){
  if(RP_OCC[ym])return RP_OCC[ym];
  const o={};(DATA.room[ym]||[]).forEach(r=>{
    const pr=physicalRooms(r.name),dm=daysInMonth(ym);if(pr&&dm)o[r.name]=r.rn/(pr*dm)*100;});
  RP_OCC[ym]=o;return o;}
// 月 ym の「k回目の曜日g」の日付（無ければ null）
function rpNthWd(ym,g,k){const dim=daysInMonth(ym);let c=0;
  for(let i=1;i<=dim;i++){const ds=ym+'-'+rpPad(i);if(rpDow(ds)===g){c++;if(c===k)return ds;}}
  return null;}
// 日次売上マップ（予約ゼロ日は行が無いので 0 とみなす）
function rpDayRev(ym){const o={};(DATA.daily[ym]||[]).forEach(d=>{o[d.date]=d.revenue;});return o;}
// 室タイプの ym 月における前年割れ判定：true=前年割れ / false=前年以上 / null=判定不能
function rpUnderPy(ym,room){
  if(!hasPy(ym))return null;
  const c=rpOccMap(ym)[room],p=rpOccMap(pyMonth(ym))[room];
  if(c==null||p==null)return null;
  return c<p;}

function drawReport(m){
  const el=document.getElementById('tab-report');if(!el)return;
  const md=DATA.monthly[m];
  if(!md){el.innerHTML='<div class="no-data">この月のデータがありません</div>';return;}
  const showPy=hasPy(m),pm=pyMonth(m),py=showPy?DATA.monthly[pm]:null;
  const moNum=parseInt(m.slice(5,7),10);

  const acc  =md.rooms?md.persons/md.rooms:0;              // 同伴係数＝人数÷室数（導出）
  const accPy=(py&&py.rooms)?py.persons/py.rooms:0;
  const salesPct=showPy?rpYoY(md.revenue,py.revenue):null;
  const roomsPct=showPy?rpYoY(md.rooms,py.rooms):null;
  const rnPct   =showPy?rpYoY(md.rn,py.rn):null;
  const adrPct  =showPy?rpYoY(md.adr,py.adr):null;
  const paxPct  =showPy?rpYoY(md.per_person,py.per_person):null;
  const accPct  =showPy?rpYoY(acc,accPy):null;

  // 売上分解：ADR＝売上÷RN なので数量側は RN を使う（rnEffect+priceEffect＝売上差 が成立）
  const rnEffect   =showPy?(md.rn-py.rn)*py.adr:0;
  const priceEffect=showPy?(md.adr-py.adr)*md.rn:0;
  const driverIsPrice=Math.abs(priceEffect)>=Math.abs(rnEffect);
  const driverPct=driverIsPrice?adrPct:rnPct;

  const pyTag=showPy?`<span class="badge">前年：${pm}</span>`
    :`<span style="font-size:10.5px;color:var(--mu);margin-left:8px">前年データなし</span>`;

  // ══════ ① エグゼクティブサマリー ══════
  let l1,l2,l3;
  if(!showPy){
    l1=`<b>${moNum}月</b>は前年同月のデータがないため、前年比較はスキップします。`;
    l2=`売上 <b>${fmtY(md.revenue)}</b>／室数 <b>${fmt(md.rooms)}室</b>／RN <b>${fmt(md.rn)}</b>／ADR <b>${fmtY(md.adr)}</b>。`;
    l3=`実績値のみを表示しています。`;
  }else{
    l1=`<b>${moNum}月</b>は売上前年比 <span class="${rpCls(salesPct)}">${rpFmtP(salesPct)}</span>。${rpWord(salesPct)}基調です。`;
    const dName=driverIsPrice?'単価(ADR)':'室泊数(RN)';
    const dDir =(driverPct!=null&&driverPct>=0)?'上昇':'低下';
    const dRole=(salesPct!=null&&salesPct>=0)?'牽引':'主因';
    l2=`${dName}の${dDir}（<span class="${rpCls(driverPct)}">${rpFmtP(driverPct)}</span>）が${dRole}。`;
    const oPct=driverIsPrice?rnPct:adrPct,oNm=driverIsPrice?'室泊数(RN)':'ADR';
    l3=`${oNm}は${rpWord(oPct)}（<span class="${rpCls(oPct)}">${rpFmtP(oPct)}</span>）。`
      +`室数 <span class="${rpCls(roomsPct)}">${rpFmtP(roomsPct)}</span>／客単価 <span class="${rpCls(paxPct)}">${rpFmtP(paxPct)}</span>。`;
  }
  let html=`<div class="card"><h3>エグゼクティブサマリー ｜ ${m} ${pyTag}</h3>
    <div class="rp-line">${l1}</div><div class="rp-line">${l2}</div><div class="rp-line">${l3}</div></div>`;

  // ══════ ② 売上分解 ══════
  html+=`<div class="card"><h3>売上分解</h3>`;
  if(!showPy){
    html+=`<div class="rp-ok">前年データがないため、売上分解はスキップします。</div>`;
  }else{
    const totalDelta=md.revenue-py.revenue;
    html+=`<div class="rp-sub">売上変化 ${rpSgnY(totalDelta)}（前年比 ${rpFmtP(salesPct)}）の内訳</div>
    <div class="rp-factor"><span class="lbl">室泊数(RN)要因（単価一定でRNが動いた分）</span><span class="amt ${rnEffect>=0?'up':'dn'}">${rpSgnY(rnEffect)}</span></div>
    <div class="rp-factor"><span class="lbl">単価(ADR)要因（RN一定で単価が動いた分）</span><span class="amt ${priceEffect>=0?'up':'dn'}">${rpSgnY(priceEffect)}</span></div>
    <div class="rp-metrics">
      <div class="kpi orange"><div class="label">ADR（売上÷RN）</div><div class="value">${fmt(md.adr)}<span class="unit">円</span></div><div class="py">前年 ${fmtY(py.adr)}<span class="d">${rpChip(adrPct)}</span></div></div>
      <div class="kpi green"><div class="label">客単価（売上÷人数）</div><div class="value">${fmt(md.per_person)}<span class="unit">円</span></div><div class="py">前年 ${fmtY(py.per_person)}<span class="d">${rpChip(paxPct)}</span></div></div>
      <div class="kpi blue"><div class="label">同伴率（人数÷室数）</div><div class="value">${acc.toFixed(2)}</div><div class="py">前年 ${accPy.toFixed(2)}<span class="d">${rpChip(accPct)}</span></div></div>
    </div>
    <div class="rp-narr">売上変化は主に <b>${driverIsPrice?'単価（ADR）要因':'室泊数（RN）要因'}</b> で動いています（${driverIsPrice?'単価':'RN'}要因 ${rpSgnY(driverIsPrice?priceEffect:rnEffect)} ＞ ${driverIsPrice?'RN':'単価'}要因 ${rpSgnY(driverIsPrice?rnEffect:priceEffect)}）。${
      driverIsPrice
        ?(adrPct>=0?'価格・プラン施策が単価を押し上げています。':'ADR低下が売上を圧迫しています。価格戦略の見直しが論点です。')
        :(rnPct>=0?'稼働が室泊数を伸ばしています。':'室泊数の減少が売上の重しになっています。稼働向上策が論点です。')
    }</div>
    <div class="rp-note">※ ADR は「売上÷RN」で月別実績タブと同一定義のため、数量側は室数ではなく RN で分解しています（両要因の合計が売上差と一致）。</div>`;
  }
  html+=`</div>`;

  // ══════ ③ チャネル別勝敗 ══════
  const cm=aggChannels([m]),cpy=showPy?aggChannels([pm]):{};
  const allCh=[...new Set([...Object.keys(cm),...Object.keys(cpy)])];
  const chRes=allCh.map(ch=>{
    const c=(cm[ch]&&cm[ch].revenue)||0,p=(cpy[ch]&&cpy[ch].revenue)||0;
    return{ch,c,p,pct:p?(c/p-1)*100:null,delta:c-p};
  });
  const winners=chRes.filter(r=>(r.pct!=null&&r.pct>5)||(r.pct==null&&r.c>0))
                     .sort((a,b)=>(b.pct==null?1e9:b.pct)-(a.pct==null?1e9:a.pct));
  const losers =chRes.filter(r=>r.pct!=null&&r.pct<-5).sort((a,b)=>a.pct-b.pct);
  const chRow=r=>{
    const isNew=r.pct==null,lost=r.p>0&&r.c===0;
    const label=isNew?'新規':(lost?'消失':rpFmtP(r.pct));
    const cl=(isNew||r.pct>=0)?'up':'dn';
    return`<div class="rp-chrow"><span>${chDot(r.ch)}${r.ch}</span><span class="amt ${cl}">${label} <span style="color:var(--mu)">(${rpSgnY(r.delta)})</span></span></div>`;
  };
  html+=`<div class="card"><h3>チャネル別 勝敗（前年比 ±5%超のみ）</h3>`;
  if(!showPy){
    html+=`<div class="rp-ok">前年データがないため、チャネル別勝敗はスキップします。</div>`;
  }else if(!winners.length&&!losers.length){
    html+=`<div class="rp-ok">前年比 ±5%超で変動したチャネルはありません（全チャネル横ばい）。</div>`;
  }else{
    html+=`<div class="rp-cols">
      <div><div class="rp-sub" style="color:var(--up)">▲ 好調チャネル</div>${winners.length?winners.map(chRow).join(''):'<div class="rp-ok">該当なし</div>'}</div>
      <div><div class="rp-sub" style="color:var(--dn)">▼ 不振チャネル</div>${losers.length?losers.map(chRow).join(''):'<div class="rp-ok">該当なし</div>'}</div>
    </div>`;
  }
  html+=`<div class="rp-note">※ チャネル別売上は実測値ではなく、Daily の日次室数シェアで按分した推計値です（当年・前年とも同一方式）。</div></div>`;

  // ══════ ④ 日別の前年割れ検出（前年同月・同回数目の同曜日と売上比較） ══════
  const RP_TOPN=5;
  let shortfalls=[],noCounter=0,pyZero=0,curZero=0,cmpDays=0;
  html+=`<div class="card"><h3>日別の前年割れ（前年同曜日比・売上）</h3>`;
  if(!showPy){
    html+=`<div class="rp-ok">前年同月のデータがないため、日別の前年割れ検出はスキップします。</div>`;
  }else{
    const dim=daysInMonth(m),maxD=rpMaxDate();
    const curRev=rpDayRev(m),pyRev=rpDayRev(pm);
    const wdCount={};
    for(let i=1;i<=dim;i++){
      const ds=m+'-'+rpPad(i);
      if(ds>maxD)continue;                       // 未到来／未取込
      const g=rpDow(ds);
      wdCount[g]=(wdCount[g]||0)+1;              // 当月で g 曜日が何回目か
      const pds=rpNthWd(pm,g,wdCount[g]);        // 前年の同回数目の同曜日
      if(!pds){noCounter++;continue;}            // 前年に対応日が無い（第5週など）
      const c=curRev[ds]||0,p=pyRev[pds]||0;
      if(!(ds in curRev))curZero++;
      if(!(pds in pyRev))pyZero++;
      cmpDays++;
      if(c-p<0)shortfalls.push({ds,pds,g,c,p,diff:c-p});
    }
    shortfalls.sort((a,b)=>a.diff-b.diff);
    if(!shortfalls.length){
      html+=`<div class="rp-ok">前年同曜日を下回った日はありません（比較対象 ${cmpDays}日）。</div>`;
    }else{
      const top=shortfalls.slice(0,RP_TOPN);
      const totalShort=shortfalls.reduce((a,x)=>a+x.diff,0);
      html+=`<div class="rp-sub">前年割れ ${shortfalls.length}日／合計 <span class="dn">${rpSgnY(totalShort)}</span>（比較対象 ${cmpDays}日）</div>
      <div class="scroll-table"><table>
        <tr><th>当年</th><th>前年対応日</th><th class="num">当年売上</th><th class="num">前年売上</th><th class="num">差額</th></tr>
        ${top.map(x=>{const iw=(x.g===0||x.g===6);
          return`<tr><td style="white-space:nowrap">${x.ds.slice(5)}<span style="${iw?'color:var(--wn)':'color:var(--mu)'};margin-left:4px">(${RP_WD[x.g]})</span></td>`
          +`<td style="white-space:nowrap;color:var(--mu)">${x.pds.slice(5)}(${RP_WD[x.g]})</td>`
          +`<td class="num">${fmtY(x.c)}</td><td class="num" style="color:var(--mu)">${fmtY(x.p)}</td>`
          +`<td class="num dn">${rpSgnY(x.diff)}</td></tr>`;}).join('')}
      </table></div>`;
      if(shortfalls.length>RP_TOPN)html+=`<div class="rp-note">※ 前年割れ${shortfalls.length}日のうち、差額の大きい上位${RP_TOPN}日を表示しています。</div>`;
    }
    html+=`<div class="rp-note">※ 比較先は「前年同月の同回数目の同曜日」（例：今年の第2土曜 → 前年の第2土曜）。`
      +`予約ゼロ日は CSV に行が無いため <b>売上0円として扱います</b>（当年${curZero}日／前年${pyZero}日）。`
      +`前年に売上が無い日は差額が必ず0以上になるため、定義上ここには挙がりません。`
      +`前年に対応する回数目の曜日が存在しない日（第5週など）は比較対象外としました（${noCounter}日）。`
      +`データ最終日 ${rpMaxDate()} より後は未到来として除外しています。</div>`;
  }
  html+=`</div>`;

  // ══════ ⑤ 部屋タイプ診断（稼働率の前年割れ・連続性で3段階） ══════
  const m1=rpPrevMonth(m),m0=rpPrevMonth(m1);
  const alerts=[];let undecided=0;
  html+=`<div class="card"><h3>部屋タイプ診断（稼働率の前年割れ・連続性で3段階）</h3>`;
  if(!showPy){
    html+=`<div class="rp-ok">前年同月のデータがないため、部屋タイプ診断はスキップします。</div>`;
  }else{
    const occC=rpOccMap(m),occP=rpOccMap(pm);
    (DATA.room[m]||[]).forEach(r=>{
      const c=occC[r.name],p=occP[r.name];
      if(c==null||p==null){undecided++;return;}   // 前年に同名が無い→判定不能（drawRoomMonthly の p&& 方式）
      if(!(c<p))return;                            // 前年割れでない
      // 連続性：当月→前月→前々月 と遡り、判定不能が出た時点で打ち切る
      let streak=1;
      for(const x of [m1,m0]){const u=rpUnderPy(x,r.name);if(u===true)streak++;else break;}
      alerts.push({room:r.name,cur:c,py:p,streak,
        prev:[m1,m0].map(x=>({ym:x,cur:rpOccMap(x)[r.name],py:hasPy(x)?rpOccMap(pyMonth(x))[r.name]:undefined}))});
    });
    alerts.sort((a,b)=>(b.streak-a.streak)||((a.cur-a.py)-(b.cur-b.py)));
    if(!alerts.length){
      html+=`<div class="rp-ok">稼働率が前年を下回った部屋タイプはありません。</div>`;
    }else{
      html+=alerts.map(a=>{
        const lv=Math.min(a.streak,3);
        const tag=lv===3?'<span class="rp-lvtag rp-lv3">最強 3ヶ月連続</span>'
                :lv===2?'<span class="rp-lvtag rp-lv2">強 2ヶ月連続</span>'
                       :'<span class="rp-lvtag rp-lv1">当月のみ</span>';
        const hist=a.prev.filter(x=>x.cur!=null&&x.py!=null)
          .map(x=>`${x.ym.slice(5)}月 ${x.cur.toFixed(1)}%/前年${x.py.toFixed(1)}%`).join('、');
        return`<div class="rp-alert ${lv===3?'':lv===2?'lv2':'lv1'}">${tag}<b>${a.room}</b> — 当月稼働率 <b class="dn">${a.cur.toFixed(1)}%</b> が前年同月 ${a.py.toFixed(1)}% を <b>${(a.py-a.cur).toFixed(1)}pt</b> 下回っています。${hist?`<span style="color:var(--mu)">（${hist}）</span>`:''}</div>`;
      }).join('');
    }
    html+=`<div class="rp-note">※ 稼働率は Room タブと同一ロジック（RN ÷ 物理室数 × 当月日数）。`
      +`前年に同名の室タイプが無い月は<b>判定不能として連続カウントを打ち切ります</b>（前年割れが続いたとは見なしません）。`
      +`当月の判定不能は ${undecided}タイプでした。</div></div>`;
  }

  // ══════ ⑥ 論点リスト ══════
  const issues=[];
  const lv3=alerts.filter(a=>a.streak>=3),lv2=alerts.filter(a=>a.streak===2);
  // 最強アラート（3ヶ月連続前年割れ）を最優先
  lv3.slice(0,3).forEach(a=>issues.push(`<b>${a.room}</b> が3ヶ月連続で稼働率前年割れ（当月 ${a.cur.toFixed(1)}% ／ 前年 ${a.py.toFixed(1)}%）。最優先で販促・料金の見直しを。`));
  if(showPy){
    if(salesPct!=null&&salesPct<-5)issues.push(`売上が前年比 ${rpFmtP(salesPct)} と減少。要因の深掘りが必要。`);
    if(adrPct  !=null&&adrPct  <-5)issues.push(`ADRが前年比 ${rpFmtP(adrPct)} と低下。価格・プラン設計の見直しを検討。`);
    if(roomsPct!=null&&roomsPct<-5)issues.push(`室数が前年比 ${rpFmtP(roomsPct)} と減少。集客チャネルの強化が必要。`);
    losers.slice(0,2).forEach(r=>issues.push((r.p>0&&r.c===0)
      ?`${r.ch} が消失（前年 ${fmtY(r.p)} → 当年ゼロ）。取扱い停止か送客減かを確認。`
      :`${r.ch} が前年比 ${rpFmtP(r.pct)} と不振。${r.ch}の販売状況を確認。`));
    winners.filter(r=>r.pct==null).slice(0,1).forEach(r=>issues.push(`${r.ch} が新規稼働。伸長要因を横展開できないか確認。`));
  }
  if(shortfalls.length){
    const w=shortfalls[0];
    issues.push(`前年割れが最大の日は ${w.ds.slice(5)}(${RP_WD[w.g]})で ${rpSgnY(w.diff)}（前年 ${w.pds.slice(5)}）。同曜日の販売状況を確認。`);
  }
  lv2.slice(0,2).forEach(a=>issues.push(`${a.room} が2ヶ月連続で稼働率前年割れ（当月 ${a.cur.toFixed(1)}% ／ 前年 ${a.py.toFixed(1)}%）。早めの対策を。`));
  const shown=issues.slice(0,5);
  html+=`<div class="card"><h3>論点リスト（確認すべきこと）</h3>`;
  if(!shown.length){
    html+=`<div class="rp-ok">大きな懸念点はありません。現状の好調を維持しつつ、上振れ要因の把握を。</div>`;
  }else{
    html+=shown.map(x=>`<div class="rp-issue">${x}</div>`).join('');
    if(issues.length>shown.length)html+=`<div class="rp-note">※ 検出した論点は全${issues.length}件で、重要度の高い上位5件を表示しています。</div>`;
  }
  html+=`</div>`;

  el.innerHTML=html;
}

showTab('report',document.querySelector('.nav-tab'));
switchAllTabs(DATA.default_month);

"""

if __name__ == "__main__":
    main()
