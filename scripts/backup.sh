#!/usr/bin/env bash
# Production (Linux) equivalent of backup.ps1.
#   * Backs up every volume declared in the Compose files to BACKUP_ROOT/<timestamp>/
#   * Stops services for a consistent copy (~1-3 min monitoring gap), restarts them
#   * Writes status metrics to exporters/textfile/monitoring_backup.prom
#     (alerts: BackupMissing, BackupFailed, BackupStatusMissing)
#   * Optional retention: KEEP_DAYS (default 14) deletes older backup folders
#     created by this script only.
#
# Usage (from the repo root on the monitoring server):
#   COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod" \
#     ./scripts/backup.sh
# Schedule daily with cron or a systemd timer (see docs/deployment.md).
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=${COMPOSE:-"docker compose"}
BACKUP_ROOT=${BACKUP_ROOT:-./backups}
KEEP_DAYS=${KEEP_DAYS:-14}
TEXTFILE=./exporters/textfile/monitoring_backup.prom
started=$(date +%s)
stamp=$(date +%Y%m%d-%H%M%S)
dest="$BACKUP_ROOT/$stamp"
mkdir -p "$dest"
dest_abs=$(cd "$dest" && pwd)

volumes=$($COMPOSE config --format json | python3 -c 'import sys,json; print(" ".join(v["name"] for v in json.load(sys.stdin)["volumes"].values()))')
tar_image=$($COMPOSE config --images | grep '^prom/prometheus:' | head -1)

write_metrics() {   # $1 = success (1/0), $2 = size bytes
  local now last_success=0
  now=$(date +%s)
  if [ "$1" = 1 ]; then last_success=$now
  elif [ -f "$TEXTFILE" ]; then
    last_success=$(awk '/^monitoring_backup_last_success_timestamp_seconds /{print $2}' "$TEXTFILE" || echo 0)
  fi
  {
    echo "# TYPE monitoring_backup_last_run_timestamp_seconds gauge"
    echo "monitoring_backup_last_run_timestamp_seconds $now"
    echo "# TYPE monitoring_backup_last_run_success gauge"
    echo "monitoring_backup_last_run_success $1"
    echo "# TYPE monitoring_backup_last_duration_seconds gauge"
    echo "monitoring_backup_last_duration_seconds $((now - started))"
    echo "# TYPE monitoring_backup_last_size_bytes gauge"
    echo "monitoring_backup_last_size_bytes $2"
    if [ "${last_success:-0}" -gt 0 ]; then
      echo "# TYPE monitoring_backup_last_success_timestamp_seconds gauge"
      echo "monitoring_backup_last_success_timestamp_seconds $last_success"
    fi
  } > "$TEXTFILE.tmp" && mv -f "$TEXTFILE.tmp" "$TEXTFILE"
}

success=0
size=0
echo "Backing up volumes to $dest_abs: $volumes"
$COMPOSE stop
trap '$COMPOSE start >/dev/null; write_metrics "$success" "$size"' EXIT
for v in $volumes; do
  echo "  $v"
  docker run --rm --user root --entrypoint tar -v "$v:/source:ro" -v "$dest_abs:/backup" "$tar_image" \
    czf "/backup/$v.tar.gz" -C /source .
done
chmod 600 "$dest_abs"/*.tar.gz
size=$(du -sb "$dest_abs" | cut -f1)
success=1
echo "Backup complete: $dest_abs ($size bytes)"

# Retention: only timestamped folders created by this script.
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -regex '.*/[0-9]\{8\}-[0-9]\{6\}' -mtime +"$KEEP_DAYS" -print -exec rm -rf {} +
