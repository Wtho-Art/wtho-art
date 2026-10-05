(function () {
  const id = location.pathname.replace(/\/+$/, "").split("/").pop();

  let place = null;
  let lang = "de";
  try { lang = localStorage.getItem("wtho-lang") === "en" ? "en" : "de"; } catch (e) {}

  function apply() {
    if (!place) return;
    document.documentElement.lang = lang;
    document.getElementById("kicker").textContent = lang === "en" ? "Studio" : "Atelier";
    document.querySelector('[data-i="back"]').textContent = lang === "en" ? "← Artist / studio" : "← Künstler/Atelier";
    document.getElementById("title").textContent = place.title[lang];
    document.getElementById("statement").textContent = place.text[lang] || "";
    document.getElementById("mainImg").alt = place.title[lang];
    document.title = place.title[lang] + " — wtho.art";
    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.classList.toggle("on", button.getAttribute("data-lang") === lang);
    });
  }

  function renderGallery() {
    const images = place.images && place.images.length ? place.images : [place.id + ".jpg"];
    document.getElementById("mainImg").src = images[0];
    const thumbs = document.getElementById("thumbs");
    if (images.length < 2) return;
    thumbs.classList.add("show");
    thumbs.innerHTML = images.map((src, index) =>
      `<button type="button" data-src="${src}" class="${index === 0 ? "on" : ""}"><img src="${src}" alt="" loading="lazy" /></button>`
    ).join("");
    thumbs.querySelectorAll("button").forEach((button) => {
      button.addEventListener("click", () => {
        document.getElementById("mainImg").src = button.dataset.src;
        thumbs.querySelectorAll("button").forEach((item) => item.classList.remove("on"));
        button.classList.add("on");
      });
    });
  }

  document.querySelectorAll("[data-lang]").forEach((button) => {
    button.addEventListener("click", () => {
      lang = button.getAttribute("data-lang");
      try { localStorage.setItem("wtho-lang", lang); } catch (e) {}
      apply();
    });
  });

  WthoContent.load("../../data/").then((data) => {
    place = (data.site.places || []).find((item) => item.id === id);
    if (!place) {
      document.getElementById("title").textContent = "Not found";
      return;
    }
    renderGallery();
    apply();
  }).catch((err) => {
    console.error(err);
    document.getElementById("title").textContent = "Could not load page";
  });
})();
