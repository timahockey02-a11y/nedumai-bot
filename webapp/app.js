const tg = window.Telegram?.WebApp;

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

let selectedCategory = null;

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
}

function haptic(style = "medium") {
  try {
    tg?.HapticFeedback?.impactOccurred(style);
  } catch {}
}

function hapticNotify(type = "success") {
  try {
    tg?.HapticFeedback?.notificationOccurred(type);
  } catch {}
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
    sendChoice({ surprise: true });
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
      sendChoice({ category: selectedCategory.id, emotion: e.id });
    });
    grid.appendChild(el);
  }
}

function openEmotions(category) {
  selectedCategory = category;
  document.getElementById("emotionTitle").textContent = `${category.emoji} ${category.title}`;
  document.getElementById("emotionSubtitle").textContent = CATEGORY_QUESTIONS[category.id] || "";
  switchScreen("screen-emotions");
  if (tg?.BackButton) {
    tg.BackButton.show();
    tg.BackButton.onClick(backToCategories);
  }
}

function backToCategories() {
  switchScreen("screen-categories");
  if (tg?.BackButton) {
    tg.BackButton.hide();
    tg.BackButton.offClick(backToCategories);
  }
  selectedCategory = null;
}

function switchScreen(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  window.scrollTo(0, 0);
}

function showLoader() {
  document.getElementById("loader").classList.remove("hidden");
}

function sendChoice(payload) {
  hapticNotify("success");
  showLoader();
  const data = JSON.stringify({ ...payload, source: "miniapp" });

  if (tg?.sendData) {
    tg.sendData(data);
    // Telegram сам закроет Mini App после sendData в большинстве клиентов.
    // Подстраховка для desktop:
    setTimeout(() => tg.close?.(), 600);
  } else {
    // Открыто в обычном браузере (для отладки)
    alert("Mini App: " + data);
    document.getElementById("loader").classList.add("hidden");
  }
}

init();
