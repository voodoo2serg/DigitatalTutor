#!/bin/bash
#
# DigitalTutor - Мастер установки
# Запуск: sudo ./install.sh
#

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Проверка прав
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Этот скрипт нужно запускать с sudo${NC}"
   exit 1
fi

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     DigitalTutor - Мастер установки v1.1                  ║"
echo "║     Система управления учебными проектами                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# === ФУНКЦИИ ===

generate_password() {
    openssl rand -base64 24 | tr -d '/+=' | head -c 32
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}Docker не установлен. Устанавливаю...${NC}"
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        echo -e "${GREEN}Docker установлен${NC}"
    fi
}

ask_value() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    if [[ -n "$default" ]]; then
        read -p "$(echo -e ${BLUE}$prompt [$default]:${NC} )" value
        value=${value:-$default}
    else
        read -p "$(echo -e ${BLUE}$prompt:${NC} )" value
    fi

    eval "$var_name='$value'"
}

# === СБОР ДАННЫХ ===

echo -e "\n${YELLOW}=== Базовые настройки ===${NC}"

SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
ask_value "IP адрес сервера" "$SERVER_IP" SERVER_IP
ask_value "Домен (Enter если нет)" "" DOMAIN_NAME
ask_value "URL n8n (на Coolify)" "http://localhost:5678" N8N_URL

echo -e "\n${YELLOW}=== Telegram ===${NC}"
ask_value "Telegram Bot Token" "" TELEGRAM_BOT_TOKEN
ask_value "Ваш Telegram ID" "" TEACHER_TELEGRAM_ID
ask_value "Ваше ФИО (для приветствия)" "" TEACHER_NAME

echo -e "\n${YELLOW}=== AI настройки ===${NC}"
ask_value "OpenAI API Key (Enter если нет)" "" OPENAI_API_KEY
ask_value "Ollama модель" "gemma3:4b" OLLAMA_MODEL
ask_value "Годовой бюджет AI (USD)" "20" AI_BUDGET_YEARLY

echo -e "\n${YELLOW}=== Яндекс интеграция ===${NC}"
ask_value "Яндекс.Диск OAuth Token (Enter если нет)" "" YANDEX_DISK_TOKEN
ask_value "Яндекс.DataLens Token (Enter если нет)" "" YANDEX_DATALENS_TOKEN

echo -e "\n${YELLOW}=== Антиплагиат ===${NC}"
ask_value "Название системы антиплагиата" "Антиплагиат ВУЗ" ANTIPLAG_SYSTEM_NAME
ask_value "URL антиплагиата" "" ANTIPLAG_URL
ask_value "Коды антиплагиата (через запятую)" "" ANTIPLAG_CODES

echo -e "\n${YELLOW}=== База данных ===${NC}"
POSTGRES_USER="teacher"
POSTGRES_PASSWORD=$(generate_password)
POSTGRES_DB="teaching"
echo -e "${GREEN}Сгенерирован пароль БД: ${POSTGRES_PASSWORD}${NC}"

echo -e "\n${YELLOW}=== Хранилище файлов ===${NC}"
MINIO_ROOT_USER="teacher"
MINIO_ROOT_PASSWORD=$(generate_password)
echo -e "${GREEN}Сгенерирован пароль MinIO: ${MINIO_ROOT_PASSWORD}${NC}"

# === СОЗДАНИЕ .env ===

INSTALL_DIR="/srv/teaching-system"
echo -e "\n${YELLOW}=== Создание конфигурации ===${NC}"
mkdir -p "$INSTALL_DIR"

cat > "$INSTALL_DIR/.env" << EOF
# === СЕТЬ ===
SERVER_IP=$SERVER_IP
N8N_URL=$N8N_URL
DOMAIN_NAME=$DOMAIN_NAME

# === TELEGRAM ===
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TEACHER_TELEGRAM_ID=$TEACHER_TELEGRAM_ID
TEACHER_NAME=$TEACHER_NAME

