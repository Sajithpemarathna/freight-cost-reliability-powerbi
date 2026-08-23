"""
USAID Supply Chain Shipment Pricing -> star schema Parquet for Power BI.

    pip install pandas pyarrow
    python prep.py

Writes to data/curated/. Commit that folder; keep the raw CSV gitignored.
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

SRC = r"C:\Users\PC\Downloads\archive (1)\SCMS_Delivery_History_Dataset.csv"
OUT = Path("data/curated")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SRC, low_memory=False)
df.columns = [c.strip() for c in df.columns]

# ---------------------------------------------------------------
# Messy numeric columns: three kinds of missing, each meaningful.
# A pure number is a number. Everything else is a REASON, not a value.
# ---------------------------------------------------------------
PURE_NUMBER = re.compile(r"^\s*\$?\s*[\d,]+(\.\d+)?\s*$")


def classify(raw):
    s = str(raw).strip()
    if PURE_NUMBER.match(s):
        return float(s.replace("$", "").replace(",", "").strip()), "Reported"
    low = s.lower()
    if "included" in low:
        return np.nan, "Included in commodity cost"
    if "invoiced separately" in low:
        return np.nan, "Invoiced separately"
    if low.startswith("see ") or "asn" in low or "dn-" in low:
        return np.nan, "Cross-referenced to other shipment"
    if "captured separately" in low:
        return np.nan, "Captured separately"
    if s.lower() in ("nan", "", "none"):
        return np.nan, "Missing"
    return np.nan, "Other / unparsed"


for src_col, stem in [("Freight Cost (USD)", "freight_cost_usd"),
                      ("Weight (Kilograms)", "weight_kg"),
                      ("Line Item Insurance (USD)", "insurance_usd")]:
    parsed = df[src_col].apply(classify)
    df[stem] = [p[0] for p in parsed]
    df[f"{stem}_status"] = [p[1] for p in parsed]

print("Freight cost coverage:")
print((df["freight_cost_usd_status"].value_counts(normalize=True) * 100).round(1).to_string())
print("\nWeight coverage:")
print((df["weight_kg_status"].value_counts(normalize=True) * 100).round(1).to_string())

# sanity: no more absurd values
print("\nfreight cost describe (reported only):")
print(df["freight_cost_usd"].describe().round(2).to_string())

# ---------------------------------------------------------------
# Dates and derived delivery measures
# ---------------------------------------------------------------
for src_col, stem in [("Scheduled Delivery Date", "scheduled_delivery_date"),
                      ("Delivered to Client Date", "delivered_date"),
                      ("Delivery Recorded Date", "delivery_recorded_date"),
                      ("PO Sent to Vendor Date", "po_sent_date"),
                      ("PQ First Sent to Client Date", "pq_sent_date")]:
    df[stem] = pd.to_datetime(df[src_col], errors="coerce")

df["delay_days"] = (df["delivered_date"] - df["scheduled_delivery_date"]).dt.days
df["is_on_time"] = (df["delay_days"] <= 0).astype(int)
df["days_early"] = (-df["delay_days"]).clip(lower=0)      # slack in the schedule
df["procurement_lead_days"] = (df["scheduled_delivery_date"] - df["po_sent_date"]).dt.days

df["Shipment Mode"] = df["Shipment Mode"].fillna("Unknown").str.strip()

df["freight_cost_per_kg"] = np.where(
    (df["weight_kg"] > 0) & df["freight_cost_usd"].notna(),
    df["freight_cost_usd"] / df["weight_kg"], np.nan)

# ---------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------
def build_dim(cols, name, key):
    d = df[cols].drop_duplicates().reset_index(drop=True)
    d.columns = [c.strip() for c in d.columns]
    d.insert(0, key, range(1, len(d) + 1))
    d.to_parquet(OUT / f"{name}.parquet", index=False)
    return d


dim_country = build_dim(["Country"], "dim_country", "country_key")
dim_vendor = build_dim(["Vendor"], "dim_vendor", "vendor_key")
dim_mode = build_dim(["Shipment Mode"], "dim_shipment_mode", "mode_key")
dim_site = build_dim(["Manufacturing Site"], "dim_manufacturing_site", "site_key")
dim_product = build_dim(
    ["Product Group", "Sub Classification", "Molecule/Test Type",
     "Brand", "Dosage Form", "Item Description"], "dim_product", "product_key")

# date dimension
lo = df["po_sent_date"].min()
hi = max(df["scheduled_delivery_date"].max(), df["delivered_date"].max())
cal = pd.DataFrame({"date": pd.date_range(lo, hi, freq="D")})
cal["date_key"] = cal["date"].dt.strftime("%Y%m%d").astype(int)
cal["year"] = cal["date"].dt.year
cal["quarter"] = "Q" + cal["date"].dt.quarter.astype(str)
cal["month_no"] = cal["date"].dt.month
cal["month_name"] = cal["date"].dt.strftime("%b")
cal["year_month"] = cal["date"].dt.strftime("%Y-%m")
cal = cal[["date_key", "date", "year", "quarter", "month_no", "month_name", "year_month"]]
cal.to_parquet(OUT / "dim_date.parquet", index=False)

# ---------------------------------------------------------------
# Fact
# ---------------------------------------------------------------
f = df.merge(dim_country, on="Country") \
      .merge(dim_vendor, on="Vendor") \
      .merge(dim_mode, on="Shipment Mode") \
      .merge(dim_site, on="Manufacturing Site") \
      .merge(dim_product, on=["Product Group", "Sub Classification",
                              "Molecule/Test Type", "Brand",
                              "Dosage Form", "Item Description"])

f["scheduled_date_key"] = f["scheduled_delivery_date"].dt.strftime("%Y%m%d").astype("Int64")
f["delivered_date_key"] = f["delivered_date"].dt.strftime("%Y%m%d").astype("Int64")

fact = f[[
    "ID", "Project Code", "PO / SO #", "ASN/DN #",
    "country_key", "vendor_key", "mode_key", "site_key", "product_key",
    "scheduled_date_key", "delivered_date_key",
    "scheduled_delivery_date", "delivered_date", "po_sent_date",
    "Fulfill Via", "Vendor INCO Term", "Managed By", "First Line Designation",
    "Line Item Quantity", "Line Item Value", "Pack Price", "Unit Price",
    "weight_kg", "weight_kg_status",
    "freight_cost_usd", "freight_cost_usd_status", "freight_cost_per_kg",
    "insurance_usd",
    "delay_days", "is_on_time", "days_early", "procurement_lead_days",
]].rename(columns={
    "ID": "shipment_id", "Project Code": "project_code",
    "PO / SO #": "po_number", "ASN/DN #": "asn_number",
    "Fulfill Via": "fulfil_via", "Vendor INCO Term": "inco_term",
    "Managed By": "managed_by", "First Line Designation": "first_line_designation",
    "Line Item Quantity": "line_item_quantity", "Line Item Value": "line_item_value",
    "Pack Price": "pack_price", "Unit Price": "unit_price",
})

fact.to_parquet(OUT / "fact_shipment.parquet", index=False)

print(f"\nfact_shipment: {len(fact)} rows (source {len(df)})")
for p in sorted(OUT.glob("*.parquet")):
    print(f"  {p.name:32} {p.stat().st_size/1024:8.1f} KB")

print("\nOn-time % by mode (sanity check against your profile):")
chk = fact.merge(dim_mode, on="mode_key")
print(chk.groupby("Shipment Mode").agg(
    n=("shipment_id", "size"),
    on_time_pct=("is_on_time", lambda s: round(s.mean() * 100, 2)),
    median_cost_per_kg=("freight_cost_per_kg", "median"),
).round(2).to_string())
