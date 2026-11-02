# fotospegasoft

Herramientas para el servidor de fotos Immich de Pegasoft.

## immich_duplicados.py

Busca fotos duplicadas y genera un reporte (`duplicados.csv` y `duplicados.json`).
No usa librerías externas, solo Python 3.8 o superior.

### Configuración

La clave API **nunca** va en el código ni en el repositorio (es público). Se pasa por variables de entorno:

```bash
export IMMICH_URL="https://fotos.pegasoft.com.co"
export IMMICH_API_KEY="tu-clave-api"
```

En Windows (PowerShell):

```powershell
$env:IMMICH_URL = "https://fotos.pegasoft.com.co"
$env:IMMICH_API_KEY = "tu-clave-api"
```

La clave se crea en Immich > Configuración de la cuenta > Claves API.

### Uso

```bash
# Solo reporte, usando la detección de duplicados de Immich (recomendado)
python3 immich_duplicados.py

# Solo duplicados exactos, por checksum
python3 immich_duplicados.py --metodo checksum

# Por nombre de archivo + fecha de captura
python3 immich_duplicados.py --metodo checksum --incluir-nombre

# Mover las copias sobrantes a la papelera de Immich (pide confirmación)
python3 immich_duplicados.py --papelera
```

En cada grupo se marca como `conservar` el archivo más pesado y como `duplicado` el resto. Con `--papelera` solo se mueven a la papelera los marcados como `duplicado`, y se pueden restaurar desde Immich.

El método `immich` necesita que el trabajo **Detección de duplicados** haya corrido antes (Administración > Trabajos). Revisa siempre el CSV antes de usar `--papelera`: las fotos "muy parecidas" no siempre son la misma foto.

## Ejecución automática cada 8 días (systemd)

La carpeta `deploy/` trae un temporizador de systemd que ejecuta la búsqueda cada 8 días **en el propio servidor** y guarda un reporte con la fecha en `/var/lib/immich-scripts/reportes/` (por ejemplo `duplicados-2026-11-10.csv`). Solo genera reportes, nunca mueve fotos a la papelera. Los reportes con más de 120 días se borran solos.

Se asume que el repositorio está en `/var/lib/immich-scripts/fotospegasoft`. Como root:

```bash
# 1. Configuración con la clave (fuera del repositorio, solo legible por root)
cp deploy/immich-duplicados.env.example /etc/immich-duplicados.env
nano /etc/immich-duplicados.env        # pon tu URL y tu clave API reales
chmod 600 /etc/immich-duplicados.env

# 2. Instalar y activar el temporizador
cp deploy/immich-duplicados.service deploy/immich-duplicados.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now immich-duplicados.timer
```

Comandos útiles:

```bash
systemctl start immich-duplicados.service      # ejecutarlo ahora mismo
journalctl -u immich-duplicados.service -n 20  # ver el resultado de la última ejecución
systemctl list-timers immich-duplicados.timer  # ver cuándo será la próxima
ls /var/lib/immich-scripts/reportes/           # ver los reportes guardados
```

Si el repositorio está en otra ruta, cambia la línea `ExecStart` de `immich-duplicados.service`. Para cambiar la frecuencia, edita `OnUnitActiveSec` en `immich-duplicados.timer` y ejecuta `systemctl daemon-reload` y `systemctl restart immich-duplicados.timer`.
