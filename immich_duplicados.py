#!/usr/bin/env python3
"""Busca fotos duplicadas en un servidor Immich.

Dos métodos:
  immich    Usa la detección de duplicados de Immich (GET /api/duplicates).
            Encuentra duplicados exactos y también fotos muy parecidas.
            Requiere que el trabajo "Detección de duplicados" ya se haya
            ejecutado en Administración > Trabajos.
  checksum  Recorre toda la biblioteca y agrupa por checksum (duplicados
            exactos byte a byte) o, con --incluir-nombre, por nombre de
            archivo + fecha de captura.

Por defecto SOLO genera un reporte (CSV y JSON). No borra nada.
Con --papelera mueve a la papelera de Immich las copias sobrantes de cada
grupo (se conserva la de mayor tamaño). La papelera permite restaurar.

Configuración por variables de entorno (no guardes la clave en el código):
  IMMICH_URL      p. ej. https://fotos.pegasoft.com.co
  IMMICH_API_KEY  clave API creada en Immich > Configuración de la cuenta
"""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict


class Cliente:
    def __init__(self, url, clave, timeout=60):
        self.base = url.rstrip("/") + "/api"
        self.clave = clave
        self.timeout = timeout

    def _peticion(self, metodo, ruta, cuerpo=None):
        datos = None
        cabeceras = {"x-api-key": self.clave, "Accept": "application/json"}
        if cuerpo is not None:
            datos = json.dumps(cuerpo).encode()
            cabeceras["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base + ruta, data=datos, headers=cabeceras, method=metodo
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                texto = r.read().decode()
                return json.loads(texto) if texto else None
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:300]
            sys.exit(f"Error HTTP {e.code} en {metodo} {ruta}: {detalle}")
        except urllib.error.URLError as e:
            sys.exit(f"No se pudo conectar a {self.base}: {e.reason}")

    def get(self, ruta):
        return self._peticion("GET", ruta)

    def post(self, ruta, cuerpo):
        return self._peticion("POST", ruta, cuerpo)

    def delete(self, ruta, cuerpo):
        return self._peticion("DELETE", ruta, cuerpo)


def tamano(activo):
    return (activo.get("exifInfo") or {}).get("fileSizeInByte") or 0


def fila(grupo_id, activo, conservar):
    exif = activo.get("exifInfo") or {}
    return {
        "grupo": grupo_id,
        "accion": "conservar" if conservar else "duplicado",
        "id": activo.get("id"),
        "archivo": activo.get("originalFileName"),
        "ruta": activo.get("originalPath"),
        "fecha": activo.get("fileCreatedAt") or activo.get("localDateTime"),
        "bytes": tamano(activo),
        "ancho": exif.get("exifImageWidth"),
        "alto": exif.get("exifImageHeight"),
    }


def grupos_immich(cli):
    """Devuelve lista de grupos (cada uno, lista de activos)."""
    respuesta = cli.get("/duplicates") or []
    return [g.get("assets", []) for g in respuesta if len(g.get("assets", [])) > 1]


def grupos_checksum(cli, incluir_nombre):
    por_clave = defaultdict(list)
    pagina = 1
    total = 0
    while pagina:
        r = cli.post("/search/metadata", {"page": pagina, "size": 1000, "withExif": True})
        bloque = (r or {}).get("assets", {})
        for a in bloque.get("items", []):
            total += 1
            if incluir_nombre:
                clave = (a.get("originalFileName"), a.get("fileCreatedAt"))
                valida = clave[0] is not None
            else:
                clave = a.get("checksum")
                valida = bool(clave)
            if valida:
                por_clave[clave].append(a)
        siguiente = bloque.get("nextPage")
        pagina = int(siguiente) if siguiente else 0
        print(f"  revisados {total} archivos...", file=sys.stderr)
    return [g for g in por_clave.values() if len(g) > 1]


def main():
    ap = argparse.ArgumentParser(description="Busca fotos duplicadas en Immich.")
    ap.add_argument("--metodo", choices=["immich", "checksum"], default="immich")
    ap.add_argument("--incluir-nombre", action="store_true",
                    help="(checksum) agrupa por nombre+fecha en vez de checksum")
    ap.add_argument("--salida", default="duplicados",
                    help="prefijo de los archivos de reporte (por defecto: duplicados)")
    ap.add_argument("--papelera", action="store_true",
                    help="mueve a la papelera las copias sobrantes (pide confirmación)")
    ap.add_argument("--si", action="store_true", help="no pedir confirmación")
    args = ap.parse_args()

    url = os.environ.get("IMMICH_URL")
    clave = os.environ.get("IMMICH_API_KEY")
    if not url or not clave:
        sys.exit("Define IMMICH_URL e IMMICH_API_KEY como variables de entorno.")

    cli = Cliente(url, clave)
    usuario = cli.get("/users/me")
    print(f"Conectado como {usuario.get('email')} en {url}", file=sys.stderr)

    if args.metodo == "immich":
        grupos = grupos_immich(cli)
    else:
        grupos = grupos_checksum(cli, args.incluir_nombre)

    filas, sobrantes, bytes_sobrantes = [], [], 0
    for n, grupo in enumerate(grupos, 1):
        ordenado = sorted(grupo, key=tamano, reverse=True)
        for i, a in enumerate(ordenado):
            filas.append(fila(n, a, i == 0))
            if i > 0:
                sobrantes.append(a["id"])
                bytes_sobrantes += tamano(a)

    with open(args.salida + ".json", "w", encoding="utf-8") as f:
        json.dump(filas, f, ensure_ascii=False, indent=2)
    campos = ["grupo", "accion", "id", "archivo", "ruta", "fecha", "bytes", "ancho", "alto"]
    with open(args.salida + ".csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    print(f"Grupos de duplicados: {len(grupos)}")
    print(f"Copias sobrantes: {len(sobrantes)} (~{bytes_sobrantes / 1048576:.1f} MB)")
    print(f"Reporte: {args.salida}.csv y {args.salida}.json")

    if args.papelera and sobrantes:
        if not args.si:
            r = input(f"¿Mover {len(sobrantes)} archivos a la papelera de Immich? [escribe si]: ")
            if r.strip().lower() != "si":
                print("Cancelado, no se movió nada.")
                return
        for i in range(0, len(sobrantes), 200):
            cli.delete("/assets", {"ids": sobrantes[i:i + 200], "force": False})
        print("Listo. Puedes restaurarlos desde la papelera de Immich.")


if __name__ == "__main__":
    main()
