# -*- coding: utf-8 -*-
"""宁德时代 A股(300750.SZ) vs 港股(03750.HK) 日交易数据对比分析 - 复权版
A股: 后复权(close × adj_factor)，含分红回补
港股: 不复权(无 hk_adjfactor 接口权限)，明确标注
AH溢价率: 用不复权收盘价计算(反映市场实时报价折溢价，合理)
"""
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

BASE = r"D:\Workbuddy_Projects\QT"
HKDCNY = 0.913
RED, GREEN, BLUE, ORANGE = "#E0322B", "#1AA260", "#2E7CD6", "#F5A623"


def load(path, market):
    df = pd.DataFrame(json.loads(open(path, "r", encoding="utf-8").read()))
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    for c in ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.sort_values("trade_date").reset_index(drop=True)
    df["market"] = market
    return df


def load_adj(path):
    df = pd.DataFrame(json.loads(open(path, "r", encoding="utf-8").read()))
    df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d")
    df["adj_factor"] = pd.to_numeric(df["adj_factor"], errors="coerce")
    return df[["trade_date", "adj_factor"]]


dfa = load(BASE + r"\catl_a_data.json", "A股")
dfh = load(BASE + r"\catl_h_data.json", "港股")

# A股合并复权因子，计算后复权价与后复权日涨跌幅
dfa = dfa.merge(load_adj(BASE + r"\catl_a_adjfactor.json"), on="trade_date", how="left")
dfa["adj_factor"] = dfa["adj_factor"].ffill().bfill()
dfa["hfq_close"] = dfa["close"] * dfa["adj_factor"]  # 后复权收盘价
dfa["hfq_pct"] = dfa["hfq_close"].pct_change() * 100  # 后复权日涨跌幅(剔除除息跳低)

# 识别除息事件(adj_factor跳变)
dfa["adj_prev"] = dfa["adj_factor"].shift(1)
dfa["is_ex_div"] = (dfa["adj_factor"] != dfa["adj_prev"]) & dfa["adj_prev"].notna()
ex_div_dates = dfa[dfa["is_ex_div"]][["trade_date", "adj_prev", "adj_factor"]].copy()
ex_div_dates["div_ratio"] = ex_div_dates["adj_factor"] / ex_div_dates["adj_prev"] - 1

# 港股无复权因子接口权限，保持不复权
dfh["hfq_close"] = dfh["close"]
dfh["hfq_pct"] = dfh["pct_chg"]
dfh["adj_factor"] = np.nan

# 共同交易日合并(用后复权价计算净值/涨跌幅，用不复权价计算AH溢价)
m = pd.merge(
    dfa[["trade_date", "close", "hfq_close", "hfq_pct", "pct_chg", "vol", "amount", "adj_factor"]].rename(
        columns={"close": "a_close_raw", "hfq_close": "a_close", "hfq_pct": "a_pct", "pct_chg": "a_pct_raw", "vol": "a_vol", "amount": "a_amount"}
    ),
    dfh[["trade_date", "close", "pct_chg", "vol", "amount"]].rename(
        columns={"close": "h_close", "pct_chg": "h_pct", "vol": "h_vol", "amount": "h_amount"}
    ),
    on="trade_date",
)
m["h_close_cny"] = m["h_close"] * HKDCNY
# AH溢价用不复权价(反映市场实时报价)
m["ah_premium"] = (m["a_close_raw"] / m["h_close_cny"] - 1) * 100
m.to_csv(BASE + r"\catl_ah_daily.csv", index=False, encoding="utf-8-sig")


def metrics(df, name, is_a):
    pct = df["hfq_pct"]
    close = df["hfq_close"]
    raw_close = df["close"]
    recent = df.tail(60)
    amt_div = 1e5 if is_a else 1e8
    amt_mul = 1.0 if is_a else HKDCNY
    vol_div = 100.0 if is_a else 1e4
    return dict(
        name=name,
        n=len(df),
        start=df["trade_date"].iloc[0].strftime("%Y-%m-%d"),
        end=df["trade_date"].iloc[-1].strftime("%Y-%m-%d"),
        first_close=round(close.iloc[0], 2),
        last_close=round(close.iloc[-1], 2),
        first_raw=round(raw_close.iloc[0], 2),
        last_raw=round(raw_close.iloc[-1], 2),
        total_ret=round((close.iloc[-1] / close.iloc[0] - 1) * 100, 2),
        total_ret_raw=round((raw_close.iloc[-1] / raw_close.iloc[0] - 1) * 100, 2),
        mean_pct=round(pct.dropna().mean(), 3),
        vol_full=round(pct.dropna().std() * (252 ** 0.5), 2),
        vol_recent=round(recent["hfq_pct"].dropna().std() * (252 ** 0.5), 2),
        max_up=round(pct.dropna().max(), 2),
        max_dn=round(pct.dropna().min(), 2),
        up_days=int((pct.dropna() > 0).sum()),
        dn_days=int((pct.dropna() < 0).sum()),
        avg_amt_yi=round(df["amount"].mean() / amt_div * amt_mul, 2),
        sum_amt_yi=round(df["amount"].sum() / amt_div * amt_mul, 0),
        avg_vol_wan=round(df["vol"].mean() / vol_div, 2),
    )


