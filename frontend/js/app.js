const CATEGORY_LABELS = {
  restaurant: "Restaurant",
  hotel: "Hôtel",
  hospital: "Santé",
  school: "École",
  supermarket: "Supermarché",
  market: "Marché",
  station: "Station-service",
};
const CATEGORY_ORDER = ["restaurant", "hotel", "hospital", "school", "supermarket", "market", "station"];

/* ============================================================
   AUTH PAGE (index.html)
   ============================================================ */
function initAuthPage() {
  const params = new URLSearchParams(window.location.search);
  const banner = document.getElementById("authBanner");
  if (banner) {
    if (params.get("locked")) {
      banner.textContent = "Connectez-vous pour explorer les lieux de Bastos.";
      banner.classList.add("show");
    } else if (params.get("expired")) {
      banner.textContent = "Votre session a expiré. Reconnectez-vous.";
      banner.classList.add("show");
    }
  }

  if (getToken()) {
    // already logged in — send straight to Explore
    window.location.href = "explore.html";
    return;
  }

  const tabLogin = document.getElementById("tabLogin");
  const tabRegister = document.getElementById("tabRegister");
  const formLogin = document.getElementById("formLogin");
  const formRegister = document.getElementById("formRegister");

  function showTab(which) {
    const isLogin = which === "login";
    tabLogin.classList.toggle("active", isLogin);
    tabRegister.classList.toggle("active", !isLogin);
    formLogin.style.display = isLogin ? "block" : "none";
    formRegister.style.display = isLogin ? "none" : "block";
  }
  tabLogin.addEventListener("click", () => showTab("login"));
  tabRegister.addEventListener("click", () => showTab("register"));

  formLogin.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("loginError");
    errEl.classList.remove("show");
    try {
      const data = await apiFetch("/api/login", {
        method: "POST",
        body: JSON.stringify({
          email: document.getElementById("loginEmail").value,
          password: document.getElementById("loginPassword").value,
        }),
      });
      setSession(data.token, data.user);
      fireStamp("stampLogin");
      setTimeout(() => (window.location.href = "explore.html"), 500);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.add("show");
    }
  });

  formRegister.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.getElementById("registerError");
    errEl.classList.remove("show");
    try {
      const data = await apiFetch("/api/register", {
        method: "POST",
        body: JSON.stringify({
          username: document.getElementById("regUsername").value,
          email: document.getElementById("regEmail").value,
          password: document.getElementById("regPassword").value,
        }),
      });
      setSession(data.token, data.user);
      fireStamp("stampRegister");
      setTimeout(() => (window.location.href = "explore.html"), 500);
    } catch (err) {
      errEl.textContent = err.message;
      errEl.classList.add("show");
    }
  });
}

function fireStamp(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("show");
  void el.offsetWidth;
  el.classList.add("show");
}

/* ============================================================
   EXPLORE PAGE
   ============================================================ */
let exploreState = { category: "", q: "", sort: "name", userLoc: null, favoritesOnly: false };
let lastLoadedPlaces = [];

async function initExplorePage() {
  if (!requireLogin()) return;
  renderCategoryChips();
  document.getElementById("searchInput").addEventListener("input", debounce(() => {
    exploreState.q = document.getElementById("searchInput").value;
    loadPlaces();
  }, 300));
  document.getElementById("sortSelect").addEventListener("change", (e) => {
    exploreState.sort = e.target.value;
    loadPlaces();
  });
  document.getElementById("favoritesToggle").addEventListener("click", (e) => {
    exploreState.favoritesOnly = !exploreState.favoritesOnly;
    e.target.classList.toggle("active", exploreState.favoritesOnly);
    loadPlaces();
  });
  document.getElementById("surpriseBtn").addEventListener("click", surpriseMe);
  loadWeatherWidget("weatherWidget");
  loadPlaces();
}

