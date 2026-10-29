/* Shared helpers. Content itself lives in /data/*.json */
(function (global) {
  const cache = {};

  async function loadJson(url) {
    if (cache[url]) return cache[url];
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error("Could not load " + url + " (" + res.status + ")");
    cache[url] = await res.json();
    return cache[url];
  }

  function formatInline(text) {
    const node = document.createElement("div");
    node.textContent = text || "";
    return node.innerHTML.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function workCover(work) {
    const file = (work.images && work.images[0]) || work.id + ".jpg";
    return "works/" + work.id + "/" + file;
  }

  function heroWork(site, works) {
    return works.find((w) => w.id === site.heroWorkId)
      || works.find((w) => w.hero)
      || works[0];
  }

  // Swipe left (negative dx) moves forward. A short flick counts; a small drift does not.
  function galleryCommit(index, count, dx, width, elapsedMs) {
    if (count < 2 || !(width > 0) || Math.abs(dx) < 24) return index;
    const direction = dx < 0 ? 1 : -1;
    const velocity = dx / Math.max(elapsedMs, 1);
    const passed = Math.abs(dx) > width * 0.18 || Math.abs(velocity) > 0.5;
    const next = index + direction;
    if (!passed || next < 0 || next >= count) return index;
    return next;
  }

  function ensureGalleryStyles() {
    if (document.getElementById("wtho-gallery-swipe")) return;
    const style = document.createElement("style");
    style.id = "wtho-gallery-swipe";
    style.textContent = [
      ".gallery-main.is-swipeable { position: relative; cursor: grab; touch-action: pan-y; user-select: none; }",
      ".gallery-main.is-dragging { cursor: grabbing; }",
      ".gallery-main > img.gallery-incoming {",
      "  position: absolute; top: 0; left: 0; width: 100%; height: 100%;",
      "  object-fit: contain; display: none; pointer-events: none; background: transparent;",
      "}"
    ].join("\n");
    document.head.appendChild(style);
  }

  function bindGallery(images, options) {
    const opts = options || {};
    const frame = opts.frame || document.querySelector(".gallery-main");
    const main = opts.main || document.getElementById("mainImg");
    const thumbs = opts.thumbs || document.getElementById("thumbs");
    const localKeys = opts.keys === "local";
    if (!frame || !main || !images || images.length < 2) return;
    if (frame.dataset.swipeBound) return;
    frame.dataset.swipeBound = "1";
    if (localKeys && frame.tabIndex < 0) frame.tabIndex = 0;
    ensureGalleryStyles();

    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const duration = reduce ? 0 : 320;
    let index = 0;
    let pointerId = null;
    let startX = 0;
    let startY = 0;
    let startT = 0;
    let axis = null;
    let dx = 0;
    let animating = false;
    let motionGen = 0;
    let incomingIndex = -1;

    const incoming = document.createElement("img");
    incoming.className = "gallery-incoming";
    incoming.alt = "";
    incoming.draggable = false;
    incoming.setAttribute("aria-hidden", "true");
    frame.appendChild(incoming);
    frame.classList.add("is-swipeable");
    main.draggable = false;
    main.addEventListener("dragstart", (event) => event.preventDefault());

    const preloaded = images.map((src) => {
      const img = new Image();
      img.src = src;
      return img;
    });

    function markThumbs() {
      if (!thumbs) return;
      thumbs.querySelectorAll("button").forEach((button, i) => {
        button.classList.toggle("on", i === index);
      });
    }

    function rubber(delta) {
      const limit = Math.max(frame.clientWidth, 1) * 0.35;
      const sign = delta < 0 ? -1 : 1;
      const distance = Math.abs(delta);
      return sign * (limit * distance) / (limit + distance);
    }

    function placeIncoming(next, delta) {
      if (next < 0) {
        incoming.style.display = "none";
        incomingIndex = -1;
        return;
      }
      if (incomingIndex !== next) {
        incoming.src = images[next];
        incomingIndex = next;
      }
      incoming.style.display = "block";
      const from = delta < 0 ? 100 : -100;
      incoming.style.transform = "translate3d(calc(" + from + "% + " + delta + "px),0,0)";
    }

    function clearMotion() {
      main.style.transition = "";
      incoming.style.transition = "";
      frame.style.transition = "";
      main.style.transform = "";
      incoming.style.transform = "";
      incoming.style.display = "none";
      incomingIndex = -1;
      frame.style.height = "";
      frame.classList.remove("is-dragging");
      animating = false;
    }

    function show(next) {
      index = next;
      main.src = images[index];
      markThumbs();
    }

    function frameHeightFor(imageIndex) {
      const img = preloaded[imageIndex];
      if (!img || !img.naturalWidth) return 0;
      return frame.clientWidth * (img.naturalHeight / img.naturalWidth);
    }

    function finish(targetIndex, delta) {
      const generation = ++motionGen;
      animating = true;
      const going = targetIndex !== index;
      main.style.transition = "transform " + duration + "ms ease";
      incoming.style.transition = "transform " + duration + "ms ease";
      if (going) {
        const dir = targetIndex > index ? -100 : 100;
        main.style.transform = "translate3d(" + dir + "%,0,0)";
        incoming.style.transform = "translate3d(0,0,0)";
        const nextHeight = frameHeightFor(targetIndex);
        if (nextHeight && !reduce) {
          frame.style.height = frame.getBoundingClientRect().height + "px";
          frame.style.transition = "height " + duration + "ms ease";
          window.requestAnimationFrame(() => {
            if (generation !== motionGen) return;
            frame.style.height = nextHeight + "px";
          });
        }
      } else {
        main.style.transform = "translate3d(0,0,0)";
        const peek = delta < 0 ? index + 1 : index - 1;
        if (peek >= 0 && peek < images.length) {
          incoming.style.transform = "translate3d(" + (delta < 0 ? 100 : -100) + "%,0,0)";
        }
      }

      function settle() {
        if (generation !== motionGen) return;
        motionGen += 1;
        if (going) show(targetIndex);
        clearMotion();
      }

      if (duration === 0) {
        settle();
        return;
      }
      main.addEventListener("transitionend", function onEnd(event) {
        if (event.propertyName !== "transform") return;
        main.removeEventListener("transitionend", onEnd);
        settle();
      });
      window.setTimeout(settle, duration + 80);
    }

    function slideTo(targetIndex) {
      if (targetIndex === index || targetIndex < 0 || targetIndex >= images.length || animating) return;
      if (reduce || Math.abs(targetIndex - index) !== 1) {
        clearMotion();
        show(targetIndex);
        return;
      }
      const delta = targetIndex > index ? -frame.clientWidth : frame.clientWidth;
      incoming.src = images[targetIndex];
      incomingIndex = targetIndex;
      incoming.style.display = "block";
      incoming.style.transition = "none";
      main.style.transition = "none";
      incoming.style.transform = "translate3d(" + (targetIndex > index ? 100 : -100) + "%,0,0)";
      incoming.offsetWidth;
      finish(targetIndex, delta);
    }

    frame.addEventListener("pointerdown", (event) => {
      if (animating) return;
      if (event.pointerType === "mouse" && event.button !== 0) return;
      pointerId = event.pointerId;
      startX = event.clientX;
      startY = event.clientY;
      startT = performance.now();
      axis = null;
      dx = 0;
    });

    frame.addEventListener("pointermove", (event) => {
      if (pointerId !== event.pointerId) return;
      dx = event.clientX - startX;
      const dy = event.clientY - startY;
      if (!axis) {
        if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
        axis = Math.abs(dx) > Math.abs(dy) ? "x" : "y";
        if (axis === "y") {
          pointerId = null;
          return;
        }
        frame.classList.add("is-dragging");
        try { frame.setPointerCapture(event.pointerId); } catch (err) {}
        main.style.transition = "none";
        incoming.style.transition = "none";
      }
      if (axis !== "x") return;
      event.preventDefault();
      const next = index + (dx < 0 ? 1 : -1);
      const shown = next < 0 || next >= images.length ? rubber(dx) : dx;
      main.style.transform = "translate3d(" + shown + "px,0,0)";
      placeIncoming(next >= 0 && next < images.length ? next : -1, shown);
    }, { passive: false });

    function endPointer(event) {
      if (pointerId !== event.pointerId) return;
      pointerId = null;
      if (axis !== "x") {
        axis = null;
        return;
      }
      axis = null;
      const elapsed = performance.now() - startT;
      finish(galleryCommit(index, images.length, dx, frame.clientWidth || 1, elapsed), dx);
    }

    frame.addEventListener("pointerup", endPointer);
    frame.addEventListener("pointercancel", endPointer);

    if (thumbs) {
      thumbs.querySelectorAll("button").forEach((button, i) => {
        button.addEventListener("click", () => slideTo(i));
      });
    }

    const keyTarget = localKeys ? frame : document;
    keyTarget.addEventListener("keydown", (event) => {
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const tag = event.target && event.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (event.target && event.target.isContentEditable)) return;
      if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
      const target = galleryCommit(index, images.length, event.key === "ArrowRight" ? -80 : 80, 100, 1000);
      if (target === index) return;
      event.preventDefault();
      slideTo(target);
    });

    markThumbs();
  }

  global.WthoContent = {
    load: function (dataDir) {
      const base = dataDir.endsWith("/") ? dataDir : dataDir + "/";
      return Promise.all([
        loadJson(base + "site.json"),
        loadJson(base + "works.json")
      ]).then(function (pair) {
        return { site: pair[0], works: pair[1] };
      });
    },
    formatInline: formatInline,
    workCover: workCover,
    heroWork: heroWork,
    galleryCommit: galleryCommit,
    bindGallery: bindGallery
  };
})(window);
