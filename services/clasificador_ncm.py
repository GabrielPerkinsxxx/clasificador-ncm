"""
Servicio de clasificación arancelaria con IA (Anthropic Claude)
y validación contra la matriz NCM de Argentina.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Sos un experto en clasificación arancelaria del Sistema Armonizado de la OMA y el Nomenclador Común del Mercosur (NCM), especializado en la normativa aduanera argentina.

Tu tarea es clasificar productos de importación analizando toda la información proporcionada (descripción, composición, uso, catálogos, imágenes, fichas técnicas).

PROCESO DE ANÁLISIS:
1. Identificar la materia constitutiva principal del producto
2. Determinar su grado de elaboración
3. Establecer su función, uso y destino
4. Aplicar las Reglas Generales de Interpretación (RGI) del Sistema Armonizado
5. Determinar la posición arancelaria NCM más precisa posible

FORMATO DE RESPUESTA (JSON estricto):
{
  "sugerencias": [
    {
      "ncm": "XXXX.XX.XX.XXX",
      "confianza": "alta|media|baja",
      "capitulo": "XX — Descripción del capítulo",
      "partida": "XXXX — Descripción de la partida",
      "subpartida_1g": "XXXX.XX — Descripción (1 guión)",
      "subpartida_2g": "XXXX.XX.XX — Descripción (2 guiones)",
      "apertura_sim": "XXXX.XX.XX.XXX — Descripción SIM",
      "justificacion": "Explicación detallada de por qué se clasifica aquí",
      "rgi_aplicadas": ["RGI 1", "RGI 6"]
    }
  ],
  "informacion_faltante": ["Lista de datos que ayudarían a mejorar la clasificación"],
  "intervenciones_probables": ["ANMAT", "SENASA", "INAL", "INTI", "SEDRONAR", etc.],
  "observaciones": "Notas relevantes sobre la clasificación",
  "resumen_producto": "Descripción resumida del producto clasificado"
}

REGLAS:
- Siempre dar al menos 1 sugerencia, idealmente 2-3 opciones ordenadas por probabilidad
- El NCM debe tener formato XXXX.XX.XX.XXX (11 dígitos argentino) si es posible, sino al menos 8 dígitos
- Indicar intervenciones probables (organismos que intervienen en la importación)
- Si falta información crucial, indicarlo en "informacion_faltante"
- Responder SIEMPRE en JSON válido, sin texto adicional fuera del JSON
- Basar la clasificación en el Sistema Armonizado 2022 y NCM vigente
"""


_SYSTEM_PROMPT_EXPRESS = """Sos un experto en clasificación arancelaria del Sistema Armonizado de la OMA y el Nomenclador Común del Mercosur (NCM), especializado en la normativa aduanera argentina.

Recibís documentación del producto (fichas técnicas, catálogos, facturas, imágenes) y debés:

PASO 1 — EXTRAER atributos del producto a partir de la documentación:
- Mercadería (nombre / denominación)
- Materia constitutiva / composición
- Grado de elaboración
- Función / uso / destino
- Presentación
- Accesorios o componentes
- Marca / modelo (si aplica)

PASO 2 — CLASIFICAR aplicando RGI del SA y determinando NCM 11 dígitos (Argentina).

FORMATO DE RESPUESTA (JSON estricto):
{
  "atributos_extraidos": {
    "mercaderia": "...",
    "materia_constitutiva": "...",
    "grado_elaboracion": "...",
    "funcion_uso_destino": "...",
    "presentacion": "...",
    "accesorios": "...",
    "marca_modelo": "..."
  },
  "sugerencias": [
    {
      "ncm": "XXXX.XX.XX.XXX",
      "confianza": "alta|media|baja",
      "capitulo": "XX — Descripción",
      "partida": "XXXX — Descripción",
      "subpartida_1g": "XXXX.XX — Descripción",
      "subpartida_2g": "XXXX.XX.XX — Descripción",
      "apertura_sim": "XXXX.XX.XX.XXX — Descripción SIM",
      "justificacion": "...",
      "rgi_aplicadas": ["RGI 1", "RGI 6"]
    }
  ],
  "informacion_faltante": ["..."],
  "intervenciones_probables": ["ANMAT", "SENASA", "INAL", "INTI", ...],
  "observaciones": "...",
  "resumen_producto": "..."
}

REGLAS:
- Si un atributo no surge claramente de la documentación, dejá string vacío en ese campo de atributos_extraidos.
- Igualmente intentá clasificar con lo que tengas, indicando información faltante.
- 2-3 sugerencias ordenadas por probabilidad.
- NCM formato XXXX.XX.XX.XXX (11 dígitos) si es posible.
- Responder SIEMPRE en JSON válido, sin texto fuera del JSON.
- Basar en Sistema Armonizado 2022 y NCM vigente.
"""


