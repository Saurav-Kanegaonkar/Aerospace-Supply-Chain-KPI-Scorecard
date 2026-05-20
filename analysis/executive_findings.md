# Executive Findings

## What I analyzed

I generated and analyzed 776 ERP-style purchase order lines across 72 active parts and 30 suppliers, then joined inventory balances, shortage tracker records, quality events, KPI definitions, refresh logs, and data-quality issues.

## Findings

- Material readiness is 66.7% in the latest reporting month, with $4,455,389 in modeled shortage exposure.
- Supplier OTIF is 52.4%, while latest-month past-due PO exposure is $23,746,805.
- Excess inventory exposure is $11,528,774, which gives Finance a working-capital review queue instead of a static inventory snapshot.
- Reporting refresh success is 43.3%, and 5 high-severity data-quality issues remain open.
- The highest-risk supplier-part record is PRT030 with a readiness risk score of 72.9.

## Recommendation

Use the scorecard as a weekly business-unit review artifact: resolve high-value shortage exposure first, escalate supplier recovery where OTIF and quality signals overlap, and keep data-quality exceptions visible until the reporting pack is certified.
