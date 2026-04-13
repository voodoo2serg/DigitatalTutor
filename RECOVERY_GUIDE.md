# DigitalTutor - Руководство по восстановлению

## Дата создания: 2026-04-13
## Версия: 4.0.1-hotfix

---

## 📦 Архив изменений

**Файл патча:** `digitatal-hotfix-4.0.1.patch` (82 KB)
**Расположение:** `/tmp/digitatal-hotfix-4.0.1.patch` на сервере
**Git коммит:** `9245ec1`

---

## 🚀 Быстрое восстановление

### Вариант 1: Применить патч

```bash
cd /opt/DigitatalTutor
git apply /tmp/digitatal-hotfix-4.0.1.patch
```

### Вариант 2: Cherry-pick коммита

```bash
cd /opt/DigitatalTutor
git cherry-pick 9245ec1
```

### Вариант 3: Ручное применение SQL-фиксов

```sql
-- 1. Добавить колонки в communications
ALTER TABLE communications ADD COLUMN message TEXT;
ALTER TABLE communications ADD COLUMN from_student BOOLEAN;
ALTER TABLE communications ADD COLUMN from_teacher BOOLEAN;

-- 2. Обновить constraint users
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('student', 'teacher', 'admin', 'Аспирант', 'ВКР + Статья'));
```

---

## 📋 Полный список изменений

### 1. База данных (PostgreSQL)

#### Таблица `communications`
```sql
ALTER TABLE communications ADD COLUMN message TEXT;
ALTER TABLE communications ADD COLUMN from_student BOOLEAN;
ALTER TABLE communications ADD COLUMN from_teacher BOOLEAN;
```

#### Таблица `users` - Constraint
```sql
ALTER TABLE users DROP CONSTRAINT users_role_check;
ALTER TABLE users ADD CONSTRAINT users_role_check 
    CHECK (role IN ('student', 'teacher', 'admin', 'Аспирант', 'ВКР + Статья'));
```

#### Новые модели SQLAlchemy (`bot/models/models.py`)
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

### 2. Исправления бота

#### `bot/handlers/start.py`
```python
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    # ... rest of code
```

#### `bot/templates/messages.py`
Добавлена константа:
```python
SUBMIT_DESCRIPTION = """<b>Описание работы</b>

Введите описание вашей работы (необязательно):
- Основная идея
- Ключевые моменты
- Что проверить

<i>Нажмите 'Пропустить' если не нужно</i>"""
```

Удалены все эмодзи (✅, 📋, 👋, 🎉, ➕, 📚, 💬, 📊, ⚙️, 📝, 🔧, 🎓, 📄)

#### `bot/services/scheduler.py`
```python
# Было:
from bot.models import AsyncSessionContext, StudentWork, User, Deadline
# Стало:
from bot.models import AsyncSessionContext, StudentWork, User
```

### 3. Исправления API

#### `backend/app/api/web_auth.py`
```python
# Было: @router.post("/bot/generate-code")
# Стало: @router.post("/bot-generate-code")
```

#### `backend/app/api/files.py`
```python
import uuid as uuid_module

# Валидация UUID
try:
    uuid_module.UUID(work_id)
except ValueError:
    return JSONResponse({"error": "Invalid UUID format"}, status_code=400)
```

### 4. AI Сервис

#### `bot/services/ai_service.py`
- Отключены: OpenRouter, Ollama, HuggingFace
- Включён только: Cerebras

### 5. Конфигурация (.env)

```bash
# Yandex Disk
YANDEX_DISK_TOKEN=y0__xD_4rwPGM6wPyD3oLftFjCp34qyCA3pLkJSklMminvH0xZRQLkKx2FV

# Cerebras AI
CEREBRAS_API_KEY=csk-2mejenvwd245jd3ded5v4cen9y2e8wxvdxtn22t2845wddrj
CEREBRAS_MODEL=llama-4-scout-17b-16e-instruct
```

---

## 🔧 Команды для восстановления

### Полный сброс и восстановление:

```bash
# 1. Остановить контейнеры
cd /opt/DigitatalTutor
docker compose down

# 2. Применить патч
git apply /tmp/digitatal-hotfix-4.0.1.patch

# 3. Пересобрать бота
docker compose build --no-cache bot

# 4. Запустить
docker compose up -d

# 5. Проверить логи
docker compose logs -f bot
```

---

## ✅ Проверка работоспособности

```bash
# Проверка API
curl http://localhost:8000/health

# Проверка AI сервиса
docker logs digitatal-bot 2>&1 | grep "Active providers"
# Должно показать: ['cerebras']

# Проверка БД
docker exec digitatal-postgres psql -U teacher -d teaching -c "\dt"
```

---

## 📞 Контакты

**Сервер:** 213.171.9.30  
**SSH ключ:** `/root/.ssh/id_openclaw`  
**Git коммит:** `9245ec1`  
**Создано:** Kimi Claw, 2026-04-13
