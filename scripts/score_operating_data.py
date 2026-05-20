import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ANALYSIS = ROOT / "analysis"
OUTPUTS = ANALYSIS / "outputs"

random.seed(1767)

BUSINESS_UNITS = [
    ("Space electronics", 0.38),
    ("C4ISR systems", 0.34),
    ("Optical sensors", 0.28),
]

SITES = ["Fairfax HQ", "Chantilly production", "Concord development"]

PART_CLASSES = [
    ("RF module", 0.23, 4200, 11500, 95),
    ("Radiation tolerant FPGA", 0.12, 9000, 28000, 160),
    ("Power subsystem", 0.16, 5200, 18500, 125),
    ("Space grade memory", 0.14, 3600, 14200, 110),
    ("Optical assembly", 0.12, 7200, 31000, 180),
    ("Cable harness", 0.13, 850, 4200, 45),
    ("Mechanical enclosure", 0.10, 1300, 6800, 70),
]

SUPPLIER_TIERS = [
    ("Strategic sole source", 0.22, 1.20, 0.065),
    ("Preferred", 0.38, 0.85, 0.025),
    ("Qualified", 0.30, 1.00, 0.040),
    ("Watch list", 0.10, 1.35, 0.095),
]

MONTHS = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03"]


def weighted_choice(items, index=1):
    total = sum(item[index] for item in items)
    draw = random.random() * total
    cumulative = 0
    for item in items:
        cumulative += item[index]
        if cumulative >= draw:
            return item
    return items[-1]


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def dollars(value):
    return int(round(value, 0))


def pct(value):
    return round(value * 100, 1)


def make_suppliers():
    states = ["VA", "MD", "CA", "CO", "TX", "AZ", "FL", "MA", "NH", "PA"]
    suppliers = []
    for index in range(1, 31):
        tier = weighted_choice(SUPPLIER_TIERS)
        suppliers.append(
            {
                "supplier_id": f"SUP{index:03d}",
                "supplier_name": f"Mission supplier {index:02d}",
                "supplier_tier": tier[0],
                "region": random.choice(states),
                "quality_system_status": random.choice(["Approved", "Approved", "Approved", "Conditional", "Audit due"]),
                "defense_flowdown_ready": random.choice(["Yes", "Yes", "Yes", "Needs review"]),
                "tier_delay_multiplier": tier[2],
                "base_escape_rate": tier[3],
            }
        )
    return suppliers


def make_parts(suppliers):
    parts = []
    for index in range(1, 73):
        part_class = weighted_choice(PART_CLASSES)
        supplier = random.choice(suppliers)
        business_unit = weighted_choice(BUSINESS_UNITS)
        unit_cost = random.randint(part_class[2], part_class[3])
        lead_time = max(25, int(random.gauss(part_class[4], 18) * float(supplier["tier_delay_multiplier"])))
        demand_rate = random.randint(8, 72)
        safety_stock = max(3, int(demand_rate * random.uniform(0.35, 0.95)))
        criticality = random.choice(["Flight critical", "Flight critical", "Program critical", "Standard"])
        parts.append(
            {
                "part_id": f"PRT{index:03d}",
                "part_name": f"{part_class[0]} {index:03d}",
                "part_class": part_class[0],
                "supplier_id": supplier["supplier_id"],
                "business_unit": business_unit[0],
                "site": random.choice(SITES),
                "unit_cost": unit_cost,
                "standard_lead_time_days": lead_time,
                "monthly_demand_units": demand_rate,
                "safety_stock_units": safety_stock,
                "criticality": criticality,
                "lifecycle_state": random.choice(["Production", "Production", "Production", "NPI", "Sustainment"]),
            }
        )
    return parts


