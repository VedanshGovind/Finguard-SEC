window.FG = (function () {
  var K = "fg_token", T = "fg_theme";
  var API = typeof window.FINGUARD_API_BASE === "string" ? window.FINGUARD_API_BASE.replace(/\/$/, "")
    : (/^https?:$/.test(location.protocol) && location.port === "8000" ? "" : "http://localhost:8000");
  function theme(t) { document.documentElement.setAttribute("data-bs-theme", t); try { localStorage.setItem(T, t); } catch (e) {} document.dispatchEvent(new Event("fg-theme")); }
  try { var s = localStorage.getItem(T); if (s) document.documentElement.setAttribute("data-bs-theme", s); } catch (e) {}
  return {
    API: API,
    token: function () { try { return sessionStorage.getItem(K); } catch (e) { return null; } },
    setToken: function (v) { try { sessionStorage.setItem(K, v); } catch (e) {} },
    clear: function () { try { sessionStorage.removeItem(K); } catch (e) {} },
    toggleTheme: function () { theme(document.documentElement.getAttribute("data-bs-theme") === "light" ? "dark" : "light"); },
    css: function (n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  };
})();