function onLanguageChanged() {
  renderCategoryChips();
  if (document.getElementById("placeGrid")) renderPlaceGrid(lastLoadedPlaces);
  if (typeof placeDetailData !== "undefined" && placeDetailData) renderPlaceDetail(placeDetailData);
}

/* ---------- FAVORITES (creative feature: localStorage wishlist) ---------- */
function getFavorites() {
  try { return JSON.parse(localStorage.getItem("bastos_favorites") || "[]"); }
  catch (e) { return []; }
}
function isFavorite(id) { return getFavorites().includes(id); }
function toggleFavorite(id, btnEl) {
  let favs = getFavorites();
  if (favs.includes(id)) favs = favs.filter((x) => x !== id);
  else favs.push(id);
  localStorage.setItem("bastos_favorites", JSON.stringify(favs));
  if (btnEl) btnEl.classList.toggle("active", favs.includes(id));
  if (exploreState.favoritesOnly) loadPlaces();
}

/* ---------- SURPRISE ME (creative feature: random place) ---------- */
async function surpriseMe() {
  try {
    const places = await apiFetch("/api/places");
    if (!places.length) return;
    const pick = places[Math.floor(Math.random() * places.length)];
    window.location.href = "place.html?id=" + pick.id;
  } catch (e) { /* ignore */ }
}

/* ---------- WEATHER WIDGET (creative feature: live Bastos weather via Open-Meteo) ---------- */
async function loadWeatherWidget(containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `<div class="hint">…</div>`;
  try {
    const res = await fetch(
      "https://api.open-meteo.com/v1/forecast?latitude=3.888&longitude=11.518&current=temperature_2m,relative_humidity_2m,weather_code&timezone=Africa%2FDouala"
    );
    const data = await res.json();
    const cur = data.current;
    const icon = weatherIcon(cur.weather_code);
    el.innerHTML = `
      <div class="weather-box">
        <div class="weather-now">
          <span class="weather-icon">${icon}</span>
          <span class="weather-temp">${Math.round(cur.temperature_2m)}°C</span>
          <span class="hint">${cur.relative_humidity_2m}% hum.</span>
        </div>
        <p class="hint" data-i18n="weatherClimate">${t("weatherClimate")}</p>
      </div>`;
  } catch (err) {
    el.innerHTML = `<p class="hint" data-i18n="weatherClimate">${t("weatherClimate")}</p>`;
  }
}

function weatherIcon(code) {
  if (code === 0) return "☀️";
  if ([1, 2, 3].includes(code)) return "⛅";
  if ([45, 48].includes(code)) return "🌫️";
  if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return "🌧️";
  if ([95, 96, 99].includes(code)) return "⛈️";
  return "🌤️";
}

function renderCategoryChips() {
  const bar = document.getElementById("categoryChips");
  const chips = [{ key: "", label: getLang() === "en" ? "All" : "Tout" }].concat(
    CATEGORY_ORDER.map((c) => ({ key: c, label: categoryLabel(c) }))
  );
  bar.innerHTML = chips
    .map((c) => `<button class="chip ${c.key === exploreState.category ? "active" : ""}" data-cat="${c.key}">${c.label}</button>`)
    .join("");
  bar.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      exploreState.category = btn.dataset.cat;
      renderCategoryChips();
      loadPlaces();
    });
  });
}

async function loadPlaces() {
  const grid = document.getElementById("placeGrid");
  grid.innerHTML = `<div class="hint">Chargement…</div>`;
  try {
    const qs = new URLSearchParams();
    if (exploreState.category) qs.set("category", exploreState.category);
    if (exploreState.q) qs.set("q", exploreState.q);
    qs.set("sort", exploreState.sort);
    if (exploreState.sort === "distance" && exploreState.userLoc) {
      qs.set("lat", exploreState.userLoc.lat);
      qs.set("lon", exploreState.userLoc.lon);
    }
    let places = await apiFetch("/api/places?" + qs.toString());
    if (exploreState.favoritesOnly) {
      const favs = getFavorites();
      places = places.filter((p) => favs.includes(p.id));
    }
    lastLoadedPlaces = places;
    renderPlaceGrid(places);
  } catch (err) {
    grid.innerHTML = `<div class="error-msg show">${err.message}</div>`;
  }
}

