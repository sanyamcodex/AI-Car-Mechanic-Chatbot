/**
 * ============================================================================
 * [ISOLATED DEMO / DEV ENVIRONMENT HARNESS]
 * ============================================================================
 * NOTICE: This file is strictly a standalone dev server harness for the AI Studio
 * container runtime on port 3000.
 *
 * THIS IS NOT THE PRODUCTION APPLICATION.
 * - Production Frontend: Located in `/frontend` (Next.js 14 App Router, TypeScript, Tailwind)
 *   Deployment target: Vercel (Root Directory: frontend)
 * - Production Backend: Located in `/backend` (Django REST Framework, SQLite/PostgreSQL)
 *   Deployment target: Render / Docker (Build: ./start.sh)
 * ============================================================================
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.env.PORT || '3000', 10);
const HOST = '0.0.0.0';

// In-memory sessions store for web preview
const sessions = new Map();

function getSession(convId) {
  if (!convId || !sessions.has(convId)) {
    const id = convId || 'conv-' + Math.random().toString(36).substring(2, 9);
    const session = {
      id,
      state: 'INTAKE',
      symptoms: [],
      answers: {},
      vehicle: {},
      vehicle_asked: false,
      step: 0,
    };
    sessions.set(id, session);
    return session;
  }
  return sessions.get(convId);
}

const STARTER_CHIPS = [
  { id: "engine_no_crank", label: "Car won't start", question_id: "intake" },
  { id: "brake_squeal", label: "Brake noise", question_id: "intake" },
  { id: "overheating", label: "Overheating", question_id: "intake" },
  { id: "check_engine_light", label: "Warning light on", question_id: "intake" },
  { id: "vibration_speed", label: "Vibration / shaking", question_id: "intake" },
  { id: "ac_not_cooling", label: "AC not cooling", question_id: "intake" },
];

function processTurn(session, text, choice) {
  const normText = (text || '').trim().toLowerCase();
  const choiceId = choice ? choice.option_id : null;
  const choiceQ = choice ? choice.question_id : null;

  let messages = [];
  let suggested_replies = [];
  let diagnosis = null;

  // Off topic check
  if (normText && (normText.includes('lasagna') || normText.includes('recipe') || normText.includes('weather') || normText.includes('joke'))) {
    messages.push({
      sender: 'bot',
      kind: 'text',
      text: "I'm a car mechanic assistant, so I can only help with vehicle and mechanical problems. Tell me what your car is doing, or pick one below.",
    });
    suggested_replies = STARTER_CHIPS;
    return { conversation_id: session.id, messages, suggested_replies, diagnosis };
  }

  // State: INTAKE
  if (session.state === 'INTAKE') {
    if (choiceQ === 'intake' || normText.includes('brake') || normText.includes('squeal') || choiceId === 'brake_squeal') {
      session.symptoms.push('brake_squeal');
      session.state = 'CLARIFYING';
      session.vehicle_asked = true;
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: "Could you share your vehicle's make, model, and year? Knowing your car helps provide more accurate diagnostic suggestions.",
      });
      suggested_replies = [{ id: 'skip', label: 'Skip', question_id: 'vehicle' }];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    if (choiceId === 'overheating' || normText.includes('overheat') || normText.includes('temp')) {
      session.symptoms.push('overheating');
      session.state = 'CLARIFYING';
      session.vehicle_asked = true;
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: "Safety first: Stop the engine immediately and let it cool. Severe risk of engine seizure.\n\nCould you share your vehicle's make, model, and year? Knowing your car helps provide more accurate diagnostic suggestions.",
      });
      suggested_replies = [{ id: 'skip', label: 'Skip', question_id: 'vehicle' }];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    // Default welcome
    messages.push({
      sender: 'bot',
      kind: 'text',
      text: "Hello! I'm your virtual mechanic assistant. What seems to be the problem with your vehicle? Describe the symptoms or pick one of the common issues below.",
    });
    suggested_replies = STARTER_CHIPS;
    return { conversation_id: session.id, messages, suggested_replies, diagnosis };
  }

  // State: CLARIFYING
  if (session.state === 'CLARIFYING') {
    if (choiceQ === 'vehicle' || session.step === 0) {
      session.step = 1;
      messages.push({
        sender: 'bot',
        kind: 'question',
        text: "When do you hear the brake noise?",
      });
      suggested_replies = [
        { id: 'only_braking', label: 'Only when braking', question_id: 'q_brake_when' },
        { id: 'all_the_time', label: 'Constantly while rolling', question_id: 'q_brake_when' },
        { id: 'unknown', label: 'Not sure', question_id: 'q_brake_when' },
      ];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    if (session.step === 1) {
      session.step = 2;
      messages.push({
        sender: 'bot',
        kind: 'question',
        text: "How does the brake pedal feel when stopping?",
      });
      suggested_replies = [
        { id: 'normal_effort', label: 'Normal pedal effort', question_id: 'q_brake_pedal_feel' },
        { id: 'pulsating_pedal', label: 'Pulsating or vibrating pedal', question_id: 'q_brake_pedal_feel' },
        { id: 'unknown', label: 'Not sure', question_id: 'q_brake_pedal_feel' },
      ];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    if (session.step === 2) {
      session.state = 'BOOKING_OFFERED';
      diagnosis = {
        top_cause_key: 'worn_brake_pads',
        top_cause_label: 'Worn brake pads',
        confidence: 0.92,
        service: {
          key: 'brake_service',
          name: 'Brake pad & disc service',
          price_min: 1500,
          price_max: 6000,
          duration_hours: 2.0,
          currency: 'INR',
        },
      };

      messages.push({
        sender: 'bot',
        kind: 'diagnosis',
        text: "Based on what you've told me, the most likely cause is **Worn brake pads** (92% confidence). Brake pads worn down to wear indicators. Recommended: **Brake pad & disc service** — est. ₹1500–₹6000, about 2h (final quote after inspection). Want me to book a mechanic?",
      });
      suggested_replies = [
        { id: 'yes', label: 'Yes, book a mechanic', question_id: 'book_offer' },
        { id: 'no', label: 'Not now', question_id: 'book_offer' },
      ];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }
  }

  // State: BOOKING_OFFERED
  if (session.state === 'BOOKING_OFFERED') {
    if (choiceId === 'yes' || normText.includes('yes') || normText.includes('book')) {
      session.state = 'BOOKING_DETAILS';
      session.pending_field = 'customer_name';
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: "Great! Who should the mechanic ask for? Please enter your full name.",
      });
      suggested_replies = [];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    } else {
      session.state = 'INTAKE';
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: "No problem. Let me know whenever you'd like to troubleshoot another vehicle issue.",
      });
      suggested_replies = STARTER_CHIPS;
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }
  }

  // State: BOOKING_DETAILS
  if (session.state === 'BOOKING_DETAILS') {
    if (!session.customer_name) {
      session.customer_name = text || 'Customer';
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: `Thanks, ${session.customer_name}. What is your 10-digit mobile number for appointment updates?`,
      });
      suggested_replies = [];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    if (!session.phone) {
      session.phone = text || '9812345670';
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: 'Got it. Which city are you located in?',
      });
      suggested_replies = [
        { id: 'Meerut', label: 'Meerut', question_id: 'city' },
        { id: 'Delhi', label: 'Delhi', question_id: 'city' },
        { id: 'Noida', label: 'Noida', question_id: 'city' },
        { id: 'Gurugram', label: 'Gurugram', question_id: 'city' },
      ];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    if (!session.city) {
      session.city = choiceId || text || 'Meerut';
      messages.push({
        sender: 'bot',
        kind: 'text',
        text: `Perfect. When should our mechanic visit in ${session.city}? Select a slot below:`,
      });
      suggested_replies = [
        { id: 'tomorrow_10am', label: 'Tomorrow at 10:00 AM', question_id: 'slot' },
        { id: 'tomorrow_2pm', label: 'Tomorrow at 02:00 PM', question_id: 'slot' },
        { id: 'dayafter_11am', label: 'Day after tomorrow at 11:00 AM', question_id: 'slot' },
      ];
      return { conversation_id: session.id, messages, suggested_replies, diagnosis };
    }

    // Booking confirmed
    session.state = 'BOOKING_CONFIRMED';
    const slotLabel = choice ? choice.label : (text || 'Tomorrow at 10:00 AM');
    messages.push({
      sender: 'bot',
      kind: 'booking',
      text: `Your booking has been confirmed (Booking ID: **BK-98F4A2B1**). Service: **Brake pad & disc service**. Assigned mechanic: **Rajesh Kumar** for **${slotLabel}**. Our mechanic will call you to confirm before heading over.`,
    });
    suggested_replies = STARTER_CHIPS;
    return { conversation_id: session.id, messages, suggested_replies, diagnosis };
  }

  // Fallback
  messages.push({
    sender: 'bot',
    kind: 'text',
    text: "How else can I help with your vehicle?",
  });
  suggested_replies = STARTER_CHIPS;
  return { conversation_id: session.id, messages, suggested_replies, diagnosis };
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = url.pathname;

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
      conversations: sessions.size,
      messages_total: 12,
      bot_messages_total: 8,
      diagnoses: 2,
      bookings: 1,
      ai_calls_total: 0,
      ai_cache_hits: 0,
      ai_failures: 0,
      ai_call_ratio: 0.0,
      by_purpose: {
        media_image: 0,
        media_audio: 0,
        media_video: 0,
        extract_text: 0
      }
    }));
    return;
  }

  // Upload endpoint (canonical /api/upload/ and alias /api/uploads/)
  if ((pathname === '/api/upload/' || pathname === '/api/upload' || pathname === '/api/uploads/' || pathname === '/api/uploads') && req.method === 'POST') {
    const dummyId = 'up-' + Math.random().toString(36).substring(2, 10);
    res.writeHead(201, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      id: dummyId,
      original_name: 'uploaded_media.jpg',
      mime_type: 'image/jpeg',
      size_bytes: 102400,
      kind: 'image',
      file_url: 'https://placehold.co/600x400/png?text=Engine+Inspection',
      analysis_status: 'completed',
      analysis_result: {
        observations: 'Visual inspection completed.',
        symptom_keys: ['brake_squeal'],
        confidence: 0.88
      },
      created_at: new Date().toISOString()
    }));
    return;
  }

  // Chat API endpoint
  if ((pathname === '/api/chat/' || pathname === '/api/chat') && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body || '{}');
        const session = getSession(payload.conversation_id);
        const result = processTurn(session, payload.text, payload.choice);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: { code: 'bad_request', message: 'Invalid JSON payload' } }));
      }
    });
    return;
  }

  // HTML Interactive Applet
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Car Mechanic Chatbot</title>
  <style>
    :root {
      --bg: #0b0f19;
      --card: #151d30;
      --card-border: #1e293b;
      --bubble-bot: #1e293b;
      --bubble-user: #f97316;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #f97316;
      --accent-hover: #ea580c;
      --success: #10b981;
      --danger: #ef4444;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background-color: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
    .sandbox-banner { background: rgba(249, 115, 22, 0.12); border-bottom: 1px solid rgba(249, 115, 22, 0.25); padding: 5px 12px; font-size: 11px; text-align: center; color: #fb923c; font-weight: 500; }
    header { background-color: var(--card); border-bottom: 1px solid var(--card-border); padding: 0.8rem 1.5rem; display: flex; justify-content: space-between; align-items: center; z-index: 10; }
    .brand { display: flex; align-items: center; gap: 0.75rem; font-weight: 700; font-size: 1.1rem; }
    .brand-icon { width: 32px; height: 32px; border-radius: 8px; background: rgba(249, 115, 22, 0.15); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; }
    .badge-live { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.25rem 0.6rem; border-radius: 9999px; background: rgba(16, 185, 129, 0.15); color: var(--success); font-size: 0.75rem; font-weight: 600; }
    .dot { width: 7px; height: 7px; border-radius: 50%; background-color: var(--success); }
    
    .chat-container { flex: 1; display: flex; flex-direction: column; max-width: 860px; margin: 0 auto; width: 100%; height: calc(100vh - 85px); overflow: hidden; }
    .messages-area { flex: 1; overflow-y: auto; padding: 1.25rem 1rem; display: flex; flex-direction: column; gap: 1rem; }
    
    .msg-group { display: flex; flex-direction: column; gap: 0.25rem; max-width: 80%; }
    .msg-group.bot { align-self: flex-start; }
    .msg-group.user { align-self: flex-end; align-items: flex-end; }
    
    .msg-bubble { padding: 0.85rem 1.15rem; border-radius: 14px; font-size: 0.95rem; line-height: 1.5; word-wrap: break-word; }
    .msg-group.bot .msg-bubble { background: var(--bubble-bot); color: var(--text); border-top-left-radius: 4px; border: 1px solid var(--card-border); }
    .msg-group.user .msg-bubble { background: var(--bubble-user); color: #fff; border-top-right-radius: 4px; }
    
    .msg-bubble.diagnosis { border: 1px solid #f97316; background: #1c1917; }
    .msg-bubble.booking { border: 1px solid var(--success); background: #062e24; }
    .alert-banner { display: block; background: rgba(239, 68, 68, 0.2); border: 1px solid var(--danger); color: #fca5a5; padding: 0.6rem 0.8rem; border-radius: 8px; margin-bottom: 0.5rem; font-size: 0.85rem; font-weight: 600; }
    
    .replies-area { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.5rem; }
    .chip-btn { background: #1e293b; color: #f1f5f9; border: 1px solid #334155; padding: 0.45rem 0.9rem; border-radius: 20px; font-size: 0.85rem; cursor: pointer; transition: all 0.15s ease-in-out; font-weight: 500; }
    .chip-btn:hover { background: var(--accent); border-color: var(--accent); color: #fff; transform: translateY(-1px); }
    
    .input-bar { background: var(--card); border-top: 1px solid var(--card-border); padding: 0.85rem 1rem; display: flex; gap: 0.75rem; align-items: center; }
    .input-bar input { flex: 1; background: #0f172a; border: 1px solid #334155; color: #fff; padding: 0.75rem 1rem; border-radius: 10px; font-size: 0.95rem; outline: none; transition: border-color 0.2s; }
    .input-bar input:focus { border-color: var(--accent); }
    .btn-send { background: var(--accent); color: #fff; border: none; padding: 0.75rem 1.4rem; border-radius: 10px; font-weight: 600; font-size: 0.95rem; cursor: pointer; transition: background 0.2s; }
    .btn-send:hover { background: var(--accent-hover); }
  </style>
</head>
<body>
  <div class="sandbox-banner">
    ⚠️ <strong>SANDBOX HARNESS</strong> &bull; Production Next.js app in <code>frontend/</code> (deploy to Vercel) &bull; Django API in <code>backend/</code> (deploy to Render)
  </div>

  <header>
    <div class="brand">
      <div class="brand-icon">🔧</div>
      <span>Car Mechanic Assistant</span>
    </div>
    <div class="badge-live">
      <span class="dot"></span> Preview Port 3000
    </div>
  </header>

  <div class="chat-container">
    <div class="messages-area" id="messages-area">
      <!-- Bot greeting -->
      <div class="msg-group bot">
        <div class="msg-bubble">
          Hello! I'm your virtual mechanic assistant. What seems to be the problem with your vehicle? Describe the symptoms or pick one of the common issues below.
        </div>
        <div class="replies-area" id="starter-replies">
          <button class="chip-btn" onclick="sendChoice('intake', 'engine_no_crank', 'Car won\\'t start')">🚗 Car won't start</button>
          <button class="chip-btn" onclick="sendChoice('intake', 'brake_squeal', 'Brake noise')">🛑 Brake noise</button>
          <button class="chip-btn" onclick="sendChoice('intake', 'overheating', 'Overheating')">🌡️ Overheating</button>
          <button class="chip-btn" onclick="sendChoice('intake', 'check_engine_light', 'Warning light on')">⚠️ Warning light on</button>
          <button class="chip-btn" onclick="sendChoice('intake', 'vibration_speed', 'Vibration / shaking')">〰️ Vibration / shaking</button>
          <button class="chip-btn" onclick="sendChoice('intake', 'ac_not_cooling', 'AC not cooling')">❄️ AC not cooling</button>
        </div>
      </div>
    </div>

    <div class="input-bar">
      <input type="text" id="user-input" placeholder="Describe symptoms (e.g. brakes squeaking when I stop)..." onkeypress="handleKeyPress(event)" />
      <button class="btn-send" onclick="sendText()">Send</button>
    </div>
  </div>

  <script>
    let currentConversationId = null;

    function handleKeyPress(e) {
      if (e.key === 'Enter') {
        sendText();
      }
    }

    function appendUserMessage(text) {
      const area = document.getElementById('messages-area');
      const group = document.createElement('div');
      group.className = 'msg-group user';
      group.innerHTML = '<div class="msg-bubble">' + escapeHtml(text) + '</div>';
      area.appendChild(group);
      area.scrollTop = area.scrollHeight;
    }

    function appendBotMessages(messages, replies) {
      const area = document.getElementById('messages-area');
      const group = document.createElement('div');
      group.className = 'msg-group bot';

      let inner = '';
      messages.forEach(msg => {
        let text = msg.text || '';
        let bubbleClass = 'msg-bubble';
        if (msg.kind === 'diagnosis') bubbleClass += ' diagnosis';
        if (msg.kind === 'booking') bubbleClass += ' booking';

        // Render Markdown **bold**
        let formatted = escapeHtml(text).replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
        if (formatted.includes('Safety first:')) {
          formatted = formatted.replace(/(Safety first:.*?)\\n\\n/s, '<span class="alert-banner">⚠️ $1</span>');
        }

        inner += '<div class="' + bubbleClass + '">' + formatted.replace(/\\n/g, '<br>') + '</div>';
      });

      if (replies && replies.length > 0) {
        inner += '<div class="replies-area">';
        replies.forEach(rep => {
          inner += '<button class="chip-btn" onclick="sendChoice(\\'' + rep.question_id + '\\', \\'' + rep.id + '\\', \\'' + escapeAttr(rep.label) + '\\')">' + escapeHtml(rep.label) + '</button>';
        });
        inner += '</div>';
      }

      group.innerHTML = inner;
      area.appendChild(group);
      area.scrollTop = area.scrollHeight;
    }

    async function sendTurn(payload) {
      if (currentConversationId) {
        payload.conversation_id = currentConversationId;
      }
      try {
        const res = await fetch('/api/chat/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.conversation_id) {
          currentConversationId = data.conversation_id;
        }
        appendBotMessages(data.messages || [], data.suggested_replies || []);
      } catch (err) {
        console.error('Chat error', err);
      }
    }

    function sendText() {
      const input = document.getElementById('user-input');
      const val = input.value.trim();
      if (!val) return;
      input.value = '';
      appendUserMessage(val);
      sendTurn({ text: val });
    }

    function sendChoice(qId, optId, label) {
      appendUserMessage(label);
      sendTurn({ choice: { question_id: qId, option_id: optId, label: label } });
    }

    function escapeHtml(str) {
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function escapeAttr(str) {
      return str.replace(/'/g, "\\\\'");
    }
  </script>
</body>
</html>`);
});

server.listen(PORT, HOST, () => {
  console.log(`[HARNESS] AI Car Mechanic dev sandbox running on http://${HOST}:${PORT}`);
});
