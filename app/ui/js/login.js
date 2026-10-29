(function () {
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (i) { return document.getElementById(i); };
  if (location.protocol === "file:") $("fileNote").hidden = false;

  /* Typed boot sequence */
  var boot = $("boot"), lines = ["> initializing secure channel", "> edge agent: offline mode", "> awaiting operator credentials"];
  function type(text, done) {
    if (reduce) { boot.textContent = text; return done && done(); }
    var i = 0, base = boot.textContent;
    (function step() { boot.textContent = base + text.slice(0, ++i); if (i < text.length) setTimeout(step, 18); else done && done(); })();
  }
  (function next(n) { if (n < lines.length) type((n ? "\n" : "") + lines[n], function () { next(n + 1); }); })(0);

  /* Network animation */
  var cv = $("bg"), cx = cv.getContext("2d"), pts = [], mouse = { x: -999, y: -999 }, col = "#fff";
  function size() {
    cv.width = innerWidth; cv.height = innerHeight;
    pts = Array.from({ length: Math.min(90, Math.floor(innerWidth * innerHeight / 14000)) }, function () {
      return { x: Math.random() * cv.width, y: Math.random() * cv.height, vx: (Math.random() - .5) * .35, vy: (Math.random() - .5) * .35 };
    });
  }
  function frame() {
    cx.clearRect(0, 0, cv.width, cv.height); cx.fillStyle = col; cx.strokeStyle = col;
    pts.forEach(function (a, i) {
      if (!reduce) { a.x += a.vx; a.y += a.vy; if (a.x < 0 || a.x > cv.width) a.vx *= -1; if (a.y < 0 || a.y > cv.height) a.vy *= -1; }
      cx.globalAlpha = .55; cx.fillRect(a.x - 1, a.y - 1, 2, 2);
      for (var j = i + 1; j < pts.length; j++) {
        var b = pts[j], d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < 130) { cx.globalAlpha = (1 - d / 130) * .22; cx.beginPath(); cx.moveTo(a.x, a.y); cx.lineTo(b.x, b.y); cx.stroke(); }
      }
      var m = Math.hypot(a.x - mouse.x, a.y - mouse.y);
      if (m < 160) { cx.globalAlpha = (1 - m / 160) * .5; cx.beginPath(); cx.moveTo(a.x, a.y); cx.lineTo(mouse.x, mouse.y); cx.stroke(); }
    });
    if (!reduce) requestAnimationFrame(frame);
  }
  function recolor() { col = FG.css("--fg") || "#fff"; if (reduce) frame(); }
  addEventListener("resize", function () { size(); if (reduce) frame(); });
  addEventListener("mousemove", function (e) { mouse.x = e.clientX; mouse.y = e.clientY; });
  document.addEventListener("fg-theme", recolor);
  size(); recolor(); frame();

  /* Sign in */
  var form = $("form"), err = $("err"), card = $("card"), go = $("go");
  function fail(msg) {
    err.textContent = msg; err.hidden = false; go.disabled = false; go.textContent = "AUTHENTICATE";
    card.classList.remove("shake"); void card.offsetWidth; card.classList.add("shake");
  }
  form.addEventListener("submit", function (e) {
    e.preventDefault(); err.hidden = true;
    var u = $("u").value.trim(), p = $("p").value;
    if (!u || !p) return fail("Enter your operator ID and passphrase.");
    go.disabled = true; go.textContent = "VERIFYING...";
    fetch(FG.API + "/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: u, password: p }) })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (b) { return { ok: r.ok, b: b }; }); })
      .then(function (r) {
        if (!r.ok) return fail(typeof r.b.detail === "string" ? r.b.detail : "Sign in failed.");
        FG.setToken(r.b.token); try { sessionStorage.setItem("fg_welcome", "1"); } catch (e) {} card.classList.add("granted"); go.textContent = "ACCESS GRANTED";
        boot.textContent += "\n> access granted";
        setTimeout(function () { location.href = "dashboard.html"; }, reduce ? 0 : 750);
      })
      .catch(function () { fail("Cannot reach the backend at " + (FG.API || location.origin) + "."); });
  });
})();
