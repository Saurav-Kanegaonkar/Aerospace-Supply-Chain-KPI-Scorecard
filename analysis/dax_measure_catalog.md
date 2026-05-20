# DAX Measure Catalog

These measures are written as Power BI-style logic for interview discussion and implementation planning.

```DAX
Material Readiness % =
DIVIDE(
    CALCULATE(DISTINCTCOUNT(Inventory[part_id]), Inventory[material_ready_flag] = "Ready"),
    DISTINCTCOUNT(Inventory[part_id])
)

Supplier OTIF % =
DIVIDE(
    CALCULATE(COUNTROWS(PurchaseOrders), PurchaseOrders[receipt_status] = "On time"),
    COUNTROWS(PurchaseOrders)
)

Shortage Exposure $ =
SUMX(Inventory, Inventory[shortage_units] * RELATED(Parts[unit_cost]))

Excess Inventory Exposure $ =
SUM(Inventory[excess_value])

Refresh SLA Attainment % =
DIVIDE(
    CALCULATE(COUNTROWS(RefreshLog), RefreshLog[refresh_status] = "Success", RefreshLog[refresh_duration_minutes] <= RefreshLog[sla_minutes]),
    COUNTROWS(RefreshLog)
)
```
