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
