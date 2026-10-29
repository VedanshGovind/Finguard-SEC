(function () {
  "use strict";
  if (!FG.token()) return (location.replace("index.html"));
  var MAX = 50 * 1024 * 1024;
  var KINDS = {
    video: { ext: [".mp4", ".avi", ".mov"], hint: "MP4, AVI or MOV, up to 50 MB", url: "/analyze/video", btn: "ANALYZE VIDEO" },
    audio: { ext: [".wav", ".mp3", ".flac"], hint: "WAV, MP3 or FLAC, up to 50 MB", url: "/analyze/audio", btn: "ANALYZE AUDIO" }
  };
  var $ = function (i) { return document.getElementById(i); };
  var panels = {}, live;

  function bytes(n) { return n < 1048576 ? (n / 1024).toFixed(1) + " KB" : (n / 1048576).toFixed(2) + " MB"; }
  function clock(s) { s = Math.round(s); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); }
  function pct(v) { return Math.round(v * 1000) / 10; }
  function signOut() { FG.clear(); location.replace("index.html"); }

  /* Welcome sequence after a fresh sign-in */
  (function () {
    var root = document.documentElement, ov = $("welcome");
    if (!root.classList.contains("welcome-on")) return ov.remove();
    try { sessionStorage.removeItem("fg_welcome"); } catch (e) {}
    var msg = "You're in an Administrator Dashboard", el = $("wMsg"), i = 0;
    var calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
    function done() { ov.classList.add("out"); setTimeout(function () { root.classList.remove("welcome-on"); ov.remove(); }, 600); }
    if (calm) { el.textContent = msg; return setTimeout(done, 1200); }
    setTimeout(function t() { el.textContent = msg.slice(0, ++i); if (i < msg.length) setTimeout(t, 32); else setTimeout(done, 1000); }, 1500);
  })();

  /* Header: live status */
  $("ep").textContent = FG.API || location.origin; $("ep").title = $("ep").textContent;
  function health() {
    fetch(FG.API + "/health").then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) {
      $("dot").className = "dot on"; $("st").textContent = "Online"; $("mode").textContent = d.mode || "-"; $("dev").textContent = String(d.device || "-").toUpperCase();
    }).catch(function () { $("dot").className = "dot off"; $("st").textContent = "Unreachable"; $("mode").textContent = $("dev").textContent = "-"; });
  }
  health(); setInterval(health, 15000);
  $("theme").onclick = FG.toggleTheme;
  $("out").onclick = function () {
    fetch(FG.API + "/auth/logout", { method: "POST", headers: { Authorization: "Bearer " + FG.token() } }).catch(function () {}).then(signOut);
  };
  fetch(FG.API + "/auth/me", { headers: { Authorization: "Bearer " + FG.token() } }).then(function (r) {
    if (r.status === 401) return signOut(); return r.json().then(function (d) { $("user").textContent = d.username; });
  }).catch(function () {});

  /* Tabs */
  document.querySelectorAll(".tabs button").forEach(function (b) {
    b.onclick = function () {
      document.querySelectorAll(".tabs button").forEach(function (x) { x.setAttribute("aria-selected", x === b); });
      Object.keys(panels).forEach(function (k) { panels[k].hidden = k !== b.dataset.kind; });
      if (live) { if (b.dataset.kind === "live") live.open(); else live.close(); }
    };
  });

  function waveform(file, canvas, onInfo) {
    var AC = window.AudioContext || window.webkitAudioContext, ctx = canvas.getContext("2d");
    canvas.width = 800; canvas.height = 90;
    function note(t) { ctx.fillStyle = FG.css("--mu"); ctx.font = "13px IBM Plex Mono, monospace"; ctx.fillText(t, 12, 50); }
    if (!AC) return note("Waveform preview unavailable");
    note("Decoding waveform...");
    var ac = new AC();
    file.arrayBuffer().then(function (b) { return ac.decodeAudioData(b); }).then(function (buf) {
      var d = buf.getChannelData(0), step = Math.floor(d.length / 800) || 1;
      ctx.clearRect(0, 0, 800, 90); ctx.fillStyle = FG.css("--fg");
      for (var x = 0; x < 800; x++) {
        var m = 0; for (var i = 0; i < step; i += 16) m = Math.max(m, Math.abs(d[x * step + i] || 0));
        var h = Math.max(1, m * 84); ctx.fillRect(x, 45 - h / 2, 1, h);
      }
      onInfo(buf); ac.close();
    }).catch(function () { ctx.clearRect(0, 0, 800, 90); note("Waveform preview unavailable for this file"); });
  }

  function build(kind) {
    var cfg = KINDS[kind], root = $("tpl").content.firstElementChild.cloneNode(true);
    $("panels").appendChild(root); root.hidden = kind !== "video"; panels[kind] = root;
    var r = function (n) { return root.querySelector('[data-r="' + n + '"]'); };
    var st = { file: null, url: null, busy: false, score: null };
    r("dzHint").textContent = cfg.hint; r("file").accept = cfg.ext.join(","); r("go").textContent = cfg.btn;

    function flash(el, msg) { el.textContent = msg; el.hidden = !msg; }
    function thrText() {
      var t = r("thr").value;
      r("thrOut").textContent = t + "%";
      r("thrHint").textContent = "This dashboard flags any file scoring " + t + "% or higher. Lower values flag more files; higher values flag fewer.";
      r("mark").style.left = "calc(" + t + "% - 1px)";
      if (st.score !== null) {
        var hit = st.score * 100 >= t;
        r("thrNote").textContent = "Score " + pct(st.score) + "% is " + (hit ? "at or above" : "below") + " your " + t + "% threshold: " + (hit ? "FLAGGED" : "not flagged") + " in this view. The backend verdict above uses its own policy thresholds.";
      }
    }
    function reset() {
      flash(r("err"), ""); flash(r("fileErr"), ""); r("res").hidden = true; st.score = null;
      if (st.url) { URL.revokeObjectURL(st.url); st.url = null; }
      r("media").textContent = ""; r("meta").textContent = "";
    }
    function meta(k, v) { var a = document.createElement("dt"), b = document.createElement("dd"); a.textContent = k; b.textContent = v; b.title = v; r("meta").append(a, b); }

    function load(f) {
      reset(); st.file = null; r("work").hidden = true; r("empty").hidden = false;
      if (!f) return;
      var low = f.name.toLowerCase();
      if (!cfg.ext.some(function (e) { return low.endsWith(e); })) return flash(r("fileErr"), "Unsupported file type. Allowed: " + cfg.ext.join(", "));
      if (f.size > MAX) return flash(r("fileErr"), "File is " + bytes(f.size) + ". The edge limit is 50 MB.");
      st.file = f; st.url = URL.createObjectURL(f);
      r("work").hidden = false; r("empty").hidden = true;
      meta("Name", f.name); meta("Size", bytes(f.size)); meta("Type", f.type || low.slice(low.lastIndexOf(".")));
      if (kind === "video") {
        var v = document.createElement("video"); v.controls = true; v.preload = "metadata"; v.src = st.url + "#t=0.5";
        v.onloadedmetadata = function () { meta("Duration", clock(v.duration)); meta("Resolution", v.videoWidth + " x " + v.videoHeight); };
        r("media").append(v);
      } else {
        var c = document.createElement("canvas"), a = document.createElement("audio"); a.controls = true; a.src = st.url;
        r("media").append(c, a);
        waveform(f, c, function (b) { meta("Duration", clock(b.duration)); meta("Sample rate", b.sampleRate + " Hz"); meta("Channels", b.numberOfChannels); });
      }
      thrText();
    }

    r("file").onchange = function () { load(r("file").files[0]); };
    ["dragenter", "dragover"].forEach(function (e) {
      r("dz").addEventListener(e, function (ev) {
        ev.preventDefault(); r("dz").classList.add("over");
        var it = ev.dataTransfer && ev.dataTransfer.items && ev.dataTransfer.items[0];
        r("dzMain").textContent = "Release to load " + ((it && it.type) || "file");
      });
    });
    ["dragleave", "drop"].forEach(function (e) {
      r("dz").addEventListener(e, function (ev) { ev.preventDefault(); r("dz").classList.remove("over"); r("dzMain").textContent = "Drop a file here, or click to browse"; });
    });
    r("dz").addEventListener("drop", function (ev) { if (!st.busy && ev.dataTransfer.files[0]) load(ev.dataTransfer.files[0]); });
    r("thr").oninput = thrText;

    function busy(b, text) {
      st.busy = b; r("go").disabled = b; r("file").disabled = b; r("bar").hidden = !b; r("prog").hidden = !b;
      if (b) { r("bar").classList.remove("ind"); r("bar").firstChild.style.width = "0"; r("prog").textContent = text; }
    }
    function show(d) {
      var dec = d.decision || {}, v = dec.verdict || "UNCERTAIN", s = Number(d.deepfake_score);
      var cls = v === "DEEPFAKE" ? "bad" : v === "REAL" ? "ok" : "warn";
      st.score = s;
      r("score").textContent = pct(s) + "%";
      r("badge").textContent = v; r("badge").className = "badge2 mono " + cls;
      r("fill").style.width = Math.min(100, s * 100) + "%"; r("fill").style.background = "var(--" + cls + ")";
      r("risk").textContent = dec.risk_level || "-"; r("rfile").textContent = d.filename || st.file.name;
      r("explain").textContent = d.explanation || "";
      r("res").hidden = false; thrText();
    }
    r("go").onclick = function () {
      if (!st.file || st.busy) return;
      flash(r("err"), ""); r("res").hidden = true; busy(true, "Uploading 0%");
      var x = new XMLHttpRequest(), fd = new FormData(); fd.append("file", st.file, st.file.name);
      x.open("POST", FG.API + cfg.url); x.setRequestHeader("Authorization", "Bearer " + FG.token());
      x.upload.onprogress = function (e) {
        if (!e.lengthComputable) return;
        var p = Math.round(e.loaded / e.total * 100); r("bar").firstChild.style.width = p + "%";
        if (p >= 100) { r("bar").classList.add("ind"); r("prog").textContent = "Processing through Edge AI pipeline..."; } else r("prog").textContent = "Uploading " + p + "%";
      };
      x.onerror = function () { busy(false); flash(r("err"), "Could not reach the Edge Agent backend at " + (FG.API || location.origin) + "."); health(); };
      x.onload = function () {
        busy(false);
        if (x.status === 401) return signOut();
        var body = {}; try { body = JSON.parse(x.responseText); } catch (e) {}
        if (x.status === 404 || x.status === 405) return flash(r("err"), "This backend does not expose " + cfg.url + " yet.");
        if (x.status < 200 || x.status > 299) return flash(r("err"), "Backend error (" + x.status + "): " + (typeof body.detail === "string" ? body.detail : x.statusText));
        show(body);
      };
      x.send(fd);
    };
    thrText();
  }
  function el(t, c, x) { var e = document.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }

  /* Live analysis: webcam capture, session code, verification */
  function buildLive() {
    var P = $("livePanel"); panels.live = P;
    var v = $("liveVideo"), stat = $("liveStatus"), frame = $("vframe"), dot = $("recdot"), lvl = $("levelBar"),
      bStart = $("recStart"), bStop = $("recStop"), bReset = $("recReset"), bar = $("liveBar"), errB = $("liveErr"), res = $("liveRes");
    var stream = null, rec = null, chunks = [], ac = null, an = null, raf = 0, code = "", busy = false, recording = false;
    var URL_ = "/analyze/live-verification";

    function status(t) { stat.textContent = t; }
    function err(m) { errB.textContent = m || ""; errB.hidden = !m; }
    function buttons() { bStart.disabled = !stream || recording || busy; bStop.disabled = !recording; bReset.disabled = recording || busy; }
    function newCode() {
      var a = new Uint32Array(1); crypto.getRandomValues(a);
      code = String(a[0] % 1000000).padStart(6, "0"); $("liveCode").textContent = code.slice(0, 3) + " " + code.slice(3);
    }

    function meter() {
      var d = new Uint8Array(an.frequencyBinCount);
      (function tick() { raf = requestAnimationFrame(tick); an.getByteFrequencyData(d); var s = 0; for (var i = 0; i < d.length; i++) s += d[i]; lvl.style.width = Math.min(100, s / d.length / 1.5) + "%"; })();
    }
    function open() {
      if (stream) return;
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return status("Camera API unavailable. Open the dashboard at http://localhost:8000 or over HTTPS.");
      status("Requesting camera and microphone access...");
      navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 360 }, audio: true }).then(function (s) {
        stream = s; v.srcObject = s;
        try { var AC = window.AudioContext || window.webkitAudioContext; ac = new AC(); an = ac.createAnalyser(); an.fftSize = 64; ac.createMediaStreamSource(s).connect(an); meter(); } catch (e) {}
        status("Camera and microphone ready"); buttons();
      }).catch(function () { status("Camera access denied. Allow camera and microphone permissions in your browser."); });
    }
    function close() {
      if (recording || busy || !stream) return;
      cancelAnimationFrame(raf); lvl.style.width = "0";
      stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; v.srcObject = null;
      if (ac) { ac.close().catch(function () {}); ac = an = null; }
      status("Camera released"); buttons();
    }

    function card(label, o) {
      var c = el("div", "sc " + (o.verdict === "REAL" ? "ok" : o.verdict === "N/A" ? "" : "bad"));
      c.append(el("div", "l mono", label), el("div", "v mono", (Number(o.score) * 100).toFixed(1) + "%"), el("div", "small mono", o.verdict || "-"));
      return c;
    }
    function render(r) {
      var s = (r && r.scores) || {}, V = s.video || { score: 0, verdict: "N/A" }, A = s.audio || { score: 0, verdict: "N/A" }, C = s.code || {};
      res.textContent = "";
      var grid = el("div", "scs"); grid.append(card("VISUAL ANALYSIS", V), card("AUDIO PATTERNS", A)); res.append(grid);
      var box = el("div", "final");
      if (!(V.score > 0) || !(A.score > 0)) {
        box.classList.add("warn"); box.append(el("h3", "mono", "TRY AGAIN"), el("p", "", "Analysis inconclusive (0% score detected). Use a well-lit environment and speak clearly."));
      } else {
        var pass = r.final_verdict === "PASS"; box.classList.add(pass ? "ok" : "bad");
        var acc = C.confidence != null ? (C.confidence * 100).toFixed(1) + "% match" : "no match data";
        box.append(el("h3", "mono", pass ? "ACCESS GRANTED" : "ACCESS DENIED"), el("p", "", pass ? "Identity verified successfully" : "Security threat detected"),
          el("p", "mono", "Detected SIC: " + (C.spoken_code || "N/A") + " (" + acc + ")"));
      }
      res.append(box);
    }

    function upload(blob) {
      busy = true; buttons(); err(""); bar.hidden = false; bar.classList.remove("ind"); bar.firstChild.style.width = "0";
      var x = new XMLHttpRequest(), fd = new FormData();
      fd.append("file", blob, "session-" + code + ".webm"); fd.append("session_code", code);
      x.open("POST", FG.API + URL_); x.setRequestHeader("Authorization", "Bearer " + FG.token());
      x.upload.onprogress = function (e) {
        if (!e.lengthComputable) return; var p = Math.round(e.loaded / e.total * 100); bar.firstChild.style.width = p + "%";
        if (p >= 100) { bar.classList.add("ind"); status("Analyzing..."); } else status("Uploading " + p + "%");
      };
      function end() { busy = false; bar.hidden = true; buttons(); }
      x.onerror = function () { end(); status("Connection failed"); err("Could not reach the backend at " + (FG.API || location.origin) + "."); health(); };
      x.onload = function () {
        end(); if (x.status === 401) return signOut();
        var body = {}; try { body = JSON.parse(x.responseText); } catch (e) {}
        if (x.status === 404 || x.status === 405) { status("Endpoint unavailable"); return err("This backend does not expose " + URL_ + " yet."); }
        if (x.status < 200 || x.status > 299) { status("Server error"); return err("Backend error (" + x.status + "): " + (typeof body.detail === "string" ? body.detail : x.statusText)); }
        render(body); status("Verification complete");
      };
      x.send(fd);
    }

    bStart.onclick = function () {
      if (!stream) return; if (ac && ac.state === "suspended") ac.resume();
      chunks = []; res.textContent = ""; err("");
      var mt = "video/webm;codecs=vp9,opus";
      try { rec = new MediaRecorder(stream, MediaRecorder.isTypeSupported(mt) ? { mimeType: mt } : undefined); } catch (e) { return err("Recording is not supported in this browser."); }
      rec.ondataavailable = function (e) { if (e.data.size) chunks.push(e.data); };
      rec.onstop = function () { recording = false; frame.classList.remove("rec"); dot.hidden = true; upload(new Blob(chunks, { type: "video/webm" })); };
      rec.start(); recording = true; frame.classList.add("rec"); dot.hidden = false;
      status("RECORDING. Speak code: " + code); buttons();
    };
    bStop.onclick = function () { if (rec && rec.state !== "inactive") rec.stop(); };
    bReset.onclick = function () { res.textContent = ""; err(""); newCode(); if (stream) status("Camera and microphone ready"); else open(); buttons(); };
    $("newCode").onclick = function () { if (!recording) newCode(); };

    /* Forensic metadata, gathered in the browser */
    var ua = navigator.userAgent, gpu = "Unknown", sr = "Unknown", AC2 = window.AudioContext || window.webkitAudioContext;
    try { var gl = document.createElement("canvas").getContext("webgl"), ext = gl && gl.getExtension("WEBGL_debug_renderer_info"); if (ext) gpu = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL); } catch (e) {}
    try { var t = new AC2(); sr = t.sampleRate + " Hz"; t.close(); } catch (e) {}
    var info = {
      os: /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Mac/.test(ua) ? "macOS" : /Linux/.test(ua) ? "Linux" : "Unknown",
      browser: /Edg\//.test(ua) ? "Edge" : /OPR\//.test(ua) ? "Opera" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : "Unknown",
      cores: navigator.hardwareConcurrency || "Unknown", memory: navigator.deviceMemory ? "~" + navigator.deviceMemory + " GB" : "Unknown",
      gpu: gpu, connection: (navigator.connection && navigator.connection.effectiveType) || "Unknown", webdriver: !!navigator.webdriver,
      audio_sample_rate: sr, language: navigator.language, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone, screen: screen.width + " x " + screen.height
    };
    [["DEVICE IDENTITY", [["OS", info.os], ["Browser", info.browser], ["Cores", info.cores]]],
     ["ENVIRONMENT", [["RAM", info.memory], ["GPU", info.gpu], ["Network", info.connection]]],
     ["SECURITY", [["Automation", info.webdriver ? "Detected" : "Clean"], ["Audio rate", info.audio_sample_rate], ["Timezone", info.timezone]]]
    ].forEach(function (g) {
      var box = el("div"), dl = el("dl", "meta mono"); box.append(el("h3", "", g[0]), dl);
      g[1].forEach(function (kv) { var a = el("dt", "", kv[0]), b = el("dd", "", kv[1]); b.title = kv[1]; dl.append(a, b); });
      $("metaGrid").append(box);
    });
    $("metaRaw").textContent = JSON.stringify(info, null, 2);

    newCode(); buttons();
    live = { open: open, close: close };
  }
  buildLive();
  Object.keys(KINDS).forEach(build);
})();