function renderPlaceGrid(places) {
  const grid = document.getElementById("placeGrid");
  if (!places.length) {
    grid.innerHTML = `<div class="hint">${t("noResults")}</div>`;
    return;
  }
  grid.innerHTML = places
    .map(
      (p) => `
    <div class="card place-card">
      <button class="fav-btn ${isFavorite(p.id) ? "active" : ""}" onclick="event.preventDefault(); toggleFavorite(${p.id}, this)" aria-label="Favori">♥</button>
      <a href="place.html?id=${p.id}">
        <img src="${p.image}" alt="${p.name}" loading="lazy">
        <div class="body">
          <span class="cat">${categoryLabel(p.category)}</span>
          <h3>${p.name}</h3>
          <p class="addr">${p.address || ""}</p>
          ${p.rating ? `<div class="rating">★ ${p.rating} <span class="hint">(${p.review_count})</span></div>` : `<div class="hint">${t("noAvis")}</div>`}
        </div>
      </a>
    </div>`
    )
    .join("");
}

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function useMyLocationForSort() {
  if (!navigator.geolocation) {
    alert("La géolocalisation n'est pas disponible sur ce navigateur.");
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      exploreState.userLoc = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      exploreState.sort = "distance";
      document.getElementById("sortSelect").value = "distance";
      loadPlaces();
    },
    () => alert("Impossible d'obtenir votre position. Vérifiez les autorisations de localisation.")
  );
}

/* ============================================================
   PLACE DETAIL PAGE
   ============================================================ */
let placeMap, placeDetailData;

async function initPlacePage() {
  if (!requireLogin()) return;
  const id = new URLSearchParams(window.location.search).get("id");
  if (!id) {
    window.location.href = "explore.html";
    return;
  }
  try {
    const place = await apiFetch("/api/places/" + id);
    placeDetailData = place;
    renderPlaceDetail(place);
    renderReviews(place.reviews || []);
    loadWeatherWidget("weatherWidget");
    document.getElementById("reviewForm").addEventListener("submit", (e) => submitReview(e, id));
    document.getElementById("directionsBtn").addEventListener("click", () => showRoute(place));
  } catch (err) {
    document.getElementById("placeDetail").innerHTML = `<div class="error-msg show">${err.message}</div>`;
  }
}

