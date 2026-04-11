# Code Review — DigitalTutor

**Дата:** 2026-04-12
**Ревьюер:** AI Agent (Super Z)
**Ветка:** restore-backend
**Файлов:** 56 | **Строк кода:** ~10,000

---

## Итоговые оценки

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| Идея проекта | 6/10 | Нишевая, но актуальная — Telegram как LMS |
| Реализация | 5/10 | 8/11 хендлеров работают, backend сломан |
| Готовность к продукту | 3/10 | Ядро бота живо, AI-фичи — заглушки |

---

## Что РАБОТАЕТ (end-to-end)

1. Регистрация студентов (4-шаговый FSM, Yandex.Disk)
2. Приём работ (6-шаговый FSM, локальное хранение)
3. Просмотр своих работ и статусов
4. Просмотр плана с дедлайнами
5. Связь с преподавателем (FSM + уведомления)
6. Админ: список всех работ, приём/возврат
7. Админ: трёхкомпонентная оценка (1-5, 100-балльная, буквенная)
8. Админ: массовая рассылка (957 строк — фильтры, троттлинг, вложения)
9. Скачивание файлов (локальное + Yandex.Disk fallback)

---

## Что — заглушки

- `bot/handlers/ai_review.py` — 12 строк, пустой роутер
- `bot/handlers/students.py` — 12 строк, пустой роутер
- `bot/handlers/works_review.py` — 12 строк, пустой роутер

---

## Что СЛОМАНО

### Backend API не стартует

- `app/api/auth.py` не существует, но импортируется в works.py, files.py, ai_analysis.py
- Таблицы `ai_providers`, `ai_analysis_logs`, `message_templates` отсутствуют в БД
- Docker Compose собирает bot-образ для backend-сервиса вместо FastAPI

---

## Критические баги (12)

| # | Баг | Серьёзность |
|---|-----|-------------|
| 1 | `app/api/auth.py` не существует | Критический |
| 2 | 3 таблицы БД отсутствуют (ai_*) | Критический |
| 3 | Docker Compose собирает bot вместо backend | Критический |
| 4 | Схема SQL не совпадает с ORM-моделями (~8 полей) | Высокий |
| 5 | `registration.py` вызывает YandexDiskService с неверной сигнатурой | Высокий |
| 6 | `ai_analysis.py` ссылается на несуществующие поля модели | Высокий |
| 7 | Отсутствует `os` import в files.py | Средний |
| 8 | Отсутствует `UUID` import в files.py | Средний |
| 9 | Смешанные Telegram-библиотеки (aiogram + ptb) | Средний |
| 10 | 3 handler-заглушки зарегистрированы как рабочие | Средний |
| 11 | Нет авторизации на части backend-эндпоинтов | Средний |
| 12 | Дублирующийся import в registration.py | Низкий |

---

## Применённые фиксы (в данном коммите)

- **backend/models/models.py**: убрано дублирование 252 строк → реэкспорт из bot/models
- **backend/core/database.py**: Base теперь импортируется из bot/models
- **backend/models/__init__.py**: добавлены реэкспорты
- **bot/bot_v2.py**: добавлены недостающие роутеры (ai_review, students, works_review, mass_messaging, grade)
- **bot/handlers/*.py**: хардкод ADMIN_IDS заменён на config.ADMIN_IDS (5 файлов)
- **bot/models/models.py**: добавлены поля grade_*, is_archived, graded_at, antiplag_*
- **bot/handlers/mass_messaging.py**: throttling перенесён в config

---

## Сильные стороны

1. **Mass messaging handler** (957 строк) — production-quality
2. **3-компонентная система оценок** — продуманная реализация
3. **YAML-конфиги** — отлично структурированные (395 + 415 строк)
4. **Docker-инфраструктура** — полный стек
5. **Install-скрипт** — интерактивная установка

---

## Что сделать для стабилизации (приоритет)

1. Создать `app/api/auth.py` (минимум заглушка verify_token)
2. Добавить 3 таблицы в `init.sql` (ai_providers, ai_analysis_logs, message_templates)
3. Исправить Docker Compose (backend → context: ./backend)
4. Синхронизировать ORM с SQL-схемой
5. Починить YandexDiskService сигнатуру в registration.py