def _get_anthropic_client():
    """Obtiene el cliente de Anthropic (Claude) configurado."""
    # Intentar cargar .env SIEMPRE (override=True) para asegurar que la key
    # se refresque si el archivo cambió o si Streamlit lanzó el proceso sin cargar el env.
    env_path = Path(__file__).resolve().parent.parent / ".env"
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except Exception:
        pass

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()

    # Fallback: leer directamente del archivo si aún no la tenemos
    if not api_key and env_path.exists():
        try:
            from dotenv import dotenv_values
            vals = dotenv_values(env_path)
            api_key = (vals.get("ANTHROPIC_API_KEY") or "").strip()
        except Exception:
            pass

    if not api_key:
        raise ValueError(
            "No se encontró ANTHROPIC_API_KEY. Configurala en el archivo .env "
            f"(buscado en: {env_path})"
        )

    import anthropic
    return anthropic.Anthropic(api_key=api_key)


def extraer_texto_pdf(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF (catálogo, ficha técnica, etc.)."""
    try:
        import pdfplumber
        import io
        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except Exception as e:
        logger.warning("Error extrayendo texto del PDF: %s", e)
        return ""


def clasificar_producto(
    descripcion: str,
    materia_constitutiva: str = "",
    grado_elaboracion: str = "",
    funcion_uso_destino: str = "",
    presentacion: str = "",
    accesorios: str = "",
    observaciones: str = "",
    catalogo_text: str = "",
    imagen_bytes: Optional[bytes] = None,
    imagen_mime: str = "image/jpeg",
    imagenes: Optional[list] = None,
) -> dict:
    """
    Clasifica un producto usando Claude (Anthropic) y devuelve sugerencias de NCM.

    Returns:
        Dict con sugerencias de NCM, intervenciones y observaciones.
    """
    client = _get_anthropic_client()

    # Construir el prompt del usuario
    user_parts = []
    user_parts.append("PRODUCTO A CLASIFICAR:\n")

    if descripcion:
        user_parts.append(f"**Mercadería:** {descripcion}")
    if materia_constitutiva:
        user_parts.append(f"**Materia constitutiva / composición:** {materia_constitutiva}")
    if grado_elaboracion:
        user_parts.append(f"**Grado de elaboración:** {grado_elaboracion}")
    if funcion_uso_destino:
        user_parts.append(f"**Función / Uso / Destino:** {funcion_uso_destino}")
    if presentacion:
        user_parts.append(f"**Presentación:** {presentacion}")
    if accesorios:
        user_parts.append(f"**Accesorios o componentes:** {accesorios}")
    if observaciones:
        user_parts.append(f"**Observaciones:** {observaciones}")
    if catalogo_text:
        user_parts.append(f"\n--- DOCUMENTACIÓN ADJUNTA ---\n{catalogo_text[:8000]}")

    user_prompt = "\n".join(user_parts)

    try:
        # Construir contenido (texto + imágenes si hay)
        # Backwards compat: imagen_bytes singular se agrega a la lista de imágenes
        imgs_lista = list(imagenes) if imagenes else []
        if imagen_bytes:
            imgs_lista.append((imagen_bytes, imagen_mime))

        content = []
        if imgs_lista:
            import base64
            for img_bytes, img_mime in imgs_lista:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_mime or "image/jpeg",
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    },
                })
        content.append({"type": "text", "text": user_prompt})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0.3,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )

        raw_text = response.content[0].text.strip()

        # Parsear JSON de la respuesta
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        resultado = json.loads(raw_text)
        return resultado

    except json.JSONDecodeError:
        logger.warning("Claude no devolvió JSON válido. Respuesta raw: %s", raw_text[:500])
        return {
            "sugerencias": [],
            "observaciones": f"Error parseando respuesta de IA. Respuesta: {raw_text[:500]}",
            "informacion_faltante": [],
            "intervenciones_probables": [],
            "error": "json_parse_error",
        }
    except Exception as e:
        logger.error("Error al clasificar producto con Claude: %s", e)
        return {
            "sugerencias": [],
            "observaciones": f"Error de conexión con Claude: {str(e)}",
            "informacion_faltante": [],
            "intervenciones_probables": [],
            "error": str(e),
        }


def clasificar_desde_documentos(
    catalogo_text: str = "",
    contexto_extra: str = "",
    imagenes: Optional[list] = None,
) -> dict:
    """
    Modo Express: la IA recibe documentación (PDFs ya extraídos a texto) y/o
    imágenes y extrae los atributos + clasifica en una sola pasada.

    Args:
        catalogo_text: Texto concatenado de todos los PDFs subidos.
        contexto_extra: Aclaraciones/notas del usuario.
        imagenes: Lista de tuplas (bytes, mime_type) — soporta múltiples imágenes.

    Returns:
        Dict con atributos_extraidos, sugerencias, intervenciones, etc.
    """
    client = _get_anthropic_client()

    user_parts = ["Te paso la documentación del producto a clasificar.\n"]
    if contexto_extra and contexto_extra.strip():
        user_parts.append(f"**Aclaración del usuario:** {contexto_extra.strip()}\n")
    if catalogo_text and catalogo_text.strip():
        user_parts.append("--- DOCUMENTACIÓN ADJUNTA (PDFs) ---")
        user_parts.append(catalogo_text[:25000])  # límite generoso para Modo Express

    user_prompt = "\n".join(user_parts)

    try:
        content = []
        if imagenes:
            import base64
            for img_bytes, img_mime in imagenes:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_mime or "image/jpeg",
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    },
                })
        content.append({"type": "text", "text": user_prompt})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0.3,
            system=_SYSTEM_PROMPT_EXPRESS,
            messages=[{"role": "user", "content": content}],
        )

        raw_text = response.content[0].text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        resultado = json.loads(raw_text)
        return resultado

    except json.JSONDecodeError:
        logger.warning("Claude no devolvió JSON válido. Respuesta raw: %s", raw_text[:500])
        return {
            "sugerencias": [],
            "atributos_extraidos": {},
            "observaciones": f"Error parseando respuesta de IA. Respuesta: {raw_text[:500]}",
            "informacion_faltante": [],
            "intervenciones_probables": [],
            "error": "json_parse_error",
        }
    except Exception as e:
        logger.error("Error al clasificar desde documentos con Claude: %s", e)
        return {
            "sugerencias": [],
            "atributos_extraidos": {},
            "observaciones": f"Error de conexión con Claude: {str(e)}",
            "informacion_faltante": [],
            "intervenciones_probables": [],
            "error": str(e),
        }


_SYSTEM_PROMPT_REFINAMIENTO = """Sos un experto en clasificación arancelaria del Sistema Armonizado de la OMA y el NCM, especializado en Argentina y en el uso de Tarifar como fuente de consulta.

Te paso:
1) Un PRODUCTO ya clasificado tentativamente (NCM sugerido + atributos del producto).
2) INFORMACIÓN DE TARIFAR sobre esa partida: capturas de pantalla, texto pegado de los tabs (Acuerdos, Notas, Resoluciones de clasificación, Sufijos de valor, Normas de origen Mercosur, Antecedentes históricos, Descripción Encadenada), tabla de aperturas SIM, y/o panel lateral de NCMs relacionados.

