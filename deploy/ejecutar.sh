#!/usr/bin/env bash
# Ejecuta la búsqueda de duplicados y guarda el reporte con la fecha en el nombre.
# Pensado para correr desde el temporizador de systemd (ver README).
# Solo genera reportes: nunca mueve fotos a la papelera.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${REPORT_DIR:-/var/lib/immich-scripts/reportes}"
CONSERVAR_DIAS="${CONSERVAR_DIAS:-120}"

: "${IMMICH_URL:?Falta IMMICH_URL (defínela en /etc/immich-duplicados.env)}"
: "${IMMICH_API_KEY:?Falta IMMICH_API_KEY (defínela en /etc/immich-duplicados.env)}"

mkdir -p "$REPORT_DIR"
umask 077

python3 "$REPO_DIR/immich_duplicados.py" --salida "$REPORT_DIR/duplicados-$(date +%F)"

# Borra reportes viejos para que no se acumulen
find "$REPORT_DIR" -maxdepth 1 -name 'duplicados-*' -type f -mtime +"$CONSERVAR_DIAS" -delete
