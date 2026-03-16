# Участие в разработке StudoBot

Мы рады вашему участию в развитии проекта! Этот документ описывает процесс внесения изменений.

## Способы участия

### Сообщить о проблеме

1. Проверьте, что проблема ещё не описана в [Issues](../../issues)
2. Создайте новый Issue с описанием:
   - Что произошло
   - Что ожидалось
   - Шаги для воспроизведения
   - Версия ПО, логи, скриншоты

### Предложить улучшение

1. Создайте Issue с меткой `enhancement`
2. Опишите предлагаемое улучшение
3. Объясните, почему оно полезно

### Внести код

#### Подготовка окружения

```bash
# Форкните репозиторий
git clone https://github.com/YOUR-USERNAME/studobot.git
cd studobot

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r backend/requirements.txt
pip install -r backend/requirements-dev.txt

# Скопируйте конфигурацию
cp .env.example .env

# Запустите тесты
pytest
```

#### Процесс разработки

1. Создайте ветку для изменений:
   ```bash
   git checkout -b feature/my-feature
   # или
   git checkout -b fix/my-fix
   ```

2. Внесите изменения, следуя стилю кода

3. Добавьте тесты

4. Убедитесь, что все тесты проходят:
   ```bash
   pytest
   flake8 backend/
   mypy backend/
   ```

5. Сделайте коммит:
   ```bash
   git add .
   git commit -m "feat: описание изменений"
   ```

   Префиксы коммитов:
   - `feat:` — новая функциональность
   - `fix:` — исправление бага
   - `docs:` — документация
   - `refactor:` — рефакторинг
   - `test:` — тесты
   - `chore:` — обслуживание

6. Отправьте изменения:
   ```bash
   git push origin feature/my-feature
   ```

7. Создайте Pull Request

#### Требования к коду

- **Python**: PEP 8, type hints, docstrings
- **SQL**: snake_case для имён таблиц и полей
- **JSON**: camelCase для API responses
- **Тесты**: покрытие > 80%
- **Документация**: обновить README при необходимости

#### Структура проекта

```
studobot/
├── backend/           # API сервер
│   ├── src/
│   │   ├── routes/   # REST endpoints
│   │   ├── models/   # Pydantic модели
│   │   ├── services/ # Бизнес-логика
│   │   └── utils/    # Утилиты
│   └── tests/        # Тесты
├── database/          # SQL схемы
├── n8n-workflows/     # n8n workflows
├── infrastructure/    # Docker конфигурация
└── docs/             # Документация
```

## Вопросы?

- Создайте Issue с меткой `question`
- Или свяжитесь с авторами проекта

## Лицензия

Внося изменения, вы соглашаетесь, что ваш код будет распространяться под лицензией MIT.
