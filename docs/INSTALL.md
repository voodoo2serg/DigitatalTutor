# Установка и настройка StudoBot

## Требования к системе

- **ОС**: Debian 11/12, Ubuntu 20.04+, или другой Linux
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **RAM**: минимум 2 GB (рекомендуется 4 GB)
- **Диск**: минимум 10 GB для файлов студентов

## Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Установка Docker Compose (если не установлен с Docker)
sudo apt install docker-compose-plugin -y

# Перезайдите в систему для применения прав Docker
```

## Шаг 2: Создание Telegram бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям:
   - Введите имя бота (например: "Мой СтудоБот")
   - Введите username бота (например: `my_studobot_bot`)
4. Сохраните полученный токен вида `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

5. Узнайте свой Telegram ID:
   - Откройте [@userinfobot](https://t.me/userinfobot)
   - Сохраните ваш ID

## Шаг 3: Установка StudoBot

```bash
# Клонирование репозитория
git clone https://github.com/your-username/studobot.git
cd studobot

# Копирование конфигурации
cp .env.example .env

# Редактирование настроек
nano .env
```

### Обязательные переменные в .env:

```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TEACHER_TELEGRAM_ID=123456789
POSTGRES_PASSWORD=ваш_надёжный_пароль
MINIO_ROOT_PASSWORD=ваш_надёжный_пароль
JWT_SECRET=случайная_строка_минимум_32_символа
```

## Шаг 4: Запуск

```bash
# Сборка и запуск всех сервисов
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f api
```

## Шаг 5: Первый запуск

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Бот автоматически создаст ваш профиль преподавателя
4. Студенты могут начинать отправлять файлы

## Шаг 6: Настройка n8n (опционально)

Если хотите использовать визуальный редактор workflow:

1. Откройте http://your-server:5678
2. Создайте аккаунт владельца
3. Импортируйте workflows из папки `n8n-workflows/`
4. Настройте credentials для:
   - Telegram API
   - PostgreSQL
   - MinIO

## Структура сервисов

| Сервис | Порт | Назначение |
|--------|------|------------|
| API | 8000 | REST API |
| PostgreSQL | 5432 | База данных |
| MinIO API | 9000 | S3-совместимое хранилище |
| MinIO Console | 9001 | Веб-интерфейс хранилища |
| n8n | 5678 | Оркестратор workflows |

## Проверка работоспособности

```bash
# Health check API
curl http://localhost:8000/health

# API документация
open http://localhost:8000/docs

# MinIO Console
open http://localhost:9001
```

## Резервное копирование

### Ручной бэкап базы данных:

```bash
docker-compose exec postgres pg_dump -U studobot studobot > backup_$(date +%Y%m%d).sql
```

### Ручной бэкап файлов:

```bash
# Синхронизация с Яндекс.Диском (требует настройки rclone)
rclone sync /var/lib/docker/volumes/studobot_minio_data student-backup:
```

## Обновление

```bash
# Остановка сервисов
docker-compose down

# Получение обновлений
git pull

# Пересборка и запуск
docker-compose up -d --build
```

## Устранение неполадок

### Бот не отвечает

```bash
# Проверьте логи
docker-compose logs telegram-bot

# Проверьте токен
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
```

### Ошибка подключения к базе данных

```bash
# Проверьте статус PostgreSQL
docker-compose exec postgres pg_isready

# Пересоздайте базу (ВНИМАНИЕ: удаляет данные!)
docker-compose down -v
docker-compose up -d
```

### MinIO недоступен

```bash
# Проверьте логи
docker-compose logs minio

# Перезапуск
docker-compose restart minio
```

## Безопасность

1. **Измените все пароли по умолчанию** в `.env`
2. **Используйте HTTPS** с nginx/traefik
3. **Ограничьте доступ** к портам через firewall
4. **Регулярно обновляйте** Docker-образы

```bash
# Пример настройки firewall (ufw)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```
