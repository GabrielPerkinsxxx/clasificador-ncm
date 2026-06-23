"""
Catálogo del cliente — base de productos ya clasificados por el usuario.

Filosofía:
- Solo NCM es realmente obligatorio. Descripción es muy recomendado.
- Cualquier columna extra que aporte el cliente (SKU, marca, modelo, materia,
  uso, presentación, observaciones) se conserva y se usa para el match.
- Match por similitud de texto (token overlap + Jaccard), sin embeddings ni
  dependencias externas.
"""

from __future__ import annotations

import io
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

# ── Rutas ───────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_CATALOGO_FILE = _ROOT / "data" / "persistencia" / "catalogo_cliente.json"

# Columnas reconocidas. Solo "ncm" es obligatoria.
CAMPOS_CANONICOS = [
    "sku",
    "descripcion",
    "ncm",
    "marca",
    "modelo",
    "materia_constitutiva",
    "funcion_uso_destino",
    "presentacion",
    "observaciones",
]

# Sinónimos comunes para autodetección de columnas al importar.
SINONIMOS = {
    "sku":                  ["sku", "codigo", "código", "cod", "code", "id", "producto_id", "item"],
    "descripcion":          ["descripcion", "descripción", "description", "producto", "nombre", "denominacion", "denominación", "articulo", "artículo"],
    "ncm":                  ["ncm", "posicion_sim", "posición sim", "posicion sim", "partida", "hs", "hs_code", "arancel"],
    "marca":                ["marca", "brand", "fabricante", "manufacturer"],
    "modelo":               ["modelo", "model"],
    "materia_constitutiva": ["materia", "composicion", "composición", "material", "materia_constitutiva"],
    "funcion_uso_destino":  ["funcion", "función", "uso", "destino", "aplicacion", "aplicación"],
    "presentacion":         ["presentacion", "presentación", "envase", "empaque", "packing"],
    "observaciones":        ["observaciones", "obs", "notas", "comentarios", "remarks"],
}


# ── Persistencia ────────────────────────────────────────────────────

def cargar_catalogo() -> dict:
    """Devuelve {id: {ncm, descripcion, ...}} desde el archivo local."""
    if not _CATALOGO_FILE.exists():
        return {}
    try:
        return json.loads(_CATALOGO_FILE.read_text())
    except Exception:
        return {}


def guardar_catalogo(catalogo: dict) -> None:
    _CATALOGO_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CATALOGO_FILE.write_text(
        json.dumps(catalogo, indent=2, ensure_ascii=False, default=str)
    )


# ── Normalización y similitud ───────────────────────────────────────

_STOPWORDS = {
    "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
    "con", "sin", "para", "por", "en", "y", "o", "u", "a",
    "ml", "mm", "cm", "kg", "gr", "g", "lt", "l",
}


