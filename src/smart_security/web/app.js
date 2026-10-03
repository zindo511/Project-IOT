const $ = (selector) => document.querySelector(selector);

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function fmtTime(value) {
  return new Intl.DateTimeFormat("vi-VN", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value));
}

async function refresh() {
  try {
    const [system, devices, events] = await Promise.all([
      jsonFetch("/api/v1/system"),
      jsonFetch("/api/v1/devices"),
      jsonFetch("/api/v1/events"),
    ]);
    $("#mode").textContent = system.mode;
    $("#policy").textContent = `${system.config.required_votes}/${system.config.vote_window} quan sát hợp lệ để kết luận.`;
    $("#devices").innerHTML = devices.length ? devices.map((d) => `
      <div class="device"><strong>${d.device_id}</strong><span>Frame: ${d.latest_frame_id || "—"}</span><span class="muted">PIR: ${d.pir_active ? "HIGH" : "LOW"} · ${fmtTime(d.last_seen_at)}</span></div>
    `).join("") : '<div class="empty">Chưa có thiết bị gửi ảnh.</div>';
    $("#events").innerHTML = events.length ? events.map((e) => `
      <tr><td>${fmtTime(e.occurred_at)}</td><td class="level-${e.level}">${e.level}</td><td>${e.reason}</td><td>${e.visit_id}</td><td>${e.acknowledged ? "Đã xem" : `<button class="ack" data-event="${e.event_id}">Đánh dấu</button>`}</td></tr>
    `).join("") : '<tr><td colspan="5" class="empty">Chưa có sự kiện.</td></tr>';
  } catch (error) {
    $("#mode").textContent = "OFFLINE";
    console.error(error);
  }
}

document.addEventListener("click", async (event) => {
  const mode = event.target.dataset.mode;
  const eventId = event.target.dataset.event;
  if (mode) await jsonFetch("/api/v1/system/mode", { method: "POST", body: JSON.stringify({ mode }) });
  if (eventId) await jsonFetch(`/api/v1/events/${eventId}/ack`, { method: "POST" });
  if (event.target.id === "silence") await jsonFetch("/api/v1/system/silence", { method: "POST" });
  if (mode || eventId || event.target.id === "silence" || event.target.id === "refresh") await refresh();
});

refresh();
setInterval(refresh, 1500);

