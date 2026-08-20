function getToken() { return localStorage.getItem("bastos_token"); }
function getUser() {
  const raw = localStorage.getItem("bastos_user");
  return raw ? JSON.parse(raw) : null;
}
function setSession(token, user) {
  localStorage.setItem("bastos_token", token);
  localStorage.setItem("bastos_user", JSON.stringify(user));
}
function clearSession() {
  localStorage.removeItem("bastos_token");
  localStorage.removeItem("bastos_user");
}
function logout() {
  clearSession();
  window.location.href = "index.html";
}

// Redirects to the login screen if there's no session. Call at the top of
// any page that requires being logged in (Explore, place detail).
function requireLogin() {
  if (!getToken()) {
    window.location.href = "index.html?locked=1";
    return false;
  }
  return true;
}

async function apiFetch(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  const token = getToken();
  if (token) headers["Authorization"] = "Bearer " + token;
  const res = await fetch(API_BASE + path, Object.assign({}, options, { headers }));
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    clearSession();
    window.location.href = "index.html?expired=1";
    throw new Error("Session expirée");
  }
  if (!res.ok) throw new Error(data.error || "Une erreur est survenue.");
  return data;
}

// Renders the nav's login state (username chip + logout, vs "Se connecter").
function renderNavAuth() {
  const slot = document.getElementById("navAuthSlot");
  if (!slot) return;
  const user = getUser();
  const logoutLabel = typeof t === "function" ? t("logout") : "Déconnexion";
  const loginLabel = typeof t === "function" ? t("login") : "Se connecter";
  if (user) {
    slot.innerHTML = `<span class="user-chip">👤 ${user.username} <button onclick="logout()">${logoutLabel}</button></span>`;
  } else {
    slot.innerHTML = `<a class="btn secondary" href="index.html">${loginLabel}</a>`;
  }
}
document.addEventListener("DOMContentLoaded", renderNavAuth);
document.addEventListener("DOMContentLoaded", () => {
  // Re-render after i18n applies in case language differs from default
  setTimeout(renderNavAuth, 0);
});
