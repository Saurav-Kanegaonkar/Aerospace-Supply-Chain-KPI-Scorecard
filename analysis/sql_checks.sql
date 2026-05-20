-- 1. Business-unit material readiness and shortage exposure.
select
  business_unit,
  count(*) as active_parts,
  avg(case when material_ready_flag = 'Ready' then 1.0 else 0.0 end) as material_readiness_rate,
  sum(shortage_units * p.unit_cost) as shortage_exposure
from inventory_balances i
join parts p on i.part_id = p.part_id
where i.month = '2026-03'
group by business_unit;

-- 2. Supplier OTIF and quality review queue.
select
  s.supplier_id,
  s.supplier_name,
  avg(case when po.receipt_status = 'On time' then 1.0 else 0.0 end) as supplier_otif_rate,
  count(q.quality_event_id) as quality_events
from suppliers s
left join purchase_orders po on s.supplier_id = po.supplier_id
left join quality_events q on s.supplier_id = q.supplier_id
group by s.supplier_id, s.supplier_name
order by supplier_otif_rate asc, quality_events desc;

-- 3. Refresh and data-quality governance for recurring reporting.
select
  dataset_name,
  avg(case when refresh_status = 'Success' then 1.0 else 0.0 end) as success_rate,
  avg(case when refresh_status = 'Success' and refresh_duration_minutes <= sla_minutes then 1.0 else 0.0 end) as sla_attainment
from report_refresh_log
group by dataset_name;