function renderPlaceDetail(p) {
  document.title = p.name + " — Bastos Explorer";
  const isEn = getLang() === "en";
  const description = isEn && p.description_en ? p.description_en : p.description;
  document.getElementById("placeDetail").innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">
      <div>
        <span class="cat">${categoryLabel(p.category)}</span>
        <h1 style="font-family:'Fraunces',serif;font-size:34px;margin:6px 0 4px;">${p.name}</h1>
        <p class="hint" style="font-size:14px;margin-bottom:14px;">${p.address || ""}</p>
      </div>
      <button class="fav-btn ${isFavorite(p.id) ? "active" : ""}" style="position:static;" onclick="toggleFavorite(${p.id}, this)" aria-label="Favori">♥</button>
    </div>
    <img src="${p.image}" alt="${p.name}" style="width:100%;max-height:320px;object-fit:cover;border-radius:12px;border:1px solid var(--line);margin-bottom:18px;">
    <p>${description || ""}</p>
    <div style="margin:14px 0;">
      ${p.cuisine ? `<span class="badge">${isEn ? "Cuisine" : "Cuisine"} : ${p.cuisine}</span>` : ""}
      ${p.hours ? `<span class="badge">${isEn ? "Hours" : "Horaires"} : ${p.hours}</span>` : ""}
      ${p.phone ? `<span class="badge">${isEn ? "Phone" : "Tél"} : ${p.phone}</span>` : ""}
      ${p.rating ? `<span class="badge">★ ${p.rating} · ${p.review_count} ${isEn ? "reviews" : "avis"}</span>` : `<span class="badge">${isEn ? "Not yet rated" : "Pas encore noté"}</span>`}
    </div>
  `;
  initPlaceMap(p);
}

function initPlaceMap(p) {
  const el = document.getElementById("placeMap");
  placeMap = L.map(el).setView([p.lat, p.lon], 15);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(placeMap);
  L.marker([p.lat, p.lon]).addTo(placeMap).bindPopup(`<b>${p.name}</b>`).openPopup();
}

function showRoute(p) {
  if (!navigator.geolocation) {
    alert("La géolocalisation n'est pas disponible sur ce navigateur.");
    return;
  }
  const routeInfo = document.getElementById("routeInfo");
  routeInfo.innerHTML = `<div class="hint">Localisation en cours…</div>`;
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const userLat = pos.coords.latitude;
      const userLon = pos.coords.longitude;
      L.marker([userLat, userLon], { title: "Vous êtes ici" })
        .addTo(placeMap)
        .bindPopup("Vous êtes ici");
      routeInfo.innerHTML = `<div class="hint">Calcul de l'itinéraire…</div>`;
      try {
        const url = `https://router.project-osrm.org/route/v1/driving/${userLon},${userLat};${p.lon},${p.lat}?overview=full&geometries=geojson`;
        const res = await fetch(url);
        const data = await res.json();
        if (!data.routes || !data.routes.length) throw new Error("Itinéraire introuvable.");
        const route = data.routes[0];
        const coords = route.geometry.coordinates.map((c) => [c[1], c[0]]);
        L.polyline(coords, { color: "#E2703A", weight: 5, opacity: 0.85 }).addTo(placeMap);
        placeMap.fitBounds(L.latLngBounds(coords), { padding: [30, 30] });
        const km = (route.distance / 1000).toFixed(1);
        const mins = Math.round(route.duration / 60);
        routeInfo.innerHTML = `
          <div class="route-info">
            <div class="stat">Distance : <b>${km} km</b></div>
            <div class="stat">Durée estimée : <b>${mins} min</b></div>
          </div>`;
      } catch (err) {
        routeInfo.innerHTML = `<div class="error-msg show">Impossible de calculer l'itinéraire (${err.message}). Le service de routage est peut-être indisponible.</div>`;
      }
    },
    () => {
      routeInfo.innerHTML = `<div class="error-msg show">Impossible d'obtenir votre position. Vérifiez les autorisations de localisation de votre navigateur.</div>`;
    }
  );
}

function renderReviews(reviews) {
  const el = document.getElementById("reviewsList");
  if (!reviews.length) {
    el.innerHTML = `<div class="hint">Aucun avis pour l'instant — soyez la première personne à en laisser un.</div>`;
    return;
  }
  el.innerHTML = reviews
    .slice()
    .reverse()
    .map(
      (r) => `
    <div class="review">
      <div class="top">
        <span class="who">${r.username}</span>
        <span class="stars">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</span>
      </div>
      <div class="comment">${r.comment}</div>
    </div>`
    )
    .join("");
}

async function submitReview(e, placeId) {
  e.preventDefault();
  const errEl = document.getElementById("reviewError");
  errEl.classList.remove("show");
  const rating = Number(document.getElementById("reviewRating").value);
  const comment = document.getElementById("reviewComment").value.trim();
  try {
    await apiFetch(`/api/places/${placeId}/reviews`, {
      method: "POST",
      body: JSON.stringify({ rating, comment }),
    });
    document.getElementById("reviewComment").value = "";
    const updated = await apiFetch("/api/places/" + placeId);
    placeDetailData = updated;
    renderReviews(updated.reviews || []);
    document.querySelector('#placeDetail .badge:last-child')?.remove();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.add("show");
  }
}
