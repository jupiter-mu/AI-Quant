"""
双均线策略核心引擎
===================
DataLoader | 复权处理 | MA计算 | 信号生成 | 交易成本 | 回测引擎 | 8指标
"""

import json
import os
import warnings
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# 0. 路径配置
# ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# 1. 数据加载与质检
# ──────────────────────────────────────────────
class DataLoader:
    """加载股票日线数据，支持 Tushare MCP / akshare / 本地缓存"""

    TRADING_DAYS_PER_YEAR = 252
    MIN_ROWS_FOR_BACKTEST = 30

    @staticmethod
    def load_from_cached(json_path: str) -> pd.DataFrame:
        """从本地 JSON 加载已缓存数据"""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df["trade_date"] = df["trade_date"].astype(str)
        df = df.sort_values("trade_date").reset_index(drop=True)
        return df

    @staticmethod
    def save_cache(df: pd.DataFrame, json_path: str):
        """保存为 JSON 缓存"""
        df_out = df.copy()
        for col in df_out.select_dtypes(include=["datetime64"]).columns:
            df_out[col] = df_out[col].astype(str)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(df_out.to_dict(orient="records"), f, ensure_ascii=False, indent=2)
        print(f"[Cache] 已保存 {len(df)} 行 → {json_path}")

    @staticmethod
    def load_from_json_records(records: list) -> pd.DataFrame:
        """从 tushare MCP 返回的 JSON records 构建 DataFrame"""
        df = pd.DataFrame(records)
        required_cols = ["trade_date", "open", "high", "low", "close", "vol", "amount"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"缺少必要字段: {col}")
        numeric_cols = ["open", "high", "low", "close", "vol", "amount"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["trade_date"] = df["trade_date"].astype(str)
        df = df.sort_values("trade_date").reset_index(drop=True)
        return df

    @staticmethod
    def quality_check(df: pd.DataFrame) -> Dict:
        """
        数据质量检测，返回诊断报告 dict
        包含：缺失值、OHLC逻辑、日期间隔、描述性统计
        """
        report = {}
        report["rows"] = len(df)
        report["date_range"] = f"{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}"

        # 缺失值
        missing = df.isnull().sum()
        missing = missing[missing > 0]
        report["missing"] = missing.to_dict() if len(missing) else "无缺失值"

        # OHLC 逻辑校验
        ohlc_issues = []
        if (df["high"] < df["open"]).any():
            ohlc_issues.append("high < open")
        if (df["high"] < df["close"]).any():
            ohlc_issues.append("high < close")
        if (df["low"] > df["open"]).any():
            ohlc_issues.append("low > open")
        if (df["low"] > df["close"]).any():
            ohlc_issues.append("low > close")
        report["ohlc_valid"] = "通过" if not ohlc_issues else f"异常: {', '.join(ohlc_issues)}"

        # 日期间隔检查
        df["date_parsed"] = pd.to_datetime(df["trade_date"], format="%Y%m%d", errors="coerce")
        gaps = df["date_parsed"].diff().dropna()
        large_gaps = gaps[gaps > pd.Timedelta(days=3)]
        report["date_gaps"] = len(large_gaps)
        report["max_gap_days"] = int(large_gaps.max().days) if len(large_gaps) else 0

        # 描述性统计
        report["desc"] = {
            "close_mean": round(float(df["close"].mean()), 2),
            "close_std": round(float(df["close"].std()), 2),
            "close_min": round(float(df["close"].min()), 2),
            "close_max": round(float(df["close"].max()), 2),
            "daily_volatility": round(float(df["close"].pct_change().std() * np.sqrt(252) * 100), 2),
        }

        # 复权因子校验（如果有）
        if "adj_factor" in df.columns:
            adj_diffs = df["adj_factor"].diff().dropna()
            adj_jumps = adj_diffs[adj_diffs.abs() > 0.001]
            report["adj_events"] = len(adj_jumps)

        df.drop(columns=["date_parsed"], inplace=True, errors="ignore")
        return report


# ──────────────────────────────────────────────
# 2. 复权处理
# ──────────────────────────────────────────────
def apply_qfq(df: pd.DataFrame, adj_factor_col: str = "adj_factor") -> pd.DataFrame:
    """
    前复权（QFQ）处理
    qfq_price = raw_price * adj_factor / adj_factor_latest
    """
    df = df.copy()
    latest_adj = df[adj_factor_col].iloc[-1]
    if latest_adj <= 0:
        raise ValueError("复权因子异常")

    price_cols = ["open", "high", "low", "close"]
    for col in price_cols:
        if col in df.columns:
            df[f"{col}_qfq"] = df[col] * df[adj_factor_col] / latest_adj

    if "pre_close" in df.columns:
        df["pre_close_qfq"] = df["pre_close"] * df[adj_factor_col] / latest_adj

    df["pct_chg_qfq"] = df["close_qfq"].pct_change() * 100
    return df


# ──────────────────────────────────────────────
# 3. 均线计算
# ──────────────────────────────────────────────
def calc_sma(series: pd.Series, period: int) -> pd.Series:
    """简单移动平均 SMA(n)，min_periods=period 确保完整窗口"""
    return series.rolling(window=period, min_periods=period).mean()


# ──────────────────────────────────────────────
# 4. 交易信号生成
# ──────────────────────────────────────────────
@dataclass
class SignalResult:
    """信号生成结果"""
    df: pd.DataFrame              # 含 short_ma / long_ma / signal 列
    golden_cross_dates: List[str] # 金叉信号确认日期
    death_cross_dates: List[str]  # 死叉信号确认日期
    golden_exec_dates: List[str]  # 金叉执行日期（t+1）
    death_exec_dates: List[str]   # 死叉执行日期（t+1）


def generate_signals(df: pd.DataFrame, short_period: int, long_period: int,
                     price_col: str = "close_qfq") -> SignalResult:
    """
    生成双均线交易信号

    金叉：short_ma[t] > long_ma[t] AND short_ma[t-1] <= long_ma[t-1]
    死叉：short_ma[t] < long_ma[t] AND short_ma[t-1] >= long_ma[t-1]

    信号在 day t 收盘后确认，实际交易在 day t+1 开盘执行
    仅在两个 MA 都有全窗口数据后才检测信号
    """
    df = df.copy()

    df["short_ma"] = calc_sma(df[price_col], short_period)
    df["long_ma"] = calc_sma(df[price_col], long_period)

    start_idx = max(short_period, long_period)

    short = df["short_ma"].values
    long = df["long_ma"].values

    signal = np.zeros(len(df), dtype=int)
    golden_cross = []
    death_cross = []

    prev_relation = 0  # 0=unknown, 1=short>long, -1=short<long

    for i in range(start_idx, len(df)):
        if np.isnan(short[i]) or np.isnan(long[i]):
            continue

        cur_relation = 1 if short[i] > long[i] else -1

        if prev_relation != 0:
            if cur_relation == 1 and prev_relation == -1:
                signal[i] = 1
                golden_cross.append(df["trade_date"].iloc[i])
            elif cur_relation == -1 and prev_relation == 1:
                signal[i] = -1
                death_cross.append(df["trade_date"].iloc[i])

        prev_relation = cur_relation

    df["signal"] = signal
    df["trade_signal"] = pd.Series(
        np.concatenate([[0], signal[:-1]]), index=df.index
    ).astype(int)

    golden_exec = df.loc[df["trade_signal"] == 1, "trade_date"].tolist()
    death_exec = df.loc[df["trade_signal"] == -1, "trade_date"].tolist()

    return SignalResult(
        df=df,
        golden_cross_dates=golden_cross,
        death_cross_dates=death_cross,
        golden_exec_dates=golden_exec,
        death_exec_dates=death_exec,
    )


# ──────────────────────────────────────────────
# 5. 交易成本模型
# ──────────────────────────────────────────────
@dataclass
class CostModel:
    commission: float = 0.0003   # 手续费率，默认万三
    slippage: float = 0.0001     # 滑点，默认万一
    stamp_duty: float = 0.0005   # 印花税（仅卖出，A股0.05%）

    def buy_cost_rate(self) -> float:
        """买入成本比例"""
        return self.commission + self.slippage

    def sell_cost_rate(self) -> float:
        """卖出成本比例"""
        return self.commission + self.slippage + self.stamp_duty

    def apply_buy(self, price: float) -> float:
        return price * (1 + self.buy_cost_rate())

    def apply_sell(self, price: float) -> float:
        return price * (1 - self.sell_cost_rate())


# ──────────────────────────────────────────────
# 6. 回测引擎
# ──────────────────────────────────────────────
@dataclass
class TradeRecord:
    """单笔交易记录"""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: int
    gross_pnl: float
    net_pnl: float
    pnl_pct: float
    holding_days: int
    trade_type: str  # "buy_sell" for long-only


@dataclass
class BacktestResult:
    """回测结果"""
    nav_series: pd.Series           # 每日净值
    daily_returns: pd.Series        # 每日收益率
    trades: List[TradeRecord]       # 交易记录
    initial_capital: float
    final_nav: float
    buyhold_nav: pd.Series          # 买入持有净值
    benchmark_nav: Optional[pd.Series] = None  # 基准净值（沪深300）


def run_backtest(df: pd.DataFrame, signal_result: SignalResult,
                 cost_model: CostModel = CostModel(),
                 initial_capital: float = 100000) -> BacktestResult:
    """
    逐日模拟双均线策略交易

    规则：
    - trade_signal == 1  →  空仓时全仓买入 @ open[t]
    - trade_signal == -1 →  持仓时全仓卖出 @ open[t]
    - 每日净值 = cash + shares * close[t]
    - 买入持有净值：始终满仓，作为比较基准
    """
    df = df.copy()
    n = len(df)

    position = 0      # 0 = 空仓, 1 = 持仓
    cash = initial_capital
    shares = 0
    entry_price = 0.0
    entry_date = ""

    nav = np.zeros(n)
    trades: List[TradeRecord] = []

    for i in range(n):
        row = df.iloc[i]
        date = row["trade_date"]
        open_p = row["open_qfq"] if "open_qfq" in df.columns else row["open"]
        close_p = row["close_qfq"] if "close_qfq" in df.columns else row["close"]
        sig = int(row.get("trade_signal", 0))

        # --- 执行交易 ---
        if sig == 1 and position == 0 and open_p > 0:
            buy_p = cost_model.apply_buy(open_p)
            shares = int(cash / buy_p / 100) * 100  # A股最小100股（1手）
            if shares >= 100:
                spent = shares * buy_p
                cash -= spent
                position = 1
                entry_price = open_p
                entry_date = date

        elif sig == -1 and position == 1 and open_p > 0:
            sell_p = cost_model.apply_sell(open_p)
            proceeds = shares * sell_p
            gross = (open_p - entry_price) * shares
            net = proceeds - (entry_price * shares * (1 + cost_model.buy_cost_rate()))
            pnl_pct = (net / (entry_price * shares * (1 + cost_model.buy_cost_rate()))) * 100
            holding_days = _count_trading_days(df, entry_date, date)

            trades.append(TradeRecord(
                entry_date=entry_date, exit_date=date,
                entry_price=entry_price, exit_price=open_p,
                shares=shares, gross_pnl=round(gross, 2),
                net_pnl=round(net, 2), pnl_pct=round(pnl_pct, 2),
                holding_days=holding_days, trade_type="buy_sell"
            ))

            cash += proceeds
            shares = 0
            position = 0

        # --- 当日净值 ---
        nav[i] = cash + shares * close_p

    # 买入持有净值（始终满仓）
    buyhold_shares = int(initial_capital / (df.iloc[0]["open_qfq"] if "open_qfq" in df.columns else df.iloc[0]["open"]) / 100) * 100
    if buyhold_shares >= 100:
        buyhold_cost = buyhold_shares * (df.iloc[0]["open_qfq"] if "open_qfq" in df.columns else df.iloc[0]["open"])
        buyhold_cash = initial_capital - buyhold_cost * (1 + cost_model.buy_cost_rate())
    else:
        buyhold_shares = 0
        buyhold_cash = initial_capital

    buyhold_nav = np.zeros(n)
    for i in range(n):
        close_p = df.iloc[i]["close_qfq"] if "close_qfq" in df.columns else df.iloc[i]["close"]
        buyhold_nav[i] = buyhold_cash + buyhold_shares * close_p

    return BacktestResult(
        nav_series=pd.Series(nav, index=df.index),
        daily_returns=pd.Series(nav, index=df.index).pct_change().fillna(0),
        trades=trades,
        initial_capital=initial_capital,
        final_nav=nav[-1],
        buyhold_nav=pd.Series(buyhold_nav, index=df.index),
    )


def _count_trading_days(df: pd.DataFrame, date_from: str, date_to: str) -> int:
    """两个交易日期之间的交易日数"""
    mask = (df["trade_date"] >= date_from) & (df["trade_date"] <= date_to)
    return mask.sum()


# ──────────────────────────────────────────────
# 7. 指标计算
# ──────────────────────────────────────────────
@dataclass
class MetricsResult:
    """8 个评估指标"""
    total_return: float            # 总收益率 (%)
    annual_return: float           # 年化收益率 (%)
    max_drawdown: float            # 最大回撤 (%)
    win_rate: float                # 胜率 (%)
    profit_loss_ratio: float       # 盈亏比
    sharpe_ratio: float            # 夏普比率
    excess_vs_buyhold: float       # 超额收益① — vs 买入持有 (%)
    alpha: float                   # 超额收益② — Jensen's Alpha (%)
    total_trades: int              # 总交易次数
    avg_holding_days: float        # 平均持仓天数
    buyhold_return: float          # 买入持有总收益 (%)
    annual_volatility: float       # 策略年化波动率 (%)


def calc_metrics(result: BacktestResult, rf: float = 0.02,
                 benchmark_nav: Optional[pd.Series] = None,
                 benchmark_returns: Optional[pd.Series] = None) -> MetricsResult:
    """
    计算 8 个评估指标
    """
    nav = result.nav_series.values
    n = len(nav)
    trading_days = n
    years = trading_days / 252

    initial = result.initial_capital
    final = result.final_nav

    # 1. 总收益率
    total_return = (final / initial - 1) * 100

    # 2. 年化收益率
    annual_return = ((final / initial) ** (1 / max(years, 0.01)) - 1) * 100

    # 3. 最大回撤
    peak = np.maximum.accumulate(nav)
    drawdowns = (nav - peak) / peak * 100
    max_drawdown = abs(drawdowns.min())

    # 4. 胜率
    trades = result.trades
    if trades:
        winning = sum(1 for t in trades if t.net_pnl > 0)
        win_rate = winning / len(trades) * 100
    else:
        win_rate = 0

    # 5. 盈亏比
    if trades:
        win_trades = [t.net_pnl for t in trades if t.net_pnl > 0]
        loss_trades = [abs(t.net_pnl) for t in trades if t.net_pnl <= 0]
        avg_win = np.mean(win_trades) if win_trades else 0
        avg_loss = np.mean(loss_trades) if loss_trades else 1
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
    else:
        profit_loss_ratio = 0

    # 6. 夏普比率
    daily_returns = result.daily_returns.values[1:]  # 去掉首日 NaN
    annual_volatility = np.std(daily_returns) * np.sqrt(252) * 100
    sharpe_ratio = (annual_return - rf * 100) / annual_volatility if annual_volatility > 0 else 0

    # 7. 超额收益① — 相对买入持有
    buyhold_final = result.buyhold_nav.values[-1]
    buyhold_return = (buyhold_final / initial - 1) * 100
    excess_vs_buyhold = total_return - buyhold_return

    # 8. 超额收益② — Jensen's Alpha
    alpha = 0.0
    if benchmark_returns is not None and len(benchmark_returns) >= len(result.daily_returns):
        strategy_daily = result.daily_returns.values[1:]
        bench_daily = benchmark_returns.values[1:len(strategy_daily)+1]

        valid = ~(np.isnan(strategy_daily) | np.isnan(bench_daily))
        if valid.sum() > 30:
            cov = np.cov(strategy_daily[valid], bench_daily[valid])
            beta = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1.0
            bench_annual = ((1 + bench_daily[valid]).prod() ** (252 / len(bench_daily[valid])) - 1) * 100
            alpha = annual_return - (rf * 100 + beta * (bench_annual - rf * 100))

    # 平均持仓天数
    avg_holding = np.mean([t.holding_days for t in trades]) if trades else 0

    return MetricsResult(
        total_return=round(total_return, 2),
        annual_return=round(annual_return, 2),
        max_drawdown=round(max_drawdown, 2),
        win_rate=round(win_rate, 1),
        profit_loss_ratio=round(profit_loss_ratio, 2),
        sharpe_ratio=round(sharpe_ratio, 2),
        excess_vs_buyhold=round(excess_vs_buyhold, 2),
        alpha=round(alpha, 2),
        total_trades=len(trades),
        avg_holding_days=round(avg_holding, 1),
        buyhold_return=round(buyhold_return, 2),
        annual_volatility=round(annual_volatility, 2),
    )


# ──────────────────────────────────────────────
# 8. 便捷函数：一键回测
# ──────────────────────────────────────────────
def full_pipeline(df: pd.DataFrame, short_period: int = 5, long_period: int = 15,
                  commission: float = 0.0003, slippage: float = 0.0001,
                  initial_capital: float = 1000000,
                  benchmark_nav: Optional[pd.Series] = None,
                  benchmark_returns: Optional[pd.Series] = None):
    """
    一键执行完整回测流程：
    均线计算 → 信号生成 → 回测 → 指标计算
    """
    price_col = "close_qfq" if "close_qfq" in df.columns else "close"

    signal_result = generate_signals(df, short_period, long_period, price_col)

    cost_model = CostModel(commission=commission, slippage=slippage)

    backtest_result = run_backtest(signal_result.df, signal_result, cost_model, initial_capital)

    metrics = calc_metrics(backtest_result, benchmark_returns=benchmark_returns)

    return signal_result, backtest_result, metrics


if __name__ == "__main__":
    # 自检：用寒武纪缓存数据做一次快速回测
    cache_path = os.path.join(DATA_DIR, "688256_daily_qfq.json")
    if os.path.exists(cache_path):
        df = DataLoader.load_from_cached(cache_path)
        report = DataLoader.quality_check(df)
        print("=" * 60)
        print("数据质量报告")
        print("=" * 60)
        for k, v in report.items():
            print(f"  {k}: {v}")

        sig, bt, m = full_pipeline(df)
        print("\n" + "=" * 60)
        print("回测指标 (MA5/15, 默认成本)")
        print("=" * 60)
        print(f"  总收益率:     {m.total_return:+.2f}%")
        print(f"  年化收益率:    {m.annual_return:+.2f}%")
        print(f"  最大回撤:     {m.max_drawdown:.2f}%")
        print(f"  胜率:        {m.win_rate:.1f}%")
        print(f"  盈亏比:       {m.profit_loss_ratio:.2f}")
        print(f"  夏普比率:      {m.sharpe_ratio:.2f}")
        print(f"  超额(vs持有):  {m.excess_vs_buyhold:+.2f}%")
        print(f"  Alpha:       {m.alpha:+.2f}%")
        print(f"  交易次数:      {m.total_trades} 笔")
        print(f"  平均持仓:      {m.avg_holding_days:.0f} 天")
        print(f"  买入持有收益:   {m.buyhold_return:+.2f}%")
    else:
        print(f"缓存数据不存在: {cache_path}")
        print("请先运行数据获取步骤")
