# GeoReport — GEO Audit Dashboard

Generative Engine Optimization (GEO) audit tool that analyzes public webpages for AI citation readiness. Deployed on Vercel with Python serverless functions.

## Структура проекта

```
georeport/
├── api/
│   └── audit.py          # Vercel serverless function
├── app/
│   ├── scraper.py        # Fetch & parse pages
│   ├── scorer.py         # Rule-based GEO scoring (4 метрики)
│   └── llm.py            # Gemini JSON-LD generation
├── frontend/
│   └── index.html        # Dashboard UI
├── vercel.json           # Vercel config
└── requirements.txt      # Python deps
```

## Развертывание на Vercel

### Через Vercel CLI

```bash
npm i -g vercel
cd /Users/gesha/Desktop/georeport
vercel
```

### Через GitHub

1. Запушьте репозиторий на GitHub
2. Подключите репозиторий в [vercel.com](https://vercel.com)
3. Vercel автоматически определит Python проект

## Как работает

1. Пользователь вводит Gemini API ключ и список URL
2. Фронтенд отправляет POST запрос на `/api/audit`
3. Python serverless function:
   - Загружает HTML страницы через httpx
   - Оценивает 4 GEO метрики (rule-based, без LLM)
   - Генерирует JSON-LD schema через Gemini API
4. Результат отображается на странице с возможностью экспорта

## Метрики аудита (100 баллов)

| Метрика | Баллы | Что проверяет |
|---------|-------|---------------|
| Schema Markup | 30 | JSON-LD структура (@type, name, description, url, image) |
| Semantic HTML | 25 | main/article/section/nav/aside |
| Image Alt Text | 25 | Alt атрибуты изображений |
| Content Structure | 20 | Иерархия заголовков (h1-h6) |

## Зависимости

- `httpx` — HTTP клиент для загрузки страниц
- `beautifulsoup4` — парсинг HTML
- `google-genai` — Gemini API для генерации JSON-LD

## Требования к API ключу

Необходим Google Gemini API ключ: https://aistudio.google.com/app/apikey