ma = metrics(dfa, "A股 300750.SZ (后复权)", True)
mh = metrics(dfh, "港股 03750.HK (不复权)", False)
corr = round(m["a_pct"].corr(m["h_pct"]), 4)
m["roll_corr"] = m["a_pct"].rolling(20).corr(m["h_pct"])
ah_mean = round(m["ah_premium"].mean(), 2)
ah_max = round(m["ah_premium"].max(), 2)
ah_min = round(m["ah_premium"].min(), 2)
ah_last = round(m["ah_premium"].iloc[-1], 2)
m["a_nav"] = m["a_close"] / m["a_close"].iloc[0] * 100
m["h_nav"] = m["h_close"] / m["h_close"].iloc[0] * 100

# 复权影响量化
a_div_gap = ma["total_ret"] - ma["total_ret_raw"]
n_div = len(ex_div_dates)

# ============ 图表 ============
fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=m["trade_date"], y=m["a_nav"], name="A股后复权(首日=100)", line=dict(color=RED, width=2)))
fig1.add_trace(go.Scatter(x=m["trade_date"], y=m["h_nav"], name="港股不复权(首日=100)", line=dict(color=BLUE, width=2)))
# 标注除息日
for _, r in ex_div_dates.iterrows():
    fig1.add_vline(x=r["trade_date"], line_dash="dot", line_color=ORANGE, opacity=0.5,
                   annotation_text=f"除息<br>{r['trade_date'].strftime('%m-%d')}", annotation_position="top", annotation_font_size=9, annotation_font_color=ORANGE)
fig1.update_layout(title="归一化净值走势（首日=100，橙色虚线=A股除息日）", xaxis_title="日期", yaxis_title="净值", height=440, hovermode="x unified", legend=dict(orientation="h", y=1.08))

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=m["trade_date"], y=m["ah_premium"], name="AH溢价率", line=dict(color=ORANGE, width=2), fill="tozeroy"))
fig2.add_hline(y=0, line_dash="dot", line_color="gray")
fig2.update_layout(title="AH股溢价率（用不复权价计算，反映市场实时报价折溢价）", xaxis_title="日期", yaxis_title="溢价率(%)", height=380)

xv = m["a_pct"].values
yv = m["h_pct"].values
mask = ~np.isnan(xv) & ~np.isnan(yv)
xv, yv = xv[mask], yv[mask]
b = np.polyfit(xv, yv, 1)
xs = np.linspace(xv.min(), xv.max(), 50)
fig3 = go.Figure()
fig3.add_trace(go.Scatter(x=xv, y=yv, mode="markers", marker=dict(size=5, color=BLUE, opacity=0.55), name="交易日"))
fig3.add_trace(go.Scatter(x=xs, y=np.polyval(b, xs), mode="lines", line=dict(color=RED), name=f"回归 y={b[0]:.2f}x+{b[1]:.2f}"))
fig3.update_layout(title=f"日涨跌幅相关性散点（A股用后复权日涨跌幅，港股不复权，相关系数={corr}）", xaxis_title="A股日涨跌幅(%)", yaxis_title="港股日涨跌幅(%)", height=420)

fig4 = go.Figure()
labels = ["A股(后复权)", "港股(不复权)"]
fig4.add_trace(go.Bar(x=labels, y=[ma["vol_full"], mh["vol_full"]], name="区间年化波动率(%)", marker_color=[RED, BLUE]))
fig4.add_trace(go.Bar(x=labels, y=[ma["vol_recent"], mh["vol_recent"]], name="近60日年化波动率(%)", marker_color=[ORANGE, GREEN]))
fig4.update_layout(title="波动率对比", barmode="group", height=380)

