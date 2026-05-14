#ifndef PAGES_H
#define PAGES_H

const char index_css[] PROGMEM = R"rawliteral(
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; }
.topnav { background: #16213e; padding: 12px 20px; display: flex; align-items: center; justify-content: space-between; }
#status { padding: 4px 12px; border-radius: 12px; color: white; background: #e74c3c; border:none; }
.content { max-width: 500px; margin: 20px auto; padding: 0 16px; }
.card { background: #16213e; border-radius: 10px; padding: 20px; margin-bottom: 16px; }
input { width: 100%; padding: 10px; border-radius: 6px; border: 1px solid #0f8b8d; background: #0f3460; color: #eee; margin-bottom: 8px; }
.btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
button.btn { padding: 12px; border: none; border-radius: 6px; cursor: pointer; background: #0f8b8d; color: white; flex: 1; }
#log { background: #0f3460; border-radius: 6px; padding: 10px; font-size: 0.8rem; height: 80px; overflow-y: auto; color: #aef; }
)rawliteral";

const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE HTML><html>
<head>
  <meta charset="utf-8">
  <title>Somfy Monitor</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="index.css">
</head>
<body>
<div class="topnav"><h1>Somfy Monitor</h1><button id="status">Offline</button></div>
<div class="content">
  <div class="card">
    <h2>Kontrol</h2>
    <input type="text" id="addr" placeholder="Adresse (hex)">
    <input type="number" id="roll" placeholder="Rolling Code" value="0">
    <div style="display:flex; gap:8px;">
        <input type="number" id="reps" placeholder="Repeats" value="1">
        <input type="number" id="delay" placeholder="Delay (ms)" value="150">
    </div>
    <div class="btn-row">
      <button class="btn" onclick="send('Up')">Op</button>
      <button class="btn" onclick="send('My')">My</button>
      <button class="btn" onclick="send('Down')">Ned</button>
    </div>
    <div class="btn-row">
      <button class="btn" onclick="send('Prog')" style="background:#c0392b">Prog</button>
    </div>
  </div>
  <div class="card"><h2>Log</h2><div id="log"></div></div>
</div>
<script>
var ws;
function log(m) { var e=document.getElementById('log'); e.innerHTML+=m+'<br>'; e.scrollTop=e.scrollHeight; }
function send(cmd) {
  var addr = document.getElementById('addr').value.trim();
  var roll = document.getElementById('roll').value;
  document.getElementById('roll').value = parseInt(roll)+1;
  var reps = document.getElementById('reps').value;
  var dly  = document.getElementById('delay').value;
  if(!addr) return;
  var msg = addr + " " + cmd + " " + roll + " " + reps + " " + dly;
  ws.send(msg);
  log("→ " + msg);
}
function connect() {
  ws = new WebSocket('ws://' + location.hostname + '/ws');
  ws.onopen = function() { document.getElementById('status').style.background='#27ae60'; log('Forbundet'); };
  ws.onclose = function() { setTimeout(connect, 2000); };
  ws.onmessage = function(e) { log("← " + e.data); };
}
connect();
</script>
</body></html>
)rawliteral";

#endif