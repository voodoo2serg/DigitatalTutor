# DigitalTutor: Документация базы данных

## Обзор

DigitalTutor использует PostgreSQL 16 как основную базу данных. Схема спроектирована для гибкого хранения данных о студентах, работах, файлах и взаимодействиях.

---

## Диаграмма связей (ER-диаграмма)

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   students   │       │ assignments  │       │ submissions  │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │◄──┐   │ id (PK)      │◄──┐   │ id (PK)      │
│ telegram_id  │   │   │ type         │   │   │ student_id   │──►┘
│ name         │   │   │ title        │   │   │ assignment_id│──►┘
│ group_name   │   │   │ milestones   │   │   │ status       │
│ role         │   │   │ status       │   │   │ deadline     │
└──────────────┘   │   └──────────────┘   │   └──────────────┘
       │           │                      │           │
       │           │                      │           │
       ▼           │                      │           ▼
┌──────────────┐   │                      │   ┌──────────────┐
│communications│   │                      │   │    files     │
├──────────────┤   │                      │   ├──────────────┤
│ id (PK)      │   │                      │   │ id (PK)      │
│ student_id   │──►┘                      │   │ submission_id│──►┘
│ submission_id│──────────────────────────┼──►│ storage_path │
│ direction    │                          │   │ checksum     │
│ message      │                          │   └──────────────┘
└──────────────┘                          │
                                          │
                                          ▼
                                   ┌──────────────┐
                                   │   reviews    │
                                   ├──────────────┤
                                   │ id (PK)      │
                                   │ submission_id│──►
                                   │ review_type  │
                                   │ ai_analysis  │
                                   └──────────────┘