fig5 = go.Figure()
fig5.add_trace(go.Bar(x=m["trade_date"], y=m["a_amount"] / 1e5, name="A股成交额(亿元RMB)", marker_color=RED, opacity=0.6))
fig5.add_trace(go.Bar(x=m["trade_date"], y=m["h_amount"] / 1e8 * HKDCNY, name="港股成交额(亿元RMB,折算)", marker_color=BLUE, opacity=0.6))
fig5.update_layout(title="日成交额对比（统一折算为人民币亿元）", barmode="group", xaxis_title="日期", yaxis_title="成交额(亿元RMB)", height=400, legend=dict(orientation="h", y=1.08))

fig6 = go.Figure()
fig6.add_trace(go.Scatter(x=m["trade_date"], y=m["roll_corr"], name="20日滚动相关系数", line=dict(color=GREEN)))
fig6.add_hline(y=corr, line_dash="dot", line_color="gray", annotation_text=f"整体={corr}")
fig6.update_layout(title="A股(后复权)与港股(不复权)日涨跌幅 20日滚动相关系数", xaxis_title="日期", yaxis_title="相关系数", height=380, yaxis=dict(range=[-1, 1]))


def fig_html(fig):
    return pio.to_html(fig, full_html=False, include_plotlyjs="cdn")


def cls(v):
    return "up" if v > 0 else "down"


def row(d):
    return "<tr>" + "".join(f"<td>{v}</td>" for v in d) + "</tr>"


tbl_rows = "".join([
    row(["标的", ma["name"], mh["name"]]),
    row(["交易日数", ma["n"], mh["n"]]),
    row(["首日收盘(后复权)", f"{ma['first_close']}", f"{mh['first_close']}（不复权）"]),
    row(["末日收盘(后复权)", f"{ma['last_close']}", f"{mh['last_close']}（不复权）"]),
    row(["区间涨跌幅(后复权)", f"<b>{ma['total_ret']:+.2f}%</b>", f"{mh['total_ret']:+.2f}%（不复权）"]),
    row(["区间涨跌幅(不复权)", f"{ma['total_ret_raw']:+.2f}%", f"{mh['total_ret']:+.2f}%"]),
    row(["分红回补贡献", f"+{a_div_gap:.2f}个百分点", "无法获取复权因子，未回补"]),
    row(["区间内除息次数", f"{n_div}次", "无接口权限，未知"]),
    row(["日均涨跌幅", f"{ma['mean_pct']:+.3f}%", f"{mh['mean_pct']:+.3f}%"]),
    row(["区间年化波动率", f"{ma['vol_full']}%", f"{mh['vol_full']}%"]),
    row(["近60日年化波动率", f"{ma['vol_recent']}%", f"{mh['vol_recent']}%"]),
    row(["最大单日涨幅", f"{ma['max_up']:+.2f}%", f"{mh['max_up']:+.2f}%"]),
    row(["最大单日跌幅", f"{ma['max_dn']:+.2f}%", f"{mh['max_dn']:+.2f}%"]),
    row(["上涨天数 / 下跌天数", f"{ma['up_days']} / {ma['dn_days']}", f"{mh['up_days']} / {mh['dn_days']}"]),
    row(["日均成交额(亿元RMB)", f"{ma['avg_amt_yi']}", f"{mh['avg_amt_yi']}"]),
    row(["区间累计成交额(亿元RMB)", f"{ma['sum_amt_yi']:.0f}", f"{mh['sum_amt_yi']:.0f}"]),
])

# 除息事件明细
ex_div_tbl = ""
if n_div > 0:
    ex_div_tbl = '<div class="fig"><h3 style="margin:8px 0 4px;font-size:15px;color:#E0322B">A股区间内除息事件明细</h3><table><thead><tr><th>除息日</th><th>前复权因子</th><th>新复权因子</th><th>分红比例(占前日股价)</th></tr></thead><tbody>'
    for _, r in ex_div_dates.iterrows():
        ex_div_tbl += f"<tr><td>{r['trade_date'].strftime('%Y-%m-%d')}</td><td>{r['adj_prev']:.4f}</td><td>{r['adj_factor']:.4f}</td><td>+{r['div_ratio']*100:.3f}%</td></tr>"
    ex_div_tbl += "</tbody></table></div>"

