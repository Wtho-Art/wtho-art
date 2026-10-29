(function () {
  let site = null;
  let lang = "de";
  try { lang = localStorage.getItem("wtho-lang") === "en" ? "en" : "de"; } catch (e) {}

  function esc(value) {
    return String(value || "").replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function page() {
    const block = (site && site.commissions) || {};
    return {
      title: block.title || {},
      cities: Array.isArray(block.cities) ? block.cities : []
    };
  }

  function cityMarkup(city) {
    const title = (city.title && city.title[lang]) || city.id;
    const text = (city.text && city.text[lang]) || "";
    const images = (city.images || []).filter(Boolean);
    const heading = "<h2>" + esc(title) + "</h2>";
    const statement = '<p class="statement">' + WthoContent.formatInline(text) + "</p>";
    if (!images.length) {
      return '<section class="city city-text" id="' + esc(city.id) + '">' + heading + statement + "</section>";
    }
    let buttons = "";
    images.forEach(function (name, index) {
      const src = esc(city.id + "/" + name);
      buttons += '<button type="button"' + (index === 0 ? ' class="on"' : "") + '><img src="' + src + '" alt="" /></button>';
    });
    const thumbsClass = images.length > 1 ? "thumbs show" : "thumbs";
    return (
      '<section class="layout city" id="' + esc(city.id) + '">' +
        "<div>" +
          '<div class="gallery-main" tabindex="0"><img src="' + esc(city.id + "/" + images[0]) + '" alt="' + esc(title) + '" /></div>' +
          '<div class="' + thumbsClass + '">' + (images.length > 1 ? buttons : "") + "</div>" +
        "</div>" +
        "<div>" + heading + statement + "</div>" +
      "</section>"
    );
  }

  function bindCity(section, city) {
    const images = (city.images || []).filter(Boolean).map(function (name) {
      return city.id + "/" + name;
    });
    if (images.length < 2) return;
    WthoContent.bindGallery(images, {
      frame: section.querySelector(".gallery-main"),
      main: section.querySelector(".gallery-main img"),
      thumbs: section.querySelector(".thumbs"),
      keys: "local"
    });
  }

  function apply() {
    if (!site) return;
    const view = page();
    document.documentElement.lang = lang;
    const title = view.title[lang] || view.title.de || "";
    document.getElementById("kicker").textContent = lang === "en" ? "Commissions" : "Aufträge";
    document.querySelector('[data-i="back"]').textContent = lang === "en" ? "← Artist / studio" : "← Künstler/Atelier";
    document.getElementById("title").textContent = title;
    document.title = title + " — wtho.art";
    const root = document.getElementById("cities");
    if (!view.cities.length) {
      root.innerHTML = '<p class="statement" id="empty">' + (lang === "en" ? "No city yet." : "Noch keine Stadt.") + "</p>";
    } else {
      root.innerHTML = view.cities.map(cityMarkup).join("");
      root.querySelectorAll(".city").forEach(function (section) {
        const city = view.cities.find(function (item) { return item.id === section.id; });
        if (city) bindCity(section, city);
      });
    }
    document.querySelectorAll("[data-lang]").forEach(function (button) {
      button.classList.toggle("on", button.getAttribute("data-lang") === lang);
    });
  }

  document.querySelectorAll("[data-lang]").forEach(function (button) {
    button.addEventListener("click", function () {
      lang = button.getAttribute("data-lang");
      try { localStorage.setItem("wtho-lang", lang); } catch (e) {}
      apply();
    });
  });

  WthoContent.load("../../data/").then(function (data) {
    site = data.site;
    apply();
  }).catch(function (err) {
    console.error(err);
    document.getElementById("title").textContent = "Could not load page";
  });
})();