```

---

## Таблицы

### students

Студенты и аспиранты. **Принцип: минимум обязательных полей, максимум гибкости.**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `telegram_id` | BIGINT | Telegram ID пользователя |
| `name` | TEXT | Имя как написал (ФИО) |
| `group_name` | TEXT | Группа как написал |
| `email` | TEXT | Email (опционально) |
| `role` | ENUM | student / monitor / phd / teacher |
| `metadata` | JSONB | Расширяемые данные |
| `is_active` | BOOLEAN | Активен ли студент |
| `created_at` | TIMESTAMPTZ | Дата создания |
| `updated_at` | TIMESTAMPTZ | Дата обновления |

**Пример metadata:**
```json
{
  "university": "МГУ",
  "faculty": "Факультет журналистики",
  "year": 3,
  "notes": "Работает параллельно"
}
```

---

### assignments

Шаблоны заданий с milestone'ами.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `type` | VARCHAR(50) | coursework / thesis / article / project |
| `title` | TEXT | Название задания |
| `description` | TEXT | Описание |
| `milestones` | JSONB | Массив milestone'ов |
| `academic_year` | VARCHAR(20) | Учебный год (2024-2025) |
| `semester` | VARCHAR(10) | Осень/Весна |
| `status` | ENUM | active / completed / cancelled |
| `created_at` | TIMESTAMPTZ | Дата создания |

**Пример milestones:**
```json
[
  {"name": "Выбор темы", "deadline_days": 14, "required": true},
  {"name": "Согласование плана", "deadline_days": 21, "required": true},
  {"name": "Черновик", "deadline_days": 45, "required": true},
  {"name": "Финальная версия", "deadline_days": 60, "required": true}
]
```

---

### submissions

Конкретные работы студентов.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `student_id` | UUID | Ссылка на students |
| `assignment_id` | UUID | Ссылка на assignments |
| `current_milestone` | VARCHAR(100) | Текущий этап |
| `status` | ENUM | draft / submitted / reviewing / revision / approved / rejected |
| `title` | TEXT | Тема работы |
| `topic` | TEXT | Уточнённая тема |
| `deadline` | DATE | Дедлайн |
| `grade` | INTEGER | Оценка (если применимо) |
| `feedback` | TEXT | Обратная связь |
| `created_at` | TIMESTAMPTZ | Дата создания |
| `submitted_at` | TIMESTAMPTZ | Дата сдачи |
| `approved_at` | TIMESTAMPTZ | Дата утверждения |

---

### files

Файлы с версионированием и контрольными суммами.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `submission_id` | UUID | Ссылка на submissions |
| `milestone` | VARCHAR(100) | К какому milestone относится |
| `filename` | TEXT | Оригинальное имя файла |
| `storage_path` | TEXT | Путь в MinIO |
| `file_size` | BIGINT | Размер в байтах |
| `mime_type` | VARCHAR(255) | MIME-тип |
| `checksum_sha256` | VARCHAR(64) | SHA256 контрольная сумма |
| `version` | INTEGER | Номер версии |
| `uploaded_by` | BIGINT | Telegram ID загрузившего |
| `uploaded_at` | TIMESTAMPTZ | Дата загрузки |

**Структура storage_path:**
```
submissions/{year}/{semester}/{student_id}/{milestone}/{filename}
```

---

### reviews

Проверки и AI-анализ.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `submission_id` | UUID | Ссылка на submissions |
| `reviewer_telegram_id` | BIGINT | Кто проверил |
| `review_type` | VARCHAR(50) | formal / content / ai_screening / antiplagiat |
| `status` | VARCHAR(50) | pending / completed / failed |
| `comment` | TEXT | Комментарий |
| `ai_analysis` | JSONB | Результат AI-анализа |
| `antiplagiat_score` | DECIMAL(5,2) | Оценка антиплагиата |
| `antiplagiat_code` | VARCHAR(100) | Код проверки |
| `created_at` | TIMESTAMPTZ | Дата создания |

**Пример ai_analysis:**
```json
{
  "plagiarism_score": 0.15,
  "ai_generated_probability": 0.35,
  "structure_score": 0.78,
  "formatting_score": 0.92,
  "issues": [
    {"type": "structure", "description": "Отсутствует введение", "severity": "high"},
    {"type": "citation", "description": "Мало источников", "severity": "medium"}
  ],
  "recommendations": [
    "Добавить введение с постановкой задачи",
    "Включить минимум 2 дополнительных источника"
  ]
}
```

---

### antiplagiat_codes

Коды для систем антиплагиата.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `code` | VARCHAR(100) | Уникальный код |
| `description` | TEXT | Описание |
| `used_for` | TEXT | Для чего использован |
| `is_active` | BOOLEAN | Активен ли |
| `used_count` | INTEGER | Количество использований |
| `last_used_at` | TIMESTAMPTZ | Последнее использование |

---

### reminders

Напоминания о дедлайнах.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `submission_id` | UUID | Ссылка на submissions |
| `remind_at` | TIMESTAMPTZ | Когда напомнить |
| `message` | TEXT | Текст напоминания |
| `channel` | VARCHAR(50) | telegram / email |
| `status` | VARCHAR(50) | pending / sent / failed |
| `sent_at` | TIMESTAMPTZ | Когда отправлено |

---

### communications

История всех коммуникаций.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `student_id` | UUID | Ссылка на students |
| `submission_id` | UUID | Ссылка на submissions (опционально) |
| `direction` | VARCHAR(10) | in (от студента) / out (к студенту) |
| `channel` | VARCHAR(50) | telegram / email / web |
| `message` | TEXT | Текст сообщения |
| `metadata` | JSONB | Дополнительные данные |
| `created_at` | TIMESTAMPTZ | Дата создания |

---

### settings

Системные настройки.

| Поле | Тип | Описание |
|------|-----|----------|
| `key` | TEXT | Ключ настройки (PK) |
| `value` | JSONB | Значение |
| `description` | TEXT | Описание |
| `updated_at` | TIMESTAMPTZ | Дата обновления |

**Стандартные настройки:**
```sql
INSERT INTO settings (key, value, description) VALUES
('system.version', '"1.0.0"', 'Версия системы'),
('ai.model', '"gemma3:4b"', 'Модель ИИ'),
('ai.budget_yearly', '20', 'Годовой бюджет на ИИ'),
('reminder.days_before', '[1, 3, 7]', 'Дни до дедлайна для напоминаний'),
('antiplagiat.system', '"Антиплагиат ВУЗ"', 'Система антиплагиата');
```

---

### citation_styles

Стили цитирования.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `name` | VARCHAR(100) | Название стиля |
| `format` | TEXT | Формат цитирования |
| `example` | TEXT | Пример |
| `is_default` | BOOLEAN | По умолчанию |

---

### milestone_templates

Шаблоны milestone'ов для разных типов работ.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Первичный ключ |
| `assignment_type` | VARCHAR(50) | Тип задания |
| `milestone_name` | VARCHAR(100) | Название milestone |
| `milestone_order` | INTEGER | Порядок |
| `default_deadline_days` | INTEGER | Дней на выполнение |
| `required` | BOOLEAN | Обязательный |
| `description` | TEXT | Описание |

---

## Индексы

```sql
-- Производительность
CREATE INDEX idx_students_telegram ON students(telegram_id);
CREATE INDEX idx_students_role ON students(role);
CREATE INDEX idx_submissions_student ON submissions(student_id);
CREATE INDEX idx_submissions_status ON submissions(status);
CREATE INDEX idx_submissions_deadline ON submissions(deadline);
CREATE INDEX idx_files_submission ON files(submission_id);
CREATE INDEX idx_files_checksum ON files(checksum_sha256);
CREATE INDEX idx_reviews_submission ON reviews(submission_id);
CREATE INDEX idx_reminders_pending ON reminders(status, remind_at) WHERE status = 'pending';
CREATE INDEX idx_communications_student ON communications(student_id);
CREATE INDEX idx_communications_created ON communications(created_at DESC);

