(function () {
  const id = location.pathname.replace(/\/+$/, "").split("/").pop();

  let site = null;
  let work = null;
  let lang = "de";
  try { lang = localStorage.getItem("wtho-lang") === "en" ? "en" : "de"; } catch (e) {}

  function apply() {
    if (!work || !site) return;
    const ui = site.copy[lang];
    document.documentElement.lang = lang;
    document.querySelector('[data-i="back"]').textContent = ui.worksBack || "← " + (lang === "en" ? "Back to all works" : "Zurück zu allen Werken");
    document.querySelector('[data-i="inquire"]').textContent = ui.inquire;
    document.getElementById("title").textContent = work.title[lang];
    document.getElementById("metaYear").textContent = work.year;
    document.getElementById("metaMedium").textContent =
      work.medium[lang] + (work.size && work.size !== "—" ? " · " + work.size : "");
    document.getElementById("statement").textContent = work.statement[lang];
    document.getElementById("mainImg").alt = work.title[lang];
    document.title = work.title[lang] + " — wtho.art";
    document.getElementById("inquire").href = "/?work=" + work.id + "#kontakt";
    document.querySelectorAll("[data-lang]").forEach((b) => {
      b.classList.toggle("on", b.getAttribute("data-lang") === lang);
    });
  }

  function renderGallery() {
    const images = work.images && work.images.length ? work.images : [work.id + ".jpg"];
    document.getElementById("mainImg").src = images[0];
    const thumbs = document.getElementById("thumbs");
    if (images.length > 1) {
      thumbs.classList.add("show");
      thumbs.innerHTML = images.map((src, i) =>
        `<button type="button" data-src="${src}" class="${i === 0 ? "on" : ""}"><img src="${src}" alt="" loading="lazy" /></button>`
      ).join("");
      thumbs.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          document.getElementById("mainImg").src = btn.dataset.src;
          thumbs.querySelectorAll("button").forEach((b) => b.classList.remove("on"));
          btn.classList.add("on");
        });
      });
    }
  }

  document.querySelectorAll("[data-lang]").forEach((b) => {
    b.addEventListener("click", () => {
      lang = b.getAttribute("data-lang");
      try { localStorage.setItem("wtho-lang", lang); } catch (e) {}
      apply();
    });
  });

  WthoContent.load("../../data/").then((data) => {
    site = data.site;
    work = data.works.find((w) => w.id === id);
    if (!work) {
      document.getElementById("title").textContent = "Not found";
      return;
    }
    renderGallery();
    apply();
  }).catch((err) => {
    console.error(err);
    document.getElementById("title").textContent = "Could not load work";
  });
})();