def make_purchase_orders(parts, suppliers):
    supplier_by_id = {supplier["supplier_id"]: supplier for supplier in suppliers}
    rows = []
    po_index = 1
    for month_index, month in enumerate(MONTHS):
        seasonal = 1 + 0.07 * math.sin(month_index / len(MONTHS) * math.pi)
        for part in parts:
            supplier = supplier_by_id[part["supplier_id"]]
            order_count = random.choice([1, 1, 2, 2, 3])
            for _ in range(order_count):
                ordered_units = max(1, int(random.gauss(int(part["monthly_demand_units"]) * seasonal, 8)))
                lead_time = int(part["standard_lead_time_days"])
                delay_days = max(-8, int(random.gauss(3, 12) * float(supplier["tier_delay_multiplier"])))
                if supplier["supplier_tier"] == "Watch list":
                    delay_days += random.randint(4, 18)
                promised_lead_time = lead_time + random.randint(-8, 12)
                actual_lead_time = max(10, promised_lead_time + delay_days)
                received_units = max(0, ordered_units - random.choice([0, 0, 0, 1, 2, 3]))
                rows.append(
                    {
                        "po_id": f"PO{po_index:05d}",
                        "month": month,
                        "part_id": part["part_id"],
                        "supplier_id": part["supplier_id"],
                        "business_unit": part["business_unit"],
                        "site": part["site"],
                        "ordered_units": ordered_units,
                        "received_units": received_units,
                        "unit_cost": part["unit_cost"],
                        "promised_lead_time_days": promised_lead_time,
                        "actual_lead_time_days": actual_lead_time,
                        "late_days": max(0, actual_lead_time - promised_lead_time),
                        "po_value": ordered_units * int(part["unit_cost"]),
                        "receipt_status": "Late" if actual_lead_time > promised_lead_time + 3 else "On time",
                    }
                )
                po_index += 1
    return rows


def make_inventory(parts):
    rows = []
    for month_index, month in enumerate(MONTHS):
        for part in parts:
            demand = int(part["monthly_demand_units"])
            safety = int(part["safety_stock_units"])
            multiplier = random.uniform(0.35, 2.65)
            if part["criticality"] == "Flight critical":
                multiplier += 0.35
            on_hand = max(0, int((demand + safety) * multiplier) - month_index * random.randint(0, 5))
            open_demand = max(1, int(random.gauss(demand, demand * 0.22)))
            allocated = min(on_hand, max(0, int(open_demand * random.uniform(0.35, 0.95))))
            excess = max(0, on_hand - demand * 2 - safety)
            shortage = max(0, open_demand + safety - on_hand)
            rows.append(
                {
                    "month": month,
                    "part_id": part["part_id"],
                    "business_unit": part["business_unit"],
                    "site": part["site"],
                    "on_hand_units": on_hand,
                    "allocated_units": allocated,
                    "open_demand_units": open_demand,
                    "safety_stock_units": safety,
                    "shortage_units": shortage,
                    "excess_units": excess,
                    "inventory_value": dollars(on_hand * int(part["unit_cost"])),
                    "excess_value": dollars(excess * int(part["unit_cost"])),
                    "material_ready_flag": "Ready" if shortage == 0 else "Short",
                }
            )
    return rows


def make_quality_events(parts, suppliers):
    supplier_by_id = {supplier["supplier_id"]: supplier for supplier in suppliers}
    rows = []
    event_index = 1
    for month in MONTHS:
        for part in parts:
            supplier = supplier_by_id[part["supplier_id"]]
            event_probability = float(supplier["base_escape_rate"])
            if part["criticality"] == "Flight critical":
                event_probability += 0.012
            if random.random() < event_probability:
                severity = random.choice(["Low", "Medium", "Medium", "High"])
                containment_days = {"Low": 3, "Medium": 8, "High": 18}[severity] + random.randint(0, 8)
                rows.append(
                    {
                        "quality_event_id": f"QE{event_index:04d}",
                        "month": month,
                        "part_id": part["part_id"],
                        "supplier_id": part["supplier_id"],
                        "event_type": random.choice(["Nonconformance", "FAI delay", "Inspection hold", "Certificate mismatch"]),
                        "severity": severity,
                        "containment_days": containment_days,
                        "estimated_program_impact": dollars(int(part["unit_cost"]) * random.randint(8, 34) * (1.0 + containment_days / 20)),
                    }
                )
                event_index += 1
    return rows


