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

  function workCover(work) {
    const file = (work.images && work.images[0]) || work.id + ".jpg";
    return "works/" + work.id + "/" + file;
  }

  function heroWork(site, works) {
    return works.find((w) => w.id === site.heroWorkId)
      || works.find((w) => w.hero)
      || works[0];
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
    workCover: workCover,
    heroWork: heroWork
  };
})(window);
