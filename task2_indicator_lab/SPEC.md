# Spec: 寒武纪(688256.SH) 技术指标计算与分析

## 目标

以寒武纪前复权日线数据为基础，用 Jupyter Notebook 完整展示 MACD、RSI、Bollinger Bands、ATR 四个技术指标的计算过程与可视化，并针对寒武纪的高波动特性做参数适配分析。

## 状态

- [x] MACD 计算与可视化
- [x] RSI 计算与可视化
- [x] Bollinger Bands 计算与可视化
- [x] ATR 计算与可视化
- [x] 四指标联动面板
- [x] 寒武纪特性 & 参数建议

---

## 1. 数据源

| 项 | 值 |
|---|---|
| 标的 | 寒武纪 688256.SH |
| 文件 | `../task1/cambricon_daily_data_qfq.json` |
| 复权方式 | 前复权（qfq_close，已处理 2026-05-08 送转股） |
| 区间 | 2025-07-01 ~ 2026-07-01，243 日 |
| 价格字段 | open, high, low, close（均为前复权） |
| 涨跌幅 | pct_chg_adjusted（基于前复权价重算） |

> **注意**：前复权版本中第一日的 pct_chg 为 NaN（已确认，正常），后续指标计算依赖 pct_chg.close() 时自动略过第一行。

## 2. 指标参数设计

### 2.1 MACD

| 参数 | 标准值 | 寒武纪适配 | 理由 |
|---|---|---|---|
| fast | 12 | 8 | 高波动下缩短快线周期，提高灵敏度 |
| slow | 26 | 21 | 慢线相应缩短，保持信号及时 |
| signal | 9 | 5 | 金叉/死叉识别更快 |

> Notebook 中先展示标准(12,26,9)，再提供(8,21,5)对照。

输出字段：`dif`, `dea`, `macd_hist`
信号标记：`golden_cross`（金叉日 True）、`death_cross`（死叉日 True）

### 2.2 RSI

| 参数 | 标准值 | 寒武纪适配 | 理由 |
|---|---|---|---|
| period | 14 | 10 | 科创板 20% 涨跌幅上限导致涨跌幅度大，缩短周期增加灵敏度 |
| overbought | 70 | 75 | 频繁触及 70 级，提高阈值过滤噪音 |
| oversold | 30 | 25 | 同理 |

> 同样在 Notebook 中展示标准版和适配版，并说明阈值调整的依据（基于数据中极端涨跌日占比 19.3%）。

输出字段：`rsi_14`, `rsi_10`

### 2.3 Bollinger Bands

| 参数 | 标准值 | 寒武纪适配 | 理由 |
|---|---|---|---|
| window | 20 | 20 | 保持标准，窗口不宜过短 |
| multiplier | 2.0 | 2.5 | 高波动下 2 倍标准差的触碰频率过高（回测数据近 30% 的交易日触及上下轨），放宽到 2.5 减少假信号 |

输出字段：`bb_mid`, `bb_upper`, `bb_lower`, `bb_width`（上轨-下轨）, `bb_pct`（价格在通道中的相对位置 0~1）

Squeeze 判断：`bb_width` 降到过去 125 日（约半年）的 10% 分位以下为 squeeze。

### 2.4 ATR

| 参数 | 值 | 说明 |
|---|---|---|
| period | 14 | 标准参数，不动 |
| Wilder 平滑 | 是 | 首日 SMA，后续 EMA(α=1/14) |

输出字段：`tr`（True Range）, `atr_14`
衍生：`atr_pct` = ATR / close（百分比波动率，更易跨时段对比）

## 3. Notebook 结构

```
01 引入 & 数据加载        [代码]  导入库，读取 JSON，校验字段
02 数据预处理 & 确认复权   [代码]  日频检查、缺失处理、除权日标注
03 MACD 指标              [代码+图] 标准参数 + 寒武纪参数，双图对比
04 RSI 指标               [代码+图] 14日 + 10日，双图对比，阈值线
05 Bollinger Bands        [代码+图] 标准 2σ + 2.5σ，通道图 + squeeze 标注
06 ATR 指标               [代码+图] TR + ATR14，价格叠加，止损示意
07 四指标联动面板          [图]     matplotlib 4 子图或 plotly subplots
08 寒武纪特性 & 参数建议    [MD]    综合解读 + 参数推荐 + 回测方向建议
```

## 4. 可视化要求

- 中国股市配色：涨红(#E0322B)，跌绿(#1AA260)
- K 线部分用 plotly Candlestick（与之前 K 线图一致）
- MACD 子图：DIF 线 + DEA 线 + 柱状图，金叉死叉箭头标注
- RSI 子图：0-100 纵轴，70/30 或 75/25 虚线
- 布林带：close 曲线 + 三轨 + squeeze 区域高亮
- ATR：价格 + ATR(14) 双轴，或单独 ATR 时间序列
- 四指标联动面板优先用 plotly make_subplots（rows=4, cols=1, shared_xaxes=True）
- 每张图标题明确标注参数

## 5. 技术实现

- 编程语言：Python 3.13
- 核心库：pandas, numpy, plotly
- 环境：managed venv（已有 plotly + pandas）
- 输出：`cambricon_indicators.ipynb`
- 额外输出：`cambricon_indicators_daily.csv`（含所有计算字段的完整日数据）

### 5.1 指标计算公式（Python 实现要点）

```python
# MACD
ema_fast = close.ewm(span=fast, adjust=False).mean()
ema_slow = close.ewm(span=slow, adjust=False).mean()
dif = ema_fast - ema_slow
dea = dif.ewm(span=signal, adjust=False).mean()
macd_hist = 2 * (dif - dea)

# RSI
delta = close.diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
rs = avg_gain / avg_loss
rsi = 100 - 100 / (1 + rs)

# Bollinger
bb_mid = close.rolling(window=20).mean()
bb_std = close.rolling(window=20).std()
bb_upper = bb_mid + multiplier * bb_std
bb_lower = bb_mid - multiplier * bb_std

# ATR (Wilder)
high_low = high - low
high_prev = abs(high - close.shift(1))
low_prev = abs(low - close.shift(1))
tr = pd.concat([high_low, high_prev, low_prev], axis=1).max(axis=1)
atr = tr.ewm(alpha=1/14, adjust=False).mean()
```

### 5.2 跨文件引用

Notebook 中相对路径引用前复权数据：
```python
DATA_PATH = "../task1/cambricon_daily_data_qfq.json"
```

## 6. 验收标准

- [ ] Notebook 可完整运行（Run All 无报错）
- [ ] 四个指标均有标准参数 + 寒武纪适配参数的对比展示
- [ ] 每张图有标题、图例、中文坐标轴标签
- [ ] Cell 间有 Markdown 说明（解释每个指标的含义和观察）
- [ ] 最终输出 `cambricon_indicators_daily.csv` 包含所有计算列
- [ ] 寒武纪特性分析至少包含：高波动特征、参数选择理由、指标联动观察、实际交易场景建议
- [ ] K 线和所有指标图统一使用前复权价格

## 7. 已知限制

- 港股 `hk_adjfactor` 接口无权限，本次仅限 A 股寒武纪
- tushare 每日数据仅至 2026-07-01（当日），非实时
- 指标计算未包含未来函数泄漏（rolling/ewm 均基于历史数据）
- ATR 的 `atr_pct` 可能有分母为 0 问题（不会，close 不可能为 0）
