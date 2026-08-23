"""
USAID Supply Chain Shipment Pricing — 15 minute go/no-go check.

Question: does this data have real signal, or is it another DataCo?
Run:  python profile_usaid.py
Paste the output back into the chat.
"""

import pandas as pd
import numpy as np

PATH = r"C:\Users\PC\Downloads\archive (1)\SCMS_Delivery_History_Dataset.csv"   # adjust to your filename

df = pd.read_csv(PATH, low_memory=False)


def find(*words):
    """Locate a column by fuzzy keyword match, so exact naming doesn't matter."""
    for c in df.columns:
        low = c.lower()
        if all(w.lower() in low for w in words):
            return c
    return None


print("=" * 70)
print("SHAPE:", df.shape)
print("=" * 70)
print("\nCOLUMNS:")
for c in df.columns:
    print(f"  {c!r:45}  nulls={df[c].isna().sum():>6}  distinct={df[c].nunique():>6}")

# ---------------------------------------------------------------
mode = find("shipment", "mode")
sched = find("scheduled", "delivery")
deliv = find("delivered", "client")
freight = find("freight", "cost")
weight = find("weight")
value = find("line item value")
country = find("country")
vendor = find("vendor") if find("vendor") and "inco" not in find("vendor").lower() else None
qty = find("line item quantity")

print("\nRESOLVED COLUMNS:", dict(mode=mode, sched=sched, deliv=deliv,
                                 freight=freight, weight=weight,
                                 value=value, country=country, vendor=vendor))

# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("1. SHIPMENT MODE MIX")
print("=" * 70)
if mode:
    print((df[mode].value_counts(dropna=False, normalize=True) * 100).round(2).to_string())

# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("2. DELIVERY PERFORMANCE — is there real variation?")
print("=" * 70)
if sched and deliv:
    s = pd.to_datetime(df[sched], errors="coerce")
    d = pd.to_datetime(df[deliv], errors="coerce")
    df["_delay_days"] = (d - s).dt.days
    print("parsed scheduled:", s.notna().sum(), " delivered:", d.notna().sum())
    print("\ndelay in days (negative = early):")
    print(df["_delay_days"].describe(
        percentiles=[.05, .25, .5, .75, .9, .95]).round(2).to_string())
    print("\non-time rate (delay <= 0): ",
          round((df["_delay_days"] <= 0).mean() * 100, 2), "%")
    if mode:
        print("\nBY MODE — this is the key table:")
        print(df.groupby(mode)["_delay_days"].agg(
            n="size", mean="mean", p50="median",
            p90=lambda x: x.quantile(.9),
            std="std",
            on_time_pct=lambda x: (x <= 0).mean() * 100).round(2).to_string())

# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("3. FREIGHT COST — how messy, and does mode drive it?")
print("=" * 70)
if freight:
    raw = df[freight].astype(str)
    numeric = pd.to_numeric(raw.str.replace(r"[^0-9.\-]", "", regex=True),
                            errors="coerce")
    print("rows:", len(raw))
    print("parse as number:", numeric.notna().sum(),
          f"({numeric.notna().mean()*100:.1f}%)")
    print("\nnon-numeric values (top 10) — the real cleaning work:")
    print(raw[numeric.isna()].value_counts().head(10).to_string())
    df["_freight"] = numeric
    if mode:
        print("\nfreight cost by mode:")
        print(df.groupby(mode)["_freight"].agg(
            n="size", median="median", mean="mean").round(2).to_string())

if weight:
    w = pd.to_numeric(df[weight].astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
                      errors="coerce")
    df["_weight"] = w
    print("\nweight parses as number:", f"{w.notna().mean()*100:.1f}%")
    if freight and mode:
        ok = df["_freight"].notna() & df["_weight"].notna() & (df["_weight"] > 0)
        df.loc[ok, "_cost_per_kg"] = df.loc[ok, "_freight"] / df.loc[ok, "_weight"]
        print("\nCOST PER KG BY MODE — the money table:")
        print(df[ok].groupby(mode)["_cost_per_kg"].agg(
            n="size", median="median",
            p25=lambda x: x.quantile(.25),
            p75=lambda x: x.quantile(.75)).round(2).to_string())

# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("4. SIGNAL CHECK — do dimensions actually differentiate?")
print("=" * 70)
for dim in [c for c in [country, vendor, find("product", "group")] if c]:
    top = df[dim].value_counts().head(8).index
    sub = df[df[dim].isin(top)]
    print(f"\n{dim} (top 8) vs delay days:")
    print(sub.groupby(dim)["_delay_days"].agg(
        n="size", p50="median",
        on_time_pct=lambda x: (x <= 0).mean() * 100).round(2).to_string())

# ---------------------------------------------------------------
print("\n" + "=" * 70)
print("5. TIME COVERAGE")
print("=" * 70)
if sched:
    s = pd.to_datetime(df[sched], errors="coerce")
    print("range:", s.min(), "->", s.max())
    print("\nshipments per year:")
    print(s.dt.year.value_counts().sort_index().to_string())
