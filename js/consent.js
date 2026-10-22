/* Google Analytics stays unloaded until the visitor accepts. */
(function () {
  var GA_ID = "G-CCKELV4JYT";
  var STORAGE_KEY = "wtho-consent";
  var MAX_AGE_MS = 180 * 24 * 60 * 60 * 1000;
  var COPY = {
    de: {
      text: "Diese Website verwendet Google Analytics, um zu verstehen, wie sie genutzt wird. Das Analyse-Cookie wird erst gesetzt, wenn Sie zustimmen.",
      privacy: "Datenschutz",
      accept: "Akzeptieren",
      decline: "Ablehnen",
      settings: "Cookie-Einstellungen"
    },
    en: {
      text: "This site uses Google Analytics to understand how it is used. The analytics cookie is set only after you agree.",
      privacy: "Privacy",
      accept: "Accept",
      decline: "Decline",
      settings: "Cookie settings"
    }
  };

  var gaLoaded = false;
  var bar = null;
  var acceptBtn = null;

  function lang() {
    try {
      return localStorage.getItem("wtho-lang") === "en" ? "en" : "de";
    } catch (error) {
      return "de";
    }
  }

  function readChoice() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || (data.choice !== "granted" && data.choice !== "denied")) return null;
      if (typeof data.ts !== "number" || Date.now() - data.ts > MAX_AGE_MS) return null;
      return data.choice;
    } catch (error) {
      return null;
    }
  }

  function writeChoice(choice) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ choice: choice, ts: Date.now() }));
      return true;
    } catch (error) {
      return false;
    }
  }

  function deleteGaCookies() {
    var names = [];
    document.cookie.split(";").forEach(function (part) {
      var name = part.split("=")[0].trim();
      if (name === "_ga" || name === "_gid" || name.indexOf("_ga_") === 0) names.push(name);
    });
    var host = location.hostname;
    var domains = ["", host, "." + host];
    var labels = host.split(".");
    if (labels.length > 2) domains.push("." + labels.slice(-2).join("."));
    names.forEach(function (name) {
      domains.forEach(function (domain) {
        var cookie = name + "=; Max-Age=0; path=/";
        if (domain) cookie += "; domain=" + domain;
        document.cookie = cookie;
      });
    });
  }

  function loadGa() {
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    if (gaLoaded) {
      window.gtag("consent", "update", {
        analytics_storage: "granted",
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied"
      });
      return;
    }
    gaLoaded = true;
    window.gtag("consent", "default", {
      analytics_storage: "granted",
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied"
    });
    window.gtag("js", new Date());
    window.gtag("config", GA_ID);
    var script = document.createElement("script");
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA_ID);
    document.head.appendChild(script);
  }

  function denyGa() {
    deleteGaCookies();
    if (window.gtag) {
      window.gtag("consent", "update", {
        analytics_storage: "denied",
        ad_storage: "denied",
        ad_user_data: "denied",
        ad_personalization: "denied"
      });
    }
  }

  function applyCopy() {
    var text = COPY[lang()];
    var node = document.getElementById("wtho-consent-text");
    var privacy = document.getElementById("wtho-consent-privacy");
    var accept = document.getElementById("wtho-consent-accept");
    var decline = document.getElementById("wtho-consent-decline");
    var settings = document.getElementById("wtho-consent-settings");
    if (node) node.textContent = text.text;
    if (privacy) privacy.textContent = text.privacy;
    if (accept) accept.textContent = text.accept;
    if (decline) decline.textContent = text.decline;
    if (settings) settings.textContent = text.settings;
    if (bar) bar.lang = lang();
  }

  function syncPad() {
    if (!bar || bar.hidden) {
      document.body.style.paddingBottom = "";
      return;
    }
    document.body.style.paddingBottom = bar.offsetHeight + "px";
  }

  function setOpen(open, focusAccept) {
    if (!bar) return;
    bar.hidden = !open;
    var settings = document.getElementById("wtho-consent-settings");
    if (settings) settings.hidden = open;
    syncPad();
    if (open && focusAccept && acceptBtn) acceptBtn.focus();
  }

  function ensureSettingsLink() {
    var existing = document.getElementById("wtho-consent-settings");
    if (existing) {
      existing.textContent = COPY[lang()].settings;
      existing.hidden = bar && !bar.hidden;
      return;
    }
    var link = document.createElement("a");
    link.id = "wtho-consent-settings";
    link.href = "#cookies";
    link.textContent = COPY[lang()].settings;
    link.addEventListener("click", function (event) {
      event.preventDefault();
      setOpen(true, true);
    });
    var privacy = document.querySelector('footer a[href="/datenschutz/"], footer a[href$="/datenschutz/"]');
    if (privacy && privacy.parentElement) {
      var display = window.getComputedStyle(privacy.parentElement).display;
      if (display !== "flex" && display !== "inline-flex") link.style.marginInlineStart = "1.5rem";
      privacy.parentElement.insertBefore(link, privacy.nextSibling);
      return;
    }
    var foot = document.querySelector("footer .foot") || document.querySelector("footer");
    if (!foot) {
      foot = document.createElement("footer");
      foot.className = "wtho-consent-footer";
      document.body.appendChild(foot);
    }
    if (!foot.classList.contains("wtho-consent-footer") && window.getComputedStyle(foot).display !== "flex") {
      link.style.marginInlineStart = "1.5rem";
    }
    foot.appendChild(link);
  }

  function choose(choice) {
    if (!writeChoice(choice)) return;
    if (choice === "granted") loadGa();
    else denyGa();
    ensureSettingsLink();
    setOpen(false);
  }

  function inject() {
    var style = document.createElement("style");
    style.id = "wtho-consent-style";
    style.textContent = [
      "#wtho-consent { position: fixed; left: 0; right: 0; bottom: 0; z-index: 50;",
      "  background: #fff; color: #161412; border-top: 1px solid #e4dfd6;",
      "  font-family: Outfit, ui-sans-serif, system-ui, sans-serif; font-size: .875rem; line-height: 1.5; }",
      "#wtho-consent[hidden] { display: none; }",
      "#wtho-consent .wtho-consent-inner { max-width: 80rem; margin: 0 auto; padding: 1rem 1.25rem;",
      "  display: flex; flex-wrap: wrap; align-items: center; gap: .75rem 1.25rem; }",
      "#wtho-consent-text { margin: 0; flex: 1 1 18rem; color: #5c574f; }",
      "#wtho-consent-privacy { color: #161412; text-decoration: underline; text-underline-offset: .22em; }",
      "#wtho-consent .wtho-consent-actions { display: flex; flex-wrap: wrap; gap: .5rem; }",
      "#wtho-consent .wtho-consent-actions button { height: 2.75rem; min-width: 8.5rem; padding: 0 1.25rem;",
      "  flex: 1 1 8.5rem; font: inherit; font-size: .875rem; letter-spacing: .04em; cursor: pointer;",
      "  border: 1px solid #161412; background: #fff; color: #161412; }",
      "#wtho-consent #wtho-consent-accept { background: #161412; color: #fff; }",
      "#wtho-consent-settings { letter-spacing: normal; text-transform: none; white-space: nowrap; }",
      "#wtho-consent-settings[hidden] { display: none; }",
      "footer.wtho-consent-footer { position: fixed; z-index: 45; left: 0; right: 0; bottom: 0;",
      "  padding: 1rem 1.25rem; text-align: center; font-family: Outfit, ui-sans-serif, system-ui, sans-serif;",
      "  font-size: .875rem; }",
      "@media (max-width: 640px) { #wtho-consent .wtho-consent-actions { width: 100%; } }"
    ].join("\n");
    document.head.appendChild(style);

    bar = document.createElement("div");
    bar.id = "wtho-consent";
    bar.hidden = true;
    bar.setAttribute("role", "dialog");
    bar.setAttribute("aria-labelledby", "wtho-consent-text");
    bar.innerHTML = [
      '<div class="wtho-consent-inner">',
      '<p id="wtho-consent-text"></p>',
      '<a id="wtho-consent-privacy" href="/datenschutz/"></a>',
      '<div class="wtho-consent-actions">',
      '<button type="button" id="wtho-consent-accept"></button>',
      '<button type="button" id="wtho-consent-decline"></button>',
      "</div></div>"
    ].join("");
    document.body.appendChild(bar);
    acceptBtn = document.getElementById("wtho-consent-accept");
    acceptBtn.addEventListener("click", function () { choose("granted"); });
    document.getElementById("wtho-consent-decline").addEventListener("click", function () { choose("denied"); });
    applyCopy();
  }

  inject();
  var choice = readChoice();
  if (choice === "granted") {
    loadGa();
    ensureSettingsLink();
  } else if (choice === "denied") {
    ensureSettingsLink();
  } else {
    setOpen(true, false);
  }

  document.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || !target.closest || !target.closest("[data-lang]")) return;
    applyCopy();
  });
  window.addEventListener("resize", syncPad);
})();