def _quitar_acentos(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _normalizar(s: str) -> str:
    if not s:
        return ""
    s = _quitar_acentos(str(s).lower())
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokens(s: str) -> set[str]:
    return {t for t in _normalizar(s).split() if t and t not in _STOPWORDS and len(t) > 1}


def _similitud_tokens(a: str, b: str) -> float:
    """Jaccard sobre tokens normalizados. 0..1."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


def _texto_match(producto: dict) -> str:
    """Concatena todos los campos textuales del producto para hacer match."""
    partes = [
        producto.get("descripcion", ""),
        producto.get("marca", ""),
        producto.get("modelo", ""),
        producto.get("materia_constitutiva", ""),
        producto.get("funcion_uso_destino", ""),
        producto.get("presentacion", ""),
        producto.get("observaciones", ""),
    ]
    return " ".join(p for p in partes if p)


def buscar_similares(
    consulta: str | dict,
    catalogo: dict,
    umbral: float = 0.30,
    top_k: int = 5,
) -> list[dict]:
    """
    Busca productos del catálogo similares a la consulta.

    Args:
        consulta: string con la descripción del producto a clasificar,
                  o dict con varios campos (descripcion, materia, uso...).
        catalogo: dict resultado de cargar_catalogo().
        umbral: similitud mínima para devolver (0..1).
        top_k: cantidad máxima de resultados.

    Returns:
        Lista ordenada desc por similitud, cada item:
            {id, similitud, producto: {...}}
    """
    if not catalogo:
        return []

    if isinstance(consulta, dict):
        texto_consulta = " ".join(str(v) for v in consulta.values() if v)
    else:
        texto_consulta = str(consulta)

    if not _tokens(texto_consulta):
        return []

    resultados = []
    for pid, prod in catalogo.items():
        sim = _similitud_tokens(texto_consulta, _texto_match(prod))
        if sim >= umbral:
            resultados.append({"id": pid, "similitud": sim, "producto": prod})

    resultados.sort(key=lambda r: r["similitud"], reverse=True)
    return resultados[:top_k]


# ── Importación de Excel/CSV ────────────────────────────────────────

def detectar_mapeo_columnas(columnas: list[str]) -> dict:
    """
    Dado un listado de columnas del archivo del cliente, devuelve un dict
    {campo_canonico: nombre_columna_real} con la mejor coincidencia.

    Algoritmo:
        1. Match exacto del nombre normalizado de la columna contra los sinónimos.
        2. Match por tokens: si alguna palabra de la columna coincide con un sinónimo.
        3. Match por substring si el sinónimo es una palabra del nombre.

    Las columnas no mapeadas se conservan como `campos_extra` del producto.
    """
    cols_info = {col: _normalizar(col) for col in columnas}
    mapeo: dict[str, str] = {}

    for campo, sinonimos in SINONIMOS.items():
        sin_norm = [_normalizar(s) for s in sinonimos]
        # Pass 1: match exacto
        matched = None
        for col_original, col_n in cols_info.items():
            if col_n in sin_norm:
                matched = col_original
                break
        # Pass 2: match por token (alguna palabra de la columna == sinónimo)
        if not matched:
            for col_original, col_n in cols_info.items():
                col_tokens = col_n.split()
                if any(s in col_tokens for s in sin_norm):
                    matched = col_original
                    break
        if matched:
            mapeo[campo] = matched
    return mapeo


def importar_desde_archivo(
    file_bytes: bytes,
    nombre_archivo: str,
    mapeo_override: Optional[dict] = None,
    reemplazar: bool = False,
) -> dict:
    """
    Importa un Excel o CSV al catálogo del cliente.

    Args:
        file_bytes: contenido binario del archivo.
        nombre_archivo: para detectar extensión.
        mapeo_override: dict {campo_canonico: nombre_columna} si el usuario
            corrigió la autodetección.
        reemplazar: si True, sobrescribe el catálogo entero; si False, hace
            merge (matchea por SKU si existe, sino agrega).

    Returns:
        Dict con stats:
            {agregados, actualizados, descartados, errores, mapeo_usado, total_final}
    """
    ext = nombre_archivo.lower().rsplit(".", 1)[-1]
    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(file_bytes))
    elif ext == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
    else:
        raise ValueError(f"Formato no soportado: .{ext}. Usá .xlsx, .xls o .csv")

    df.columns = [str(c).strip() for c in df.columns]
    mapeo = mapeo_override or detectar_mapeo_columnas(list(df.columns))

    if "ncm" not in mapeo:
        raise ValueError(
            "No se encontró columna de NCM. El archivo debe tener una columna "
            "llamada NCM, Posición SIM, Partida o similar."
        )

    catalogo = {} if reemplazar else cargar_catalogo()
    sku_index = {p.get("sku", ""): pid for pid, p in catalogo.items() if p.get("sku")}

    agregados = 0
    actualizados = 0
    descartados = 0
    errores: list[str] = []

    for idx, fila in df.iterrows():
        try:
            producto = {}
            for campo_canonico, col_real in mapeo.items():
                valor = fila.get(col_real)
                if pd.isna(valor):
                    valor = ""
                producto[campo_canonico] = str(valor).strip()

            campos_extra = {}
            for col in df.columns:
                if col not in mapeo.values():
                    val = fila.get(col)
                    if not pd.isna(val) and str(val).strip():
                        campos_extra[col] = str(val).strip()
            if campos_extra:
                producto["campos_extra"] = campos_extra

            ncm = producto.get("ncm", "").strip()
            if not ncm:
                descartados += 1
                continue

            producto["fecha_alta"] = datetime.now().isoformat()

            sku = producto.get("sku", "").strip()
            if sku and sku in sku_index:
                pid = sku_index[sku]
                catalogo[pid].update(producto)
                actualizados += 1
            else:
                import uuid
                pid = f"cat_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}_{idx}"
                catalogo[pid] = producto
                if sku:
                    sku_index[sku] = pid
                agregados += 1

        except Exception as e:
            errores.append(f"Fila {idx + 2}: {e}")

    guardar_catalogo(catalogo)

    return {
        "agregados": agregados,
        "actualizados": actualizados,
        "descartados": descartados,
        "errores": errores,
        "mapeo_usado": mapeo,
        "total_final": len(catalogo),
    }


# ── Operaciones individuales ────────────────────────────────────────

def agregar_producto(producto: dict) -> str:
    """Agrega un producto manual al catálogo. Devuelve el id asignado."""
    import uuid
    catalogo = cargar_catalogo()
    if not producto.get("ncm", "").strip():
        raise ValueError("El NCM es obligatorio.")
    producto["fecha_alta"] = datetime.now().isoformat()
    pid = f"cat_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{uuid.uuid4().hex[:6]}"
    catalogo[pid] = producto
    guardar_catalogo(catalogo)
    return pid


def eliminar_producto(pid: str) -> bool:
    catalogo = cargar_catalogo()
    if pid in catalogo:
        del catalogo[pid]
        guardar_catalogo(catalogo)
        return True
    return False


def exportar_a_dataframe(catalogo: Optional[dict] = None) -> pd.DataFrame:
    """Devuelve el catálogo como DataFrame para descargar/exportar."""
    if catalogo is None:
        catalogo = cargar_catalogo()
    if not catalogo:
        return pd.DataFrame(columns=CAMPOS_CANONICOS + ["fecha_alta"])

    filas = []
    for pid, prod in catalogo.items():
        fila = {"id": pid}
        for campo in CAMPOS_CANONICOS:
            fila[campo] = prod.get(campo, "")
        fila["fecha_alta"] = prod.get("fecha_alta", "")
        # Campos extra como JSON en una columna aparte
        if prod.get("campos_extra"):
            fila["campos_extra"] = json.dumps(prod["campos_extra"], ensure_ascii=False)
        filas.append(fila)
    return pd.DataFrame(filas)


def stats(catalogo: Optional[dict] = None) -> dict:
    if catalogo is None:
        catalogo = cargar_catalogo()
    total = len(catalogo)
    ncms = [p.get("ncm", "") for p in catalogo.values() if p.get("ncm")]
    ncms_unicos = set(ncms)
    # Top NCMs
    from collections import Counter
    top_ncms = Counter(ncms).most_common(5)
    return {
        "total": total,
        "ncms_unicos": len(ncms_unicos),
        "top_ncms": top_ncms,
    }