conc = f"""
<h2>分析结论</h2>
<div class="warn"><b>⚠ 复权说明（重要）</b>：A股采用<b>后复权</b>价格（close × adj_factor），已回补区间内 {n_div} 次现金分红的除息跳低；港股因无 hk_adjfactor 接口权限，仍为<b>不复权</b>价格，若区间内有分红除息，港股真实涨幅会被低估。AH溢价率始终用不复权价计算（反映市场实时报价折溢价，合理）。</div>
<ol>
<li><b>港股涨幅仍显著领先A股，但A股复权后涨幅略有上调。</b>A股后复权区间涨跌幅 <span class="{cls(ma['total_ret'])}">{ma['total_ret']:+.2f}%</span>（不复权 {ma['total_ret_raw']:+.2f}%，分红回补贡献 +{a_div_gap:.2f} 个百分点）；港股不复权区间涨跌幅 <span class="{cls(mh['total_ret'])}">{mh['total_ret']:+.2f}%</span>。即便A股已复权，港股涨幅仍约为A股的 {mh['total_ret']/ma['total_ret']:.1f} 倍。</li>
<li><b>A股相对港股长期折价（A/H折价）。</b>当前AH溢价率 <span class="{cls(ah_last)}">{ah_last:+.2f}%</span>，区间均值 {ah_mean:+.2f}%，区间 [{ah_min:+.2f}%, {ah_max:+.2f}%]。这与多数A+H股"A股溢价"常态相反——港股上市定价偏高且后续上涨更猛，A股反成折价方。</li>
<li><b>港股波动率高于A股。</b>港股区间年化波动率 {mh['vol_full']}% 高于A股后复权 {ma['vol_full']}%；港股最大单日跌幅 {mh['max_dn']:+.2f}%（如4月28日-6.88%）。近期（近60日）港股波动率收敛至 {mh['vol_recent']}%，仍略高于A股 {ma['vol_recent']}%。</li>
<li><b>两市联动性较强。</b>日涨跌幅相关系数 {corr}（A股后复权 vs 港股不复权），回归斜率 {b[0]:.2f}，意味着A股每涨跌1个百分点，港股平均同向变动约 {b[0]:.2f} 个百分点。复权处理后相关性更干净（剔除A股除息日的假下跌）。</li>
<li><b>成交活跃度：A股为主上市地。</b>A股日均成交额约 {ma['avg_amt_yi']} 亿元人民币，港股约 {mh['avg_amt_yi']} 亿元人民币（折算）；港股在事件日脉冲式放量（如4月28日约85亿、5月6日约76亿人民币），反映外资博弈更激烈。</li>
<li><b>投资含义。</b>追求弹性与全球定价、可承受更高波动者可关注港股；偏好相对稳健、流动性平稳者可配置A股。当前A股折价幅度较大（{ah_last:+.2f}%），若折价收敛存在相对收益机会，但需注意港股估值高位回撤风险。</li>
</ol>
<p class="note">注①：A股后复权价 = 不复权收盘价 × 累计复权因子(adj_factor)；港股因 hk_adjfactor 接口无权限，未能复权。<br>注②：AH溢价率按近似汇率 HKDCNY={HKDCNY} 折算，用不复权价计算（反映市场实时报价）。<br>注③：数据区间 {m['trade_date'].iloc[0].strftime('%Y-%m-%d')} 至 {m['trade_date'].iloc[-1].strftime('%Y-%m-%d')}，共同交易日 {len(m)} 个。本报告仅供研究参考，不构成投资建议。</p>
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>宁德时代 A股 vs 港股 股价对比分析（复权版）</title>
<style>
body{{font-family:'Microsoft YaHei','Segoe UI',Arial,sans-serif;background:#f5f6f8;margin:0;padding:22px;color:#222}}
.wrap{{max-width:1120px;margin:0 auto}}
h1{{font-size:23px;border-left:5px solid #E0322B;padding-left:12px;margin-bottom:6px}}
.summary{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}}
.card{{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.card .k{{font-size:12px;color:#888}}.card .v{{font-size:20px;font-weight:700;margin-top:6px}}
.up{{color:#E0322B}}.down{{color:#1AA260}}
table{{border-collapse:collapse;width:100%;background:#fff;border-radius:10px;overflow:hidden;margin:12px 0;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
th,td{{border:1px solid #eef0f2;padding:9px 12px;text-align:center;font-size:13px}}
th{{background:#fafbfc;font-weight:600}}td:first-child{{text-align:left;background:#fafbfc;font-weight:600}}
.fig{{background:#fff;border-radius:10px;padding:10px 12px 4px;margin:16px 0;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
.note{{color:#999;font-size:12px;line-height:1.7;margin-top:6px}}
.conc{{background:#fff;border-radius:10px;padding:20px 24px;margin:16px 0;box-shadow:0 1px 4px rgba(0,0,0,.06);line-height:1.75;font-size:14px}}
.conc h2{{font-size:18px;margin-top:0;border-left:5px solid #2E7CD6;padding-left:10px}}
.conc li{{margin-bottom:8px}}
.warn{{background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:12px 16px;margin:10px 0 16px;font-size:13px;line-height:1.7}}
</style></head><body><div class="wrap">
<h1>宁德时代 A股 vs 港股 股价对比分析（复权版）</h1>
<p class="note">A 股 300750.SZ（<b>后复权</b>，已回补分红）｜ 港股 03750.HK（<b>不复权</b>，无 hk_adjfactor 接口权限）｜ 数据区间 {m['trade_date'].iloc[0].strftime('%Y-%m-%d')} 至 {m['trade_date'].iloc[-1].strftime('%Y-%m-%d')}，共同交易日 {len(m)} 个</p>
<div class="summary">
<div class="card"><div class="k">A股后复权涨跌幅</div><div class="v {cls(ma['total_ret'])}">{ma['total_ret']:+.2f}%</div><div class="k" style="margin-top:2px">不复权 {ma['total_ret_raw']:+.2f}%</div></div>
<div class="card"><div class="k">港股涨跌幅(不复权)</div><div class="v {cls(mh['total_ret'])}">{mh['total_ret']:+.2f}%</div><div class="k" style="margin-top:2px">未回补分红</div></div>
<div class="card"><div class="k">日涨跌幅相关系数</div><div class="v">{corr}</div><div class="k" style="margin-top:2px">A股后复权 vs 港股</div></div>
<div class="card"><div class="k">当前AH溢价率</div><div class="v {cls(ah_last)}">{ah_last:+.2f}%</div><div class="k" style="margin-top:2px">用不复权价计算</div></div>
</div>
<table>
<thead><tr><th>指标</th><th>A股 300750.SZ（后复权）</th><th>港股 03750.HK（不复权）</th></tr></thead>
<tbody>{tbl_rows}</tbody></table>
{ex_div_tbl}
<div class="fig">{fig_html(fig1)}</div>
<div class="fig">{fig_html(fig2)}</div>
<div class="fig">{fig_html(fig3)}</div>
<div class="fig">{fig_html(fig4)}</div>
<div class="fig">{fig_html(fig5)}</div>
<div class="fig">{fig_html(fig6)}</div>
<div class="conc">{conc}</div>
</div></body></html>"""

