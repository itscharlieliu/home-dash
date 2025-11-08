const registry = new Map();
const palette = [
  "#38bdf8",
  "#c084fc",
  "#4ade80",
  "#facc15",
  "#fb7185",
  "#f97316",
  "#818cf8",
];

let homeDashConfig = null;
let refreshIntervalSeconds = 5;

document.addEventListener("DOMContentLoaded", () => {
  const config = loadConfig();
  refreshIntervalSeconds = Math.max(Number(config.refreshInterval ?? 5) || 5, 1);
  setupRegistry(config);
  refreshMetrics();
  setInterval(refreshMetrics, refreshIntervalSeconds * 1000);
});

function loadConfig() {
  if (homeDashConfig) {
    return homeDashConfig;
  }
  if (window.HOME_DASH && typeof window.HOME_DASH === "object" && !Array.isArray(window.HOME_DASH)) {
    homeDashConfig = window.HOME_DASH;
    return homeDashConfig;
  }
  const element = document.getElementById("home-dash-config");
  if (!element) {
    console.warn("Home Dash config script tag not found.");
    homeDashConfig = {};
    return homeDashConfig;
  }
  try {
    homeDashConfig = JSON.parse(element.textContent || "{}");
  } catch (error) {
    console.error("Failed to parse Home Dash config JSON.", error);
    homeDashConfig = {};
  }
  window.HOME_DASH = homeDashConfig;
  return homeDashConfig;
}

function setupRegistry(config) {
  const metricDefinitions = Array.isArray(config.metrics) ? config.metrics : [];
  const chartAvailable = typeof window.Chart === "function";

  metricDefinitions.forEach((definition) => {
    const card = document.querySelector(`[data-metric-id="${definition.id}"]`);
    if (!card) return;
    const config = { ...(definition.display ?? { type: "json" }) };
    const output = card.querySelector(".metric-output");
    const chartCanvas = card.querySelector(".metric-chart");
    const entry = {
      definition,
      config,
      card,
      output,
      chartCanvas,
      chartContainer: chartCanvas ? chartCanvas.parentElement : null,
      chart: null,
      table: null,
      tableHead: null,
      tableBody: null,
      tableCaption: null,
    };

    if (config.type === "timeseries" && chartAvailable) {
      activateChart(card, chartCanvas, output);
      try {
        entry.chart = buildChart(chartCanvas, definition);
      } catch (error) {
        console.error("Failed to initialise chart for", definition.id, error);
        entry.config.type = "json";
        deactivateChart(chartCanvas, output);
      }
    } else if (config.type === "timeseries") {
      console.warn(
        `Chart.js unavailable; falling back to JSON view for metric '${definition.id}'.`
      );
      entry.config.type = "json";
      deactivateChart(chartCanvas, output);
    }

    registry.set(definition.id, entry);

    if (entry.config.type !== "timeseries") {
      deactivateChart(chartCanvas, output);
    }
  });
}

function activateChart(card, canvas, output) {
  if (!canvas) return;
  const container = canvas.parentElement;
  if (container) {
    container.classList.remove("hidden");
  }
  canvas.classList.remove("hidden");
  canvas.setAttribute("aria-hidden", "false");
  if (output) {
    output.classList.add("hidden");
  }
}

function deactivateChart(canvas, output) {
  if (canvas?.parentElement) {
    canvas.parentElement.classList.add("hidden");
  }
  if (canvas) {
    canvas.classList.add("hidden");
    canvas.setAttribute("aria-hidden", "true");
  }
  if (output) {
    output.classList.remove("hidden");
  }
}

function buildChart(canvas, definition) {
  if (!canvas) return null;
  const ctx = canvas.getContext("2d");
  const display = definition.display ?? {};

  return new Chart(ctx, {
    type: "line",
    data: {
      datasets: [],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: "time",
          time: { tooltipFormat: "HH:mm:ss", displayFormats: { minute: "HH:mm" } },
          ticks: { maxRotation: 0, color: "rgba(226,232,240,0.6)" },
          grid: { color: "rgba(148,163,184,0.15)" },
        },
        y: {
          ticks: { color: "rgba(226,232,240,0.6)" },
          grid: { color: "rgba(148,163,184,0.15)" },
        },
      },
      plugins: {
        legend: { labels: { color: "#e2e8f0" } },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            label(tooltipItem) {
              const unit = display.unit ? ` ${display.unit}` : "";
              return `${tooltipItem.dataset.label}: ${tooltipItem.parsed.y}${unit}`;
            },
          },
        },
      },
    },
  });
}

async function refreshMetrics() {
  try {
    const response = await fetch(`/api/metrics?history=1`);
    if (!response.ok) {
      throw new Error(`Failed to load metrics (${response.status})`);
    }
    const payload = await response.json();
    payload.forEach((item) => updateMetric(item));
  } catch (error) {
    console.error(error);
    registry.forEach(({ output }) => {
      if (output) {
        output.classList.remove("hidden");
        output.textContent = String(error);
      }
    });
  }
}

function updateMetric(item) {
  const entry = registry.get(item.definition.id);
  if (!entry) return;

  entry.definition = item.definition;
  const displayType = entry.config.type;
  const latestData = item.latest?.data ?? null;
  const timestamp = item.latest?.timestamp ?? null;

  if (displayType === "timeseries") {
    if (!entry.chart) {
      entry.config.type = "json";
      deactivateChart(entry.chartCanvas, entry.output);
      updateJson(entry, latestData, timestamp);
      return;
    }
    updateChart(entry, item.history ?? []);
    updateMeta(entry, latestData, timestamp);
  } else if (displayType === "table") {
    updateTable(entry, latestData, timestamp);
  } else {
    updateJson(entry, latestData, timestamp);
  }
}

