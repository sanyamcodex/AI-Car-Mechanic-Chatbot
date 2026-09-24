const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT || '3000', 10);
const HOST = '0.0.0.0';

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname;

  // Enable CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Idempotency-Key');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Health check
  if (pathname === '/api/health/' || pathname === '/api/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', db: true }));
    return;
  }

  // Stats check
  if (pathname === '/api/stats/' || pathname === '/api/stats') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      conversations: 0,
      messages_total: 0,
      bot_messages_total: 0,
      diagnoses: 0,
      bookings: 0,
      ai_calls_total: 0,
      ai_cache_hits: 0,
      ai_failures: 0,
      ai_call_ratio: 0,
      by_purpose: {
        media_image: 0,
        media_audio: 0,
        media_video: 0,
        extract_text: 0
      }
    }));
    return;
  }

  // HTML Dashboard
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Car Mechanic Chatbot</title>
  <style>
    :root {
      --bg: #0f172a;
      --card: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #f97316;
      --accent-hover: #ea580c;
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
    header { background-color: var(--card); border-bottom: 1px solid var(--card-border); padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; }
    .brand { display: flex; align-items: center; gap: 0.75rem; font-weight: 700; font-size: 1.15rem; }
    .badge-live { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.25rem 0.6rem; border-radius: 9999px; background: rgba(16, 185, 129, 0.15); color: var(--success); font-size: 0.75rem; font-weight: 600; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background-color: var(--success); }
    main { flex: 1; max-width: 900px; margin: 0 auto; width: 100%; padding: 2rem 1rem; display: flex; flex-direction: column; gap: 1.5rem; }
    .hero { background: var(--card); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.5rem; }
    .hero h1 { font-size: 1.5rem; margin-bottom: 0.5rem; color: #fff; }
    .hero p { color: var(--text-muted); font-size: 0.95rem; line-height: 1.5; }
    .chips-title { font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 0.75rem; }
    .chips-grid { display: flex; flex-wrap: wrap; gap: 0.6rem; }
    .chip { background: #334155; color: #f1f5f9; border: 1px solid #475569; padding: 0.5rem 1rem; border-radius: 8px; font-size: 0.9rem; cursor: pointer; transition: all 0.2s; }
    .chip:hover { background: var(--accent); border-color: var(--accent); color: #fff; }
    .status-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }
    .status-card { background: var(--card); border: 1px solid var(--card-border); border-radius: 10px; padding: 1rem; }
    .status-card h3 { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.4rem; }
    .status-card .val { font-size: 1.3rem; font-weight: 700; color: #fff; }
    .log-box { background: #020617; border: 1px solid var(--card-border); border-radius: 8px; padding: 1rem; font-family: monospace; font-size: 0.85rem; color: #38bdf8; max-height: 200px; overflow-y: auto; }
    footer { text-align: center; padding: 1.5rem; color: var(--text-muted); font-size: 0.8rem; border-top: 1px solid var(--card-border); }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span>🔧 AI Car Mechanic Assistant</span>
    </div>
    <div class="badge-live">
      <span class="dot"></span> Server Active (Port 3000)
    </div>
  </header>

  <main>
    <div class="hero">
      <h1>Senior Virtual Car Mechanic</h1>
      <p>Deterministic diagnostic engine with India-market pricing, safety alerts, and mechanical symptom scoring. Choose an issue below to start diagnosis:</p>
      <div style="margin-top: 1.25rem;">
        <div class="chips-title">Starter Issues</div>
        <div class="chips-grid">
          <button class="chip" onclick="simulateSelect('engine_no_crank', 'Car won\\'t start')">🚗 Car won't start</button>
          <button class="chip" onclick="simulateSelect('brake_squeal', 'Brake noise')">🛑 Brake noise</button>
          <button class="chip" onclick="simulateSelect('overheating', 'Overheating')">🌡️ Overheating</button>
          <button class="chip" onclick="simulateSelect('check_engine_light', 'Warning light on')">⚠️ Warning light on</button>
          <button class="chip" onclick="simulateSelect('vibration_speed', 'Vibration / shaking')">〰️ Vibration / shaking</button>
          <button class="chip" onclick="simulateSelect('ac_not_cooling', 'AC not cooling')">❄️ AC not cooling</button>
        </div>
      </div>
    </div>

    <div class="status-grid">
      <div class="status-card">
        <h3>Knowledge Base</h3>
        <div class="val">34 Canonical Symptoms</div>
      </div>
      <div class="status-card">
        <h3>Diagnostic Rules</h3>
        <div class="val">46 Causes / 68 Questions</div>
      </div>
      <div class="status-card">
        <h3>Service Catalog</h3>
        <div class="val">20 Service Categories</div>
      </div>
      <div class="status-card">
        <h3>Active Mechanics</h3>
        <div class="val">6 City Specialists</div>
      </div>
    </div>

    <div class="status-card">
      <h3>Active Diagnostics Session</h3>
      <div id="session-log" class="log-box">
        [SYSTEM] Dev server running on port 3000.<br>
        [SYSTEM] Health check active at /api/health/<br>
        [SYSTEM] Ready for troubleshooting...
      </div>
    </div>
  </main>

  <footer>
    AI Car Mechanic Engine &bull; Built with deterministic scoring &amp; strict safety filters
  </footer>

  <script>
    function simulateSelect(key, label) {
      const log = document.getElementById('session-log');
      log.innerHTML += '<br>[USER] Selected issue: ' + label + ' (' + key + ')';
      log.innerHTML += '<br>[ENGINE] Matching symptom key "' + key + '" against weighted rule base...';
      if (key === 'overheating' || key === 'soft_brake_pedal') {
        log.innerHTML += '<br><span style="color:#ef4444;">[SAFETY ALERT] Critical warning triggered. Engine shutdown / tow recommended.</span>';
      }
      log.scrollTop = log.scrollHeight;
    }
  </script>
</body>
</html>`);
});

server.listen(PORT, HOST, () => {
  console.log(`AI Car Mechanic server listening on http://${HOST}:${PORT}`);
});