with open(BASE + r"\catl_ah_report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("=== 宁德时代 A股(后复权) vs 港股(不复权) 对比分析完成 ===")
print(f"A股后复权: {ma['first_close']:.2f} -> {ma['last_close']:.2f} ({ma['total_ret']:+.2f}%)")
print(f"A股不复权: {ma['first_raw']} -> {ma['last_raw']} ({ma['total_ret_raw']:+.2f}%)")
print(f"分红回补贡献: +{a_div_gap:.2f} 个百分点  除息次数: {n_div}")
print("除息事件:")
for _, r in ex_div_dates.iterrows():
    print(f"  {r['trade_date'].strftime('%Y-%m-%d')}: adj {r['adj_prev']:.4f} -> {r['adj_factor']:.4f} (分红比例 +{r['div_ratio']*100:.3f}%)")
print(f"港股不复权: {mh['first_close']} -> {mh['last_close']} ({mh['total_ret']:+.2f}%)  年化波动率 {mh['vol_full']}%")
print(f"日涨跌幅相关系数(A后复权 vs H不复权): {corr}  回归斜率: {b[0]:.3f}")
print(f"AH溢价率(不复权价): 均值{ah_mean:+.2f}%  当前{ah_last:+.2f}%  区间[{ah_min:+.2f}%, {ah_max:+.2f}%]")
print(f"日均成交额(亿RMB): A股{ma['avg_amt_yi']}  港股{mh['avg_amt_yi']}")
print(f"输出: catl_ah_daily.csv, catl_ah_report.html, catl_a_adjfactor.json")
