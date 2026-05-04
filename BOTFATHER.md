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

## ADMIN_CHAT_ID для /feedback

1. В Telegram найди [@userinfobot](https://t.me/userinfobot) → отправь `/start` → он покажет твой numeric ID.
2. В Railway → Variables → добавь `ADMIN_CHAT_ID=твой_id`.
3. Передеплой произойдёт автоматически.
4. После этого при `/feedback` от пользователей сообщения будут падать тебе в личку от твоего бота.
