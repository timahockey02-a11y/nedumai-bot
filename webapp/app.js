const tg = window.Telegram?.WebApp;
const API_BASE = document.querySelector('meta[name="api-base"]')?.content?.replace(/\/+$/, "") || "";

const CATEGORIES = [
  { id: "cat_theatre",     emoji: "🎭", title: "Театр",     subtitle: "Спектакли, мюзиклы" },
  { id: "cat_cinema",      emoji: "🎬", title: "Кино",      subtitle: "Фестивали, авторское" },
  { id: "cat_restaurants", emoji: "🍽", title: "Рестораны", subtitle: "Поесть и посидеть" },
  { id: "cat_nature",      emoji: "🌿", title: "Природа",   subtitle: "Парки, набережные" },
  { id: "cat_sport",       emoji: "🏃", title: "Спорт",     subtitle: "Падел, теннис, бег" },
  { id: "cat_exhibitions", emoji: "🖼", title: "Выставки",  subtitle: "Современное и не очень" },
];

const EMOTIONS = [
  { id: "em_exhale", emoji: "🫁", title: "Расслабиться" },
  { id: "em_lol",    emoji: "😈", title: "Поугарать" },
  { id: "em_new",    emoji: "🔮", title: "Открыть новое" },
  { id: "em_feel",   emoji: "🫀", title: "Прочувствовать" },
  { id: "em_charge", emoji: "⚡", title: "Зарядиться" },
  { id: "em_wow",    emoji: "🤯", title: "Удивиться" },
];

const CATEGORY_QUESTIONS = {
  cat_theatre:     "Театр сегодня — какого вечера хочешь?",
  cat_cinema:      "Кино — что должно произойти?",
  cat_restaurants: "А какого вкуса не хватает?",
  cat_nature:      "На воздух — зачем именно сегодня?",
  cat_sport:       "Двигаться — что внутри сейчас?",
  cat_exhibitions: "Выставка — что хочешь поймать?",
};

const CATEGORY_BY_ID = Object.fromEntries(CATEGORIES.map(c => [c.id, c]));

let selectedCategory = null;
let selectedEmotion = null;
let currentRec = null;
let isLoading = false;

function init() {
  if (tg) {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#0f0f12");
    tg.setBackgroundColor("#0f0f12");
    tg.disableVerticalSwipes?.();
  }
  renderCategories();
  renderEmotions();
  bindResultButtons();
  bindHomeButtons();
}

function haptic(style = "medium") {
  try { tg?.HapticFeedback?.impactOccurred(style); } catch {}
}
function hapticNotify(type = "success") {
  try { tg?.HapticFeedback?.notificationOccurred(type); } catch {}
}

async function api(path, { method = "GET", body = null } = {}) {
  if (!API_BASE) {
    throw new Error("API_BASE не задан");
  }
  const headers = {
    "Content-Type": "application/json",
    "X-Telegram-Init-Data": tg?.initData || "",
  };
  const opts = { method, headers };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch(API_BASE + path, opts);
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`HTTP ${resp.status}: ${txt.slice(0, 200)}`);
  }
  return resp.json();
}

function renderCategories() {
  const grid = document.getElementById("categories");
  grid.innerHTML = "";
  for (const c of CATEGORIES) {
    const el = document.createElement("button");
    el.className = "card";
    el.dataset.cat = c.id;
    el.innerHTML = `
      <div class="emoji">${c.emoji}</div>
      <div>
        <div class="title">${c.title}</div>
        <div class="subtitle">${c.subtitle}</div>
      </div>
    `;
    el.addEventListener("click", () => {
      haptic("light");
      openEmotions(c);
    });
    grid.appendChild(el);
  }
  document.getElementById("surpriseBtn").addEventListener("click", () => {
    haptic("medium");
    requestRecommendation({ surprise: true });
  });
  document.getElementById("btnSavedFromHome").addEventListener("click", () => {
    haptic("light");
    openSaved();
  });
}

function renderEmotions() {
  const grid = document.getElementById("emotions");
  grid.innerHTML = "";
  for (const e of EMOTIONS) {
    const el = document.createElement("button");
    el.className = "card emotion";
    el.dataset.em = e.id;
    el.innerHTML = `
      <div class="emoji">${e.emoji}</div>
      <div class="title">${e.title}</div>
    `;
    el.addEventListener("click", () => {
      haptic("light");
      selectedEmotion = e.id;
      requestRecommendation({ category: selectedCategory.id, emotion: e.id });
    });
    grid.appendChild(el);
  }
}

function openEmotions(category) {
  selectedCategory = category;
  document.getElementById("emotionTitle").textContent = `${category.emoji} ${category.title}`;
  document.getElementById("emotionSubtitle").textContent = CATEGORY_QUESTIONS[category.id] || "";
  switchScreen("screen-emotions");
  setBackButton(() => goCategories());
}

function goCategories() {
  selectedCategory = null;
  selectedEmotion = null;
  switchScreen("screen-categories");
  setBackButton(null);
}

