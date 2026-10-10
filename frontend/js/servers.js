const REFRESH_MS = 10_000;

const rows = document.getElementById("servers");
const summary = document.getElementById("summary");
const updated = document.getElementById("updated");


function renderMetric(value) {
  const width = Math.min(Math.max(value, 0), 100);
  return `
    <div class="metric">
      <span class="metric-value">${value.toFixed(1)}%</span>
      <div class="bar"><div class="bar-fill ${level(value)}" style="width: ${width}%"></div></div>
    </div>`;
}

function renderRow(server) {
  const url = `/server/${encodeURIComponent(server.hostname)}`;
  return `
    <tr class="${server.online ? "" : "row-offline"}" data-href="${url}">
      <td><span class="status ${server.online ? "" : "offline"}">${server.online ? "Работает" : "Недоступен"}</span></td>
      <td><a class="server-name" href="${url}">${escapeHtml(server.hostname)}</a></td>
      <td>${renderMetric(server.cpu_usage)}</td>
      <td>${renderMetric(server.memory_used_percent)}</td>
      <td>${renderMetric(server.disk_used_percent)}</td>
      <td class="seen">${formatAgo(server.seconds_ago)}</td>
    </tr>`;
}

async function loadServers() {
  try {
    const response = await fetch("/servers");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const servers = await response.json();

    if (servers.length === 0) {
      rows.innerHTML = `<tr><td colspan="6" class="empty">Пока нет ни одного сервера. Запустите агента.</td></tr>`;
      summary.textContent = "0 серверов";
    } else {
      rows.innerHTML = servers.map(renderRow).join("");
      const online = servers.filter((s) => s.online).length;
      summary.textContent = `${servers.length} всего · ${online} работает`;
    }

    updated.textContent = `обновлено ${new Date().toLocaleTimeString("ru-RU")}`;
  } catch (error) {
    summary.textContent = `Не удалось обновить данные: ${error.message}`;
  }
}


rows.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-href]");
  if (row) window.location.href = row.dataset.href;
});

loadServers();
setInterval(loadServers, REFRESH_MS);