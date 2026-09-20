#!/usr/bin/env python3
"""Capital multiplication tracker.

Reads contributions.csv, transactions.csv and holdings.csv from this directory
and prints the numbers the daily report needs. No dependencies beyond stdlib so
it runs in any fresh session.

    python3 portfolio/tracker.py
    python3 portfolio/tracker.py --as-of 2026-10-01
"""

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_rows(name):
    """Read a CSV, skipping blank lines and '#' comment lines."""
    path = HERE / name
    if not path.exists():
        return []
    with path.open(newline="") as fh:
        lines = [ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    return list(csv.DictReader(lines))


def num(value, default=0.0):
    """Parse a possibly-blank CSV field as float."""
    if value is None:
        return default
    value = value.strip().replace(",", "")
    if not value:
        return default
    return float(value)


def parse_date(value):
    return dt.date.fromisoformat(value.strip())


def xirr(flows, guess=0.15):
    """Annualised money-weighted return. flows = [(date, amount)], investments
    negative, terminal value positive. Newton's method with bisection fallback."""
    if len(flows) < 2:
        return None
    if not (any(a < 0 for _, a in flows) and any(a > 0 for _, a in flows)):
        return None

    t0 = min(d for d, _ in flows)
    years = [((d - t0).days / 365.0, a) for d, a in flows]

    def npv(rate):
        total = 0.0
        for t, amount in years:
            # (1+rate) can go non-positive during iteration; guard it.
            base = 1.0 + rate
            if base <= 0:
                return float("inf")
            total += amount / base**t
        return total

    rate = guess
    for _ in range(100):
        value = npv(rate)
        if value == float("inf"):
            break
        step = 1e-6
        slope = (npv(rate + step) - value) / step
        if slope == 0 or slope == float("inf"):
            break
        new_rate = rate - value / slope
        if new_rate <= -0.9999:
            break
        if abs(new_rate - rate) < 1e-9:
            return new_rate
        rate = new_rate
    else:
        return rate

    # Fallback: bracket and bisect.
    low, high = -0.9999, 10.0
    if npv(low) * npv(high) > 0:
        return None
    for _ in range(200):
        mid = (low + high) / 2
        if npv(low) * npv(mid) <= 0:
            high = mid
        else:
            low = mid
    return (low + high) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    args = ap.parse_args()
    as_of = parse_date(args.as_of)

    contributions = read_rows("contributions.csv")
    transactions = read_rows("transactions.csv")
    holdings = read_rows("holdings.csv")

    contributed = sum(num(r["amount_inr"]) for r in contributions)
    charges = sum(num(r.get("charges_inr")) for r in transactions)

    # Realised P&L from SELLs, against the average cost recorded on the sell row.
    realised = 0.0
    for r in transactions:
        if r["action"].strip().upper() == "SELL":
            realised += num(r["price_inr"]) * num(r["qty"]) - num(r.get("cost_basis_inr"))

    stale = []
    missing_price = []
    invested = 0.0
    market_value = 0.0
    lines = []
    for r in holdings:
        symbol = r["symbol"].strip()
        qty = num(r["qty"])
        avg = num(r["avg_cost_inr"])
        last = num(r.get("last_price_inr"))
        cost = qty * avg
        invested += cost
        if last == 0:
            missing_price.append(symbol)
            value = cost
        else:
            value = qty * last
        market_value += value
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost else 0.0

        price_date = (r.get("last_price_date") or "").strip()
        if price_date:
            try:
                age = (as_of - parse_date(price_date)).days
                if age > 5:
                    stale.append(f"{symbol} ({age}d old)")
            except ValueError:
                stale.append(f"{symbol} (bad date)")

        lines.append(
            (symbol, qty, avg, last, cost, value, pnl, pnl_pct,
             (r.get("status") or "").strip() or "-")
        )

    # Cash = contributions not yet spent, net of charges, plus sale proceeds.
    deployed = sum(
        num(r["price_inr"]) * num(r["qty"])
        for r in transactions
        if r["action"].strip().upper() == "BUY"
    )
    proceeds = sum(
        num(r["price_inr"]) * num(r["qty"])
        for r in transactions
        if r["action"].strip().upper() == "SELL"
    )
    cash = contributed - deployed + proceeds - charges

    total_value = market_value + cash
    total_pnl = total_value - contributed
    multiple = (total_value / contributed) if contributed else None

    flows = [(parse_date(r["date"]), -num(r["amount_inr"])) for r in contributions]
    if flows and total_value > 0:
        flows.append((as_of, total_value))
    rate = xirr(flows)

    print(f"PORTFOLIO — {as_of.isoformat()}")
    print("=" * 58)
    if not holdings:
        print("No holdings recorded.")
    else:
        head = f"{'SYMBOL':<14}{'QTY':>7}{'AVG':>10}{'LAST':>10}{'VALUE':>12}{'P&L%':>9}  STATUS"
        print(head)
        print("-" * 58)
        for (sym, qty, avg, last, cost, value, pnl, pct, status) in lines:
            last_txt = f"{last:,.2f}" if last else "n/a"
            print(
                f"{sym:<14}{qty:>7.0f}{avg:>10,.2f}{last_txt:>10}"
                f"{value:>12,.0f}{pct:>8.1f}%  {status}"
            )
        print("-" * 58)

    print(f"Contributed      : Rs {contributed:>12,.2f}")
    print(f"Invested at cost : Rs {invested:>12,.2f}")
    print(f"Holdings value   : Rs {market_value:>12,.2f}")
    print(f"Cash             : Rs {cash:>12,.2f}")
    print(f"Total value      : Rs {total_value:>12,.2f}")
    print(f"Charges paid     : Rs {charges:>12,.2f}")
    print(f"Realised P&L     : Rs {realised:>12,.2f}")
    print(f"Total P&L        : Rs {total_pnl:>12,.2f}"
          + (f"  ({total_pnl / contributed * 100:+.2f}%)" if contributed else ""))
    if multiple is None:
        print("CAPITAL MULTIPLE : n/a (no capital contributed yet)")
    else:
        print(f"CAPITAL MULTIPLE : {multiple:.3f}x")
        for target in (1.25, 1.5, 2.0, 3.0, 5.0):
            need = contributed * target - total_value
            mark = "REACHED" if need <= 0 else f"needs Rs {need:,.0f} more value"
            print(f"  {target:>4.2f}x        : {mark}")
    print("XIRR             : " + (f"{rate * 100:.2f}%" if rate is not None else "n/a"))

    if missing_price:
        print("\nWARNING no last_price_inr (held at cost): " + ", ".join(missing_price))
    if stale:
        print("WARNING stale prices: " + ", ".join(stale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