def make_shortage_tracker(parts, inventory):
    latest_inventory = [row for row in inventory if row["month"] == MONTHS[-1] and int(row["shortage_units"]) > 0]
    rows = []
    for index, row in enumerate(latest_inventory, start=1):
        part = next(part for part in parts if part["part_id"] == row["part_id"])
        severity = "High" if int(row["shortage_units"]) > int(part["monthly_demand_units"]) * 0.65 else "Medium"
        rows.append(
            {
                "shortage_id": f"SH{index:04d}",
                "part_id": row["part_id"],
                "business_unit": row["business_unit"],
                "site": row["site"],
                "shortage_units": row["shortage_units"],
                "program_need_date": "2026-04-" + str(random.randint(3, 27)).zfill(2),
                "severity": severity,
                "root_cause": random.choice(["Supplier slip", "Demand change", "Quality hold", "PO not released", "Min max gap"]),
                "owner": random.choice(["Supply chain", "Program", "Operations", "Finance"]),
                "mitigation_status": random.choice(["Open", "Open", "In progress", "Blocked"]),
            }
        )
    return rows


def make_governance_rows():
    kpis = [
        ("Material Readiness Rate", "Inventory", "Parts with no shortage divided by active demand parts.", "Daily", "Supply chain"),
        ("Supplier OTIF", "Supplier", "PO lines received on time and in full divided by closed PO lines.", "Weekly", "Supply chain"),
        ("Past Due Exposure", "Supplier", "Open PO value where receipt is more than three days past promise.", "Weekly", "Operations"),
        ("Shortage Exposure", "Material", "Shortage units multiplied by unit cost for active program demand.", "Daily", "Program"),
        ("Inventory Turns", "Working capital", "Trailing demand value divided by average inventory value.", "Monthly", "Finance"),
        ("Excess Inventory Exposure", "Working capital", "Inventory value above demand plus safety stock thresholds.", "Monthly", "Finance"),
        ("Quality Escape Rate", "Supplier quality", "Supplier quality events divided by PO lines.", "Monthly", "Quality"),
        ("Refresh SLA Attainment", "Reporting ops", "Successful reporting refreshes completed by SLA.", "Weekly", "Analytics"),
    ]
    definitions = [
        {
            "kpi_name": name,
            "domain": domain,
            "business_definition": definition,
            "reporting_cadence": cadence,
            "business_owner": owner,
            "certification_status": random.choice(["Certified", "Certified", "In review"]),
        }
        for name, domain, definition, cadence, owner in kpis
    ]
    refreshes = []
    datasets = ["ERP purchase orders", "ERP inventory balances", "Excel shortage tracker", "SharePoint quality log", "Power BI semantic model"]
    for index, month in enumerate(MONTHS, start=1):
        for dataset in datasets:
            status = random.choice(["Success", "Success", "Success", "Late", "Failed"])
            refreshes.append(
                {
                    "refresh_id": f"RF{index:02d}{datasets.index(dataset) + 1:02d}",
                    "month": month,
                    "dataset_name": dataset,
                    "source_type": dataset.split()[0],
                    "refresh_status": status,
                    "refresh_duration_minutes": random.randint(7, 46),
                    "sla_minutes": 30,
                    "rows_processed": random.randint(420, 8200),
                    "owner": "Analytics",
                }
            )
    quality_issues = []
    checks = [
        "Supplier master missing defense flowdown status",
        "PO receipt date after invoice date",
        "Part master lead time missing",
        "Shortage tracker owner blank",
        "Inventory balance negative",
        "Business unit mapping mismatch",
    ]
    for index in range(1, 27):
        severity = random.choice(["Low", "Medium", "Medium", "High"])
        quality_issues.append(
            {
                "issue_id": f"DQ{index:04d}",
                "source_system": random.choice(["ERP", "Excel shortage tracker", "SharePoint quality log"]),
                "check_name": random.choice(checks),
                "severity": severity,
                "records_impacted": random.randint(4, 220),
                "business_owner": random.choice(["Supply chain", "Operations", "Finance", "Program", "Quality"]),
                "status": random.choice(["Open", "Open", "In progress", "Resolved"]),
                "recommended_fix": random.choice(["Add owner rule", "Reconcile source extract", "Update master data", "Certify KPI mapping"]),
            }
        )
    return definitions, refreshes, quality_issues


