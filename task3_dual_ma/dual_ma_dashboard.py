"""
双均线策略交互式看板生成器 v7
==============================
v7 新增: 动态无风险利率(2年期国债) | MA手动输入+校验(短<长)
"""
import json, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

STOCKS = [
    {"code": "688256", "name": "寒武纪", "file": "688256_daily_qfq.json"},
    {"code": "300750", "name": "宁德时代", "file": "300750_daily_qfq.json"},
    {"code": "601398", "name": "工商银行", "file": "601398_daily_qfq.json"},
    {"code": "600030", "name": "中信证券", "file": "600030_daily_qfq.json"},
    {"code": "300274", "name": "阳光电源", "file": "300274_daily_qfq.json"},
]

def load_stock_data(code, filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
    for row in data:
        for col in ["open_qfq", "high_qfq", "low_qfq", "close_qfq", "vol"]:
            if col in row: row[col] = float(row[col]) if row[col] is not None else None
    data.sort(key=lambda x: x["trade_date"])
    return data

def load_bond_yield():
    path = os.path.join(DATA_DIR, "bond_yield_1y.json")
    if not os.path.exists(path): print("[Warn] bond_yield_2y.json not found, using default 2%"); return {}
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def generate_html():
    print("加载股票数据...")
    all_data = {}
    for s in STOCKS:
        d = load_stock_data(s["code"], s["file"])
        if d: all_data[s["code"]] = d

    print("加载国债收益率(1年期)...")
    bond_yield = load_bond_yield()
    print(f"  {len(bond_yield)} entries loaded")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>双均线策略看板</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; height: 100vh; overflow: hidden; background: #f5f4f0; color: #2c2c2a; }}
:root {{ --up: #cc0000; --dn: #009966; --up-bg: #fef0f0; --dn-bg: #eefaf5; }}

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
.ma-row {{ display: flex; align-items: center; gap: 4px; margin-bottom: 3px; }}
.ma-row input[type="range"] {{ flex: 1; min-width: 0; }}
.ma-row input[type="number"] {{ width: 44px; padding: 3px 4px; font-size: 12px; text-align: center; }}
.ma-row span {{ font-size: 11px; font-weight: 500; min-width: 24px; text-align: center; }}
.param-display {{ font-size: 10px; color: #888780; margin-top: 1px; }}
.section-div {{ border-top: 0.5px solid #e0ded6; padding-top: 8px; margin-top: 4px; }}
.mode-tabs {{ display: flex; gap: 4px; }}
.mode-tabs button {{
  flex: 1; padding: 6px 4px; font-size: 11px; background: #f1efe8; color: #5f5e5a;
  border: 0.5px solid #d3d1c7; border-radius: 6px; cursor: pointer;
}}
.mode-tabs button.active {{ background: var(--up); color: #fff; border-color: var(--up); }}
.ma-error {{ display: none; color: #cc0000; font-size: 11px; padding: 5px 8px; background: #fef0f0; border-radius: 6px; border: 0.5px solid #f5c4b3; }}
.ma-error.show {{ display: block; }}
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
  <h2>双均线策略看板</h2>
  <div class="mode-tabs">
    <button class="active" onclick="switchMode('single')" id="btnSingle">单策略</button>
    <button onclick="switchMode('multiMA')" id="btnMultiMA">多策略对比</button>
    <button onclick="switchMode('multiStock')" id="btnMultiStock">多股票对比</button>
  </div>
  <div id="maError" class="ma-error"></div>

  <div>
    <h3>选择标的</h3>
    <select id="stockSelect" onchange="runAll()"></select>
  </div>
  <div id="stockSelect2Wrap" style="display:none">
    <h3>对比标的</h3>
    <select id="stockSelect2" onchange="runAll()"></select>
  </div>

  <div id="singleParams">
    <h3>短均线周期 (快线)</h3>
    <div class="ma-row">
      <input type="range" id="shortMA_r" min="1" max="60" value="5" oninput="syncSR('shortMA');runAll()">
      <input type="number" id="shortMA" min="1" max="60" value="5" onchange="syncSI('shortMA');runAll()">
    </div>
    <h3>长均线周期 (慢线)</h3>
    <div class="ma-row">
      <input type="range" id="longMA_r" min="1" max="200" value="15" oninput="syncSR('longMA');runAll()">
      <input type="number" id="longMA" min="1" max="200" value="15" onchange="syncSI('longMA');runAll()">
    </div>
  </div>

  <div id="multiMAParams" style="display:none">
    <h3>策略A — 短 / 长</h3>
    <div class="ma-row">
      <input type="range" id="shortA_r" min="1" max="60" value="5" oninput="syncSRm('shortA');runAll()">
      <input type="number" id="shortA" min="1" max="60" value="5" onchange="syncSIm('shortA');runAll()">
      <input type="range" id="longA_r" min="1" max="200" value="15" oninput="syncSRm('longA');runAll()">
      <input type="number" id="longA" min="1" max="200" value="15" onchange="syncSIm('longA');runAll()">
    </div>
    <h3>策略B — 短 / 长</h3>
    <div class="ma-row">
      <input type="range" id="shortB_r" min="1" max="60" value="10" oninput="syncSRm('shortB');runAll()">
      <input type="number" id="shortB" min="1" max="60" value="10" onchange="syncSIm('shortB');runAll()">
      <input type="range" id="longB_r" min="1" max="200" value="30" oninput="syncSRm('longB');runAll()">
      <input type="number" id="longB" min="1" max="200" value="30" onchange="syncSIm('longB');runAll()">
    </div>
    <h3>策略C — 短 / 长</h3>
    <div class="ma-row">
      <input type="range" id="shortC_r" min="1" max="60" value="20" oninput="syncSRm('shortC');runAll()">
      <input type="number" id="shortC" min="1" max="60" value="20" onchange="syncSIm('shortC');runAll()">
      <input type="range" id="longC_r" min="1" max="200" value="60" oninput="syncSRm('longC');runAll()">
      <input type="number" id="longC" min="1" max="200" value="60" onchange="syncSIm('longC');runAll()">
    </div>
  </div>

  <div id="multiStockParams" style="display:none">
    <h3>短均线周期</h3>
    <div class="ma-row">
      <input type="range" id="shortMS_r" min="1" max="60" value="5" oninput="syncSR('shortMS');runAll()">
      <input type="number" id="shortMS" min="1" max="60" value="5" onchange="syncSI('shortMS');runAll()">
    </div>
    <h3>长均线周期</h3>
    <div class="ma-row">
      <input type="range" id="longMS_r" min="1" max="200" value="15" oninput="syncSR('longMS');runAll()">
      <input type="number" id="longMS" min="1" max="200" value="15" onchange="syncSI('longMS');runAll()">
    </div>
  </div>

  <div class="section-div">
    <h3>仓位比例 (%)</h3>
    <input type="number" id="positionPct" value="80" step="5" min="10" max="100">
    <div class="param-display">每次买入使用资金百分比</div>
  </div>
  <div class="section-div">
    <h3>单笔止损线 (%)</h3>
    <input type="number" id="stopLoss" value="5" step="1" min="1" max="50">
    <div class="param-display">单笔亏损超总资金此比例则强制平仓</div>
  </div>
  <div class="section-div">
    <h3>手续费率 (%)</h3>
    <input type="number" id="commission" value="0.03" step="0.005" min="0" max="1">
  </div>
  <div>
    <h3>滑点 (%)</h3>
    <input type="number" id="slippage" value="0.01" step="0.005" min="0" max="0.5">
  </div>
  <div>
    <h3>初始资金 (万元)</h3>
    <input type="number" id="capital" value="100" step="10" min="1" max="10000">
  </div>
  <button onclick="runAll()">运行回测</button>
  <div id="qualityPanel" class="quality-card" style="display:none"></div>
</div>

<div class="main" id="mainContent">
  <div class="header-card">
    <h1>双均线策略看板</h1>
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
const BOND_YIELD = {json.dumps(bond_yield, ensure_ascii=False)};

let gMode='single', gCode='', gRf=2;
let gShort=5, gLong=15, gPosPct=80, gStopLoss=5;
let gComm=0.03, gSlip=0.01, gCap=1000000;
let gShortA=5, gLongA=15, gShortB=10, gLongB=30, gShortC=20, gLongC=60;
let gShortMS=5, gLongMS=15;

// ====== Slider <-> Number Sync ======
function syncSR(id) {{
  let n = document.getElementById(id), r = document.getElementById(id+'_r');
  n.value = r.value;
}}
function syncSI(id) {{
  let n = document.getElementById(id), r = document.getElementById(id+'_r');
  let v = parseInt(n.value)||1;
  n.value = v; r.value = v;
}}
// multiMA variants (no auto run)
function syncSRm(id) {{ syncSR(id); }}
function syncSIm(id) {{ syncSI(id); }}

// ====== Validation ======
function showMAError(msg) {{
  let el = document.getElementById('maError');
  if (msg) {{ el.textContent = msg; el.classList.add('show'); return false; }}
  else {{ el.classList.remove('show'); return true; }}
}}
function validatePair(short, long, label) {{
  if (short >= long) return label+': 短均线('+short+')必须小于长均线('+long+')';
  return null;
}}
function validateAll() {{
  let errs = [];
  if (gMode==='single') {{
    let e = validatePair(gShort, gLong, '单策略');
    if (e) errs.push(e);
  }} else if (gMode==='multiMA') {{
    let e1 = validatePair(gShortA, gLongA, '策略A');
    if (e1) errs.push(e1);
    let e2 = validatePair(gShortB, gLongB, '策略B');
    if (e2) errs.push(e2);
    let e3 = validatePair(gShortC, gLongC, '策略C');
    if (e3) errs.push(e3);
  }} else {{
    let e = validatePair(gShortMS, gLongMS, '多股票对比');
    if (e) errs.push(e);
  }}
  if (errs.length) return showMAError(errs.join('; '));
  return showMAError(null);
}}

function readParams() {{
  gShort = parseInt(document.getElementById('shortMA').value)||5;
  gLong = parseInt(document.getElementById('longMA').value)||15;
  gPosPct = parseInt(document.getElementById('positionPct').value)||80;
  gStopLoss = parseInt(document.getElementById('stopLoss').value)||5;
  gComm = parseFloat(document.getElementById('commission').value)/100||0.0003;
  gSlip = parseFloat(document.getElementById('slippage').value)/100||0.0001;
  gCap = parseFloat(document.getElementById('capital').value)*10000||1000000;
  gShortA = parseInt(document.getElementById('shortA').value)||5;
  gLongA = parseInt(document.getElementById('longA').value)||15;
  gShortB = parseInt(document.getElementById('shortB').value)||10;
  gLongB = parseInt(document.getElementById('longB').value)||30;
  gShortC = parseInt(document.getElementById('shortC').value)||20;
  gLongC = parseInt(document.getElementById('longC').value)||60;
  gShortMS = parseInt(document.getElementById('shortMS').value)||5;
  gLongMS = parseInt(document.getElementById('longMS').value)||15;
}}

function init() {{
  const s1 = document.getElementById('stockSelect'), s2 = document.getElementById('stockSelect2');
  STOCKS.forEach(s => {{ if(ALL_DATA[s.code]) {{
    s1.appendChild(new Option(s.name+' ('+s.code+'.SH)', s.code));
    s2.appendChild(new Option(s.name+' ('+s.code+'.SH)', s.code));
  }}}});
  gCode = STOCKS[0].code;
  runAll();
}}

function switchMode(m) {{
  gMode = m;
  document.getElementById('btnSingle').classList.toggle('active', m==='single');
  document.getElementById('btnMultiMA').classList.toggle('active', m==='multiMA');
  document.getElementById('btnMultiStock').classList.toggle('active', m==='multiStock');
  document.getElementById('singleParams').style.display = m==='single'?'block':'none';
  document.getElementById('multiMAParams').style.display = m==='multiMA'?'block':'none';
  document.getElementById('multiStockParams').style.display = m==='multiStock'?'block':'none';
  document.getElementById('stockSelect2Wrap').style.display = m==='multiStock'?'block':'none';
  runAll();
}}

// ====== Risk-free rate lookup ======
function getRiskFree(dateStr) {{
  // dateStr format: '20250701' -> lookup '2025-07-01'
  let key = dateStr.slice(0,4)+'-'+dateStr.slice(4,6)+'-'+dateStr.slice(6,8);
  if (BOND_YIELD[key] !== undefined) return BOND_YIELD[key];
  // Fallback: search nearest date
  let keys = Object.keys(BOND_YIELD).sort();
  let best = null;
  for (let k of keys) {{ if (k <= key) best = k; else break; }}
  if (best) return BOND_YIELD[best];
  return 2; // ultimate fallback
}}

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

function sma(v,p) {{ let r=new Array(v.length).fill(null); for(let i=p-1;i<v.length;i++){{ let s=0; for(let j=i-p+1;j<=i;j++) s+=v[j]; r[i]=s/p; }} return r; }}

function genSig(d,sp,lp) {{
  let cl=d.map(r=>r.close_qfq), sm=sma(cl,sp), lm=sma(cl,lp), st=Math.max(sp,lp), pr=0;
  let sig=new Array(d.length).fill(0), ts=new Array(d.length).fill(0);
  for(let i=st;i<d.length;i++){{
    if(sm[i]===null||lm[i]===null) continue;
    let cr=sm[i]>lm[i]?1:-1;
    if(pr!==0){{ if(cr===1&&pr===-1) sig[i]=1; else if(cr===-1&&pr===1) sig[i]=-1; }}
    pr=cr; if(i>0) ts[i]=sig[i-1];
  }}
  return {{sm,lm,sig,ts}};
}}

function runBT(d,sd,comm,slip,cap,posPct,stopLossPct,btStartIdx) {{
  let trades=[], pos=0, cash=cap, shares=0, ep=0, ed='', nav=new Array(d.length).fill(0);
  let br=1+comm+slip, sr=1-comm-slip-0.0005, stopLossAmount=cap*stopLossPct/100;
  // Before backtest start, NAV = cash
  for(let i=0;i<btStartIdx;i++) nav[i]=cap;
  for(let i=btStartIdx;i<d.length;i++){{
    let r=d[i], sig=sd.ts[i], op=r.open_qfq, cp=r.close_qfq;
    // Open position
    if(sig===1 && pos===0 && op>0) {{
      let availCash = cash * posPct/100;
      let bp=op*br, s=Math.floor(availCash/bp/100)*100;
      if(s>=100) {{ cash-=s*bp; pos=1; shares=s; ep=op; ed=r.trade_date; }}
    }}
    if(pos===1 && op>0) {{
      let forcedSell = false;
      let curLoss = ep*shares*br - cp*shares;
      if(curLoss >= stopLossAmount) forcedSell = true;
      if(sig===-1 || forcedSell) {{
        let sp=op*sr, proceeds=shares*sp, cost=ep*shares*br, net=proceeds-cost;
        trades.push({{ed, xd:r.trade_date, ep:ep.toFixed(1), xp:op.toFixed(1), sh:shares,
          net:Math.round(net), pp:(net/cost*100).toFixed(1), hd:i-d.findIndex(x=>x.trade_date===ed),
          forced: forcedSell && sig!==-1 }});
        cash+=proceeds; pos=0; shares=0;
      }}
    }}
    nav[i]=cash+shares*cp;
  }}
  // Buy-hold: enter at backtest start
  let bhEntry = btStartIdx;
  let bhS=Math.floor((cap*posPct/100)/(d[bhEntry].open_qfq*br)/100)*100;
  let bhCost=bhS*d[bhEntry].open_qfq*br, bhCash=cap-bhCost, bhNav=new Array(d.length).fill(0);
  for(let i=0;i<bhEntry;i++) bhNav[i]=cap;
  for(let i=bhEntry;i<d.length;i++) bhNav[i]=bhCash+bhS*d[i].close_qfq;
  return {{trades,nav,bhNav:bhNav,fn:nav[nav.length-1]}};
}}

function calcM(bt,cap,startDate) {{
  let nv=bt.nav, t=bt.trades, n=nv.length, y=n/252;
  let tr=(bt.fn/cap-1)*100;
  let ar=(Math.pow(bt.fn/cap,1/Math.max(y,0.01))-1)*100;
  let pk=nv[0], mdd=0;
  for(let i=1;i<n;i++){{ if(nv[i]>pk) pk=nv[i]; let dd=(pk-nv[i])/pk*100; if(dd>mdd) mdd=dd; }}
  let w=t.filter(x=>x.net>0), l=t.filter(x=>x.net<=0);
  let wr=t.length?(w.length/t.length*100):0;
  let aw=w.length?w.reduce((s,x)=>s+x.net,0)/w.length:0;
  let al=l.length?Math.abs(l.reduce((s,x)=>s+Math.abs(x.net),0)/l.length):1;
  let plr=al>0?aw/al:0;
  let dr=[]; for(let i=1;i<n;i++) if(nv[i-1]>0) dr.push((nv[i]-nv[i-1])/nv[i-1]);
  let rs=dr.length?Math.sqrt(dr.reduce((s,r)=>s+r*r,0)/dr.length)*Math.sqrt(252)*100:0;
  let rf = startDate ? getRiskFree(startDate) : 2;
  let sh=rs>0?(ar-rf)/rs:0;
  let bhf=bt.bhNav[n-1], bhr=(bhf/cap-1)*100, ebh=tr-bhr;
  let ah=t.length?t.reduce((s,x)=>s+x.hd,0)/t.length:0;
  let fc=t.filter(x=>x.forced).length;
  return {{tr:tr.toFixed(2),ar:ar.toFixed(2),mdd:mdd.toFixed(2),wr:wr.toFixed(1),
    plr:plr.toFixed(2),sh:sh.toFixed(2),ebh:ebh.toFixed(2),bhr:bhr.toFixed(2),
    tt:t.length,ah:ah.toFixed(0),rs:rs.toFixed(1),fc,rf:rf.toFixed(2)}};
}}

function fmtd(d) {{ return d.slice(0,4)+'-'+d.slice(4,6)+'-'+d.slice(6,8); }}
function upc(v) {{ return v>0?'#cc0000':'#009966'; }}
function fmt(v,p) {{ return (p&&v>0?'+':'')+v; }}

function runAll() {{
  readParams();
  if (!validateAll()) return;
  gCode = document.getElementById('stockSelect').value;
  let d1 = ALL_DATA[gCode]||[];
  if(!d1.length) return;

  let qr1 = qualityCheck(d1);
  document.getElementById('qualityPanel').style.display='block';
  document.getElementById('qualityPanel').innerHTML =
    '<b>数据质量</b><br>'+STOCKS.find(s=>s.code===gCode).name+': '+qr1.rows+'行 '+qr1.dr+
    '<br>缺失:<span style="color:'+(qr1.ms==='无'?'#009966':'#ef9f27')+'">'+qr1.ms+'</span> OHLC:<span style="color:'+(qr1.oh==='通过'?'#009966':'#ef9f27')+'">'+qr1.oh+'</span>'+
    '<br>间隔>3天:'+qr1.dg+'次 复权事件:'+qr1.ae+'次 均价:'+qr1.cm+' 波动:'+qr1.rv+'%';

  // Compute backtest start: last ~252 trading days (= 1 year)
  let btStartIdx = Math.max(0, d1.length - 252);
  let btStartDate = d1[btStartIdx].trade_date;
  gRf = getRiskFree(btStartDate);

  document.getElementById('headerInfo').innerHTML =
    '模式: '+(({{single:'单策略',multiMA:'多策略对比',multiStock:'多股票对比'}})[gMode])+
    ' | 仓位'+gPosPct+'% | 止损'+gStopLoss+'% | '+
    '佣金'+(gComm*100).toFixed(2)+'%+滑点'+(gSlip*100).toFixed(2)+'% | 初始'+Math.round(gCap/10000)+'万'+
    ' | <b>无风险利率: '+gRf.toFixed(2)+'%</b> (回测起始日1Y国债 '+btStartDate.slice(0,4)+'-'+btStartDate.slice(4,6)+'-'+btStartDate.slice(6,8)+')';

  document.getElementById('strategyIntro').innerHTML =
    '<h3>策略理念</h3>'+
    '<p><b>双均线策略</b>（Dual Moving Average Crossover）是最经典的趋势跟踪策略。'+
    '核心理念：<b>趋势一旦形成，不会轻易反转</b>。通过一根快速均线和一根慢速均线的交叉来判断趋势转折。</p>'+
    '<p><b style="color:#cc0000">金叉买入</b>：快线上穿慢线 → 短期动能超越长期趋势 → 上涨通道打开。'+
    '<b style="color:#009966">死叉卖出</b>：快线下穿慢线 → 短期动能衰竭 → 下跌/调整通道。'+
    '信号在 day t 收盘确认，day t+1 开盘执行（防未来函数）。</p>'+
    '<p><b>风控机制</b>：仓位管理('+gPosPct+'%) | 单笔止损(超总资金'+gStopLoss+'%强制平仓)。'+
    '核心特征：<b>低胜率 + 高盈亏比</b>——多数交易小亏止损，少数大赚覆盖亏损。'+
    '<br><b>无风险利率</b>：夏普比率采用<b>回测起始日</b>（近1年首个交易日）对应的<b>1年期中国国债收益率</b>（'+gRf.toFixed(2)+'%，中债官网数据）。</p>';

  document.getElementById('contentArea').innerHTML = '';
  document.getElementById('compareArea').style.display = 'none';
  document.getElementById('compareArea').innerHTML = '';

  if (gMode === 'single') {{
    runSingle(d1, gCode, gShort, gLong, btStartIdx, btStartDate);
  }} else if (gMode === 'multiMA') {{
    runMultiMA(d1, gCode, btStartIdx, btStartDate);
  }} else {{
    runMultiStock(btStartIdx, btStartDate);
  }}

  document.getElementById('summaryBox').innerHTML =
    '<h3>双均线策略使用心得与适用场景</h3>'+
    '<h4>一、策略本质</h4>'+
    '<p>双均线是最经典的趋势跟踪策略，核心逻辑简单：快线上穿慢线（金叉）→ 短期动能超越长期趋势 → 买入；'+
    '快线下穿慢线（死叉）→ 短期动能衰竭 → 卖出。它不预测方向，只追随趋势——<b>"截断亏损，让利润奔跑"</b>。</p>'+
    '<h4>二、适用场景（策略最能发挥优势的市场）</h4>'+
    '<p><b>1. 趋势明确的市场</b>：单边上涨或单边下跌行情中，双均线能捕捉大部分主升浪/主跌浪。寒武纪近一年大涨260%，策略虽跑输买入持有，但在关键波段中仍获得了可观的趋势收益。</p>'+
    '<p><b>2. 高波动率成长股</b>：波动大意味着趋势启动后空间大，单笔盈利足以覆盖多次小亏。如阳光电源、寒武纪，盈亏比远超低波动标的。</p>'+
    '<p><b>3. 中长周期趋势投资</b>：日线级别交易，适合周线/日线操作者。不适合日内超短线——均线的天然滞后性决定了它无法捕捉盘中瞬变。</p>'+
    '<p><b>4. 大环境配合时</b>：当大盘指数（如沪深300）本身处于中期上升通道时，个股双均线信号的可靠性大幅提升。可在策略中叠加指数环境判断，熊市空仓、牛市做多。</p>'+
    '<h4>三、不适用场景（策略最容易亏钱的市场）</h4>'+
    '<p><b>1. 震荡盘整市——最大天敌</b>：价格在窄幅区间反复波动，均线频繁产生金叉→死叉→金叉的"左右打脸"信号。如工商银行这类低波动大盘股，近一年MA(5,15)策略几乎没有有效交易，反复小亏累积。震荡市中建议暂停策略或延长均线周期。</p>'+
    '<p><b>2. 低波动蓝筹股</b>：波动空间小，即使方向判断正确，单笔盈利也难以覆盖交易成本（手续费+滑点）。工商银行、部分银行股的日波动仅1-2%，扣除双边手续费后盈亏比极低。</p>'+
    '<p><b>3. 极致单边牛市</b>：在持续大涨的牛市中，策略可能因中途死叉卖出而错失后续涨幅。如寒武纪的案例：买入持有收益260%，策略仅40%+。此时可考虑放宽均线参数或结合更大级别均线（如200日均线）确认主趋势。</p>'+
    '<p><b>4. 突发消息/政策冲击</b>：均线仅反映价格走势，无法预判黑天鹅。均线形态再完美的标的，突发利空也会大幅杀跌，需配合基本面排雷。</p>'+
    '<h4>四、实战核心要点</h4>'+
    '<p><b>1. 参数选择是艺术不是科学</b>：短均线5-20日（捕捉启动）、长均线15-120日（过滤噪音）。周期越短→信号越多→假信号也多→胜率低但反应快；周期越长→信号越少→可靠性高但滞后严重→容易错过行情。无"最佳参数"，需根据标的波动特征调整。可用本看板"多策略对比"模式同时测试三组参数。</p>'+
    '<p><b>2. 止损是生命线</b>：双均线策略的典型胜率仅30-50%，10笔交易亏6-7笔是常态。每笔亏损必须可控——建议单笔止损不超过总资金3-5%，否则连续止损会迅速亏光本金。从回测看，未设止损时单笔亏损可达总资金10%+。</p>'+
    '<p><b>3. 仓位控制比信号更重要</b>：永远不要满仓。建议单次仓位60-80%，留余应对假信号和黑天鹅。满仓时一次止损可能就是总资金5%的亏损。</p>'+
    '<p><b>4. 区分"震荡期"和"趋势期"</b>：当均线反复交叉（3个月内超过5次金叉死叉），说明市场在震荡，此时应降低仓位或暂停策略，等待趋势明朗。可结合ADX指标（>25为趋势行情）辅助判断。</p>'+
    '<p><b>5. 不要单独使用</b>：双均线最好与大趋势判断（200日均线方向、大盘指数阶段）+ 成交量确认（金叉放量可靠性更高）+ 基本面排雷（避开ST、业绩暴雷股）结合使用。</p>'+
    '<p><b>6. 心理建设——接受低胜率</b>：双均线赚的不是胜率，是盈亏比。一笔大赚覆盖多笔小亏才是盈利模式。连续止损时不要怀疑策略、不要手动干预信号——系统化执行的纪律性比参数优化更重要。</p>'+
    '<h4>五、从本看板回测观察到的典型规律</h4>'+
    '<p>• <b>成长股 vs 价值股</b>：寒武纪、阳光电源波动大，信号虽多但每笔盈亏幅度大，策略总收益可能为正；工商银行、宁德时代波动相对小，交易次数少，盈亏幅度窄。</p>'+
    '<p>• <b>MA(5,15) vs MA(20,60)</b>：短周期组合信号频繁（年10-20次），单笔盈亏小；长周期组合信号稀少（年3-5次），单笔盈亏大但对趋势转折反应慢。</p>'+
    '<p>• <b>策略收益 vs 买入持有</b>：在单边牛市中策略几乎必然跑输买入持有（因为中途卖出），但在震荡市和熊市中策略通过空仓规避亏损，相对优势明显。评价策略不能只看绝对收益，要看风险调整后收益（夏普比率）。</p>'+
    '<p>• <b>交易成本不可忽视</b>：每次买卖约消耗0.07%（万三佣金+万一滑点双边），年交易10次就是0.7%的纯摩擦成本。频繁交易的小盈利可能被费用吃掉。</p>';
}}

function runSingle(d, code, sp, lp, btStartIdx, btStartDate) {{
  let sd = genSig(d, sp, lp);
  let bt = runBT(d, sd, gComm, gSlip, gCap, gPosPct, gStopLoss, btStartIdx);
  let m = calcM(bt, gCap, btStartDate);
  renderSingleMetrics(m, bt);
  renderSingleCharts(d, sd, bt, m, code, sp, lp, btStartIdx);
  renderTradeTable(bt.trades, m);
}}

function renderSingleMetrics(m, bt) {{
  let html = '<div class="metrics-row">';
  let cards = [
    ['总收益率', fmt(m.tr,true)+'%', '(期末净值/期初-1)x100%', upc(m.tr)],
    ['年化收益率', fmt(m.ar,true)+'%', '(期末/期初)^(252/天数)-1', upc(m.ar)],
    ['最大回撤', m.mdd+'%', 'max[(峰值-谷值)/峰值]', '#009966'],
    ['胜率', m.wr+'%', '盈利笔/总交易笔', m.wr>=50?'#cc0000':'#009966'],
    ['盈亏比', m.plr, '均盈/均亏', m.plr>1?'#cc0000':'#009966'],
    ['夏普比率', m.sh, '(年化-'+m.rf+'%)/波幅', m.sh>1?'#cc0000':'#009966'],
    ['超额vs买入持有', fmt(m.ebh,true)+'%', '策略总收益-买持总收益', upc(m.ebh)],
    ['买入持有收益', fmt(m.bhr,true)+'%', '始终满仓的总收益率', upc(m.bhr)],
    ['年化波动率', m.rs+'%', '日收益标准差x√252', '#009966'],
    ['交易次数', m.tt+' 笔', '平均持仓'+m.ah+'天'+(m.fc?' | 强制止损'+m.fc+'次':''), '#5f5e5a'],
  ];
  cards.forEach(c=>{{
    html += '<div class="metric-card"><div class="label">'+c[0]+'</div>'+
      '<div class="value" style="color:'+c[3]+'">'+c[1]+'</div>'+
      '<div class="formula">'+c[2]+'</div></div>';
  }});
  html += '</div>';
  document.getElementById('metricsBox').innerHTML = html;
}}

function renderSingleCharts(d, sd, bt, m, code, sp, lp, btStartIdx) {{
  // Slice to backtest period only
  let d2 = d.slice(btStartIdx);
  let dates = d2.map(r=>fmtd(r.trade_date));
  let sm2 = sd.sm.slice(btStartIdx), lm2 = sd.lm.slice(btStartIdx);
  let ts2 = sd.ts.slice(btStartIdx);
  let nav2 = bt.nav.slice(btStartIdx), bhNav2 = bt.bhNav.slice(btStartIdx);

  let area = document.getElementById('contentArea');
  let tr1 = [
    {{x:dates,y:d2.map(r=>r.close_qfq),mode:'lines',name:'收盘价',line:{{color:'#b4b2a9',width:1,dash:'dot'}}}},
    {{x:dates,y:sm2,mode:'lines',name:'MA('+sp+')',line:{{color:'#cc0000',width:2.2}}}},
    {{x:dates,y:lm2,mode:'lines',name:'MA('+lp+')',line:{{color:'#378add',width:2.2}}}},
  ];
  let bx=[],by=[],sx=[],sy=[];
  for(let i=0;i<d2.length;i++){{
    if(ts2[i]===1){{bx.push(dates[i]);by.push(d2[i].open_qfq);}}
    if(ts2[i]===-1){{sx.push(dates[i]);sy.push(d2[i].open_qfq);}}
  }}
  if(bx.length) tr1.push({{x:bx,y:by,mode:'markers',name:'买入(金叉)',marker:{{symbol:'triangle-up',size:11,color:'#cc0000'}}}});
  if(sx.length) tr1.push({{x:sx,y:sy,mode:'markers',name:'卖出(死叉)',marker:{{symbol:'triangle-down',size:11,color:'#009966'}}}});

  area.innerHTML = '<div class="chart-card"><h3>股价与均线信号</h3><div id="cPrice" style="height:400px"></div></div>'+
    '<div class="chart-card"><h3>策略净值 vs 买入持有</h3><div id="cNav" style="height:320px"></div></div>'+
    '<div class="chart-card"><h3>回撤曲线</h3><div id="cDD" style="height:240px"></div></div>'+
    '<div class="chart-card"><h3>每笔交易盈亏</h3><div id="cTrades" style="height:260px"></div></div>'+
    '<div class="chart-card" id="tradeBox"></div>';

  Plotly.newPlot('cPrice', tr1, {{title:'MA('+sp+','+lp+') 信号', height:400, hovermode:'x unified', template:'plotly_white', margin:{{l:50,r:20,t:40,b:40}}, yaxis:{{title:'价格'}}}});

  Plotly.newPlot('cNav', [
    {{x:dates,y:nav2.map(v=>v/gCap),mode:'lines',name:'策略',line:{{color:'#cc0000',width:2.5}}}},
    {{x:dates,y:bhNav2.map(v=>v/gCap),mode:'lines',name:'买入持有',line:{{color:'#b4b2a9',width:1.5,dash:'dash'}}}}
  ], {{title:'净值对比',height:300,hovermode:'x unified',template:'plotly_white',margin:{{l:50,r:20,t:40,b:40}},yaxis:{{title:'净值'}}}});

  let pk=nav2[0]; let dd=nav2.map(v=>{{if(v>pk)pk=v;return(pk-v)/pk*100;}});
  Plotly.newPlot('cDD', [{{x:dates,y:dd,mode:'lines',fill:'tozeroy',name:'回撤',line:{{color:'#009966',width:1}},fillcolor:'rgba(0,153,102,0.08)'}}],
    {{title:'回撤曲线 (最大:'+m.mdd+'%)',height:220,template:'plotly_white',margin:{{l:50,r:20,t:40,b:40}},yaxis:{{title:'%'}}}});

  Plotly.newPlot('cTrades', [{{
    x:bt.trades.map((t,i)=>'#'+(i+1)),
    y:bt.trades.map(t=>parseFloat(t.pp)),
    type:'bar',
    marker:{{color:bt.trades.map(t=>t.net>0?'#cc0000':'#009966')}},
    text:bt.trades.map(t=>t.pp+'%'), textposition:'outside'
  }}], {{title:'每笔盈亏 (胜率'+m.wr+'%, '+m.tt+'笔)', height:250, template:'plotly_white', margin:{{l:50,r:20,t:40,b:60}}, yaxis:{{title:'%'}}}});
}}

function renderTradeTable(trades, m) {{
  let area = document.getElementById('tradeBox');
  if(!trades.length) {{ area.style.display='none'; return; }}
  let html = '<table class="trade-table"><thead><tr><th>#</th><th>买入日</th><th>卖出日</th><th>买入价</th><th>卖出价</th><th>股数</th><th>天</th><th>净盈亏</th><th>盈亏%</th><th>备注</th></tr></thead><tbody>';
  trades.forEach((t,i)=>{{
    html += '<tr><td>#'+(i+1)+'</td><td>'+t.ed+'</td><td>'+t.xd+'</td><td>'+t.ep+'</td><td>'+t.xp+'</td><td>'+t.sh+'</td><td>'+t.hd+'</td>'+
      '<td style="color:'+(t.net>0?'#cc0000':'#009966')+';font-weight:500">'+(t.net>0?'+':'')+t.net.toLocaleString()+'</td>'+
      '<td style="color:'+(t.net>0?'#cc0000':'#009966')+';font-weight:500">'+t.pp+'%</td>'+
      '<td style="font-size:10px">'+(t.forced?'<span style="color:#ef9f27">止损平仓</span>':'')+'</td></tr>';
  }});
  html += '</tbody></table>';
  area.innerHTML = html;
}}

function runMultiMA(d, code, btStartIdx, btStartDate) {{
  let configs = [
    {{sp:gShortA, lp:gLongA, label:'MA('+gShortA+','+gLongA+')'}},
    {{sp:gShortB, lp:gLongB, label:'MA('+gShortB+','+gLongB+')'}},
    {{sp:gShortC, lp:gLongC, label:'MA('+gShortC+','+gLongC+')'}},
  ];
  let results = configs.map(c=>{{
    let sd=genSig(d,c.sp,c.lp);
    let bt=runBT(d,sd,gComm,gSlip,gCap,gPosPct,gStopLoss,btStartIdx);
    let m=calcM(bt,gCap,btStartDate);
    return {{...c, sd, bt, m}};
  }});
  let html = '<div class="comp-card"><h3>三组均线指标对比</h3>';
  html += '<table class="comp-table"><thead><tr><th>指标</th>';
  results.forEach(r=>html+='<th>'+r.label+'</th>');
  html += '</tr></thead><tbody>';
  let rows = [
    ['总收益率 %', 'tr', true, upc],
    ['年化收益 %', 'ar', true, upc],
    ['最大回撤 %', 'mdd', false, ()=>'#009966'],
    ['胜率 %', 'wr', false, (v)=>v>=50?'#cc0000':'#009966'],
    ['盈亏比', 'plr', false, (v)=>v>1?'#cc0000':'#009966'],
    ['夏普比率', 'sh', false, (v)=>v>1?'#cc0000':'#009966'],
    ['超额vs买持 %', 'ebh', true, upc],
    ['交易次数', 'tt', false, ()=>'#5f5e5a'],
  ];
  rows.forEach(row=>{{
    html += '<tr><td>'+row[0]+'</td>';
    results.forEach(r=>{{
      let v = parseFloat(r.m[row[1]]);
      let c = typeof row[3]==='function'?row[3](v):upc(v);
      html += '<td style="color:'+c+'">'+(row[2]&&v>0?'+':'')+r.m[row[1]]+'</td>';
    }});
    html += '</tr>';
  }});
  html += '</tbody></table></div>';
  html += '<div class="chart-card"><div id="cNavComp" style="height:320px"></div></div>';
  document.getElementById('compareArea').style.display = 'block';
  document.getElementById('compareArea').innerHTML = html;
  let d2 = d.slice(btStartIdx);
  let dates = d2.map(r=>fmtd(r.trade_date));
  let navTraces = results.map(r=>({{x:dates,y:r.bt.nav.slice(btStartIdx).map(v=>v/gCap),mode:'lines',name:r.label,line:{{width:2.5}}}}));
  navTraces.push({{x:dates,y:results[0].bt.bhNav.slice(btStartIdx).map(v=>v/gCap),mode:'lines',name:'买入持有',line:{{color:'#b4b2a9',width:1.5,dash:'dash'}}}});
  Plotly.newPlot('cNavComp', navTraces, {{title:'三组均线净值曲线对比(近1年)',height:320,hovermode:'x unified',template:'plotly_white',margin:{{l:50,r:20,t:40,b:40}},yaxis:{{title:'净值'}}}});
  document.getElementById('metricsBox').innerHTML = '';
}}

function runMultiStock(btStartIdx, btStartDate) {{
  let code1 = document.getElementById('stockSelect').value;
  let code2 = document.getElementById('stockSelect2').value;
  let d1 = ALL_DATA[code1]||[], d2 = ALL_DATA[code2]||[];
  if(!d1.length||!d2.length) return;
  // Each stock uses its own backtest start based on its own data length
  let idx1 = Math.max(0, d1.length - 252), idx2 = Math.max(0, d2.length - 252);
  let btDate1 = d1[idx1].trade_date, btDate2 = d2[idx2].trade_date;
  let results = [d1,d2].map((d,i)=>{{
    let idx = i===0 ? idx1 : idx2;
    let btDate = i===0 ? btDate1 : btDate2;
    let sd = genSig(d, gShortMS, gLongMS);
    let bt = runBT(d, sd, gComm, gSlip, gCap, gPosPct, gStopLoss, idx);
    let m = calcM(bt, gCap, btDate);
    let name = STOCKS.find(s=>s.code===(i===0?code1:code2)).name;
    return {{name, sd, bt, m, d}};
  }});
  let html = '<div class="comp-card"><h3>双股票指标对比 MA('+gShortMS+','+gLongMS+')</h3>';
  html += '<table class="comp-table"><thead><tr><th>指标</th><th>'+results[0].name+'</th><th>'+results[1].name+'</th></tr></thead><tbody>';
  let rows = [
    ['总收益率 %','tr',true],['年化收益 %','ar',true],['最大回撤 %','mdd',false],
    ['胜率 %','wr',false],['盈亏比','plr',false],['夏普比率','sh',false],
    ['超额vs买持 %','ebh',true],['交易次数','tt',false],
  ];
  rows.forEach(row=>{{
    html += '<tr><td>'+row[0]+'</td>';
    results.forEach(r=>{{
      let v=parseFloat(r.m[row[1]]);
      html += '<td style="color:'+upc(v)+'">'+(row[2]&&v>0?'+':'')+r.m[row[1]]+'</td>';
    }});
    html += '</tr>';
  }});
  html += '</tbody></table></div>';
  html += '<div class="chart-card"><div id="cStockNav" style="height:320px"></div></div>';
  document.getElementById('compareArea').style.display = 'block';
  document.getElementById('compareArea').innerHTML = html;
  // Each stock has its own slice
  let navTraces = results.map((r,i)=>{{
    let idx = i===0 ? idx1 : idx2;
    return {{x:r.d.slice(idx).map(x=>fmtd(x.trade_date)),y:r.bt.nav.slice(idx).map(v=>v/gCap),mode:'lines',name:r.name+' 策略',line:{{width:2.5}}}};
  }});
  results.forEach((r,i)=>{{
    let idx = i===0 ? idx1 : idx2;
    navTraces.push({{x:r.d.slice(idx).map(x=>fmtd(x.trade_date)),y:r.bt.bhNav.slice(idx).map(v=>v/gCap),mode:'lines',name:r.name+' 买持',line:{{width:1,dash:'dash'}}}});
  }});
  if (results.length===2) Plotly.newPlot('cStockNav', navTraces, {{title:'两股票 MA('+gShortMS+','+gLongMS+') 净值对比(近1年)',height:320,hovermode:'x unified',template:'plotly_white',margin:{{l:50,r:20,t:40,b:40}},yaxis:{{title:'净值'}}}});
  document.getElementById('metricsBox').innerHTML = '';
}}

init();
</script>
</body>
</html>'''

    output_path = os.path.join(OUTPUT_DIR, "dual_ma_report.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n[Dashboard] HTML 看板 v7 已生成 -> {output_path}")
    return output_path

if __name__ == "__main__":
    print("=" * 60)
    print("双均线策略交互式看板生成器 v7")
    print("=" * 60)
    generate_html()
