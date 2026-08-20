const I18N = {
  fr: {
    navExplore: "Explorer",
    navAbout: "À propos",
    login: "Se connecter",
    logout: "Déconnexion",
    heroTitleExplore: "Explorer Bastos",
    heroSubExplore: "Filtrez par catégorie, cherchez par nom, ou triez par distance depuis votre position.",
    searchPlaceholder: "Chercher un lieu (nom, description)…",
    sortName: "Trier : Nom",
    sortRating: "Trier : Mieux notés",
    sortDistance: "Trier : Distance (ma position)",
    myLocation: "📍 Ma position",
    surpriseMe: "🎲 Surprends-moi",
    favoritesOnly: "♥ Mes favoris",
    noAvis: "Pas encore d'avis",
    noResults: "Aucun lieu ne correspond à ces filtres.",
    back: "← Retour au carnet",
    mapTitle: "Carte & itinéraire",
    directionsBtn: "📍 Itinéraire depuis ma position",
    reviewsTitle: "Avis",
    reviewLabel: "Votre avis",
    reviewPlaceholder: "Partagez votre expérience…",
    publish: "Publier l'avis",
    weatherTitle: "Météo à Bastos",
    weatherClimate: "Climat équatorial : chaud toute l'année (19–28 °C), deux saisons des pluies (mars–juin et sept–nov) et deux saisons sèches.",
  },
  en: {
    navExplore: "Explore",
    navAbout: "About",
    login: "Log in",
    logout: "Log out",
    heroTitleExplore: "Explore Bastos",
    heroSubExplore: "Filter by category, search by name, or sort by distance from your location.",
    searchPlaceholder: "Search a place (name, description)…",
    sortName: "Sort: Name",
    sortRating: "Sort: Top rated",
    sortDistance: "Sort: Distance (my location)",
    myLocation: "📍 My location",
    surpriseMe: "🎲 Surprise me",
    favoritesOnly: "♥ My favourites",
    noAvis: "No reviews yet",
    noResults: "No place matches these filters.",
    back: "← Back to the directory",
    mapTitle: "Map & directions",
    directionsBtn: "📍 Directions from my location",
    reviewsTitle: "Reviews",
    reviewLabel: "Your review",
    reviewPlaceholder: "Share your experience…",
    publish: "Publish review",
    weatherTitle: "Weather in Bastos",
    weatherClimate: "Equatorial climate: warm year-round (19–28°C), two rainy seasons (Mar–Jun and Sep–Nov) and two dry seasons.",
  },
};

const CATEGORY_LABELS_EN = {
  restaurant: "Restaurant",
  hotel: "Hotel",
  hospital: "Health",
  school: "School",
  supermarket: "Supermarket",
  market: "Market",
  station: "Filling station",
};

function getLang() {
  return localStorage.getItem("bastos_lang") || "fr";
}

function t(key) {
  const lang = getLang();
  return (I18N[lang] && I18N[lang][key]) || I18N.fr[key] || key;
}

function categoryLabel(cat) {
  return getLang() === "en" ? (CATEGORY_LABELS_EN[cat] || cat) : (CATEGORY_LABELS[cat] || cat);
}

function toggleLanguage() {
  const next = getLang() === "fr" ? "en" : "fr";
  localStorage.setItem("bastos_lang", next);
  applyTranslations();
  if (typeof onLanguageChanged === "function") onLanguageChanged();
}

function applyTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.dataset.i18nPlaceholder));
  });
  const langBtn = document.getElementById("langToggle");
  if (langBtn) langBtn.textContent = getLang() === "fr" ? "FR" : "EN";
}

document.addEventListener("DOMContentLoaded", applyTranslations);
