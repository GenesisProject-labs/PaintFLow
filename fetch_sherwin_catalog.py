# -*- coding: utf-8 -*-
"""Descarga el catalogo completo de colores Sherwin-Williams y lo guarda local.

Estrategia: como la API publica de Prism no admite paginacion explicita ni
un wildcard global, unimos los resultados de multiples queries (letras y
digitos) y deduplicamos por colorNumber. Con vocales y digitos cubrimos el
catalogo entero (>2000 colores).

Salida: sherwin_colors_cache.json (lista normalizada).
"""

import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "sherwin_colors_cache.json")
QUERIES = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["sw", "color", "white", "black", "red", "blue", "green"]
TIMEOUT_SECONDS = 25
SLEEP_BETWEEN_REQUESTS = 0.4


def fetch_query(q: str):
    params = urlencode({"query": q, "lng": "en-US", "_corev": "7.16.0"})
    url = f"https://api.sherwin-williams.com/prism/v1/search/sherwin?{params}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "PaintFlow/1.0"})
    with urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def normalize(item):
    code = str(item.get("colorNumber") or "").strip().upper().replace(" ", "")
    if not code:
        return None
    families = item.get("colorFamilyNames") or []
    if not isinstance(families, list):
        families = []
    return {
        "code": code,
        "name": str(item.get("name") or "").strip(),
        "hex": str(item.get("hex") or "").strip(),
        "lrv": item.get("lrv"),
        "red": item.get("red"),
        "green": item.get("green"),
        "blue": item.get("blue"),
        "families": [str(f).strip() for f in families if str(f).strip()],
        "collections": [str(c).strip() for c in (item.get("brandedCollectionNames") or []) if str(c).strip()],
        "isInterior": bool(item.get("isInterior")),
        "isExterior": bool(item.get("isExterior")),
        "isDark": bool(item.get("isDark")),
    }


def main():
    merged = {}
    for idx, q in enumerate(QUERIES, start=1):
        try:
            data = fetch_query(q)
        except (HTTPError, URLError) as e:
            print(f"[{idx}/{len(QUERIES)}] {q!r} ERROR {e}")
            continue
        except Exception as e:
            print(f"[{idx}/{len(QUERIES)}] {q!r} ERROR {e}")
            continue

        results = data.get("results") or []
        new_count = 0
        for raw in results:
            if not isinstance(raw, dict):
                continue
            norm = normalize(raw)
            if not norm:
                continue
            if norm["code"] not in merged:
                merged[norm["code"]] = norm
                new_count += 1
        print(f"[{idx}/{len(QUERIES)}] q={q!r:8} got={len(results):5} new={new_count:4} total={len(merged)}")
        time.sleep(SLEEP_BETWEEN_REQUESTS)

    colors = sorted(merged.values(), key=lambda c: c["code"])
    payload = {
        "fetched_at": int(time.time()),
        "total": len(colors),
        "colors": colors,
    }

    tmp_path = OUTPUT_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp_path, OUTPUT_PATH)

    size_kb = os.path.getsize(OUTPUT_PATH) / 1024.0
    print(f"OK guardado {OUTPUT_PATH} | colores={len(colors)} | tamano={size_kb:.1f} KB")


if __name__ == "__main__":
    main()
