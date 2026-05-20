# Data Dictionary

| Table | Grain | Purpose |
|---|---|---|
| `data/suppliers.csv` | Supplier | Supplier tier, region, quality status, and defense flowdown readiness. |
| `data/parts.csv` | Part | Business unit, site, part class, lead time, demand, safety stock, criticality, and supplier mapping. |
| `data/purchase_orders.csv` | PO line | ERP-style order quantity, receipt quantity, promised lead time, actual lead time, OTIF status, and PO value. |
| `data/inventory_balances.csv` | Part x month | Inventory, allocation, open demand, shortage, excess, value, and material readiness flag. |
| `data/shortage_tracker.csv` | Shortage | Excel-style shortage root cause, severity, owner, need date, and mitigation status. |
| `data/quality_events.csv` | Quality event | SharePoint-style supplier quality issue, severity, containment days, and estimated program impact. |
| `data/kpi_definitions.csv` | KPI | Governed metric definition, cadence, owner, and certification status. |
| `data/report_refresh_log.csv` | Dataset refresh | Source type, refresh status, duration, SLA, row counts, and owner. |
| `data/data_quality_issues.csv` | Data-quality issue | Source-system exception, impacted records, owner, status, and recommended fix. |
| `analysis/outputs/supplier_part_priority_queue.csv` | Supplier part | Ranked readiness-risk queue with recommended actions. |
| `analysis/outputs/material_readiness_summary.csv` | Business unit | Material readiness, shortage exposure, inventory value, and excess exposure. |
| `analysis/outputs/supplier_scorecard.csv` | Supplier | OTIF, quality events, PO value, and review status. |
| `analysis/outputs/data_quality_queue.csv` | Issue | Prioritized data-quality remediation queue. |
| `analysis/outputs/refresh_governance.csv` | Dataset | Refresh success, SLA attainment, latest status, and owner. |
