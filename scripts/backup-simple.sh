#!/bin/bash
# DigitalTutor PostgreSQL Backup Script (Docker-based)
# Запускать на хосте или через cron

set -euo pipefail

# Configuration
PROJECT_DIR="/srv/teaching-system"
BACKUP_DIR="${PROJECT_DIR}/backups/postgres"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="pg_backup_teaching_${DATE}.sql.gz"

# Load environment
export $(grep -E '^(POSTGRES_|DATABASE_URL)' ${PROJECT_DIR}/.env | xargs)

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting PostgreSQL backup..."
echo "[$(date)] Database: ${POSTGRES_DB:-teaching}"
echo "[$(date)] Backup file: ${BACKUP_FILE}"

# Run backup inside postgres container
docker exec digitatal-postgres pg_dump \
    -U "${POSTGRES_USER:-teacher}" \
    -d "${POSTGRES_DB:-teaching}" \
    --verbose \
    --no-owner \
    --no-privileges 2>/dev/null | \
    gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup was successful
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ] && [ -s "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo "[$(date)] Backup completed: ${BACKUP_SIZE}"
    
    # Create latest symlink
    ln -sf "${BACKUP_FILE}" "${BACKUP_DIR}/pg_backup_latest.sql.gz"
else
    echo "[$(date)] ERROR: Backup failed"
    rm -f "${BACKUP_DIR}/${BACKUP_FILE}"
    exit 1
fi

# Rotate old backups
echo "[$(date)] Rotating backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "pg_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# Count remaining backups
BACKUP_COUNT=$(find "${BACKUP_DIR}" -name "pg_backup_*.sql.gz" -type f | wc -l)
echo "[$(date)] Total backups: ${BACKUP_COUNT}"
echo "[$(date)] Backup process completed"