# === AI ===
OPENAI_API_KEY=$OPENAI_API_KEY
OLLAMA_MODEL=$OLLAMA_MODEL
AI_BUDGET_YEARLY=$AI_BUDGET_YEARLY

# === ЯНДЕКС ===
YANDEX_DISK_TOKEN=$YANDEX_DISK_TOKEN
YANDEX_DATALENS_TOKEN=$YANDEX_DATALENS_TOKEN
YANDEX_BACKUP_FOLDER=/studobot-backup

# === АНТИПЛАГИАТ ===
ANTIPLAG_SYSTEM_NAME=$ANTIPLAG_SYSTEM_NAME
ANTIPLAG_URL=$ANTIPLAG_URL
ANTIPLAG_CODES=$ANTIPLAG_CODES

# === БАЗА ДАННЫХ ===
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=$POSTGRES_DB

# === ХРАНИЛИЩЕ ===
MINIO_ROOT_USER=$MINIO_ROOT_USER
MINIO_ROOT_PASSWORD=$MINIO_ROOT_PASSWORD

# === NOCODB ===
NOCODB_JWT_SECRET=$(generate_password)

# === БЕЗОПАСНОСТЬ ===
JWT_SECRET=$(generate_password)
WEBHOOK_SECRET=$(generate_password | head -c 16)

# === БЭКАП ===
BACKUP_RETENTION_DAYS=30
EOF

chmod 600 "$INSTALL_DIR/.env"
echo -e "${GREEN}.env создан${NC}"

# === КОПИРОВАНИЕ ФАЙЛОВ ===
echo -e "\n${YELLOW}=== Копирование файлов ===${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$INSTALL_DIR"/{postgres,minio,nocodb,backups,logs,master-config,web/student,nginx,n8n-workflows,database,config,bot}

cp "$SCRIPT_DIR/docker-compose.yml" "$INSTALL_DIR/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/database/"* "$INSTALL_DIR/database/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/master-config/"* "$INSTALL_DIR/master-config/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/web/"* "$INSTALL_DIR/web/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/nginx/"* "$INSTALL_DIR/nginx/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/n8n-workflows/"* "$INSTALL_DIR/n8n-workflows/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/config/"* "$INSTALL_DIR/config/" 2>/dev/null || true
cp -r "$SCRIPT_DIR/bot/"* "$INSTALL_DIR/bot/" 2>/dev/null || true

chmod +x "$INSTALL_DIR/master-config/wizard.sh" 2>/dev/null || true
chmod +x "$INSTALL_DIR/bot/"*.py 2>/dev/null || true
echo -e "${GREEN}Файлы скопированы${NC}"

# === ПРОВЕРКА DOCKER ===
echo -e "\n${YELLOW}=== Проверка Docker ===${NC}"
check_docker

# === ЗАПУСК ===
echo -e "\n${YELLOW}=== Запуск сервисов ===${NC}"
cd "$INSTALL_DIR"
docker-compose up -d
echo -e "${GREEN}Сервисы запущены${NC}"

# === ИТОГИ ===
echo -e "\n${GREEN}"
echo "═══════════════════════════════════════════════════════════"
echo "                 УСТАНОВКА ЗАВЕРШЕНА                       "
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "📁 Директория: $INSTALL_DIR"
echo ""
echo "🌐 Доступные сервисы:"
echo "   • NocoDB (дашборд):    http://$SERVER_IP:8080"
echo "   • MinIO Console:       http://$SERVER_IP:9001"
echo "   • Веб для студентов:   http://$SERVER_IP:3000"
echo ""
echo "📝 Следующий шаг:"
echo "   cd $INSTALL_DIR && ./master-config/wizard.sh"
echo ""
echo "🔐 Пароли сохранены в: $INSTALL_DIR/.env"
echo -e "${NC}"