def summarize(parts, suppliers, purchase_orders, inventory, quality_events, shortages, refreshes, quality_issues):
    parts_by_id = {part["part_id"]: part for part in parts}
    suppliers_by_id = {supplier["supplier_id"]: supplier for supplier in suppliers}
    latest_inventory = [row for row in inventory if row["month"] == MONTHS[-1]]
    latest_by_part = {row["part_id"]: row for row in latest_inventory}
    po_latest = [row for row in purchase_orders if row["month"] == MONTHS[-1]]
    po_by_part = defaultdict(list)
    for row in purchase_orders:
        po_by_part[row["part_id"]].append(row)
    quality_by_part = defaultdict(list)
    for row in quality_events:
        quality_by_part[row["part_id"]].append(row)
    shortage_by_part = {row["part_id"]: row for row in shortages}

    queue = []
    for part in parts:
        inv = latest_by_part[part["part_id"]]
        pos = po_by_part[part["part_id"]]
        closed = len(pos)
        late_lines = sum(1 for po in pos if po["receipt_status"] == "Late")
        otif = 1 - late_lines / max(1, closed)
        shortage_value = int(inv["shortage_units"]) * int(part["unit_cost"])
        excess_value = int(inv["excess_value"])
        quality_impact = sum(int(event["estimated_program_impact"]) for event in quality_by_part[part["part_id"]])
        lead_time_pressure = min(1, int(part["standard_lead_time_days"]) / 180)
        criticality_pressure = {"Flight critical": 1.0, "Program critical": 0.72, "Standard": 0.38}[part["criticality"]]
        shortage_pressure = min(1, shortage_value / 650000)
        supplier_pressure = min(1, (1 - otif) * 1.4 + len(quality_by_part[part["part_id"]]) * 0.12)
        working_capital_pressure = min(1, excess_value / 900000)
        readiness_score = round(
            100
            * (
                0.34 * shortage_pressure
                + 0.24 * supplier_pressure
                + 0.16 * lead_time_pressure
                + 0.14 * criticality_pressure
                + 0.12 * working_capital_pressure
            ),
            1,
        )
        root_cause = shortage_by_part.get(part["part_id"], {}).get("root_cause", "Inventory policy")
        if shortage_value > 250000 and supplier_pressure > 0.35:
            action = "Escalate supplier recovery plan"
        elif shortage_value > 120000:
            action = "Pull in PO and approve alternate source"
        elif working_capital_pressure > 0.55:
            action = "Reduce buys and review excess disposition"
        elif supplier_pressure > 0.42:
            action = "Start supplier performance review"
        else:
            action = "Monitor in next recurring review"
        queue.append(
            {
                "part_id": part["part_id"],
                "part_name": part["part_name"],
                "supplier_id": part["supplier_id"],
                "supplier_name": suppliers_by_id[part["supplier_id"]]["supplier_name"],
                "business_unit": part["business_unit"],
                "site": part["site"],
                "criticality": part["criticality"],
                "standard_lead_time_days": part["standard_lead_time_days"],
                "supplier_otif_pct": pct(otif),
                "shortage_units": inv["shortage_units"],
                "shortage_value": shortage_value,
                "excess_value": excess_value,
                "quality_events": len(quality_by_part[part["part_id"]]),
                "quality_impact": quality_impact,
                "readiness_risk_score": readiness_score,
                "root_cause": root_cause,
                "recommended_action": action,
                "business_owner": random.choice(["Supply chain", "Operations", "Program", "Finance"]),
            }
        )
    queue.sort(key=lambda row: row["readiness_risk_score"], reverse=True)

    readiness_summary = []
    for business_unit, _ in BUSINESS_UNITS:
        unit_parts = [part for part in parts if part["business_unit"] == business_unit]
        unit_inv = [latest_by_part[part["part_id"]] for part in unit_parts]
        ready = sum(1 for row in unit_inv if row["material_ready_flag"] == "Ready")
        shortage_value = sum(int(row["shortage_units"]) * int(parts_by_id[row["part_id"]]["unit_cost"]) for row in unit_inv)
        inventory_value = sum(int(row["inventory_value"]) for row in unit_inv)
        excess_value = sum(int(row["excess_value"]) for row in unit_inv)
        readiness_summary.append(
            {
                "business_unit": business_unit,
                "active_parts": len(unit_parts),
                "material_readiness_pct": pct(ready / max(1, len(unit_parts))),
                "shortage_exposure": shortage_value,
                "inventory_value": inventory_value,
                "excess_inventory_exposure": excess_value,
                "working_capital_review_flag": "Review" if excess_value > inventory_value * 0.18 else "Monitor",
            }
        )

    supplier_rows = []
    for supplier in suppliers:
        supplier_pos = [po for po in purchase_orders if po["supplier_id"] == supplier["supplier_id"]]
        late = sum(1 for po in supplier_pos if po["receipt_status"] == "Late")
        supplier_quality = [event for event in quality_events if event["supplier_id"] == supplier["supplier_id"]]
        po_value = sum(int(po["po_value"]) for po in supplier_pos)
        supplier_rows.append(
            {
                "supplier_id": supplier["supplier_id"],
                "supplier_name": supplier["supplier_name"],
                "supplier_tier": supplier["supplier_tier"],
                "po_lines": len(supplier_pos),
                "supplier_otif_pct": pct(1 - late / max(1, len(supplier_pos))),
                "quality_events": len(supplier_quality),
                "po_value": po_value,
                "supplier_review_status": "Escalate" if late / max(1, len(supplier_pos)) > 0.35 or len(supplier_quality) > 3 else "Monitor",
            }
        )
    supplier_rows.sort(key=lambda row: (row["supplier_review_status"] == "Escalate", row["po_value"]), reverse=True)

    dq_queue = sorted(
        quality_issues,
        key=lambda row: ({"High": 3, "Medium": 2, "Low": 1}[row["severity"]], int(row["records_impacted"])),
        reverse=True,
    )
    refresh_summary = []
    for dataset in sorted(set(row["dataset_name"] for row in refreshes)):
        rows = [row for row in refreshes if row["dataset_name"] == dataset]
        successful = sum(1 for row in rows if row["refresh_status"] == "Success")
        sla = sum(1 for row in rows if int(row["refresh_duration_minutes"]) <= int(row["sla_minutes"]) and row["refresh_status"] == "Success")
        refresh_summary.append(
            {
                "dataset_name": dataset,
                "refreshes": len(rows),
                "success_rate_pct": pct(successful / len(rows)),
                "sla_attainment_pct": pct(sla / len(rows)),
                "latest_status": rows[-1]["refresh_status"],
                "owner": rows[-1]["owner"],
            }
        )

    total_shortage = sum(row["shortage_value"] for row in queue)
    total_inventory = sum(int(row["inventory_value"]) for row in latest_inventory)
    total_excess = sum(int(row["excess_value"]) for row in latest_inventory)
    latest_po_value = sum(int(row["po_value"]) for row in po_latest)
    latest_late_value = sum(int(row["po_value"]) for row in po_latest if row["receipt_status"] == "Late")
    material_ready = sum(1 for row in latest_inventory if row["material_ready_flag"] == "Ready") / len(latest_inventory)
    supplier_otif = 1 - sum(1 for po in purchase_orders if po["receipt_status"] == "Late") / len(purchase_orders)
    refresh_success = sum(1 for row in refreshes if row["refresh_status"] == "Success") / len(refreshes)
    high_dq = sum(1 for row in quality_issues if row["severity"] == "High" and row["status"] != "Resolved")

    summary = {
        "active_parts": len(parts),
        "suppliers": len(suppliers),
        "po_lines": len(purchase_orders),
        "material_readiness_pct": pct(material_ready),
        "supplier_otif_pct": pct(supplier_otif),
        "shortage_exposure": total_shortage,
        "inventory_value": total_inventory,
        "excess_inventory_exposure": total_excess,
        "latest_po_value": latest_po_value,
        "past_due_po_value": latest_late_value,
        "refresh_success_pct": pct(refresh_success),
        "open_high_data_quality_issues": high_dq,
        "top_risk_part": queue[0]["part_id"],
        "top_risk_score": queue[0]["readiness_risk_score"],
        "source_note": "Synthetic aerospace supply chain reporting data generated from documented ERP, Excel, and SharePoint-style structures. It does not represent any real company performance.",
    }

    return queue, readiness_summary, supplier_rows, dq_queue, refresh_summary, summary