TU TAREA:
A) REFINAR LA APERTURA SIM (11 dígitos) eligiendo la sub-apertura más apropiada para ESTE producto puntual, en base a las aperturas SIM que ves listadas en Tarifar. Si la sugerencia original ya era la correcta, confirmala.
B) Si el panel de NCMs RELACIONADOS o algún antecedente sugiere una PARTIDA DISTINTA mejor, decilo explícitamente (no inventes — solo si surge de la información de Tarifar).
C) RESUMIR EN LENGUAJE CLARO los Acuerdos / Resoluciones / Antecedentes históricos que sean APLICABLES A ESTE PRODUCTO. No copies todo lo que aparece — filtrá lo que efectivamente impacta este caso. Si nada aplica, decilo.
D) Indicar normas de origen Mercosur y sufijos de valor solo si aplican al producto.
E) Alertas / riesgos / preguntas que el despachante debería revisar.

FORMATO JSON ESTRICTO:
{
  "ncm_refinado": "XXXX.XX.XX.XXX",
  "cambio_vs_original": "ninguno|apertura_sim_ajustada|partida_distinta",
  "justificacion_refinamiento": "Explicación del por qué de la apertura elegida, citando la sub-apertura específica vista en Tarifar.",
  "acuerdos_aplicables": [
    {"nombre": "...", "resumen": "Qué dice y cómo aplica a este producto", "aplicabilidad": "alta|media|baja"}
  ],
  "resoluciones_relevantes": [
    {"numero": "...", "resumen": "...", "aplicabilidad": "alta|media|baja"}
  ],
  "antecedentes_historicos": [
    {"caso": "...", "resumen": "Qué se decidió y por qué importa acá"}
  ],
  "normas_origen_mercosur": "Resumen aplicable o vacío si no aplica",
  "sufijos_valor": "Resumen aplicable o vacío si no aplica",
  "descripcion_encadenada": "Texto consolidado de la descripción encadenada si está disponible",
  "riesgos_o_alertas": ["..."],
  "preguntas_para_despachante": ["..."]
}

