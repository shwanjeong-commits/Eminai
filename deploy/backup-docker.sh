#!/usr/bin/env sh
set -eu

KEEP="${KEEP_BACKUPS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="./backups/$STAMP"
VOLUME="${NEWS_DATA_VOLUME:-telegram-news-dashboard_news-data}"

mkdir -p "$BACKUP_DIR"

docker run --rm \
  -v "$VOLUME:/data:ro" \
  -v "$(pwd)/$BACKUP_DIR:/backup" \
  alpine sh -c "cd /data && tar czf /backup/news-data.tgz ."

cat > "$BACKUP_DIR/manifest.txt" <<EOF
created_at=$STAMP
volume=$VOLUME
include_env=false
EOF

find ./backups -mindepth 1 -maxdepth 1 -type d | sort -r | awk "NR>$KEEP" | xargs -r rm -rf

echo "Backup created: $BACKUP_DIR"
