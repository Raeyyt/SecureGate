"""
SecureGate - Real-Time Dashboard (Stage 11, v2)

A small local web app that serves a live-updating security dashboard.
Reads securegate_log.jsonl each time it's asked and returns the parsed
events as JSON; the browser page polls that endpoint every 2 seconds
and redraws itself - no page reloads needed.

Setup (one time):
    pip install flask

Usage:
    python securegate_dashboard.py

Then open this in your browser:
    http://127.0.0.1:5000
Leave it open - it updates on its own as new events arrive in the log.
"""

import json
from collections import Counter, defaultdict
from flask import Flask, jsonify, Response

LOG_FILE = "securegate_log.jsonl"

app = Flask(__name__)


def load_events():
    events = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return events


@app.route("/api/events")
def api_events():
    events = load_events()

    counts = Counter(e.get("event", "UNKNOWN") for e in events)

    per_minute = defaultdict(int)
    for e in events:
        ts = e.get("timestamp", "")
        minute_key = ts[:16] if len(ts) >= 16 else ts
        per_minute[minute_key] += 1

    timeline_keys = list(per_minute.keys())[-15:]
    timeline_values = [per_minute[k] for k in timeline_keys]
    timeline_labels = [k[-5:] for k in timeline_keys]

    recent = list(reversed(events[-25:]))

    return jsonify({
        "total": len(events),
        "counts": dict(counts),
        "recent": recent,
        "timeline_labels": timeline_labels,
        "timeline_values": timeline_values,
        "last_timestamp": events[-1]["timestamp"] if events else None
    })


@app.route("/")
def index():
    return Response(DASHBOARD_HTML, mimetype="text/html")


DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>SecureGate Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #0f1115;
    --panel: #171a21;
    --panel-border: #262b36;
    --text-main: #e8e9ec;
    --text-muted: #9aa0ac;
    --accent: #3b82f6;
    --green: #22c55e;
    --red: #ef4444;
    --amber: #f59e0b;
    --purple: #a855f7;
  }
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, "Segoe UI", Arial, sans-serif;
    background: var(--bg);
    color: var(--text-main);
    margin: 0;
    padding: 32px;
  }
  header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
  h1 { font-size: 22px; font-weight: 600; margin: 0; }
  .status { display: flex; align-items: center; gap: 8px; color: var(--text-muted); font-size: 13px; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }

  .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .card { background: var(--panel); border: 1px solid var(--panel-border); border-radius: 10px; padding: 18px 20px; }
  .card .num { font-size: 30px; font-weight: 700; line-height: 1.2; }
  .card .label { color: var(--text-muted); font-size: 13px; margin-top: 4px; }
  .card.total .num { color: var(--accent); }
  .card.granted .num { color: var(--green); }
  .card.denied .num { color: var(--red); }
  .card.intrusion .num { color: var(--amber); }
  .card.lockout .num { color: var(--purple); }

  .panels { display: grid; grid-template-columns: 1.1fr 1fr; gap: 16px; margin-bottom: 24px; }
  @media (max-width: 900px) { .panels { grid-template-columns: 1fr; } }
  .panel { background: var(--panel); border: 1px solid var(--panel-border); border-radius: 10px; padding: 18px 20px; }
  .panel h2 { font-size: 14px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin: 0 0 14px 0; }

  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 8px 10px; font-size: 13px; border-bottom: 1px solid var(--panel-border); }
  th { color: var(--text-muted); font-weight: 500; }
  td.uid { color: var(--text-muted); font-family: monospace; }

  .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; }
  .badge.granted { background: rgba(34,197,94,0.15); color: var(--green); }
  .badge.denied { background: rgba(239,68,68,0.15); color: var(--red); }
  .badge.intrusion { background: rgba(245,158,11,0.15); color: var(--amber); }
  .badge.lockout { background: rgba(168,85,247,0.15); color: var(--purple); }
  .badge.other { background: rgba(148,163,184,0.15); color: var(--text-muted); }

  footer { color: var(--text-muted); font-size: 12px; margin-top: 8px; }
</style>
</head>
<body>

<header>
  <h1>SecureGate security dashboard</h1>
  <div class="status"><span class="dot"></span><span id="statusText">Live - updating every 2s</span></div>
</header>

