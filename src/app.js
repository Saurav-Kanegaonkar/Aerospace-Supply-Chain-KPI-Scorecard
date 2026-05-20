const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const whole = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

const paths = {
  summary: "analysis/outputs/summary.json",
  readiness: "analysis/outputs/material_readiness_summary.csv",
  suppliers: "analysis/outputs/supplier_scorecard.csv",
  queue: "analysis/outputs/supplier_part_priority_queue.csv",
  refresh: "analysis/outputs/refresh_governance.csv",
  quality: "analysis/outputs/data_quality_queue.csv",
  definitions: "data/kpi_definitions.csv",
};

function parseCsv(text) {
  const rows = [];
  const lines = text.trim().split(/\r?\n/);
  const headers = lines.shift().split(",");
  for (const line of lines) {
    const values = [];
    let current = "";
    let quoted = false;
    for (const char of line) {
      if (char === '"') {
        quoted = !quoted;
      } else if (char === "," && !quoted) {
        values.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    values.push(current);
    rows.push(Object.fromEntries(headers.map((header, index) => [header, values[index] || ""])));
  }
  return rows;
}

async function loadCsv(path) {
  const response = await fetch(path);
  return parseCsv(await response.text());
}

function metric(label, value, context, tone = "") {
  return `
    <article class="metric ${tone}">
      <span>${label}</span>
      <strong>${value}</strong>
      <em>${context}</em>
    </article>
  `;
}

function barRow(label, value, detail, tone = "") {
  const width = Math.max(6, Math.min(100, Number(value)));
  return `
    <div class="bar-row ${tone}">
      <div class="bar-copy">
        <strong>${label}</strong>
        <span>${detail}</span>
      </div>
      <div class="bar-track" aria-label="${label} ${value}%">
        <div style="width:${width}%"></div>
      </div>
      <b>${value}%</b>
    </div>
  `;
}

function table(headers, rows) {
  return `
    <table>
      <thead>
        <tr>${headers.map((header) => `<th>${header}</th>`).join("")}</tr>
      </thead>
      <tbody>${rows.join("")}</tbody>
    </table>
  `;
}

function renderMetrics(summary) {
  document.querySelector("#metricGrid").innerHTML = [
    metric("Material readiness", `${summary.material_readiness_pct}%`, `${summary.active_parts} active parts`, "good"),
    metric("Shortage exposure", currency.format(summary.shortage_exposure), "latest month risk", "alert"),
    metric("Supplier OTIF", `${summary.supplier_otif_pct}%`, `${summary.suppliers} suppliers`, "warn"),
    metric("Refresh success", `${summary.refresh_success_pct}%`, "reporting operations", "good"),
    metric("Past due PO value", currency.format(summary.past_due_po_value), "latest month", "alert"),
    metric("Excess inventory", currency.format(summary.excess_inventory_exposure), "working capital queue", "warn"),
  ].join("");
}

function renderReadiness(rows) {
  document.querySelector("#readinessBars").innerHTML = rows
    .map((row) =>
      barRow(
        row.business_unit,
        row.material_readiness_pct,
        `${whole.format(row.active_parts)} parts, ${currency.format(row.shortage_exposure)} shortage exposure`,
        row.working_capital_review_flag === "Review" ? "warn" : "good",
      ),
    )
    .join("");
}

function renderSupplierTable(rows) {
  const body = rows.slice(0, 7).map((row) => `
    <tr>
      <td><b>${row.supplier_name}</b><span>${row.supplier_tier}</span></td>
      <td>${row.supplier_otif_pct}%</td>
      <td>${row.quality_events}</td>
      <td><strong class="${row.supplier_review_status === "Escalate" ? "text-alert" : "text-ok"}">${row.supplier_review_status}</strong></td>
    </tr>
  `);
  document.querySelector("#supplierTable").innerHTML = table(["Supplier", "OTIF", "Quality", "Status"], body);
}

function renderRiskQueue(rows) {
  document.querySelector("#riskQueue").innerHTML = rows.slice(0, 10).map((row, index) => `
    <article class="queue-row">
      <div class="rank">${String(index + 1).padStart(2, "0")}</div>
      <div class="queue-main">
        <h3>${row.part_name}</h3>
        <p>${row.supplier_name} - ${row.business_unit} - ${row.site}</p>
        <div class="tags">
          <span>${row.criticality}</span>
          <span>${row.root_cause}</span>
          <span>${row.business_owner}</span>
        </div>
      </div>
      <div class="queue-values">
        <strong>${row.readiness_risk_score}</strong>
        <span>risk score</span>
        <b>${currency.format(row.shortage_value)}</b>
        <em>${row.recommended_action}</em>
      </div>
    </article>
  `).join("");
}

function renderRefresh(rows) {
  document.querySelector("#refreshBars").innerHTML = rows
    .map((row) =>
      barRow(
        row.dataset_name,
        row.sla_attainment_pct,
        `${row.refreshes} refreshes, latest status: ${row.latest_status}`,
        row.latest_status === "Success" ? "good" : "warn",
      ),
    )
    .join("");
}

function renderQuality(rows) {
  const body = rows.slice(0, 8).map((row) => `
    <tr>
      <td><b>${row.check_name}</b><span>${row.source_system}</span></td>
      <td><strong class="${row.severity === "High" ? "text-alert" : "text-warn"}">${row.severity}</strong></td>
      <td>${whole.format(row.records_impacted)}</td>
      <td>${row.business_owner}</td>
    </tr>
  `);
  document.querySelector("#qualityTable").innerHTML = table(["Issue", "Severity", "Records", "Owner"], body);
}

function renderDefinitions(rows) {
  document.querySelector("#definitionGrid").innerHTML = rows.map((row) => `
    <article class="definition">
      <div>
        <h3>${row.kpi_name}</h3>
        <p>${row.business_definition}</p>
      </div>
      <footer>
        <span>${row.domain}</span>
        <b>${row.business_owner}</b>
        <em>${row.certification_status}</em>
      </footer>
    </article>
  `).join("");
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      activateSurface(button.dataset.tab);
    });
  });
}

function activateSurface(surfaceId) {
  const button = document.querySelector(`.tab[data-tab="${surfaceId}"]`);
  const surface = document.getElementById(surfaceId);
  if (!button || !surface) return;
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("is-active"));
  document.querySelectorAll(".surface").forEach((item) => item.classList.remove("is-active"));
  button.classList.add("is-active");
  surface.classList.add("is-active");
}

async function init() {
  bindTabs();
  const [summary, readiness, suppliers, queue, refresh, quality, definitions] = await Promise.all([
    fetch(paths.summary).then((response) => response.json()),
    loadCsv(paths.readiness),
    loadCsv(paths.suppliers),
    loadCsv(paths.queue),
    loadCsv(paths.refresh),
    loadCsv(paths.quality),
    loadCsv(paths.definitions),
  ]);
  renderMetrics(summary);
  renderReadiness(readiness);
  renderSupplierTable(suppliers);
  renderRiskQueue(queue);
  renderRefresh(refresh);
  renderQuality(quality);
  renderDefinitions(definitions);
  const requestedSurface = new URLSearchParams(window.location.search).get("surface");
  if (requestedSurface) activateSurface(requestedSurface);
}

init();