async function openSaved() {
  switchScreen("screen-saved");
  setBackButton(() => goCategories());
  const list = document.getElementById("savedList");
  const empty = document.getElementById("savedEmpty");
  list.innerHTML = `<div class="saved-skeleton"></div><div class="saved-skeleton"></div>`;
  empty.classList.add("hidden");
  try {
    const data = await api("/api/saved");
    list.innerHTML = "";
    if (!data.items?.length) {
      empty.classList.remove("hidden");
      return;
    }
    for (const item of data.items) {
      const cat = CATEGORY_BY_ID[item.category] || { emoji: "✨" };
      const el = document.createElement("div");
      el.className = "saved-item";
      el.dataset.cat = item.category;
      const meta = [];
      if (item.address) meta.push(`📍 ${escapeHtml(item.address)}`);
      if (item.price) meta.push(`💰 ${escapeHtml(item.price)}`);
      el.innerHTML = `
        <div class="saved-emoji">${cat.emoji}</div>
        <div class="saved-text">
          <div class="saved-title">${escapeHtml(item.name)}</div>
          ${item.description ? `<div class="saved-desc">${escapeHtml(item.description)}</div>` : ""}
          ${meta.length ? `<div class="saved-meta">${meta.join(" · ")}</div>` : ""}
        </div>
      `;
      if (item.map_url) {
        el.classList.add("clickable");
        el.addEventListener("click", () => {
          haptic("light");
          tg?.openLink ? tg.openLink(item.map_url) : window.open(item.map_url, "_blank");
        });
      }
      list.appendChild(el);
    }
  } catch (err) {
    list.innerHTML = `<div class="error-box">Не получилось загрузить: ${escapeHtml(String(err.message || err))}</div>`;
  }
}

function bindHomeButtons() {
  document.getElementById("btnHome").addEventListener("click", () => {
    haptic("light");
    goCategories();
  });
  document.getElementById("btnChangeMood").addEventListener("click", () => {
    haptic("light");
    if (!selectedCategory) {
      goCategories();
      return;
    }
    switchScreen("screen-emotions");
    setBackButton(() => goCategories());
  });
}

function bindResultButtons() {
  document.getElementById("btnSave").addEventListener("click", async () => {
    if (!currentRec) return;
    haptic("medium");
    try {
      await api("/api/save", { method: "POST", body: { rec_id: currentRec.rec_id } });
      hapticNotify("success");
      showToast("❤ Сохранил");
    } catch (err) {
      hapticNotify("error");
      showToast("Не получилось сохранить");
    }
  });
  document.getElementById("btnAnother").addEventListener("click", () => {
    if (isLoading) return;
    haptic("medium");
    if (selectedCategory && selectedEmotion) {
      requestRecommendation({ category: selectedCategory.id, emotion: selectedEmotion });
    } else if (currentRec) {
      const cat = CATEGORY_BY_ID[currentRec.category];
      if (cat) selectedCategory = cat;
      selectedEmotion = currentRec.emotion;
      requestRecommendation({ category: currentRec.category, emotion: currentRec.emotion });
    }
  });
  document.getElementById("btnReject").addEventListener("click", async () => {
    if (!currentRec || isLoading) return;
    haptic("heavy");
    const name = currentRec.name;
    const cat = currentRec.category;
    const em = currentRec.emotion || selectedEmotion;
    try {
      await api("/api/reject", { method: "POST", body: { name } });
    } catch {}
    showToast("Понял-принял, ищу другое");
    requestRecommendation({ category: cat, emotion: em });
  });
}

async function requestRecommendation(payload) {
  if (isLoading) return;
  isLoading = true;
  showLoader(payload.surprise ? "Бросаю кубик…" : "Подбираю одно место…");
  try {
    const data = await api("/api/recommend", { method: "POST", body: payload });
    currentRec = data;
    if (data.category && CATEGORY_BY_ID[data.category]) {
      selectedCategory = CATEGORY_BY_ID[data.category];
    }
    if (data.emotion) selectedEmotion = data.emotion;
    renderResult(data);
    switchScreen("screen-result");
    setBackButton(() => {
      if (selectedCategory) {
        switchScreen("screen-emotions");
        setBackButton(() => goCategories());
      } else {
        goCategories();
      }
    });
    hapticNotify("success");
  } catch (err) {
    hapticNotify("error");
    showToast("Сбой. Попробуй ещё раз");
    console.error(err);
  } finally {
    isLoading = false;
    hideLoader();
  }
}

function renderResult(rec) {
  const hero = document.getElementById("resultHero");
  hero.dataset.cat = rec.category || "";
  document.getElementById("resultEmoji").textContent = (CATEGORY_BY_ID[rec.category]?.emoji) || "✨";
  document.getElementById("resultTitle").textContent = rec.name || "";
  document.getElementById("resultDesc").textContent = rec.description || "";

  const meta = document.getElementById("resultMeta");
  meta.innerHTML = "";
  const items = [];
  if (rec.address) items.push(`📍 ${escapeHtml(rec.address)}`);
  if (rec.price) items.push(`💰 ${escapeHtml(rec.price)}`);
  if (rec.link) {
    items.push(`🔗 <a href="${escapeAttr(rec.link)}" target="_blank" rel="noopener">${escapeHtml(rec.link)}</a>`);
  }
  meta.innerHTML = items.map(i => `<div class="meta-item">${i}</div>`).join("");

  const btnMap = document.getElementById("btnMap");
  if (rec.map_url) {
    btnMap.href = rec.map_url;
    btnMap.classList.remove("hidden");
  } else {
    btnMap.classList.add("hidden");
    btnMap.href = "#";
  }
}

function setBackButton(handler) {
  if (!tg?.BackButton) return;
  tg.BackButton.offClick(setBackButton._handler || (() => {}));
  if (handler) {
    setBackButton._handler = handler;
    tg.BackButton.onClick(handler);
    tg.BackButton.show();
  } else {
    setBackButton._handler = null;
    tg.BackButton.hide();
  }
}

function switchScreen(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  window.scrollTo(0, 0);
}

function showLoader(text = "Бросаю кубик…") {
  document.getElementById("loaderText").textContent = text;
  document.getElementById("loader").classList.remove("hidden");
}
function hideLoader() {
  document.getElementById("loader").classList.add("hidden");
}

let toastTimer = null;
function showToast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.remove("hidden");
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.remove("show");
    setTimeout(() => el.classList.add("hidden"), 250);
  }, 1800);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

init();
