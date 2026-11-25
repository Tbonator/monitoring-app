#!/usr/bin/env bash
# Production (Linux) restore from a backup.sh folder. DESTRUCTIVE for the
# volumes being restored: their current contents are replaced.
#
#   COMPOSE="docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env.prod" \
#     ./scripts/restore.sh backups/20261201-020000 [volume ...]
#
# Without volume names, every archive in the folder is restored. Rehearse with
# a drill first (scripts/restore.ps1 -Mode Drill on a workstation, or restore
# into a scratch server) - see docs/deployment.md "Restore procedure".
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE=${COMPOSE:-"docker compose"}
src=$(cd "${1:?usage: restore.sh <backup-dir> [volume ...]}" && pwd); shift || true
tar_image=$($COMPOSE config --images | grep '^prom/prometheus:' | head -1)

if [ "$#" -gt 0 ]; then vols="$*"; else vols=$(cd "$src" && ls *.tar.gz | sed 's/\.tar\.gz$//'); fi
echo "About to REPLACE the contents of: $vols"
read -r -p "Type RESTORE to continue: " answer
[ "$answer" = "RESTORE" ] || { echo "Aborted."; exit 1; }

$COMPOSE stop
trap '$COMPOSE start' EXIT
for v in $vols; do
  [ -f "$src/$v.tar.gz" ] || { echo "missing $src/$v.tar.gz"; exit 1; }
  echo "  restoring $v"
  docker volume create "$v" >/dev/null
  docker run --rm --user root --entrypoint sh -v "$v:/target" -v "$src:/backup:ro" "$tar_image" \
    -c "find /target -mindepth 1 -delete && tar xzf /backup/$v.tar.gz -C /target"
done
echo "Restore complete; services restarting. Check with: $COMPOSE ps"