def write_documents(summary):
    (ANALYSIS / "analysis_plan.md").write_text(
        "# Analysis Plan\n\n"
        "1. Build ERP-style supplier, part, purchase order, and inventory source tables.\n"
        "2. Add Excel-style shortage tracker records and SharePoint-style quality, request, and refresh governance records.\n"
        "3. Calculate material readiness, supplier OTIF, shortage exposure, excess inventory, quality impact, and refresh SLA metrics.\n"
        "4. Score supplier-part readiness risk with transparent weighted business rules.\n"
        "5. Produce executive findings, SQL checks, a DAX measure catalog, and dashboard-ready output tables.\n"
    )
    (ANALYSIS / "methodology.md").write_text(
        "# Methodology\n\n"
        "The artifact uses synthetic data because real ERP, inventory, supplier, and SharePoint records are private. "
        "The generated structure mirrors common aerospace and defense electronics reporting workflows: suppliers support specialized part classes, parts carry lead time and criticality attributes, purchase orders create delivery performance, inventory creates material readiness and working capital signals, and governance logs create report trust signals.\n\n"
        "The readiness risk score is transparent: 34% shortage exposure, 24% supplier performance, 16% lead time pressure, 14% part criticality, and 12% excess inventory pressure. "
        "This favors explainable BI reporting over black-box modeling because the intended audience needs recurring, governed leadership reporting.\n"
    )
    (ANALYSIS / "executive_findings.md").write_text(
        "# Executive Findings\n\n"
        "## What I analyzed\n\n"
        f"I generated and analyzed {summary['po_lines']:,} ERP-style purchase order lines across {summary['active_parts']} active parts and {summary['suppliers']} suppliers, then joined inventory balances, shortage tracker records, quality events, KPI definitions, refresh logs, and data-quality issues.\n\n"
        "## Findings\n\n"
        f"- Material readiness is {summary['material_readiness_pct']}% in the latest reporting month, with ${summary['shortage_exposure']:,} in modeled shortage exposure.\n"
        f"- Supplier OTIF is {summary['supplier_otif_pct']}%, while latest-month past-due PO exposure is ${summary['past_due_po_value']:,}.\n"
        f"- Excess inventory exposure is ${summary['excess_inventory_exposure']:,}, which gives Finance a working-capital review queue instead of a static inventory snapshot.\n"
        f"- Reporting refresh success is {summary['refresh_success_pct']}%, and {summary['open_high_data_quality_issues']} high-severity data-quality issues remain open.\n"
        f"- The highest-risk supplier-part record is {summary['top_risk_part']} with a readiness risk score of {summary['top_risk_score']}.\n\n"
        "## Recommendation\n\n"
        "Use the scorecard as a weekly business-unit review artifact: resolve high-value shortage exposure first, escalate supplier recovery where OTIF and quality signals overlap, and keep data-quality exceptions visible until the reporting pack is certified.\n"
    )
    (ANALYSIS / "dax_measure_catalog.md").write_text(
        "# DAX Measure Catalog\n\n"
        "These measures are written as Power BI-style logic for interview discussion and implementation planning.\n\n"
        "```DAX\n"
        "Material Readiness % =\n"
        "DIVIDE(\n"
        "    CALCULATE(DISTINCTCOUNT(Inventory[part_id]), Inventory[material_ready_flag] = \"Ready\"),\n"
        "    DISTINCTCOUNT(Inventory[part_id])\n"
        ")\n\n"
        "Supplier OTIF % =\n"
        "DIVIDE(\n"
        "    CALCULATE(COUNTROWS(PurchaseOrders), PurchaseOrders[receipt_status] = \"On time\"),\n"
        "    COUNTROWS(PurchaseOrders)\n"
        ")\n\n"
        "Shortage Exposure $ =\n"
        "SUMX(Inventory, Inventory[shortage_units] * RELATED(Parts[unit_cost]))\n\n"
        "Excess Inventory Exposure $ =\n"
        "SUM(Inventory[excess_value])\n\n"
        "Refresh SLA Attainment % =\n"
        "DIVIDE(\n"
        "    CALCULATE(COUNTROWS(RefreshLog), RefreshLog[refresh_status] = \"Success\", RefreshLog[refresh_duration_minutes] <= RefreshLog[sla_minutes]),\n"
        "    COUNTROWS(RefreshLog)\n"
        ")\n"
        "```\n"
    )
    (ANALYSIS / "sql_checks.sql").write_text(
        "-- 1. Business-unit material readiness and shortage exposure.\n"
        "select\n"
        "  business_unit,\n"
        "  count(*) as active_parts,\n"
        "  avg(case when material_ready_flag = 'Ready' then 1.0 else 0.0 end) as material_readiness_rate,\n"
        "  sum(shortage_units * p.unit_cost) as shortage_exposure\n"
        "from inventory_balances i\n"
        "join parts p on i.part_id = p.part_id\n"
        "where i.month = '2026-03'\n"
        "group by business_unit;\n\n"
        "-- 2. Supplier OTIF and quality review queue.\n"
        "select\n"
        "  s.supplier_id,\n"
        "  s.supplier_name,\n"
        "  avg(case when po.receipt_status = 'On time' then 1.0 else 0.0 end) as supplier_otif_rate,\n"
        "  count(q.quality_event_id) as quality_events\n"
        "from suppliers s\n"
        "left join purchase_orders po on s.supplier_id = po.supplier_id\n"
        "left join quality_events q on s.supplier_id = q.supplier_id\n"
        "group by s.supplier_id, s.supplier_name\n"
        "order by supplier_otif_rate asc, quality_events desc;\n\n"
        "-- 3. Refresh and data-quality governance for recurring reporting.\n"
        "select\n"
        "  dataset_name,\n"
        "  avg(case when refresh_status = 'Success' then 1.0 else 0.0 end) as success_rate,\n"
        "  avg(case when refresh_status = 'Success' and refresh_duration_minutes <= sla_minutes then 1.0 else 0.0 end) as sla_attainment\n"
        "from report_refresh_log\n"
        "group by dataset_name;\n"
    )
    (ROOT / "data_dictionary.md").write_text(
        "# Data Dictionary\n\n"
        "| Table | Grain | Purpose |\n"
        "|---|---|---|\n"
        "| `data/suppliers.csv` | Supplier | Supplier tier, region, quality status, and defense flowdown readiness. |\n"
        "| `data/parts.csv` | Part | Business unit, site, part class, lead time, demand, safety stock, criticality, and supplier mapping. |\n"
        "| `data/purchase_orders.csv` | PO line | ERP-style order quantity, receipt quantity, promised lead time, actual lead time, OTIF status, and PO value. |\n"
        "| `data/inventory_balances.csv` | Part x month | Inventory, allocation, open demand, shortage, excess, value, and material readiness flag. |\n"
        "| `data/shortage_tracker.csv` | Shortage | Excel-style shortage root cause, severity, owner, need date, and mitigation status. |\n"
        "| `data/quality_events.csv` | Quality event | SharePoint-style supplier quality issue, severity, containment days, and estimated program impact. |\n"
        "| `data/kpi_definitions.csv` | KPI | Governed metric definition, cadence, owner, and certification status. |\n"
        "| `data/report_refresh_log.csv` | Dataset refresh | Source type, refresh status, duration, SLA, row counts, and owner. |\n"
        "| `data/data_quality_issues.csv` | Data-quality issue | Source-system exception, impacted records, owner, status, and recommended fix. |\n"
        "| `analysis/outputs/supplier_part_priority_queue.csv` | Supplier part | Ranked readiness-risk queue with recommended actions. |\n"
        "| `analysis/outputs/material_readiness_summary.csv` | Business unit | Material readiness, shortage exposure, inventory value, and excess exposure. |\n"
        "| `analysis/outputs/supplier_scorecard.csv` | Supplier | OTIF, quality events, PO value, and review status. |\n"
        "| `analysis/outputs/data_quality_queue.csv` | Issue | Prioritized data-quality remediation queue. |\n"
        "| `analysis/outputs/refresh_governance.csv` | Dataset | Refresh success, SLA attainment, latest status, and owner. |\n"
    )
    (DATA / "README.md").write_text(
        "# Data\n\n"
        "This folder contains synthetic aerospace supply chain reporting data generated by `scripts/score_operating_data.py`. "
        "It does not represent any real company, supplier, program, ERP system, inventory balance, or operational performance.\n\n"
        "The structure is modeled on recurring supply chain BI sources: ERP purchase orders, ERP inventory balances, supplier and part master data, Excel shortage trackers, SharePoint quality logs, KPI documentation, refresh logs, and data-quality issue queues.\n\n"
        "Synthetic assumptions include specialized aerospace electronics part classes, supplier tiers, long lead-time components, flight-critical and program-critical demand, late receipts, quality holds, safety stock, shortage exposure, excess inventory, and reporting refresh SLA outcomes.\n"
    )
    (ROOT / "STATUS.md").write_text(
        "# Status\n\n"
        "- Project: Aerospace Supply Chain KPI Scorecard\n"
        "- GitHub: https://github.com/Saurav-Kanegaonkar/Aerospace-Supply-Chain-KPI-Scorecard\n"
        "- Status: upgraded through the Portfolio Artifact Upgrade Workflow\n"
        "- Artifact: governed aerospace supply chain BI console with synthetic ERP, Excel, and SharePoint-style data, KPI definitions, DAX catalog, SQL checks, executive findings, and screenshots\n"
        "- Resume Link Ready: Yes\n"
    )


