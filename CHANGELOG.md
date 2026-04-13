# DigitalTutor - Полный список изменений

## Дата: 2026-04-13
## Версия: 4.0.1-hotfix

---

## 🔧 Критические исправления базы данных

### 1. Таблица `communications` - добавлены колонки
**Файл:** `backend/app/models/models.py`, SQLAlchemy + PostgreSQL

```sql
ALTER TABLE communications ADD COLUMN message TEXT;
ALTER TABLE communications ADD COLUMN from_student BOOLEAN;
ALTER TABLE communications ADD COLUMN from_teacher BOOLEAN;
```

**Причина:** API communications падал с ошибкой отсутствия колонок.

### 2. Таблица `users` - обновлён constraint
**Файл:** `backend/app/models/models.py`

```sql
ALTER TABLE users DROP CONSTRAINT users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('student', 'teacher', 'admin', 'Аспирант', 'ВКР + Статья'));
```

**Причина:** Регистрация не работала с ролями 'Аспирант' и 'ВКР + Статья'.

### 3. Добавлены модели `Milestone` и `MilestoneSubmission`
**Файл:** `bot/models/models.py`

```python
class Milestone(Base):
    __tablename__ = "milestones"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_type_id = Column(UUID(as_uuid=True), ForeignKey("work_types.id", ondelete="CASCADE"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    order_number = Column(Integer, nullable=False)
    weight_percent = Column(Integer, default=0)
    deadline_offset_days = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class MilestoneSubmission(Base):
    __tablename__ = "milestone_submissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_id = Column(UUID(as_uuid=True), ForeignKey("student_works.id", ondelete="CASCADE"))
    milestone_id = Column(UUID(as_uuid=True), ForeignKey("milestones.id"))
    status = Column(String(50), default="pending")
    student_comment = Column(Text)
    teacher_feedback = Column(Text)
    submitted_files = Column(JSONB)
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Причина:** Таблица `files` ссылалась на `milestone_submissions`, но модели не существовало.

---

## 🤖 Исправления бота

### 4. Исправлен `start.py` - добавлен FSMContext
**Файл:** `bot/handlers/start.py`

```python
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    # ...
```

**Причина:** Ошибка `TypeError: cmd_start() missing 1 required positional argument: 'state'`.

### 5. Исправлен `messages.py` - добавлена константа
**Файл:** `bot/templates/messages.py`

```python
SUBMIT_DESCRIPTION = """<b>Описание работы</b>

Введите описание вашей работы (необязательно):
- Основная идея
- Ключевые моменты
- Что проверить

<i>Нажмите 'Пропустить' если не нужно</i>"""
```

**Причина:** Ошибка `AttributeError: type object 'Messages' has no attribute 'SUBMIT_DESCRIPTION'`.

### 6. Очищены эмодзи из messages.py
**Файл:** `bot/templates/messages.py`

Удалены все Unicode-эмодзи (✅, 📋, 👋, 🎉, ➕, 📚, 💬, 📊, ⚙️, 📝, 🔧, 🎓, 📄) для совместимости с Python в контейнере.

### 7. Исправлен `scheduler.py` - убран импорт Deadline
**Файл:** `bot/services/scheduler.py`

```python
# Было:
from bot.models import AsyncSessionContext, StudentWork, User, Deadline
# Стало:
from bot.models import AsyncSessionContext, StudentWork, User
```

**Причина:** Модель `Deadline` не существовала, вызывало ImportError.

---

## 🔌 Исправления API

### 8. Исправлен URL endpoint
**Файл:** `backend/app/api/web_auth.py`

```python
# Было: @router.post("/bot/generate-code")
# Стало: @router.post("/bot-generate-code")
```

**Причина:** Бот не мог получить код авторизации (404 ошибка).

### 9. Исправлена валидация UUID в Files API
**Файл:** `backend/app/api/files.py`

```python
import uuid as uuid_module

try:
    uuid.UUID(work_id)
except ValueError:
    return JSONResponse({"error": "Invalid UUID format"}, status_code=400)
```

**Причина:** Ошибка `ValueError: badly formed hexadecimal UUID string`.

---

## 🤖 AI Сервис

### 10. Отключены публичные AI провайдеры
**Файл:** `bot/services/ai_service.py`

Отключены: OpenRouter, Ollama, HuggingFace
Включён только: Cerebras (для скрытой рецензии преподавателя)

### 11. Убрана AI проверка из меню помощи
**Файл:** `bot/templates/messages.py`

Удалён раздел "<b>AI Проверка:</b>" из HELP_TEXT.

---

## 📨 Массовая рассылка

### 12. Упрощён интерфейс массовой рассылки
**Файл:** `bot/handlers/mass_messaging.py`

- Убрано сложное меню фильтров
- Теперь простой список студентов с двумя кнопками:
  - 💬 — начать диалог в боте
  - ✉️ — открыть в Telegram (личные сообщения)

---

## 🔧 Конфигурация

### 13. Добавлены переменные окружения
**Файл:** `.env` на сервере

```bash
# Yandex Disk
YANDEX_DISK_TOKEN=y0__xD_4rwPGM6wPyD3oLftFjCp34qyCA3pLkJSklMminvH0xZRQLkKx2FV

# Cerebras AI
CEREBRAS_API_KEY=csk-2mejenvwd245jd3ded5v4cen9y2e8wxvdxtn22t2845wddrj
CEREBRAS_MODEL=llama-4-scout-17b-16e-instruct
```

---

## 🐳 Docker

### 14. Обновлён docker-compose.yml
- Добавлено подключение `.env` файла для бота
- Исправлены healthcheck'и

---

## 📋 Проверка статуса

### Работает:
- ✅ API Health (200 OK)
- ✅ Work Types API
- ✅ Communications API
- ✅ Files API
- ✅ Web Login
- ✅ Регистрация (все роли)
- ✅ Бот (polling активен)
- ✅ AI Service (Cerebras)
- ✅ Yandex Disk интеграция
- ✅ Массовая рассылка

### Контейнеры:
- digitatal-backend
- digitatal-postgres
- digitatal-bot
- digitatal-nginx
- digitatal-redis

---

## 📝 Как восстановить

1. Клонировать репозиторий
2. Скопировать `.env` файл с сервера (содержит токены)
3. Запустить: `docker compose up -d`
4. Применить SQL-фиксы (если БД пустая):
   ```bash
   docker exec digitatal-postgres psql -U teacher -d teaching -f /tmp/db_fixes.sql
   ```

---

**Создано:** 2026-04-13
**Автор:** Kimi Claw
**Сервер:** 213.171.9.30
