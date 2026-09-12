# Air Freight Premium

A Power BI analysis of $69M in freight spend across 10,324 health commodity
shipments to 43 countries, 2006 to 2015.

**The question:** the programme moves 62% of its freight by air at several
times the ocean rate. How much of that premium actually buys faster, more
reliable delivery?

![Overview](docs/screenshots/01-overview.png)

## What the analysis found

**Air costs 6x more per kilogram than ocean and buys 8 percentage points of
on-time performance.** Median air rate is $10.02/kg against $1.68/kg for
ocean. On-time delivery runs 90.4% by air and 82.5% by ocean.

**Small shipments pay a 27-fold premium.** Freight costs $30.63/kg on
shipments under 100 kg and $1.11/kg above 10,000 kg. Consolidation is worth
more here than rate negotiation, and it sits entirely within the programme's
control.

**Routing through a regional distribution centre costs 11 points of
reliability.** Direct drop delivers 94.9% on-time. From RDC delivers 84.1%,
at comparable cost per kilogram. The cheaper route is also the less reliable
one.

**$1.79M of air spend has no reliability justification.** 244 shipments moved
by air yet arrived more than 30 days ahead of schedule. Shifting those to
ocean releases 3.4% of air freight spend without touching a single delivery
date that mattered.

**Freight cost visibility is a contract structure, not a data problem.**
Freight is separately invoiced on only 60% of shipments. The rest is bundled
into commodity cost or cross-referenced elsewhere, and which one you get is
determined by the INCO term.

## Why this dataset

I started on the DataCo Smart Supply Chain dataset, which is one of the most
downloaded supply chain datasets on Kaggle. Before modelling anything I
profiled it, and the numbers did not survive the check:

- `Days for shipping (real)` is randomly generated. First Class is a constant
  2 days with zero variance. Second and Standard Class are both uniform over
  2 to 6 days, identically.
- Discount rate is uniform across 18 values with no relationship to product
  or category.
- Correlation between discount rate and profit ratio is **-0.0015**. In real
  data, discounting eats margin. Here they are independent.
- 36% of rows fail the internal identity
  `Order Item Total x Profit Ratio = Order Profit Per Order`.

Any dashboard built on those fields reports noise. I documented the findings
in [docs/why-not-dataco.md](docs/why-not-dataco.md) and rebuilt the same
analysis on real procurement data instead.

## How it is built

```
USAID SCMS CSV
   -> prep.py        clean, classify missing values, build star schema
   -> parquet        fact_shipment + 6 dimensions
   -> Power BI       DAX measures, 4 report pages
```

**Model:** star schema, single-direction relationships, marked date table.

**Notable measures:** median cost per kilogram rather than mean, because
individual freight costs span $0.75 to $290,000. A what-if parameter drives
the mode shift simulation. Matrix cells below 20 shipments are suppressed
rather than shown as misleading 100% figures.

**Interactivity:** field parameters let the viewer switch both dimension and
metric on the reliability page. Decomposition tree for root cause. Sidebar
navigation, synced slicers, filter reset.

## Assumptions and limits

- Savings on the Mode Shift page are **modelled, not realised**. The estimate
  applies the median ocean rate to air shipments that arrived with schedule
  slack, and assumes that slack would have absorbed the longer transit.
- Cost measures cover the 60% of shipments with separately invoiced freight.
  Weight is recorded on 61.7%.
- Country breakdowns are limited to destinations with 100+ shipments.
- 2006 carries 65 shipments against roughly 1,500 in 2014, so early-year
  comparisons are volume-sensitive.

## Files

| Path | What it is |
|---|---|
| `src/prep.py` | Cleaning and star schema build |
| `src/profiling/` | The profiling scripts, including the DataCo checks |
| `data/curated/` | Parquet model files |
| `pbix/` | The Power BI file |
| `docs/` | PDF export, screenshots, DataCo write-up |

## Data source

USAID Supply Chain Management System delivery history. Public domain.

## Walkthrough

[3 minute video walkthrough](YOUR_YOUTUBE_LINK)

---

Built by Sajith Pemarathna. Data analyst based in Berlin.
[LinkedIn](https://www.linkedin.com/in/sajith-pemarathna/)
