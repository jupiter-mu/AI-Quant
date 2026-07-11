# -*- coding: utf-8 -*-
"""寒武纪(688256.SH) 前复权转换脚本
原始数据来源: tushare daily (不复权)
复权因子: tushare adj_factor
事件: 2026-05-08 送转股 (adj_factor 1.0 -> 1.4912, 约10送5)
"""
import json
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

BASE = r"D:\Workbuddy_Projects\QT\task1"

# 1. 加载原始数据
raw = pd.DataFrame(json.loads(open(BASE + r"\cambricon_daily_data.json", "r", encoding="utf-8").read()))
raw["trade_date"] = pd.to_datetime(raw["trade_date"], format="%Y%m%d")
for c in ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.sort_values("trade_date").reset_index(drop=True)

# 2. 加载复权因子
adj = pd.DataFrame(json.loads(open(BASE + r"\cambricon_adjfactor.json", "r", encoding="utf-8").read()))
adj["trade_date"] = pd.to_datetime(adj["trade_date"], format="%Y%m%d")
adj["adj_factor"] = pd.to_numeric(adj["adj_factor"], errors="coerce")
adj = adj[["trade_date", "adj_factor"]]

# 3. 合并
df = raw.merge(adj, on="trade_date", how="left")
df["adj_factor"] = df["adj_factor"].ffill().bfill()

# 确定最新复权因子
adj_latest = df["adj_factor"].iloc[-1]
print(f"最新复权因子: {adj_latest}")

# 4. 识别除权事件
df["adj_prev"] = df["adj_factor"].shift(1)
df["is_ex_right"] = (df["adj_factor"] != df["adj_prev"]) & df["adj_prev"].notna()
events = df[df["is_ex_right"]][["trade_date", "adj_prev", "adj_factor"]].copy()
events["ratio_pct"] = (events["adj_factor"] / events["adj_prev"] - 1) * 100

print("除权事件:")
for _, r in events.iterrows():
    print(f"  {r['trade_date'].strftime('%Y-%m-%d')}: factor {r['adj_prev']:.4f} -> {r['adj_factor']:.4f} (+{r['ratio_pct']:.1f}%)")

# 5. 前复权: qfq = raw × adj_factor / adj_latest
for col in ["open", "high", "low", "close", "pre_close"]:
    df["qfq_" + col] = df[col] * df["adj_factor"] / adj_latest

# 6. 重新计算前复权日涨跌幅
df["qfq_pct"] = df["qfq_close"].pct_change() * 100

# 7. 生成输出数据：保留原始字段名，值替换为前复权
out = df[["trade_date", "qfq_open", "qfq_high", "qfq_low", "qfq_close",
           "qfq_pre_close", "qfq_pct", "vol", "amount", "adj_factor"]].copy()
out.columns = ["trade_date", "open", "high", "low", "close",
               "pre_close", "pct_chg", "vol", "amount", "adj_factor"]
out["trade_date"] = out["trade_date"].dt.strftime("%Y%m%d")
out["change"] = out["close"] - out["pre_close"]
for c in ["open", "high", "low", "close", "pre_close", "change", "pct_chg", "vol", "amount"]:
    out[c] = round(out[c], 4)

# 保存 JSON（按 trade_date 降序，和原始保持一致）
out_desc = out.sort_values("trade_date", ascending=False).reset_index(drop=True)
json_str = out_desc.to_json(orient="records", force_ascii=False)
# Parse and re-serialize to get clean JSON without escaping
out_json = json.loads(json_str)
with open(BASE + r"\cambricon_daily_data_qfq.json", "w", encoding="utf-8") as f:
    json.dump(out_json, f, ensure_ascii=False)

# 保存 CSV（按时间正序）
out_asc = out.sort_values("trade_date").reset_index(drop=True)
out_asc.to_csv(BASE + r"\cambricon_daily_data_qfq.csv", index=False, encoding="utf-8-sig")

# ============ K线图 ============
df_plot = out_asc.copy()
df_plot["trade_date"] = pd.to_datetime(df_plot["trade_date"], format="%Y%m%d")

RED, GREEN = "#E0322B", "#1AA260"
colors = [RED if df_plot["close"].iloc[i] >= df_plot["open"].iloc[i] else GREEN for i in range(len(df_plot))]

fig = go.Figure(data=go.Candlestick(
    x=df_plot["trade_date"],
    open=df_plot["open"], high=df_plot["high"], low=df_plot["low"], close=df_plot["close"],
    increasing=dict(line_color=RED, fillcolor=RED),
    decreasing=dict(line_color=GREEN, fillcolor=GREEN),
    name="K线(前复权)",
))

