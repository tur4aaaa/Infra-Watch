const REFRESH_MS = 30_000;


const hostname = decodeURIComponent(window.location.pathname.split("/").pop());

const el = {
  hostname: document.getElementById("hostname"),
  status: document.getElementById("status"),
  message: document.getElementById("message"),
  updated: document.getElementById("updated"),
  cpu: document.getElementById("stat-cpu"),
  mem: document.getElementById("stat-mem"),
  disk: document.getElementById("stat-disk"),
  seen: document.getElementById("stat-seen"),
};

el.hostname.textContent = hostname;
document.title = `${hostname} · InfraWatch`;


const css = getComputedStyle(document.documentElement);
const cssColor = (name) => css.getPropertyValue(name).trim();
const COLORS = {
  green: cssColor("--ok"),
  yellow: cssColor("--warn"),
  border: cssColor("--border"),
  muted: cssColor("--muted"),
  blue: "#58a6ff",
};

Chart.defaults.color = COLORS.muted;
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.font.size = 11;

let minutes = 60;


function formatBytes(bytes) {
  if (bytes < 1024) return `${Math.round(bytes)} B/s`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB/s`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB/s`;
}

function formatTime(ts) {
  const date = new Date(ts * 1000);  // unix seconds to milliseconds
  const time = date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  if (minutes <= 24 * 60) return time;
  const day = date.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
  return `${day} ${time}`;
}

function createChart(canvasId, series, { percent = true } = {}) {
  const format = (value) => (percent ? `${value.toFixed(1)}%` : formatBytes(value));

  return new Chart(document.getElementById(canvasId), {
    type: "line",
    data: {
      labels: [],
      datasets: series.map((s) => ({
        label: s.label,
        data: [],
        borderColor: s.color,
        backgroundColor: s.color + "1a",  
        fill: true,
        borderWidth: 1.5,
        pointRadius: 0,                  
        tension: 0.25,                   
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: "index", intersect: false },  
      plugins: {
        legend: {
          display: series.length > 1,
          align: "end",
          labels: { boxWidth: 10, boxHeight: 2 },
        },
        tooltip: {
          callbacks: { label: (ctx) => `${ctx.dataset.label}: ${format(ctx.parsed.y)}` },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 6, maxRotation: 0 } },
        y: {
          min: 0,
          max: percent ? 100 : undefined,
          border: { display: false },
          grid: { color: COLORS.border },
          ticks: { maxTicksLimit: 5, callback: (v) => (percent ? `${v}%` : formatBytes(v)) },
        },
      },
    },
  });
}

const charts = {
  cpu: createChart("chart-cpu", [{ label: "CPU", color: COLORS.green }]),
  mem: createChart("chart-mem", [{ label: "Память", color: COLORS.blue }]),
  disk: createChart("chart-disk", [{ label: "Диск", color: COLORS.yellow }]),
  net: createChart(
    "chart-net",
    [
      { label: "Входящий", color: COLORS.green },
      { label: "Исходящий", color: COLORS.blue },
    ],
    { percent: false },
  ),
};


function setData(chart, labels, ...series) {
  chart.data.labels = labels;
  series.forEach((values, i) => {
    chart.data.datasets[i].data = values;
  });
  chart.update();
}

async function loadCurrent() {
  const response = await fetch("/servers");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const servers = await response.json();
  const server = servers.find((s) => s.hostname === hostname);

  if (!server) {
    el.status.textContent = "Сервер не найден";
    el.status.className = "status offline";
    return;
  }

  el.status.textContent = server.online ? "Работает" : "Недоступен";
  el.status.className = server.online ? "status" : "status offline";
  el.cpu.textContent = `${server.cpu_usage.toFixed(1)}%`;
  el.mem.textContent = `${server.memory_used_percent.toFixed(1)}%`;
  el.disk.textContent = `${server.disk_used_percent.toFixed(1)}%`;
  el.seen.textContent = formatAgo(server.seconds_ago);
}

async function loadHistory() {
  const params = new URLSearchParams({ hostname, minutes });
  const response = await fetch(`/metrics/history?${params}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const { points } = await response.json();

  el.message.textContent = points.length ? "" : "Нет данных за выбранный период.";

  const labels = points.map((p) => formatTime(p.ts));
  setData(charts.cpu, labels, points.map((p) => p.cpu_usage));
  setData(charts.mem, labels, points.map((p) => p.memory_used_percent));
  setData(charts.disk, labels, points.map((p) => p.disk_used_percent));
  setData(
    charts.net,
    labels,
    points.map((p) => p.rx_bytes_per_sec),
    points.map((p) => p.tx_bytes_per_sec),
  );
}

async function refresh() {
  try {
    await Promise.all([loadCurrent(), loadHistory()]);  
    el.updated.textContent = `обновлено ${new Date().toLocaleTimeString("ru-RU")}`;
  } catch (error) {
    el.message.textContent = `Не удалось обновить данные: ${error.message}`;
  }
}


document.getElementById("periods").addEventListener("click", (event) => {
  const tab = event.target.closest("[data-minutes]");
  if (!tab) return;
  minutes = Number(tab.dataset.minutes);
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
  refresh();
});

refresh();
setInterval(refresh, REFRESH_MS);