-- Полнотекстовый поиск
CREATE INDEX idx_students_search ON students USING GIN (
    to_tsvector('russian', name || ' ' || COALESCE(group_name, ''))
);
```

---

## Триггеры

```sql
-- Автоматическое обновление updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_students_updated_at
    BEFORE UPDATE ON students
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_submissions_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();
```

---

## Представления (Views)

### active_submissions

Активные работы с информацией о студенте.

```sql
CREATE VIEW active_submissions AS
SELECT
    s.id,
    s.title,
    s.current_milestone,
    s.status,
    s.deadline,
    st.name AS student_name,
    st.telegram_id,
    a.type AS assignment_type,
    CASE
        WHEN s.deadline < CURRENT_DATE THEN 'overdue'
        WHEN s.deadline = CURRENT_DATE THEN 'today'
        WHEN s.deadline <= CURRENT_DATE + 3 THEN 'soon'
        ELSE 'normal'
    END AS deadline_status
FROM submissions s
JOIN students st ON s.student_id = st.id
JOIN assignments a ON s.assignment_id = a.id
WHERE s.status NOT IN ('approved', 'rejected')
ORDER BY s.deadline;
```

### teacher_workload

Загрузка преподавателя по неделям.

```sql
CREATE VIEW teacher_workload AS
SELECT
    DATE_TRUNC('week', deadline) AS week,
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE status = 'submitted') AS pending_review,
    a.type AS assignment_type
FROM submissions s
JOIN assignments a ON s.assignment_id = a.id
WHERE deadline BETWEEN CURRENT_DATE - 30 AND CURRENT_DATE + 60
GROUP BY DATE_TRUNC('week', deadline), a.type
ORDER BY week;
```

---

## Миграции

Миграции выполняются через Alembic:

```bash
# Создать миграцию
alembic revision --autogenerate -m "Add antiplagiat_codes"

# Применить миграции
alembic upgrade head

# Откатить последнюю
alembic downgrade -1
```

---

## Резервное копирование

```bash
# Полный дамп
docker exec teaching-postgres pg_dump -U teacher teaching > backup_$(date +%Y%m%d).sql

# Восстановление
cat backup_20240101.sql | docker exec -i teaching-postgres psql -U teacher teaching
```