REGLAS:
- Si la información de Tarifar es insuficiente para refinar, devolvé `ncm_refinado` igual al sugerido original y explicalo en `justificacion_refinamiento`.
- Listas vacías [] si no hay info en esa categoría. No inventes acuerdos ni resoluciones.
- Responder SIEMPRE en JSON válido, sin texto fuera del JSON.
"""


def refinar_con_tarifar(
    ncm_sugerido: str,
    descripcion_producto: str = "",
    atributos: Optional[dict] = None,
    justificacion_original: str = "",
    tarifar_url: str = "",
    tarifar_texto: str = "",
    tarifar_imagenes: Optional[list] = None,
    scraped_data: Optional[dict] = None,
) -> dict:
    """
    Refina una clasificación NCM usando información extraída de Tarifar.

    Args:
        ncm_sugerido: NCM tentativo dado por el clasificador inicial.
        descripcion_producto: Descripción del producto (mercadería).
        atributos: Dict con atributos extraídos (materia, uso, etc).
        justificacion_original: Justificación de la sugerencia inicial.
        tarifar_url: URL de Tarifar consultada (para registro).
        tarifar_texto: Texto pegado por el usuario (tabs de Tarifar).
        tarifar_imagenes: Lista de tuplas (bytes, mime) — capturas de Tarifar.
        scraped_data: Hook opcional para futuro módulo de scraping de Tarifar.

    Returns:
        Dict con apertura SIM refinada + resumen de acuerdos/resoluciones/antecedentes.
    """
    client = _get_anthropic_client()

    user_parts = []
    user_parts.append("PRODUCTO YA CLASIFICADO TENTATIVAMENTE:\n")
    user_parts.append(f"**NCM sugerido inicial:** {ncm_sugerido}")
    if descripcion_producto:
        user_parts.append(f"**Mercadería:** {descripcion_producto}")
    if atributos:
        for k, v in atributos.items():
            if v and str(v).strip():
                user_parts.append(f"**{k.replace('_', ' ').title()}:** {v}")
    if justificacion_original:
        user_parts.append(f"\n**Justificación de la clasificación inicial:**\n{justificacion_original}")

    user_parts.append("\n--- INFORMACIÓN DE TARIFAR ---")
    if tarifar_url:
        user_parts.append(f"**URL consultada:** {tarifar_url}")
    if tarifar_texto and tarifar_texto.strip():
        user_parts.append(f"\n**Texto pegado desde Tarifar (Acuerdos / Notas / Resoluciones / Antecedentes / etc):**\n{tarifar_texto[:20000]}")
    if scraped_data:
        import json as _json
        user_parts.append(f"\n**Datos scrapeados de Tarifar (estructurados):**\n{_json.dumps(scraped_data, ensure_ascii=False, indent=2)[:15000]}")
    if tarifar_imagenes:
        user_parts.append(f"\n(Se adjuntan {len(tarifar_imagenes)} captura(s) de pantalla de Tarifar — tabla de aperturas SIM, panel lateral de NCMs relacionados, contenido de tabs, etc.)")

    user_prompt = "\n".join(user_parts)

    try:
        content = []
        if tarifar_imagenes:
            import base64
            for img_bytes, img_mime in tarifar_imagenes:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": img_mime or "image/jpeg",
                        "data": base64.b64encode(img_bytes).decode("utf-8"),
                    },
                })
        content.append({"type": "text", "text": user_prompt})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0.2,
            system=_SYSTEM_PROMPT_REFINAMIENTO,
            messages=[{"role": "user", "content": content}],
        )

        raw_text = response.content[0].text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
            raw_text = raw_text.strip()

        resultado = json.loads(raw_text)
        resultado["_meta"] = {
            "ncm_original": ncm_sugerido,
            "tarifar_url": tarifar_url,
            "tuvo_imagenes": bool(tarifar_imagenes),
            "tuvo_texto": bool(tarifar_texto and tarifar_texto.strip()),
            "tuvo_scrape": bool(scraped_data),
        }
        return resultado

    except json.JSONDecodeError:
        logger.warning("Refinamiento Tarifar: Claude no devolvió JSON válido. Raw: %s", raw_text[:500])
        return {
            "ncm_refinado": ncm_sugerido,
            "cambio_vs_original": "ninguno",
            "justificacion_refinamiento": f"Error parseando respuesta de IA. Raw: {raw_text[:500]}",
            "error": "json_parse_error",
        }
    except Exception as e:
        logger.error("Error refinando con Tarifar: %s", e)
        return {
            "ncm_refinado": ncm_sugerido,
            "cambio_vs_original": "ninguno",
            "justificacion_refinamiento": f"Error de conexión con Claude: {str(e)}",
            "error": str(e),
        }


def validar_ncm_en_matriz(ncm: str, matriz_principal, matriz_mipyme) -> dict:
    """
    Cruza un NCM con la matriz para obtener tributos y flags regulatorios.

    Returns:
        Dict con todos los datos arancelarios o None si no se encuentra.
    """
    from lector_matriz import buscar_ncm

    resultado = buscar_ncm(matriz_principal, matriz_mipyme, ncm)
    if not resultado:
        return None

    def _sf(val, default=0.0):
        try:
            v = float(val) if val is not None and str(val).strip() not in ("", "nan", "-") else default
            return v
        except (ValueError, TypeError):
            return default

    def _flag(val):
        return str(val).strip().upper() in ("SI", "S", "YES", "1")

    ficha = {
        "ncm": ncm,
        "encontrado": True,
        "tributos": {
            "die_pct": _sf(resultado.get("DIE %")),
            "aec_pct": _sf(resultado.get("AEC %")),
            "te_pct": _sf(resultado.get("TE %")),
            "dii_pct": _sf(resultado.get("DII %")),
            "iva_pct": _sf(resultado.get("IVA %", 21)),
            "iva_ad_pct": _sf(resultado.get("IVA Ad. %", 10)),
            "ganancias_pct": _sf(resultado.get("Ganancias %", 6)),
            "iibb_pct": _sf(resultado.get("IIBB %", 2.5)),
        },
        "flags": {
            "dumping": _flag(resultado.get("DUMPING")),
            "seguridad_electrica": _flag(resultado.get("SEGURIDAD ELECTRICA")),
            "bk": _flag(resultado.get("BK")),
            "mipyme": resultado.get("MiPyme_detectado", "NO") == "SI",
        },
        "posicion_sim": resultado.get("Posición SIM", resultado.get("Posicion SIM", ncm)),
    }

    # Calcular carga tributaria total estimada sobre CIF
    t = ficha["tributos"]
    base = 100  # CIF hipotético de 100
    die = base * t["die_pct"] / 100
    te = base * t["te_pct"] / 100
    base_iva = base + die + te
    iva = base_iva * t["iva_pct"] / 100
    iva_ad = base_iva * t["iva_ad_pct"] / 100
    gan = base_iva * t["ganancias_pct"] / 100
    iibb = base_iva * t["iibb_pct"] / 100

    ficha["carga_tributaria"] = {
        "irrecuperable_pct": round(t["die_pct"] + t["te_pct"], 2),
        "recuperable_pct": round(t["iva_pct"] + t["iva_ad_pct"] + t["ganancias_pct"] + t["iibb_pct"], 2),
        "total_sobre_cif_pct": round(t["die_pct"] + t["te_pct"] + t["iva_pct"] + t["iva_ad_pct"] + t["ganancias_pct"] + t["iibb_pct"], 2),
        "erogacion_por_100_cif": round(base + die + te + iva + iva_ad + gan + iibb, 2),
    }

    return ficha
