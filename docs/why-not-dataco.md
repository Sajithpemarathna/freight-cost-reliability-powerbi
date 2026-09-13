# Why I did not use the DataCo dataset

I started this project on **DataCo Smart Supply Chain for Big Data Analysis**,
which is one of the most downloaded supply chain datasets on Kaggle. Before
modelling anything I ran three profiling passes on it. The dataset did not
survive them.

This note documents what I found. The scripts are in `../src/profiling/`.

## What the dataset looks like

180,519 rows, 53 columns, 65,752 distinct orders. The grain is order line, not
order. Date range 2015-01-01 to 2018-01-31.

## Finding 1: delivery times are randomly generated

The promised lead time is a constant per shipping mode, identical across all
five markets:

| Mode | Promised days |
|---|---|
| Same Day | 0 |
| First Class | 1 |
| Second Class | 2 |
| Standard Class | 4 |

The actual lead times are not a distribution, they are a random draw:

| Mode | Actual lead time distribution | Std dev |
|---|---|---|
| First Class | 100.0% exactly 2 days | 0.000 |
| Same Day | 51.6% at 0 days, 48.4% at 1 day | 0.500 |
| Second Class | 20.1 / 19.8 / 20.1 / 20.0 / 20.1% across 2-6 days | 1.415 |
| Standard Class | 20.1 / 20.0 / 20.0 / 19.8 / 20.1% across 2-6 days | 1.416 |

Second Class and Standard Class have **identical** distributions. Two service
tiers are sold; one capability exists.

The monthly view confirms it. First Class mean lead time is exactly 2.00 in all
37 months. On-time rate sits between 40.1% and 45.0% for three straight years
with no trend, no seasonality and no shocks.

## Finding 2: the commercial fields are random too

**Discount rate** takes 18 distinct values from 0.00 to 0.25, each appearing
5.55% to 5.58% of the time. Category means span 0.0934 to 0.1094, and every
extreme sits on a sample of fewer than 120 rows while the large-sample
categories land on the 0.1016 global mean.

**Profit ratio** by customer segment:

| Segment | Mean profit ratio | n |
|---|---|---|
| Consumer | 0.1213 | 89,420 |
| Corporate | 0.1208 | 52,528 |
| Home Office | 0.1195 | 30,817 |

Identical means on samples that large are not coincidence. There is no segment
effect because there is no segment effect to find.

**The decisive number: the correlation between discount rate and profit ratio
is -0.0015.** In any real business, discounting eats margin. Here the two are
statistically independent.

**Quantity** is 54.93% ones, then 11.2% each for 2, 3, 4 and 5.

**Products:** 118 names, but nine of them carry 149,729 of 172,765 lines. That
is 86.7% of the file in nine SKUs, then a cliff to a few hundred lines each for
names like "Summer dresses" and "Children's heaters".

## Finding 3: an internal identity fails on a third of rows

Three integrity checks:

| Check | Match rate |
|---|---|
| `Sales = Product Price x Quantity` | 100.0% |
| `Sales - Discount = Order Item Total` | 100.0% |
| `Order Item Total x Profit Ratio = Order Profit Per Order` | **63.9%** |

The first two hold perfectly. The third fails on 36% of rows, on an identity
that should hold by definition.

## Finding 4: delivery outcome is independent of everything

Revenue and margin by delivery outcome, per market:

| Market | On-time margin | Late margin |
|---|---|---|
| Africa | 10.98% | 10.80% |
| Europe | 11.35% | 10.53% |
| LATAM | 11.12% | 10.70% |
| Pacific Asia | 10.31% | 10.47% |
| USCA | 11.48% | 10.90% |

Late shipments carry the same margin as on-time ones, everywhere. Lateness was
assigned independently of any commercial attribute.

## Conclusion

DataCo is a schema exercise, not a business dataset. Its dimensional hierarchy
is sound and its arithmetic is mostly self-consistent, but no measure in it
carries signal.

Cleaning does not fix this. The problem is not bad records, it is a bad
generating process applied to every record. There is no subset of clean rows
underneath.

I moved the analysis to the USAID Supply Chain Shipment Pricing dataset, which
is real procurement data, and the same profiling approach found genuine
structure there on the first pass.

## What this is worth knowing

A lot of published dashboards use these fields to report delivery KPIs. The
generating process is easy to miss if you go straight to modelling, because the
data looks entirely plausible in a preview. Thirty minutes of profiling is
cheaper than a dashboard that reports noise.

## Source

Constante, F., Silva, F., Pereira, A. (2019). *DataCo Smart Supply Chain for
Big Data Analysis.* Mendeley Data.