# 标注除权日
for _, r in events.iterrows():
    fig.add_vline(x=r["trade_date"], line_dash="dot", line_color="#F5A623", opacity=0.6,
                  annotation_text=f"除权 {r['trade_date'].strftime('%m-%d')}", annotation_position="top",
                  annotation_font_size=9, annotation_font_color="#F5A623")

fig.update_layout(
    title="寒武纪 688256.SH 日K线（前复权）",
    xaxis_title="日期", yaxis_title="前复权价格(元)",
    xaxis_rangeslider_visible=False,
    height=550,
    hovermode="x unified",
)
fig.update_xaxes(showgrid=False)
fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>寒武纪 688256.SH 日K线（前复权）</title>
<style>
body{{font-family:'Microsoft YaHei','Segoe UI',Arial,sans-serif;background:#f5f6f8;margin:0;padding:20px;color:#222}}
.wrap{{max-width:1100px;margin:0 auto}}
h1{{font-size:22px;border-left:5px solid #E0322B;padding-left:12px;margin-bottom:8px}}
.warn{{background:#fff8e1;border:1px solid #ffe082;border-radius:8px;padding:12px 16px;margin:10px 0 16px;font-size:13px;line-height:1.7}}
.info{{color:#666;font-size:13px;margin:6px 0 12px}}
.fig{{background:#fff;border-radius:10px;padding:10px 12px 4px;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
table{{border-collapse:collapse;width:100%;background:#fff;border-radius:10px;overflow:hidden;margin:12px 0;box-shadow:0 1px 4px rgba(0,0,0,.06)}}
th,td{{border:1px solid #eef0f2;padding:9px 12px;text-align:center;font-size:13px}}
th{{background:#fafbfc}}
</style></head><body><div class="wrap">
<h1>寒武纪 688256.SH 日K线（前复权）</h1>
<div class="warn"><b>复权说明</b><br>
区间内存在 <b>1 次除权事件</b>（2026-05-08，送转股约 10送5）。原数据为 <b>不复权</b> 价格，除权日会出现约 -33% 的假跌幅。<br>
本图表采用 <b>前复权</b> 处理：除权日之前所有价格按复权因子同比缩小，使价格序列保持连续。<br>
<b>前复权公式</b>：qfq_price = raw_price × adj_factor / adj_factor_latest (={adj_latest})&emsp;|&emsp;vol 和 amount 未调整（成交量和成交额保持原始值）。</div>
<p class="info">数据区间: {df_plot['trade_date'].iloc[0].strftime('%Y-%m-%d')} 至 {df_plot['trade_date'].iloc[-1].strftime('%Y-%m-%d')}，共 {len(df_plot)} 个交易日</p>
<table><thead><tr><th>除权日</th><th>旧复权因子</th><th>新复权因子</th><th>变动比例</th></tr></thead><tbody>
{"".join(f"<tr><td>{r['trade_date'].strftime('%Y-%m-%d')}</td><td>{r['adj_prev']:.4f}</td><td>{r['adj_factor']:.4f}</td><td>+{r['ratio_pct']:.1f}%</td></tr>" for _, r in events.iterrows())}
</tbody></table>
<p class="info">前复权后：首日收盘 {df_plot['close'].iloc[0]:.2f} 元 → 末日收盘 {df_plot['close'].iloc[-1]:.2f} 元，区间涨跌幅 <b style="color:{'#E0322B' if df_plot['close'].iloc[-1] >= df_plot['close'].iloc[0] else '#1AA260'}">{((df_plot['close'].iloc[-1] / df_plot['close'].iloc[0] - 1) * 100):+.2f}%</b></p>
<div class="fig">{pio.to_html(fig, full_html=False, include_plotlyjs="cdn")}</div>
</div></body></html>"""

with open(BASE + r"\cambricon_kline_qfq.html", "w", encoding="utf-8") as f:
    f.write(html)

# 也更新原文件
with open(BASE + r"\cambricon_kline.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"=== 寒武纪前复权转换完成 ===")
print(f"原始首日(不复权): {raw['close'].iloc[0]:.2f} -> 末日: {raw['close'].iloc[-1]:.2f}")
print(f"前复权首日: {df_plot['close'].iloc[0]:.2f} -> 末日: {df_plot['close'].iloc[-1]:.2f}")
print(f"前复权区间涨跌幅: {((df_plot['close'].iloc[-1] / df_plot['close'].iloc[0] - 1) * 100):+.2f}%")
print(f"输出: cambricon_daily_data_qfq.json, cambricon_daily_data_qfq.csv, cambricon_kline_qfq.html")
