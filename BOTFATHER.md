# Настройка бота в @BotFather

Открой [@BotFather](https://t.me/BotFather) и выполни команды по очереди.
Выбирай своего бота, когда BotFather попросит.

## /setname (название в шапке профиля, до 64 симв.)

```
Не думай — Москва
```

## /setabouttext (короткое описание, до 120 симв., видно в превью бота)

```
Скажи, что чувствуешь — назову одно место в Москве. Без подборок и «топ-10».
```

## /setdescription (длинное описание, до 512 симв., видно перед стартом)

```
Бывает: хочется куда-то выбраться, но листаешь подборки и в итоге снова дома.

Я работаю иначе. Выбираешь категорию (кино, театр, рестораны, спорт, природа, выставки) и настроение — я даю один конкретный вариант. Не десять, не «топ-5». Один.

Поехали — нажми /start.
```

## /setcommands (меню команд)

```
start - запустить бота
saved - мои сохранённые места
feedback - написать создателю
```

## /setuserpic (иконка)

Нужна квадратная картинка минимум 512×512.

Промпт для генератора (Midjourney / DALL-E / Sora):

```
A minimalist Telegram bot icon, 512x512, square, flat design, soft warm beige background (#f5ead6).
Bold black silhouette of a human head in profile, where the brain is replaced by a single small empty cloud outline.
Subtle paper grain texture. No text. Centered. Clean, modern, slightly playful.
Style: editorial illustration, like The New Yorker meets Notion icons.
```

## Картинка в приветственное сообщение

Если хочешь, чтобы при /start пришла картинка — положи файл `assets/welcome.jpg` в папку проекта,
закоммить и запушь. Бот сам её подхватит. Без картинки шлёт обычный текст.

Рекомендуемый размер: 1280×720 или 1080×1080, до 5 МБ.

## ADMIN_CHAT_ID для /feedback и /stats

1. В Telegram найди [@userinfobot](https://t.me/userinfobot) → отправь `/start` → он покажет твой numeric ID.
2. В Railway → Variables → добавь `ADMIN_CHAT_ID=твой_id`.
3. Передеплой произойдёт автоматически.
4. После этого:
   - при `/feedback` от пользователей сообщения будут падать тебе в личку от твоего бота;
   - команда `/stats` (только для тебя) показывает агрегированную аналитику.

## Mini App (Telegram Web App)

Mini App-страница лежит в репо в папке `webapp/`. Хостим её бесплатно на GitHub Pages.

### Шаг 1 — включить GitHub Pages

1. Открой репо: https://github.com/timahockey02-a11y/nedumai-bot
2. **Settings → Pages**
3. **Source**: Deploy from a branch
4. **Branch**: `main` / `/ (root)` → **Save**.
   (GitHub Pages раздаст всю папку с репо. Mini App доступен по `/webapp/`.)
5. Через 1–2 минуты страница будет жить по URL:
   ```
   https://timahockey02-a11y.github.io/nedumai-bot/webapp/
   ```
6. Проверь — открой URL в браузере. Должен виднеться экран «Не думай» с категориями.

### Шаг 2 — задать URL в Railway

В Railway → Variables:
- Name: `WEBAPP_URL`
- Value: `https://timahockey02-a11y.github.io/nedumai-bot/webapp/`
- Apply → Deploy.

После передеплоя бот автоматически:
- поставит постоянную menu-кнопку слева от поля ввода (значок ☰ → «✨ Открыть»);
- покажет inline-кнопку «✨ Открыть в приложении» на главном экране.

### Шаг 3 — зарегистрировать Mini App в @BotFather (опционально)

Если хочешь короткую ссылку вида `t.me/nedumai1_bot/app`:

1. @BotFather → `/newapp`
2. Выбери `@nedumai1_bot`
3. Title: `Не думай`
4. Description: `Одно место в Москве — под настроение`
5. Photo: 640×360, любая твоя
6. Demo GIF — пропустить
7. Web App URL: `https://timahockey02-a11y.github.io/nedumai-bot/webapp/`
8. Short name: `app`

После этого `t.me/nedumai1_bot/app` будет открывать Mini App напрямую — можно шарить как обычный бот.

## Persistent storage на Railway (важно!)

По умолчанию SQLite-файл `bot.db` живёт в файловой системе контейнера и **теряется при каждом передеплое**.
Чтобы пользовательские данные (сохранённые места, история, аналитика) не пропадали:

1. В Railway → сервис **nedumai-bot** → **Settings** → раздел **Volumes** → **+ New Volume**.
2. Mount path: `/data` → Create.
3. Перейди в **Variables** → добавь `DB_PATH=/data/bot.db` → Deploy.

После этого данные переживут любые рестарты и обновления кода.