function updateJson(entry, data, timestamp) {
  if (entry.chartCanvas) {
    deactivateChart(entry.chartCanvas, entry.output);
  }
  if (!entry.output) return;
  entry.output.classList.remove("hidden");
  entry.output.textContent = formatMetric(data, timestamp);
}

function updateTable(entry, data, timestamp) {
  if (entry.chartCanvas) {
    deactivateChart(entry.chartCanvas, entry.output);
  }
  const rows = Array.isArray(data?.partitions) ? data.partitions : [];
  const columns = entry.config.options?.columns ?? Object.keys(rows[0] ?? {});

  if (!entry.table) {
    entry.table = document.createElement("table");
    entry.table.className = "metric-table";
    entry.tableCaption = document.createElement("caption");
    entry.tableCaption.classList.add("hidden");
    entry.tableHead = document.createElement("thead");
    entry.tableBody = document.createElement("tbody");
    entry.table.append(entry.tableCaption, entry.tableHead, entry.tableBody);
    const body = entry.card.querySelector(".metric-body");
    if (entry.output) {
      entry.output.classList.add("hidden");
    }
    body.appendChild(entry.table);
  } else if (!entry.tableHead || !entry.tableBody || !entry.tableCaption) {
    entry.tableCaption = entry.tableCaption ?? document.createElement("caption");
    entry.tableCaption.classList.add("hidden");
    entry.tableHead = entry.tableHead ?? document.createElement("thead");
    entry.tableBody = entry.tableBody ?? document.createElement("tbody");
    entry.table.replaceChildren(entry.tableCaption, entry.tableHead, entry.tableBody);
  }

  entry.tableHead.replaceChildren();
  entry.tableBody.replaceChildren();

  if (!rows.length) {
    entry.table.classList.add("hidden");
    if (entry.tableCaption) {
      entry.tableCaption.textContent = "";
      entry.tableCaption.classList.add("hidden");
    }
    if (entry.output) {
      entry.output.classList.remove("hidden");
      entry.output.textContent = timestamp
        ? `No data (last update ${formatTimestamp(timestamp)})`
        : "No data";
    }
    return;
  }

  entry.table.classList.remove("hidden");
  if (entry.output) {
    entry.output.classList.add("hidden");
  }

  if (entry.tableCaption) {
    if (timestamp) {
      entry.tableCaption.textContent = `Last updated ${formatTimestamp(timestamp)}`;
      entry.tableCaption.classList.remove("hidden");
    } else {
      entry.tableCaption.textContent = "";
      entry.tableCaption.classList.add("hidden");
    }
  }

  const headerRow = document.createElement("tr");
  columns.forEach((column) => {
    const th = document.createElement("th");
    th.textContent = column;
    headerRow.appendChild(th);
  });
  entry.tableHead.appendChild(headerRow);

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => {
      const td = document.createElement("td");
      td.textContent = formatCell(row[column]);
      tr.appendChild(td);
    });
    entry.tableBody.appendChild(tr);
  });
}

function updateChart(entry, history) {
  if (!entry.chart) return;
  const display = entry.definition.display ?? {};
  const series = display.series ?? { Value: null };

  const entries = Object.entries(series);
  entry.chart.data.datasets = entries.map(([label, path], index) => {
    const color = palette[index % palette.length];
    const dataPoints = history
      .map((sample) => ({
        x: new Date(sample.timestamp),
        y: getByPath(sample.data, path),
      }))
      .filter((point) => typeof point.y === "number");

    return {
      label,
      data: dataPoints,
      parsing: false,
      borderColor: color,
      backgroundColor: hexToRgba(color, 0.25),
      pointRadius: 0,
      pointHitRadius: 8,
      tension: 0.3,
      fill: true,
    };
  });
  entry.chart.update("none");
}

function updateMeta(entry, data, timestamp) {
  if (!entry.output) return;
  const display = entry.definition.display ?? {};
  const series = display.series ?? {};
  const summaryLines = [];
  Object.entries(series).forEach(([label, path]) => {
    const value = getByPath(data, path);
    if (typeof value === "number") {
      summaryLines.push(`${label}: ${value}`);
    }
  });
  if (timestamp) {
    summaryLines.push(`Updated: ${formatTimestamp(timestamp)}`);
  }
  entry.output.classList.remove("hidden");
  entry.output.textContent = summaryLines.join("\n") || "No data";
}

function formatMetric(data, timestamp) {
  const base =
    data === null
      ? "No data"
      : typeof data === "string" || typeof data === "number" || typeof data === "boolean"
      ? String(data)
      : JSON.stringify(data, (_, value) => value, 2);
  if (!timestamp) return base;
  return `${base}\n\nUpdated: ${formatTimestamp(timestamp)}`;
}

function formatTimestamp(timestamp) {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function formatCell(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    if (value > 1_000_000_000_000) return `${(value / 1_000_000_000_000).toFixed(2)}T`;
    if (value > 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
    if (value > 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
    if (value > 1_000) return `${(value / 1_000).toFixed(2)}K`;
    return value.toString();
  }
  return String(value);
}

function getByPath(data, path) {
  if (!path) return null;
  return path.split(".").reduce((value, key) => (value != null ? value[key] : undefined), data);
}

function hexToRgba(hex, alpha) {
  const bigint = parseInt(hex.slice(1), 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

