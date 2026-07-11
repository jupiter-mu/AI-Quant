"""
海龟交易策略交互式看板生成器 v1
================================
唐奇安通道突破 | ATR动态仓位 | 2N止损 | 金字塔加仓
"""
import json, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "task3_dual_ma", "data")

STOCKS = [
    {"code": "688256", "name": "寒武纪", "file": "688256_daily_qfq.json"},
    {"code": "300750", "name": "宁德时代", "file": "300750_daily_qfq.json"},
    {"code": "601398", "name": "工商银行", "file": "601398_daily_qfq.json"},
    {"code": "600030", "name": "中信证券", "file": "600030_daily_qfq.json"},
    {"code": "300274", "name": "阳光电源", "file": "300274_daily_qfq.json"},
]

def load_stock_data(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
    for row in data:
        for col in ["open_qfq", "high_qfq", "low_qfq", "close_qfq", "vol"]:
            if col in row: row[col] = float(row[col]) if row[col] is not None else None
    data.sort(key=lambda x: x["trade_date"])
    return data

def load_bond_yield(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path): return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def generate_html():
    print("加载股票数据...")
    all_data = {}
    for s in STOCKS:
        d = load_stock_data(s["file"])
        if d: all_data[s["code"]] = d
        print(f"  {s['name']}({s['code']}): {len(d)} 行")

    print("加载国债收益率...")
    bond_1y = load_bond_yield("bond_yield_1y.json")
    bond_2y = load_bond_yield("bond_yield_2y.json")
    print(f"  1年期: {len(bond_1y)} 条, 2年期: {len(bond_2y)} 条")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>task4_turtle — 海龟交易策略看板</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; height: 100vh; overflow: hidden; background: #f5f4f0; color: #2c2c2a; }}
:root {{ --up: #cc0000; --dn: #009966; --warn: #ef9f27; --blue: #378add; }}

.sidebar {{
  width: 340px; min-width: 340px; background: #fff; border-right: 0.5px solid #e0ded6;
  display: flex; flex-direction: column; overflow-y: auto; padding: 16px 14px; gap: 8px;
}}
.sidebar h2 {{ font-size: 16px; font-weight: 500; color: var(--up); margin-bottom: 2px; }}
.sidebar h3 {{ font-size: 12px; font-weight: 500; color: #5f5e5a; margin-bottom: 2px; }}
.sidebar select, .sidebar input[type="number"] {{
  width: 100%; padding: 5px 8px; border: 0.5px solid #d3d1c7; border-radius: 6px; font-size: 12px; font-family: inherit;
}}
.sidebar button {{
  width: 100%; padding: 9px; background: var(--up); color: #fff; border: none; border-radius: 8px;
  font-size: 13px; font-weight: 500; cursor: pointer;
}}
.sidebar button:hover {{ background: #a30000; }}
.slider-row {{ display: flex; align-items: center; gap: 4px; margin-bottom: 3px; }}
.slider-row input[type="range"] {{ flex: 1; min-width: 0; }}
.slider-row input[type="number"] {{ width: 44px; padding: 3px 4px; font-size: 12px; text-align: center; }}
.slider-row span {{ font-size: 11px; font-weight: 500; min-width: 28px; text-align: center; }}
.param-display {{ font-size: 10px; color: #888780; margin-top: 1px; }}
.section-div {{ border-top: 0.5px solid #e0ded6; padding-top: 8px; margin-top: 4px; }}
.mode-tabs {{ display: flex; gap: 4px; }}
.mode-tabs button {{
  flex: 1; padding: 6px 4px; font-size: 11px; background: #f1efe8; color: #5f5e5a;
  border: 0.5px solid #d3d1c7; border-radius: 6px; cursor: pointer;
}}
.mode-tabs button.active {{ background: var(--up); color: #fff; border-color: var(--up); }}
.quality-card {{ background: #f8f8f6; border-radius: 8px; padding: 8px 10px; font-size: 10px; line-height: 1.6; border: 0.5px solid #e0ded6; max-height: 140px; overflow-y: auto; }}

.main {{ flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 16px; gap: 10px; }}
.header-card {{
  background: linear-gradient(135deg, #fef0f0 0%, #fff 100%);
  border: 0.5px solid #f5c4b3; border-radius: 10px; padding: 12px 18px;
}}
.header-card h1 {{ font-size: 18px; font-weight: 500; color: var(--up); margin-bottom: 4px; }}
.header-card .tagline {{ font-size: 12px; color: #5f5e5a; line-height: 1.6; }}
.strategy-box {{ background: #fff; border: 0.5px solid #e0ded6; border-radius: 10px; padding: 12px 16px; font-size: 12px; line-height: 1.7; }}
.strategy-box h3 {{ font-size: 13px; font-weight: 500; color: #2c2c2a; margin-bottom: 4px; }}
.metrics-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }}
.metric-card {{ background: #fff; border-radius: 8px; border: 0.5px solid #e0ded6; padding: 8px 10px; }}
.metric-card .label {{ font-size: 10px; color: #888780; margin-bottom: 1px; }}
.metric-card .value {{ font-size: 17px; font-weight: 500; }}
.metric-card .formula {{ font-size: 9px; color: #b4b2a9; margin-top: 1px; font-family: monospace; white-space: nowrap; }}
.chart-card {{ background: #fff; border-radius: 10px; border: 0.5px solid #e0ded6; padding: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.03); transition: box-shadow 0.2s; margin-bottom: 12px; }}
.chart-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.07); }}
.chart-card h3 {{ font-size: 13px; font-weight: 500; color: #2c2c2a; margin-bottom: 6px; padding-left: 4px; border-left: 3px solid var(--up); }}
.comp-card {{ background: #fff; border-radius: 10px; border: 0.5px solid #e0ded6; padding: 10px; }}
.comp-card h3 {{ font-size: 13px; font-weight: 500; margin-bottom: 6px; }}
.comp-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
.comp-table th, .comp-table td {{ padding: 5px 8px; text-align: right; border-bottom: 0.5px solid #e0ded6; }}
.comp-table th {{ background: #f8f8f6; font-weight: 500; color: #5f5e5a; white-space: nowrap; }}
.comp-table td:first-child, .comp-table th:first-child {{ text-align: left; }}
.trade-table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
.trade-table th, .trade-table td {{ padding: 4px 6px; text-align: right; border-bottom: 0.5px solid #e0ded6; }}
.trade-table th {{ background: #f8f8f6; font-weight: 500; color: #5f5e5a; }}
.trade-table td:first-child, .trade-table th:first-child {{ text-align: left; }}
.summary-box {{ background: #fff; border: 0.5px solid #e0ded6; border-radius: 10px; padding: 14px 18px; font-size: 12px; line-height: 1.8; }}
.summary-box h3 {{ font-size: 14px; font-weight: 500; color: var(--up); margin-bottom: 8px; }}
.summary-box h4 {{ font-size: 12px; font-weight: 500; color: #5f5e5a; margin: 10px 0 4px; }}
</style>
</head>
<body>

<div class="sidebar">
  <h2>海龟交易策略看板</h2>
  <div class="mode-tabs">
    <button class="active" onclick="switchMode('single')" id="btnSingle">单策略</button>
    <button onclick="switchMode('multiParam')" id="btnMultiParam">多参数对比</button>
    <button onclick="switchMode('multiStock')" id="btnMultiStock">多股票对比</button>
  </div>

  <div id="stockSelectWrap">
    <h3>选择标的</h3>
    <select id="stockSelect" onchange="runAll()"></select>
  </div>

  <div class="section-div">
    <h3>◆ 通道参数</h3>
    <h3>入场通道周期</h3>
    <select id="entryPeriod" onchange="runAll()">
      <option value="20" selected>20 日（系统一）</option>
      <option value="55">55 日（系统二）</option>
    </select>
    <h3 style="margin-top:6px">退出通道周期</h3>
    <select id="exitPeriod" onchange="runAll()">
      <option value="10" selected>10 日（系统一）</option>
      <option value="20">20 日（系统二）</option>
    </select>
    <h3 style="margin-top:6px">ATR 计算周期</h3>
    <div class="slider-row">
      <input type="range" id="atrPeriod_r" min="5" max="60" value="20" oninput="syncSR('atrPeriod');runAll()">
      <input type="number" id="atrPeriod" min="5" max="60" value="20" onchange="syncSI('atrPeriod');runAll()">
      <span>日</span>
    </div>
  </div>

  <div class="section-div">
    <h3>◆ 风险管理</h3>
    <h3>单笔风险上限 (%)</h3>
    <input type="number" id="riskPct" value="2" step="0.5" min="0.5" max="10">
    <div class="param-display">每笔交易最大亏损占总资金比例</div>
    <h3 style="margin-top:6px">止损倍数 (×ATR)</h3>
    <div class="slider-row">
      <input type="range" id="stopMult_r" min="0.5" max="5" step="0.1" value="2.0" oninput="syncSR('stopMult');runAll()">
      <input type="number" id="stopMult" min="0.5" max="5" step="0.1" value="2.0" onchange="syncSI('stopMult');runAll()">
      <span>N</span>
    </div>
    <h3 style="margin-top:6px">加仓间距 (×ATR)</h3>
    <div class="slider-row">
      <input type="range" id="addSpacing_r" min="0.1" max="2" step="0.1" value="0.5" oninput="syncSR('addSpacing');runAll()">
      <input type="number" id="addSpacing" min="0.1" max="2" step="0.1" value="0.5" onchange="syncSI('addSpacing');runAll()">
      <span>N</span>
    </div>
    <h3 style="margin-top:6px">最大加仓单位</h3>
    <input type="number" id="maxUnits" value="4" step="1" min="1" max="10">
    <h3 style="margin-top:6px">最大仓位比例 (%)</h3>
    <input type="number" id="maxPosPct" value="80" step="5" min="10" max="100">
  </div>

  <div class="section-div">
    <h3>◆ 交易成本</h3>
    <h3>佣金 (%)</h3>
    <input type="number" id="commission" value="0.03" step="0.005" min="0" max="1">
    <h3 style="margin-top:6px">滑点 (%)</h3>
    <input type="number" id="slippage" value="0.01" step="0.005" min="0" max="0.5">
    <h3 style="margin-top:6px">初始资金 (万元)</h3>
    <input type="number" id="capital" value="100" step="10" min="1" max="10000">
  </div>

  <div class="section-div">
    <h3>◆ 回测设置</h3>
    <h3>回测区间</h3>
    <select id="btRange" onchange="runAll()">
      <option value="252">近 1 年（252 交易日）</option>
      <option value="504" selected>近 2 年（504 交易日）</option>
      <option value="0">全部数据</option>
    </select>
  </div>

  <button onclick="runAll()">运行回测</button>
  <div id="qualityPanel" class="quality-card" style="display:none"></div>
</div>

<div class="main" id="mainContent">
  <div class="header-card">
    <h1>海龟交易策略看板</h1>
    <div class="tagline" id="headerInfo"></div>
  </div>
  <div class="strategy-box" id="strategyIntro"></div>
  <div id="metricsBox"></div>
  <div id="contentArea"></div>
  <div id="compareArea" style="display:none"></div>
  <div class="summary-box" id="summaryBox"></div>
</div>

<script>
const STOCKS = {json.dumps(STOCKS, ensure_ascii=False)};
const ALL_DATA = {json.dumps(all_data, ensure_ascii=False)};
const BOND_1Y = {json.dumps(bond_1y, ensure_ascii=False)};
const BOND_2Y = {json.dumps(bond_2y, ensure_ascii=False)};

let gMode='single', gCode='';
let gEntryPeriod=20, gExitPeriod=10, gAtrPeriod=20;
let gRiskPct=2, gStopMult=2.0, gAddSpacing=0.5, gMaxUnits=4, gMaxPosPct=80;
let gComm=0.0003, gSlip=0.0001, gCap=1000000, gBtRange=504;

// ====== Slider <-> Number Sync ======
function syncSR(id) {{
  let n = document.getElementById(id), r = document.getElementById(id+'_r');
  n.value = r.value;
}}
function syncSI(id) {{
  let n = document.getElementById(id), r = document.getElementById(id+'_r');
  let v = parseFloat(n.value)||1;
  n.value = v; r.value = v;
}}

function readParams() {{
  gEntryPeriod = parseInt(document.getElementById('entryPeriod').value)||20;
  gExitPeriod = parseInt(document.getElementById('exitPeriod').value)||10;
  gAtrPeriod = parseInt(document.getElementById('atrPeriod').value)||20;
  gRiskPct = parseFloat(document.getElementById('riskPct').value)||2;
  gStopMult = parseFloat(document.getElementById('stopMult').value)||2.0;
  gAddSpacing = parseFloat(document.getElementById('addSpacing').value)||0.5;
  gMaxUnits = parseInt(document.getElementById('maxUnits').value)||4;
  gMaxPosPct = parseFloat(document.getElementById('maxPosPct').value)||80;
  gComm = parseFloat(document.getElementById('commission').value)/100||0.0003;
  gSlip = parseFloat(document.getElementById('slippage').value)/100||0.0001;
  gCap = parseFloat(document.getElementById('capital').value)*10000||1000000;
  gBtRange = parseInt(document.getElementById('btRange').value)||504;
}}

// ====== Risk-free rate lookup ======
function getRiskFree(dateStr, range) {{
  let key = dateStr.slice(0,4)+'-'+dateStr.slice(4,6)+'-'+dateStr.slice(6,8);
  let bondData = (range <= 252) ? BOND_1Y : BOND_2Y;
  if (bondData[key] !== undefined) return bondData[key];
  let keys = Object.keys(bondData).sort();
  let best = null;
  for (let k of keys) {{ if (k <= key) best = k; else break; }}
  if (best) return bondData[best];
  return 2;
}}

// ====== Data Quality ======
function qualityCheck(data) {{
  let n=data.length, missing=[], ohlcOk=true, dateGaps=0, adjEvents=0, closes=[];
  for(let i=0;i<n;i++){{
    let r=data[i];
    if(r.open_qfq===null||r.close_qfq===null) missing.push(r.trade_date);
    if(r.high_qfq<Math.max(r.open_qfq,r.close_qfq)) ohlcOk=false;
    if(r.low_qfq>Math.min(r.open_qfq,r.close_qfq)) ohlcOk=false;
    closes.push(r.close_qfq||0);
  }}
  for(let i=1;i<n;i++){{
    let d1=data[i-1].trade_date,d2=data[i].trade_date;
    let diff=(new Date(d2.slice(0,4),d2.slice(4,6)-1,d2.slice(6,8))-new Date(d1.slice(0,4),d1.slice(4,6)-1,d1.slice(6,8)))/86400000;
    if(diff>3) dateGaps++;
  }}
  try {{ for(let i=1;i<n;i++) if(data[i].adj_factor&&data[i-1].adj_factor&&Math.abs(data[i].adj_factor-data[i-1].adj_factor)>0.001) adjEvents++; }} catch(e){{}}
  let cm=closes.reduce((a,b)=>a+b,0)/n;
  let cs=Math.sqrt(closes.reduce((s,c)=>s+(c-cm)**2,0)/n);
  let rets=[];
  for(let i=1;i<n;i++) if(closes[i-1]) rets.push((closes[i]-closes[i-1])/closes[i-1]);
  let rv=rets.length?Math.sqrt(rets.reduce((s,r)=>s+r*r,0)/rets.length)*Math.sqrt(252)*100:0;
  return {{rows:n, dr:data[0].trade_date+'~'+data[n-1].trade_date,
    ms:missing.length?missing.length+'处':'无', oh:ohlcOk?'通过':'异常', dg:dateGaps, ae:adjEvents, cm:cm.toFixed(1), cs:cs.toFixed(1), rv:rv.toFixed(1)}};
}}

// ====== Donchian Channel ======
function calcDonchian(data, entryPeriod, exitPeriod) {{
  let n = data.length;
  let entryUpper = new Array(n).fill(null);
  let entryLower = new Array(n).fill(null);
  let exitUpper = new Array(n).fill(null);
  let exitLower = new Array(n).fill(null);
  for (let i = entryPeriod; i < n; i++) {{
    let hi = -Infinity, lo = Infinity;
    for (let j = i - entryPeriod; j < i; j++) {{
      if (data[j].high_qfq > hi) hi = data[j].high_qfq;
      if (data[j].low_qfq < lo) lo = data[j].low_qfq;
    }}
    entryUpper[i] = hi;
    entryLower[i] = lo;
  }}
  for (let i = exitPeriod; i < n; i++) {{
    let hi = -Infinity, lo = Infinity;
    for (let j = i - exitPeriod; j < i; j++) {{
      if (data[j].high_qfq > hi) hi = data[j].high_qfq;
      if (data[j].low_qfq < lo) lo = data[j].low_qfq;
    }}
    exitUpper[i] = hi;
    exitLower[i] = lo;
  }}
  return {{entryUpper, entryLower, exitUpper, exitLower}};
}}

// ====== ATR Calculation ======
function calcATR(data, period) {{
  let n = data.length;
  let tr = new Array(n).fill(null);
  let atr = new Array(n).fill(null);
  // Step 1: True Range
  for (let i = 0; i < n; i++) {{
    if (i === 0) {{
      tr[i] = data[i].high_qfq - data[i].low_qfq;
    }} else {{
      let h = data[i].high_qfq, l = data[i].low_qfq, pc = data[i-1].close_qfq;
      tr[i] = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
    }}
  }}
  // Step 2: EMA smoothing (Wilder's method)
  // Initial ATR = SMA of first 'period' TRs
  if (n >= period) {{
    let sum = 0;
    for (let i = 0; i < period; i++) sum += tr[i];
    atr[period - 1] = sum / period;
    for (let i = period; i < n; i++) {{
      atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period;
    }}
  }}
  return atr;
}}

// ====== Signal Generation + Backtest ======
function runTurtleBT(data, entryPeriod, exitPeriod, atrPeriod, riskPct, stopMult, addSpacing, maxUnits, maxPosPct, comm, slip, cap, btStartIdx) {{
  let n = data.length;
  let dc = calcDonchian(data, entryPeriod, exitPeriod);
  let atr = calcATR(data, atrPeriod);

  let trades = [];
  let pos = 0;          // 0=空仓, >0=持仓单位数
  let cash = cap;
  let shares = 0;       // 总持仓股数
  let units = [];       // 每个单位的 price/shares/date
  let stopPrice = null;  // 当前止损价（固定，加仓时上移）
  let lastBuyPrice = 0;  // 最近一次买入价（用于加仓判断）
  let signalDayAtr = 0;  // 信号确认日的ATR（用于次日执行时计算仓位）
  let pendingBuy = false;
  let pendingAdd = false;
  let pendingExit = false;

  let nav = new Array(n).fill(0);
  let warmupEnd = Math.max(entryPeriod, atrPeriod);

  // Before backtest start, NAV = cash
  for (let i = 0; i < btStartIdx; i++) nav[i] = cap;

  for (let i = btStartIdx; i < n; i++) {{
    let r = data[i];
    let op = r.open_qfq, cp = r.close_qfq, hp = r.high_qfq, lp = r.low_qfq;
    let buyRate = 1 + comm + slip;
    let sellRate = 1 - comm - slip - 0.0005; // 印花税0.05%

    // === Step 1: Execute pending trades at open ===
    if (pendingBuy && op > 0) {{
      // Check for limit-up (can't buy)
      let isLimitUp = (hp === lp && lp === op && op >= cp * 0.999);
      if (!isLimitUp) {{
        let buyPrice = op;
        let riskAmount = cap * riskPct / 100;
        let unitShares = Math.floor(riskAmount / (stopMult * signalDayAtr) / 100) * 100;
        let maxShares = Math.floor(cap * maxPosPct / 100 / (buyPrice * buyRate) / 100) * 100;
        if (unitShares > maxShares) unitShares = maxShares;
        if (unitShares >= 100 && signalDayAtr > 0) {{
          let cost = unitShares * buyPrice * buyRate;
          if (cost <= cash) {{
            cash -= cost;
            shares += unitShares;
            units.push({{price: buyPrice, shares: unitShares, date: r.trade_date}});
            pos = 1;
            lastBuyPrice = buyPrice;
            stopPrice = buyPrice - stopMult * signalDayAtr;
          }}
        }}
      }}
      pendingBuy = false;
    }}

    if (pendingAdd && op > 0 && pos > 0 && units.length < maxUnits) {{
      let buyPrice = op;
      let riskAmount = cap * riskPct / 100;
      let unitShares = Math.floor(riskAmount / (stopMult * signalDayAtr) / 100) * 100;
      let currentVal = shares * cp;
      let maxShares = Math.floor(cap * maxPosPct / 100 / (buyPrice * buyRate) / 100) * 100;
      let remainingShares = Math.max(0, maxShares - shares);
      if (unitShares > remainingShares) unitShares = remainingShares;
      if (unitShares >= 100 && signalDayAtr > 0) {{
        let cost = unitShares * buyPrice * buyRate;
        if (cost <= cash) {{
          cash -= cost;
          shares += unitShares;
          units.push({{price: buyPrice, shares: unitShares, date: r.trade_date}});
          lastBuyPrice = buyPrice;
          stopPrice = buyPrice - stopMult * signalDayAtr;
        }}
      }}
      pendingAdd = false;
    }}

    if (pendingExit && pos > 0 && op > 0) {{
      let sellPrice = op;
      let proceeds = shares * sellPrice * sellRate;
      let totalCost = units.reduce((s, u) => s + u.shares * u.price * buyRate, 0);
      let net = proceeds - totalCost;
      let pnlPct = (net / totalCost) * 100;
      let entryDate = units[0].date;
      let holdingDays = countTradingDays(data, entryDate, r.trade_date);
      trades.push({{
        ed: entryDate, xd: r.trade_date, ep: units[0].price.toFixed(2),
        xp: sellPrice.toFixed(2), sh: shares, units: units.length, hd: holdingDays,
        net: Math.round(net), pp: pnlPct.toFixed(1), exitType: '通道退出'
      }});
      cash += proceeds;
      shares = 0; pos = 0; units = []; stopPrice = null; lastBuyPrice = 0;
      pendingExit = false;
    }}

    // === Step 2: Check stop-loss (intraday, same-day execution) ===
    if (pos > 0 && stopPrice !== null && lp <= stopPrice) {{
      let execPrice = Math.max(stopPrice, op); // gap-down: use open
      if (op < stopPrice) execPrice = op;
      let proceeds = shares * execPrice * sellRate;
      let totalCost = units.reduce((s, u) => s + u.shares * u.price * buyRate, 0);
      let net = proceeds - totalCost;
      let pnlPct = (net / totalCost) * 100;
      let entryDate = units[0].date;
      let holdingDays = countTradingDays(data, entryDate, r.trade_date);
      trades.push({{
        ed: entryDate, xd: r.trade_date, ep: units[0].price.toFixed(2),
        xp: execPrice.toFixed(2), sh: shares, units: units.length, hd: holdingDays,
        net: Math.round(net), pp: pnlPct.toFixed(1), exitType: '止损平仓'
      }});
      cash += proceeds;
      shares = 0; pos = 0; units = []; stopPrice = null; lastBuyPrice = 0;
    }}

    // === Step 3: Check exit signal (close-confirmed, next-day execution) ===
    if (pos > 0 && dc.exitLower[i] !== null && cp < dc.exitLower[i]) {{
      pendingExit = true;
    }}

    // === Step 4: Check entry signal (close-confirmed, next-day execution) ====
    if (pos === 0 && dc.entryUpper[i] !== null && atr[i] !== null && cp > dc.entryUpper[i]) {{
      pendingBuy = true;
      signalDayAtr = atr[i];
    }}

    // === Step 5: Check add signal (close-confirmed, next-day execution) ===
    if (pos > 0 && units.length < maxUnits && atr[i] !== null && lastBuyPrice > 0) {{
      if (cp >= lastBuyPrice + addSpacing * atr[i]) {{
        pendingAdd = true;
        signalDayAtr = atr[i];
      }}
    }}

    // === Step 6: Calculate NAV ===
    nav[i] = cash + shares * cp;
  }}

  // Close any remaining position at last close
  if (pos > 0) {{
    let lastIdx = n - 1;
    let cp = data[lastIdx].close_qfq;
    let sellRate = 1 - gComm - gSlip - 0.0005;
    let proceeds = shares * cp * sellRate;
    let buyRate = 1 + gComm + gSlip;
    let totalCost = units.reduce((s, u) => s + u.shares * u.price * buyRate, 0);
    let net = proceeds - totalCost;
    let pnlPct = (net / totalCost) * 100;
    let entryDate = units[0].date;
    let holdingDays = countTradingDays(data, entryDate, data[lastIdx].trade_date);
    trades.push({{
      ed: entryDate, xd: data[lastIdx].trade_date, ep: units[0].price.toFixed(2),
      xp: cp.toFixed(2), sh: shares, units: units.length, hd: holdingDays,
      net: Math.round(net), pp: pnlPct.toFixed(1), exitType: '期末平仓'
    }});
    cash += proceeds;
    nav[lastIdx] = cash;
    shares = 0; pos = 0;
  }}

  // Buy-hold benchmark
  let bhShares = Math.floor((cap * maxPosPct / 100) / (data[btStartIdx].open_qfq * (1 + comm + slip)) / 100) * 100;
  let bhCost = bhShares * data[btStartIdx].open_qfq * (1 + comm + slip);
  let bhCash = cap - bhCost;
  let bhNav = new Array(n).fill(0);
  for (let i = 0; i < btStartIdx; i++) bhNav[i] = cap;
  for (let i = btStartIdx; i < n; i++) bhNav[i] = bhCash + bhShares * data[i].close_qfq;

  let dcFull = dc;
  let atrFull = atr;
  return {{trades, nav, bhNav, fn: nav[n-1], dc: dcFull, atr: atrFull}};
}}

function countTradingDays(data, dateFrom, dateTo) {{
  let count = 0;
  for (let r of data) {{
    if (r.trade_date >= dateFrom && r.trade_date <= dateTo) count++;
  }}
  return count;
}}

// ====== Metrics ======
function calcMetrics(bt, cap, startDate, range, btStartIdx) {{
  let nv = bt.nav, t = bt.trades, n = nv.length;
  let btDays = n - btStartIdx;  // 实际回测天数
  let y = btDays / 252;          // 回测年数
  let tr = (bt.fn / cap - 1) * 100;
  let ar = (Math.pow(bt.fn / cap, 1 / Math.max(y, 0.01)) - 1) * 100;
  let pk = nv[btStartIdx], mdd = 0;
  for (let i = btStartIdx + 1; i < n; i++) {{
    if (nv[i] > pk) pk = nv[i];
    let dd = (pk - nv[i]) / pk * 100;
    if (dd > mdd) mdd = dd;
  }}
  let w = t.filter(x => x.net > 0), l = t.filter(x => x.net <= 0);
  let wr = t.length ? (w.length / t.length * 100) : 0;
  let aw = w.length ? w.reduce((s, x) => s + x.net, 0) / w.length : 0;
  let al = l.length ? Math.abs(l.reduce((s, x) => s + Math.abs(x.net), 0) / l.length) : 1;
  let plr = al > 0 ? aw / al : 0;
  let dr = [];
  for (let i = btStartIdx + 1; i < n; i++) if (nv[i-1] > 0) dr.push((nv[i] - nv[i-1]) / nv[i-1]);
  let rs = dr.length ? Math.sqrt(dr.reduce((s, r) => s + r * r, 0) / dr.length) * Math.sqrt(252) * 100 : 0;
  let rf = getRiskFree(startDate, range);
  let sh = rs > 0 ? (ar - rf) / rs : 0;
  let bhf = bt.bhNav[n-1], bhr = (bhf / cap - 1) * 100, ebh = tr - bhr;
  let ah = t.length ? t.reduce((s, x) => s + x.hd, 0) / t.length : 0;
  // Max consecutive losses
  let maxConsecLoss = 0, curConsec = 0;
  for (let x of t) {{
    if (x.net <= 0) {{ curConsec++; if (curConsec > maxConsecLoss) maxConsecLoss = curConsec; }}
    else curConsec = 0;
  }}
  let stopCount = t.filter(x => x.exitType === '止损平仓').length;
  return {{
    tr: tr.toFixed(2), ar: ar.toFixed(2), mdd: mdd.toFixed(2), wr: wr.toFixed(1),
    plr: plr.toFixed(2), sh: sh.toFixed(2), ebh: ebh.toFixed(2), bhr: bhr.toFixed(2),
    tt: t.length, ah: ah.toFixed(0), rs: rs.toFixed(1), mcl: maxConsecLoss,
    rf: rf.toFixed(2), sc: stopCount
  }};
}}

function fmtd(d) {{ return d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6,8); }}
function upc(v) {{ return v > 0 ? '#cc0000' : '#009966'; }}
function fmt(v, p) {{ return (p && v > 0 ? '+' : '') + v; }}

// ====== Main Run ======
function init() {{
  const s1 = document.getElementById('stockSelect');
  STOCKS.forEach(s => {{ if (ALL_DATA[s.code]) {{
    s1.appendChild(new Option(s.name + ' (' + s.code + ')', s.code));
  }}}});
  gCode = STOCKS[0].code;
  runAll();
}}

function switchMode(m) {{
  gMode = m;
  document.getElementById('btnSingle').classList.toggle('active', m === 'single');
  document.getElementById('btnMultiParam').classList.toggle('active', m === 'multiParam');
  document.getElementById('btnMultiStock').classList.toggle('active', m === 'multiStock');
  document.getElementById('stockSelectWrap').style.display = m === 'multiStock' ? 'none' : 'block';
  runAll();
}}

function runAll() {{
  readParams();
  gCode = document.getElementById('stockSelect').value;

  let d1 = ALL_DATA[gCode] || [];
  if (!d1.length && gMode !== 'multiStock') return;

  if (gMode !== 'multiStock') {{
    let qr1 = qualityCheck(d1);
    document.getElementById('qualityPanel').style.display = 'block';
    let stockName = STOCKS.find(s => s.code === gCode) ? STOCKS.find(s => s.code === gCode).name : gCode;
    document.getElementById('qualityPanel').innerHTML =
      '<b>数据质量</b><br>' + stockName + ': ' + qr1.rows + '行 ' + qr1.dr +
      '<br>缺失:<span style="color:' + (qr1.ms === '无' ? '#009966' : '#ef9f27') + '">' + qr1.ms + '</span> OHLC:<span style="color:' + (qr1.oh === '通过' ? '#009966' : '#ef9f27') + '">' + qr1.oh + '</span>' +
      '<br>间隔>3天:' + qr1.dg + '次 复权事件:' + qr1.ae + '次 均价:' + qr1.cm + ' 波动:' + qr1.rv + '%';
  }} else {{
    document.getElementById('qualityPanel').style.display = 'block';
    document.getElementById('qualityPanel').innerHTML = '<b>多股票对比模式</b><br>全部 ' + STOCKS.length + ' 只股票同时对比';
  }}

  let warmup = Math.max(gEntryPeriod, gAtrPeriod);
  let btStartIdx = gBtRange === 0 ? warmup : Math.max(warmup, d1.length - gBtRange);
  let btStartDate = d1.length ? d1[btStartIdx].trade_date : '20250101';
  let rf = getRiskFree(btStartDate, gBtRange);
  let bondLabel = gBtRange <= 252 ? '1年期' : '2年期';

  document.getElementById('headerInfo').innerHTML =
    '模式: ' + (({{single: '单策略', multiParam: '多参数对比', multiStock: '多股票对比'}})[gMode]) +
    ' | 通道' + gEntryPeriod + '/' + gExitPeriod + ' | ATR' + gAtrPeriod +
    ' | 风险' + gRiskPct + '% | 止损' + gStopMult + 'N | 加仓' + gAddSpacing + 'N' +
    ' | <b>无风险利率: ' + rf.toFixed(2) + '%</b> (' + bondLabel + '国债)';

  document.getElementById('strategyIntro').innerHTML =
    '<h3>海龟策略理念</h3>' +
    '<p><b>海龟交易系统</b>由 Richard Dennis 于 1983 年创立，是最经典的<b>趋势跟踪策略</b>。' +
    '核心理念：<b>截断亏损，让利润奔跑</b>——不预测方向，只跟随趋势，用小亏损换大盈利。</p>' +
    '<p><b style="color:#cc0000">唐奇安通道突破</b>：价格突破 ' + gEntryPeriod + ' 日最高价 → 入场；跌破 ' + gExitPeriod + ' 日最低价 → 退出。</p>' +
    '<p><b style="color:#378add">ATR 动态仓位</b>：每笔风险 = 资金' + gRiskPct + '% ÷ (' + gStopMult + '×N)，N=ATR。波动大的品种自动配小仓位。</p>' +
    '<p><b style="color:#ef9f27">止损规则</b>：入场后设 ' + gStopMult + 'N 硬止损（盘中触发即执行），加仓时止损上移。金字塔加仓每 ' + gAddSpacing + 'N 加 1 单位，最多 ' + gMaxUnits + ' 单位。</p>' +
    '<p><b>信号时点</b>：t 日收盘确认 → t+1 日开盘执行（通道突破/退出/加仓）。止损为盘中事件，当日执行。</p>';

  document.getElementById('contentArea').innerHTML = '';
  document.getElementById('compareArea').style.display = 'none';
  document.getElementById('compareArea').innerHTML = '';

  if (gMode === 'single') {{
    let warmup = Math.max(gEntryPeriod, gAtrPeriod);
    let btIdx = gBtRange === 0 ? warmup : Math.max(warmup, d1.length - gBtRange);
    let btDate = d1[btIdx].trade_date;
    runSingle(d1, gCode, btIdx, btDate);
  }} else if (gMode === 'multiParam') {{
    let warmup = Math.max(55, gAtrPeriod);
    let btIdx = gBtRange === 0 ? warmup : Math.max(warmup, d1.length - gBtRange);
    let btDate = d1[btIdx].trade_date;
    runMultiParam(d1, gCode, btIdx, btDate);
  }} else {{
    runMultiStock();
  }}

  document.getElementById('summaryBox').innerHTML = getSummary();
}}

function runSingle(d, code, btStartIdx, btStartDate) {{
  let bt = runTurtleBT(d, gEntryPeriod, gExitPeriod, gAtrPeriod, gRiskPct, gStopMult, gAddSpacing, gMaxUnits, gMaxPosPct, gComm, gSlip, gCap, btStartIdx);
  let m = calcMetrics(bt, gCap, btStartDate, gBtRange, btStartIdx);
  renderSingleMetrics(m, bt);
  renderSingleCharts(d, bt, m, code, btStartIdx);
  renderTradeTable(bt.trades, m);
}}

function renderSingleMetrics(m, bt) {{
  let html = '<div class="metrics-row">';
  let cards = [
    ['总收益率', fmt(m.tr, true) + '%', '(期末/期初-1)×100%', upc(parseFloat(m.tr))],
    ['年化收益率', fmt(m.ar, true) + '%', '(期末/期初)^(252/天)-1', upc(parseFloat(m.ar))],
    ['最大回撤', m.mdd + '%', 'max[(峰值-谷值)/峰值]', '#009966'],
    ['胜率', m.wr + '%', '盈利笔/总交易笔', parseFloat(m.wr) >= 50 ? '#cc0000' : '#009966'],
    ['盈亏比', m.plr, '均盈/均亏', parseFloat(m.plr) > 1 ? '#cc0000' : '#009966'],
    ['夏普比率', m.sh, '(年化-' + m.rf + '%)/波幅', parseFloat(m.sh) > 1 ? '#cc0000' : '#009966'],
    ['超额vs买持', fmt(m.ebh, true) + '%', '策略总收益-买持总收益', upc(parseFloat(m.ebh))],
    ['买入持有', fmt(m.bhr, true) + '%', '始终满仓的总收益', upc(parseFloat(m.bhr))],
    ['年化波动率', m.rs + '%', '日收益标准差×√252', '#009966'],
    ['交易次数', m.tt + ' 笔', '止损' + m.sc + '次 | 均持仓' + m.ah + '天', '#5f5e5a'],
    ['最大连续亏损', m.mcl + ' 次', '连续亏损交易最大次数', parseFloat(m.mcl) > 3 ? '#ef9f27' : '#5f5e5a'],
    ['无风险利率', m.rf + '%', gBtRange <= 252 ? '1年期国债' : '2年期国债', '#378add'],
  ];
  cards.forEach(c => {{
    html += '<div class="metric-card"><div class="label">' + c[0] + '</div>' +
      '<div class="value" style="color:' + c[3] + '">' + c[1] + '</div>' +
      '<div class="formula">' + c[2] + '</div></div>';
  }});
  html += '</div>';
  document.getElementById('metricsBox').innerHTML = html;
}}

function renderSingleCharts(d, bt, m, code, btStartIdx) {{
  let d2 = d.slice(btStartIdx);
  let dates = d2.map(r => fmtd(r.trade_date));
  let dc2 = {{
    entryUpper: bt.dc.entryUpper.slice(btStartIdx),
    entryLower: bt.dc.entryLower.slice(btStartIdx),
    exitLower: bt.dc.exitLower.slice(btStartIdx),
  }};
  let atr2 = bt.atr.slice(btStartIdx);
  let nav2 = bt.nav.slice(btStartIdx);
  let bhNav2 = bt.bhNav.slice(btStartIdx);
  let stockName = STOCKS.find(s => s.code === code) ? STOCKS.find(s => s.code === code).name : code;

  // Chart 1: Price + Donchian Channel + Signals
  let tr1 = [
    {{x: dates, y: d2.map(r => r.close_qfq), mode: 'lines', name: '收盘价', line: {{color: '#b4b2a9', width: 1.2}}}},
    {{x: dates, y: dc2.entryUpper, mode: 'lines', name: '入场上轨(' + gEntryPeriod + '日)', line: {{color: '#378add', width: 1.5}}}},
    {{x: dates, y: dc2.entryLower, mode: 'lines', name: '入场下轨(' + gEntryPeriod + '日)', line: {{color: '#378add', width: 1, dash: 'dot'}}}},
    {{x: dates, y: dc2.exitLower, mode: 'lines', name: '退出下轨(' + gExitPeriod + '日)', line: {{color: '#ef9f27', width: 1.5}}}},
  ];
  // Buy/sell/stop markers
  let bx = [], by = [], sx = [], sy = [], stopx = [], stopy = [];
  for (let t of bt.trades) {{
    if (t.ed >= d[btStartIdx].trade_date) {{
      bx.push(fmtd(t.ed)); by.push(parseFloat(t.ep));
      if (t.exitType === '止损平仓') {{ stopx.push(fmtd(t.xd)); stopy.push(parseFloat(t.xp)); }}
      else {{ sx.push(fmtd(t.xd)); sy.push(parseFloat(t.xp)); }}
    }}
  }}
  if (bx.length) tr1.push({{x: bx, y: by, mode: 'markers', name: '买入', marker: {{symbol: 'triangle-up', size: 12, color: '#cc0000'}}}});
  if (sx.length) tr1.push({{x: sx, y: sy, mode: 'markers', name: '卖出(通道退出)', marker: {{symbol: 'triangle-down', size: 12, color: '#009966'}}}});
  if (stopx.length) tr1.push({{x: stopx, y: stopy, mode: 'markers', name: '止损平仓', marker: {{symbol: 'x', size: 12, color: '#ef9f27'}}}});

  let area = document.getElementById('contentArea');
  area.innerHTML =
    '<div class="chart-card"><h3>股价与唐奇安通道 — ' + stockName + '</h3><div id="cPrice" style="height:420px"></div></div>' +
    '<div class="chart-card"><h3>ATR 波动率曲线 (N值)</h3><div id="cATR" style="height:200px"></div></div>' +
    '<div class="chart-card"><h3>策略净值 vs 买入持有</h3><div id="cNav" style="height:320px"></div></div>' +
    '<div class="chart-card"><h3>回撤曲线</h3><div id="cDD" style="height:220px"></div></div>' +
    '<div class="chart-card"><h3>每笔交易盈亏</h3><div id="cTrades" style="height:260px"></div></div>' +
    '<div class="chart-card" id="tradeBox"></div>';

  Plotly.newPlot('cPrice', tr1, {{
    title: '通道' + gEntryPeriod + '/' + gExitPeriod + ' ATR' + gAtrPeriod + ' 风险' + gRiskPct + '%',
    height: 420, hovermode: 'x unified', template: 'plotly_white',
    margin: {{l: 50, r: 20, t: 40, b: 40}}, yaxis: {{title: '价格'}}
  }});

  // Chart 2: ATR
  Plotly.newPlot('cATR', [{{
    x: dates, y: atr2, mode: 'lines', fill: 'tozeroy', name: 'ATR',
    line: {{color: '#378add', width: 1.5}}, fillcolor: 'rgba(55,138,221,0.08)'
  }}], {{
    title: 'ATR(N=' + gAtrPeriod + ')', height: 200, template: 'plotly_white',
    margin: {{l: 50, r: 20, t: 40, b: 40}}, yaxis: {{title: 'N值'}}
  }});

  // Chart 3: NAV vs Buy-Hold
  Plotly.newPlot('cNav', [
    {{x: dates, y: nav2.map(v => v / gCap), mode: 'lines', name: '海龟策略', line: {{color: '#cc0000', width: 2.5}}}},
    {{x: dates, y: bhNav2.map(v => v / gCap), mode: 'lines', name: '买入持有', line: {{color: '#b4b2a9', width: 1.5, dash: 'dash'}}}}
  ], {{
    title: '净值对比', height: 320, hovermode: 'x unified', template: 'plotly_white',
    margin: {{l: 50, r: 20, t: 40, b: 40}}, yaxis: {{title: '净值'}}
  }});

  // Chart 4: Drawdown
  let pk = nav2[0], dd = nav2.map(v => {{ if (v > pk) pk = v; return (pk - v) / pk * 100; }});
  Plotly.newPlot('cDD', [{{
    x: dates, y: dd, mode: 'lines', fill: 'tozeroy', name: '回撤',
    line: {{color: '#009966', width: 1}}, fillcolor: 'rgba(0,153,102,0.08)'
  }}], {{
    title: '回撤曲线 (最大:' + m.mdd + '%)', height: 220, template: 'plotly_white',
    margin: {{l: 50, r: 20, t: 40, b: 40}}, yaxis: {{title: '%'}}
  }});

  // Chart 5: Per-trade PnL
  Plotly.newPlot('cTrades', [{{
    x: bt.trades.map((t, i) => '#' + (i + 1)),
    y: bt.trades.map(t => parseFloat(t.pp)),
    type: 'bar',
    marker: {{color: bt.trades.map(t => t.net > 0 ? '#cc0000' : '#009966')}},
    text: bt.trades.map(t => t.pp + '%'), textposition: 'outside'
  }}], {{
    title: '每笔盈亏 (胜率' + m.wr + '%, ' + m.tt + '笔, 止损' + m.sc + '次)', height: 260,
    template: 'plotly_white', margin: {{l: 50, r: 20, t: 40, b: 60}}, yaxis: {{title: '%'}}
  }});
}}

function renderTradeTable(trades, m) {{
  let area = document.getElementById('tradeBox');
  if (!trades.length) {{ area.style.display = 'none'; return; }}
  let html = '<h3>交易明细表</h3><table class="trade-table"><thead><tr><th>#</th><th>买入日</th><th>卖出日</th><th>买入价</th><th>卖出价</th><th>股数</th><th>加仓</th><th>天</th><th>净盈亏</th><th>盈亏%</th><th>退出</th></tr></thead><tbody>';
  trades.forEach((t, i) => {{
    let exitColor = t.exitType === '止损平仓' ? '#ef9f27' : (t.exitType === '期末平仓' ? '#888780' : '#009966');
    html += '<tr><td>#' + (i+1) + '</td><td>' + t.ed + '</td><td>' + t.xd + '</td><td>' + t.ep + '</td><td>' + t.xp + '</td><td>' + t.sh + '</td><td>' + t.units + '单位</td><td>' + t.hd + '</td>' +
      '<td style="color:' + (t.net > 0 ? '#cc0000' : '#009966') + ';font-weight:500">' + (t.net > 0 ? '+' : '') + t.net.toLocaleString() + '</td>' +
      '<td style="color:' + (t.net > 0 ? '#cc0000' : '#009966') + ';font-weight:500">' + t.pp + '%</td>' +
      '<td style="font-size:10px;color:' + exitColor + '">' + t.exitType + '</td></tr>';
  }});
  html += '</tbody></table>';
  area.innerHTML = html;
}}

// ====== Multi-Param Mode ======
function runMultiParam(d, code, btStartIdx, btStartDate) {{
  let configs = [
    {{entry: 20, exit: 10, label: '系统一(20/10)'}},
    {{entry: 55, exit: 20, label: '系统二(55/20)'}},
    {{entry: gEntryPeriod, exit: gExitPeriod, label: '自定义(' + gEntryPeriod + '/' + gExitPeriod + ')'}},
  ];
  // Deduplicate if custom matches system1 or system2
  let results = configs.map(c => {{
    let btIdx = gBtRange === 0 ? Math.max(c.entry, gAtrPeriod) : Math.max(c.entry, gAtrPeriod, d.length - gBtRange);
    let btDate = d[btIdx].trade_date;
    let bt = runTurtleBT(d, c.entry, c.exit, gAtrPeriod, gRiskPct, gStopMult, gAddSpacing, gMaxUnits, gMaxPosPct, gComm, gSlip, gCap, btIdx);
    let m = calcMetrics(bt, gCap, btDate, gBtRange, btIdx);
    return {{...c, bt, m, btIdx}};
  }});

  let html = '<div class="comp-card"><h3>三组通道参数指标对比</h3>';
  html += '<table class="comp-table"><thead><tr><th>指标</th>';
  results.forEach(r => html += '<th>' + r.label + '</th>');
  html += '</tr></thead><tbody>';
  let rows = [
    ['总收益率 %', 'tr', true], ['年化收益 %', 'ar', true], ['最大回撤 %', 'mdd', false],
    ['胜率 %', 'wr', false], ['盈亏比', 'plr', false], ['夏普比率', 'sh', false],
    ['超额vs买持 %', 'ebh', true], ['交易次数', 'tt', false], ['最大连续亏损', 'mcl', false],
  ];
  rows.forEach(row => {{
    html += '<tr><td>' + row[0] + '</td>';
    results.forEach(r => {{
      let v = parseFloat(r.m[row[1]]);
      let c = upc(v);
      if (row[0] === '最大回撤 %' || row[0] === '年化波动率 %' || row[0] === '最大连续亏损') c = '#009966';
      html += '<td style="color:' + c + '">' + (row[2] && v > 0 ? '+' : '') + r.m[row[1]] + '</td>';
    }});
    html += '</tr>';
  }});
  html += '</tbody></table></div>';
  html += '<div class="chart-card"><div id="cNavComp" style="height:320px"></div></div>';
  document.getElementById('compareArea').style.display = 'block';
  document.getElementById('compareArea').innerHTML = html;
  document.getElementById('metricsBox').innerHTML = '';

  // Use the first result's btIdx for chart slicing
  let btIdx = results[0].btIdx;
  let d2 = d.slice(btIdx);
  let dates = d2.map(r => fmtd(r.trade_date));
  let navTraces = results.map(r => ({{
    x: dates, y: r.bt.nav.slice(btIdx).map(v => v / gCap), mode: 'lines', name: r.label, line: {{width: 2.5}}
  }}));
  navTraces.push({{x: dates, y: results[0].bt.bhNav.slice(btIdx).map(v => v / gCap), mode: 'lines', name: '买入持有', line: {{color: '#b4b2a9', width: 1.5, dash: 'dash'}}}});
  Plotly.newPlot('cNavComp', navTraces, {{
    title: '三组参数净值曲线对比', height: 320, hovermode: 'x unified', template: 'plotly_white',
    margin: {{l: 50, r: 20, t: 40, b: 40}}, yaxis: {{title: '净值'}}
  }});
}}

// ====== Multi-Stock Mode ======
function runMultiStock() {{
  let results = STOCKS.filter(s => ALL_DATA[s.code]).map(s => {{
    let d = ALL_DATA[s.code];
    let btIdx = gBtRange === 0 ? Math.max(gEntryPeriod, gAtrPeriod) : Math.max(gEntryPeriod, gAtrPeriod, d.length - gBtRange);
    if (btIdx >= d.length) btIdx = Math.max(gEntryPeriod, gAtrPeriod);
    let btDate = d[btIdx].trade_date;
    let bt = runTurtleBT(d, gEntryPeriod, gExitPeriod, gAtrPeriod, gRiskPct, gStopMult, gAddSpacing, gMaxUnits, gMaxPosPct, gComm, gSlip, gCap, btIdx);
    let m = calcMetrics(bt, gCap, btDate, gBtRange, btIdx);
    return {{name: s.name, code: s.code, bt, m, d, btIdx}};
  }});

  let html = '<div class="comp-card"><h3>全部股票指标对比 — 通道' + gEntryPeriod + '/' + gExitPeriod + '</h3>';
  html += '<table class="comp-table"><thead><tr><th>指标</th>';
  results.forEach(r => html += '<th>' + r.name + '</th>');
  html += '</tr></thead><tbody>';
  let rows = [
    ['总收益率 %', 'tr', true], ['年化收益 %', 'ar', true], ['最大回撤 %', 'mdd', false],
    ['胜率 %', 'wr', false], ['盈亏比', 'plr', false], ['夏普比率', 'sh', false],
    ['超额vs买持 %', 'ebh', true], ['交易次数', 'tt', false], ['最大连续亏损', 'mcl', false],
  ];
  rows.forEach(row => {{
    html += '<tr><td>' + row[0] + '</td>';
    results.forEach(r => {{
      let v = parseFloat(r.m[row[1]]);
      let c = upc(v);
      if (row[0] === '最大回撤 %' || row[0] === '最大连续亏损') c = '#009966';
      html += '<td style="color:' + c + '">' + (row[2] && v > 0 ? '+' : '') + r.m[row[1]] + '</td>';
    }});
    html += '</tr>';
  }});
  html += '</tbody></table></div>';
  html += '<div class="chart-card"><div id="cStockNav" style="height:360px"></div></div>';
  document.getElementById('compareArea').style.display = 'block';
  document.getElementById('compareArea').innerHTML = html;
  document.getElementById('metricsBox').innerHTML = '';

  // Use the longest common date range
  let minLen = Math.min(...results.map(r => r.d.length - r.btIdx));
  let refD = results[0].d;
  let refBtIdx = results[0].btIdx;
  let dates = refD.slice(refD.length - minLen).map(r => fmtd(r.trade_date));
  let colors = ['#cc0000', '#378add', '#ef9f27', '#9b59b6', '#009966'];
  let navTraces = results.map((r, i) => ({{
    x: dates,
    y: r.bt.nav.slice(r.d.length - minLen).map(v => v / gCap),
    mode: 'lines', name: r.name, line: {{color: colors[i % colors.length], width: 2}}
  }}));
  Plotly.newPlot('cStockNav', navTraces, {{
    title: '全部股票净值曲线对比', height: 360, hovermode: 'x unified', template: 'plotly_white',
    margin: {{l: 50, r: 20, t: 40, b: 40}}, yaxis: {{title: '净值'}}
  }});
}}

// ====== Summary ======
function getSummary() {{
  return '<h3>海龟交易策略使用心得与适用场景</h3>' +
    '<h4>一、策略本质</h4>' +
    '<p>海龟策略是最经典的<b>趋势跟踪系统</b>，核心逻辑：价格突破 N 日最高价入场，跌破短期低点退出。' +
    '它不预测方向，只跟随趋势——<b>"截断亏损，让利润奔跑"</b>。' +
    '通过 ATR 动态仓位管理，确保每笔交易风险固定在 2%，不管交易什么品种，单笔亏损对总账户的冲击都可控。</p>' +
    '<h4>二、适用场景（策略最能发挥优势的市场）</h4>' +
    '<p><b>1. 趋势明确的市场</b>：单边上涨或单边下跌行情中，海龟能捕捉大部分主升浪。通道突破一旦确认，趋势通常会延续。</p>' +
    '<p><b>2. 高波动率标的</b>：波动大意味着趋势启动后空间大，ATR 仓位管理自动适配——波动大的品种配小仓位，波动小的配大仓位，风险对等。</p>' +
    '<p><b>3. 多品种分散</b>：海龟原版同时运行在几十个不相关的市场。每个品种只承担 2% 风险，即使一半品种止损，账户也只回撤 10% 左右。</p>' +
    '<p><b>4. 中长周期持仓</b>：日线级别交易，单笔持仓数周到数月。不适合日内超短线——通道的天然滞后性决定了它无法捕捉盘中瞬变。</p>' +
    '<h4>三、不适用场景（策略最容易亏钱的市场）</h4>' +
    '<p><b>1. 震荡盘整市——最大天敌</b>：价格在窄幅区间反复波动，通道频繁产生突破-回撤-再突破的"左右打脸"信号。频繁止损累积亏损，这是海龟策略最大的失效场景。</p>' +
    '<p><b>2. 低波动蓝筹股</b>：波动空间小，即使方向判断正确，单笔盈利也难以覆盖交易成本。工商银行等低波动标的日波动仅 1-2%，ATR 很小但趋势空间也不够。</p>' +
    '<p><b>3. 突发消息/政策冲击</b>：通道仅反映价格走势，无法预判黑天鹅。通道形态再完美的标的，突发利空也会大幅杀跌跳空，止损可能远差于预期。</p>' +
    '<h4>四、参数选择心得</h4>' +
    '<p><b>1. 系统一(20日) vs 系统二(55日)</b>：系统一更灵敏，信号多但假信号也多；系统二更稳健，信号少但可靠性高。海龟原版两个系统同时运行，互为补充。</p>' +
    '<p><b>2. 退出通道的选择</b>：退出通道(10/20日)比入场通道(20/55日)更窄，这是有意为之——让利润多跑一会儿，但要在线索出现时果断离场。</p>' +
    '<p><b>3. 止损倍数</b>：2N 是海龟标准。太近(1N)会被正常噪音震出去；太远(3N+)单笔风险过大。加仓后止损上移，保护已有盈利。</p>' +
    '<p><b>4. 加仓间距</b>：0.5N 是标准值。加大间距减少加仓次数但错过部分趋势；缩小间距加仓更密集但风险集中。</p>' +
    '<h4>五、风险管理要点</h4>' +
    '<p><b>1. 2% 风险上限是铁律</b>：不管信号多看好，单笔亏损不超过总资金 2%。连续止损 5 次也只回撤 10%，还能继续交易。</p>' +
    '<p><b>2. 金字塔加仓的前提是趋势确认</b>：只有在价格朝有利方向移动 0.5N 后才加仓。越赚越加，而不是亏损补仓。</p>' +
    '<p><b>3. 连续止损的心理承受</b>：海龟策略胜率通常只有 35-45%，连续 10 次以上止损是正常的。绝大多数人在策略"应该赚钱"之前就放弃了。</p>' +
    '<p><b>4. 仓位上限防止过度集中</b>：4 个单位加仓后总仓位不超过 80%，留有余地应对极端情况。</p>' +
    '<h4>六、从本看板回测可观察到的典型规律</h4>' +
    '<p>• <b>成长股 vs 价值股</b>：寒武纪、阳光电源等高波动股趋势空间大，海龟策略表现通常优于工商银行等低波动股。</p>' +
    '<p>• <b>系统一 vs 系统二</b>：20 日通道交易频繁，单笔盈亏小但捕捉趋势快；55 日通道交易稀少，单笔盈亏大但对趋势转折反应慢。</p>' +
    '<p>• <b>策略 vs 买入持有</b>：在单边牛市中海龟可能跑输买入持有（中途止损离场），但在震荡市和熊市中海龟通过空仓规避亏损，相对优势明显。</p>' +
    '<p>• <b>ATR 仓位管理的效果</b>：高波动品种自动配小仓位，低波动品种自动配大仓位，使不同品种的风险敞口一致。这是海龟最精妙的设计。</p>' +
    '<p>• <b>止损跳空风险</b>：A 股有涨跌停限制，但跳空缺口仍可能导致止损价远差于预期。回测中的止损执行价是理想化的，实盘可能更差。</p>' +
    '<p><b>⚠️ 以上内容由 AI 基于公开信息整理生成，仅供参考，不构成任何投资建议或个股推荐。投资有风险，决策需谨慎。</b></p>';
}}

init();
</script>
</body>
</html>''';

    output_path = os.path.join(BASE_DIR, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✅ 看板已生成: {output_path}")
    print(f"   文件大小: {os.path.getsize(output_path) / 1024:.0f} KB")
    return output_path

if __name__ == "__main__":
    generate_html()