<div class="cards">
  <div class="card total"><div class="num" id="totalCount">0</div><div class="label">Total events logged</div></div>
  <div class="card granted"><div class="num" id="grantedCount">0</div><div class="label">Access granted</div></div>
  <div class="card denied"><div class="num" id="deniedCount">0</div><div class="label">Access denied</div></div>
  <div class="card intrusion"><div class="num" id="intrusionCount">0</div><div class="label">Intrusions detected</div></div>
  <div class="card lockout"><div class="num" id="lockoutCount">0</div><div class="label">Brute-force lockouts</div></div>
</div>

<div class="panels">
  <div class="panel">
    <h2>Activity over time</h2>
    <canvas id="timelineChart" height="160"></canvas>
  </div>
  <div class="panel">
    <h2>Events by type</h2>
    <canvas id="typeChart" height="160"></canvas>
  </div>
</div>

<div class="panel">
  <h2>Recent events</h2>
  <table>
    <thead><tr><th>Time</th><th>Event</th><th>Detail</th><th>UID</th></tr></thead>
    <tbody id="eventsBody"></tbody>
  </table>
</div>

<footer id="lastUpdate"></footer>

<script>
let timelineChart, typeChart;

function badgeClass(eventType) {
  if (eventType === "ACCESS_GRANTED") return "granted";
  if (eventType.includes("DENIED") || eventType.includes("FAILURE")) return "denied";
  if (eventType === "INTRUSION_DETECTED") return "intrusion";
  if (eventType === "BRUTE_FORCE_DETECTED") return "lockout";
  return "other";
}

function initCharts() {
  const tctx = document.getElementById('timelineChart');
  timelineChart = new Chart(tctx, {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Events per minute', data: [], borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,0.15)', fill: true, tension: 0.3 }] },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, color: '#9aa0ac' }, grid: { color: '#262b36' } },
        x: { ticks: { color: '#9aa0ac' }, grid: { color: '#262b36' } }
      }
    }
  });

  const ctx = document.getElementById('typeChart');
  typeChart = new Chart(ctx, {
    type: 'bar',
    data: { labels: [], datasets: [{ label: 'Count', data: [], backgroundColor: '#3b82f6' }] },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, color: '#9aa0ac' }, grid: { color: '#262b36' } },
        x: { ticks: { color: '#9aa0ac' }, grid: { color: '#262b36' } }
      }
    }
  });
}

async function refresh() {
  try {
    const res = await fetch('/api/events');
    const data = await res.json();

    document.getElementById('totalCount').textContent = data.total;
    document.getElementById('grantedCount').textContent = data.counts.ACCESS_GRANTED || 0;
    document.getElementById('deniedCount').textContent = data.counts.ACCESS_DENIED || 0;
    document.getElementById('intrusionCount').textContent = data.counts.INTRUSION_DETECTED || 0;
    document.getElementById('lockoutCount').textContent = data.counts.BRUTE_FORCE_DETECTED || 0;

    timelineChart.data.labels = data.timeline_labels;
    timelineChart.data.datasets[0].data = data.timeline_values;
    timelineChart.update();

    typeChart.data.labels = Object.keys(data.counts);
    typeChart.data.datasets[0].data = Object.values(data.counts);
    typeChart.update();

    const tbody = document.getElementById('eventsBody');
    tbody.innerHTML = data.recent.map(e => {
      const cls = badgeClass(e.event || "");
      const uid = e.uid ? e.uid : "-";
      return `<tr>
        <td>${e.timestamp || '-'}</td>
        <td><span class="badge ${cls}">${e.event || '-'}</span></td>
        <td>${e.detail || '-'}</td>
        <td class="uid">${uid}</td>
      </tr>`;
    }).join('');

    document.getElementById('lastUpdate').textContent =
      data.last_timestamp ? `Last event: ${data.last_timestamp}` : 'No events logged yet';
    document.getElementById('statusText').textContent = 'Live - updating every 2s';
  } catch (err) {
    document.getElementById('statusText').textContent = 'Connection lost - retrying...';
  }
}

initCharts();
refresh();
setInterval(refresh, 2000);
</script>

</body>
</html>"""


if __name__ == "__main__":
    print("Starting SecureGate dashboard at http://127.0.0.1:5000")
    print("Leave this window open. Press Ctrl+C to stop.")
    app.run(debug=False, port=5000)