def main():
    DATA.mkdir(exist_ok=True)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    suppliers = make_suppliers()
    parts = make_parts(suppliers)
    purchase_orders = make_purchase_orders(parts, suppliers)
    inventory = make_inventory(parts)
    quality_events = make_quality_events(parts, suppliers)
    shortages = make_shortage_tracker(parts, inventory)
    kpi_definitions, refreshes, quality_issues = make_governance_rows()
    queue, readiness, supplier_rows, dq_queue, refresh_summary, summary = summarize(
        parts, suppliers, purchase_orders, inventory, quality_events, shortages, refreshes, quality_issues
    )

    write_csv(DATA / "suppliers.csv", suppliers)
    write_csv(DATA / "parts.csv", parts)
    write_csv(DATA / "purchase_orders.csv", purchase_orders)
    write_csv(DATA / "inventory_balances.csv", inventory)
    write_csv(DATA / "shortage_tracker.csv", shortages)
    write_csv(DATA / "quality_events.csv", quality_events)
    write_csv(DATA / "kpi_definitions.csv", kpi_definitions)
    write_csv(DATA / "report_refresh_log.csv", refreshes)
    write_csv(DATA / "data_quality_issues.csv", quality_issues)
    write_csv(OUTPUTS / "supplier_part_priority_queue.csv", queue)
    write_csv(OUTPUTS / "material_readiness_summary.csv", readiness)
    write_csv(OUTPUTS / "supplier_scorecard.csv", supplier_rows)
    write_csv(OUTPUTS / "data_quality_queue.csv", dq_queue)
    write_csv(OUTPUTS / "refresh_governance.csv", refresh_summary)
    (OUTPUTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_documents(summary)

    print(f"Generated {summary['po_lines']:,} purchase order rows across {summary['active_parts']} parts.")
    print(f"Material readiness: {summary['material_readiness_pct']}%")
    print(f"Shortage exposure: ${summary['shortage_exposure']:,}")
    print(f"Top risk part: {summary['top_risk_part']} ({summary['top_risk_score']})")


if __name__ == "__main__":
    main()
