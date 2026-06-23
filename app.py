"""
CLASIFICADOR NCM — Sistema standalone de clasificación arancelaria con IA.
Independiente, sin auth ni dependencias de GP TRADELINK.

Uso:
    streamlit run app.py
"""

import datetime
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lector_matriz import cargar_matriz, buscar_ncm
from services import catalogo_cliente as cat
from services.extractor_documentos import procesar_archivos, TODAS_EXTS

# ════════════════════════════════════════════════════════════════
# SETUP
# ════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Clasificador NCM",
    page_icon="🧾",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&display=swap');
    /* ─── GP COMEX — Manual de Identidad Visual v1.0 ─── */
    :root {
        --gp-primary: #415FC3;
        --gp-primary-dark: #364E9B;
        --gp-primary-shad: #1D284E;
        --gp-primary-light: #93A8DC;
        --gp-primary-soft: #D7E5F4;
        --gp-secondary: #BD7247;
        --gp-secondary-dark: #965C3B;
        --gp-secondary-light: #DCBA93;
        --gp-secondary-soft: #F4EAD5;
        --gp-black: #1E1E1E;
        --gp-gray-50: #7C7E83;
        --gp-gray-75: #BDBFC1;
        --gp-gray-90: #E5E5E6;
        --gp-white: #F6F6F6;
    }

    html, body, [class*="css"], .stApp, .stMarkdown, .stTextInput, .stTextArea,
    .stButton button, .stSelectbox, .stRadio, .stCheckbox, .stDownloadButton button {
        font-family: 'Onest', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    h1, h2, h3, h4, h5 {
        font-family: 'Onest', sans-serif !important;
        font-weight: 700 !important;
        color: var(--gp-primary-shad);
        letter-spacing: -0.01em;
    }

    /* Header de marca */
    .gp-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1.2rem 1.5rem;
        background: linear-gradient(135deg, var(--gp-primary) 0%, var(--gp-primary-dark) 100%);
        border-radius: 0.75rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(65, 95, 195, 0.18);
    }
    .gp-header-icon {
        width: 48px; height: 48px;
        background: white;
        color: var(--gp-primary);
        border-radius: 0.5rem;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1.15rem;
        letter-spacing: -0.02em;
        flex-shrink: 0;
    }
    .gp-header-text { display: flex; flex-direction: column; }
    .gp-brand {
        color: white;
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1;
        letter-spacing: 0.04em;
    }
    .gp-brand-sub {
        color: var(--gp-primary-soft);
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.18em;
        margin-top: 0.35rem;
    }
    .gp-page-title {
        font-size: 1.15rem;
        color: var(--gp-black);
        font-weight: 600;
        margin: 1.2rem 0 0.2rem 0;
    }
    .gp-page-sub {
        color: var(--gp-gray-50);
        font-size: 0.9rem;
        margin-bottom: 1.2rem;
    }

    /* Disclaimer global */
    .global-disclaimer {
        background: var(--gp-secondary-soft);
        border-left: 4px solid var(--gp-secondary);
        color: var(--gp-secondary-dark);
        padding: 0.7rem 1rem;
        border-radius: 0.4rem;
        margin: 0.5rem 0 1.3rem 0;
        font-size: 0.88rem;
        font-weight: 500;
    }
    .global-disclaimer b { color: var(--gp-secondary-shad, #38271F); font-weight: 700; }

    /* Match box (catálogo cliente) */
    .match-box {
        border-left: 4px solid var(--gp-primary);
        background: var(--gp-primary-soft);
        padding: 0.75rem 1rem;
        border-radius: 0.4rem;
        margin: 0.5rem 0;
    }

    /* Botones primary */
    .stButton button[kind="primary"], .stDownloadButton button[kind="primary"],
    .stFormSubmitButton button[kind="primaryFormSubmit"] {
        background: var(--gp-primary) !important;
        border-color: var(--gp-primary) !important;
        color: white !important;
        font-weight: 600 !important;
        transition: background 0.15s ease;
    }
    .stButton button[kind="primary"]:hover, .stDownloadButton button[kind="primary"]:hover,
    .stFormSubmitButton button[kind="primaryFormSubmit"]:hover {
        background: var(--gp-primary-dark) !important;
        border-color: var(--gp-primary-dark) !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        border-bottom: 2px solid var(--gp-gray-90);
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600 !important;
        color: var(--gp-gray-50) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--gp-primary) !important;
    }

    /* Métricas */
    [data-testid="stMetricValue"] {
        color: var(--gp-primary-shad);
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: var(--gp-gray-50);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.72rem;
    }

    /* Expanders */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        color: var(--gp-primary-shad) !important;
    }

    /* Footer minimal */
    footer { display: none !important; }
    </style>
    <div class="gp-header">
        <div class="gp-header-icon">GP</div>
        <div class="gp-header-text">
            <span class="gp-brand">GPCOMEX</span>
            <span class="gp-brand-sub">Global Partner · Clasificador Arancelario NCM</span>
        </div>
    </div>
    <div class="global-disclaimer">
        ⚠️ <b>IMPORTANTE</b> — Para chequeo final hablá con tu despachante de aduana o clasificador.
        El sistema sugiere; la responsabilidad de la clasificación es del operador.
    </div>
    """,
    unsafe_allow_html=True,
)

ss = st.session_state

# ── Matriz NCM ──────────────────────────────────────────────────
_MATRIZ_PATH = ROOT / "data" / "matriz_ncm.xlsx"
_MATRIZ_DISPONIBLE = False

if "matriz_principal" not in ss:
    try:
        ss["matriz_principal"], ss["matriz_mipyme"] = cargar_matriz(str(_MATRIZ_PATH))
        _MATRIZ_DISPONIBLE = True
    except Exception as e:
        st.error(f"Error cargando matriz NCM ({_MATRIZ_PATH}): {e}")
else:
    _MATRIZ_DISPONIBLE = True

_matriz_p = ss.get("matriz_principal")
_matriz_m = ss.get("matriz_mipyme")

# ── Fichas guardadas ────────────────────────────────────────────
_FICHAS_FILE = ROOT / "data" / "persistencia" / "fichas_arancelarias.json"

if "fichas_arancelarias" not in ss:
    if _FICHAS_FILE.exists():
        try:
            ss["fichas_arancelarias"] = json.loads(_FICHAS_FILE.read_text())
        except Exception:
            ss["fichas_arancelarias"] = {}
    else:
        ss["fichas_arancelarias"] = {}


def _guardar_fichas():
    _FICHAS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _FICHAS_FILE.write_text(
        json.dumps(ss["fichas_arancelarias"], indent=2, ensure_ascii=False, default=str)
    )


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _renderizar_matches_catalogo(matches: list):
    """Renderiza el panel de coincidencias con el catálogo del cliente."""
    if not matches:
        return

    st.markdown("### 🎯 Coincidencias en tu catálogo")
    st.caption(
        "Antes de la sugerencia de la IA: encontré productos similares "
        "que **vos ya clasificaste** previamente."
    )

    for m in matches:
        prod = m["producto"]
        sim_pct = int(m["similitud"] * 100)
        color = "🟢" if sim_pct >= 70 else ("🟡" if sim_pct >= 50 else "🔵")
        st.markdown(
            f"""
            <div class="match-box">
                <b>{color} {sim_pct}% similar</b> — NCM <b>{prod.get('ncm', '?')}</b><br>
                <span style="color:#374151;">{prod.get('descripcion', '(sin descripción)')}</span>
                <span style="color:#6b7280; font-size:0.85rem;">
                    {' · SKU: ' + prod['sku'] if prod.get('sku') else ''}
                    {' · ' + prod['marca'] if prod.get('marca') else ''}
                    {' · ' + prod['modelo'] if prod.get('modelo') else ''}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _renderizar_sugerencia_ia(sug: dict, idx: int, mercaderia_label: str):
    """Renderiza una sugerencia de la IA con el cruce contra la matriz."""
    _conf = sug.get("confianza", "media")
    _conf_icon = {"alta": "🟢", "media": "🟡", "baja": "🔴"}.get(_conf, "⚪")

    with st.expander(
        f"{_conf_icon} **{sug.get('ncm', '?')}** — "
        f"Confianza: {_conf.upper()} — "
        f"{sug.get('apertura_sim', sug.get('subpartida_2g', ''))}",
        expanded=(idx == 0),
    ):
        _sc1, _sc2 = st.columns([3, 2])
        with _sc1:
            st.markdown("**Jerarquía arancelaria:**")
            if sug.get("capitulo"):
                st.write(f"📘 Capítulo: {sug['capitulo']}")
            if sug.get("partida"):
                st.write(f"📗 Partida: {sug['partida']}")
            if sug.get("subpartida_1g"):
                st.write(f"📙 Subpartida (1g): {sug['subpartida_1g']}")
            if sug.get("subpartida_2g"):
                st.write(f"📕 Subpartida (2g): {sug['subpartida_2g']}")
            if sug.get("apertura_sim"):
                st.write(f"📎 Apertura SIM: {sug['apertura_sim']}")

            st.divider()
            st.markdown("**Justificación:**")
            st.write(sug.get("justificacion", "—"))

            if sug.get("rgi_aplicadas"):
                st.write(f"**RGI aplicadas:** {', '.join(sug['rgi_aplicadas'])}")

        with _sc2:
            _ncm_sug = sug.get("ncm", "")
            if _MATRIZ_DISPONIBLE and _ncm_sug:
                from services.clasificador_ncm import validar_ncm_en_matriz
                _ficha = validar_ncm_en_matriz(_ncm_sug, _matriz_p, _matriz_m)

                if _ficha:
                    _t = _ficha["tributos"]
                    st.markdown("**Tributos (matriz NCM):**")
                    _trib_df = pd.DataFrame({
                        "Concepto": ["DIE", "AEC", "TE", "IVA", "IVA Ad.", "Ganancias", "IIBB"],
                        "%": [
                            _t["die_pct"], _t["aec_pct"], _t["te_pct"],
                            _t["iva_pct"], _t["iva_ad_pct"], _t["ganancias_pct"], _t["iibb_pct"],
                        ],
                        "Tipo": [
                            "Irrecup.", "Ref. Mercosur ℹ️", "Irrecup.",
                            "Recup.", "Recup.", "Recup.", "Recup.",
                        ],
                    })
                    st.dataframe(_trib_df, use_container_width=True, hide_index=True)
                    st.caption("ℹ️ AEC = Arancel Externo Común (referencia normativa Mercosur). **No se suma al DIE ni impacta en ningún cálculo.**")

                    _ct = _ficha["carga_tributaria"]
                    st.metric("CARGA TOTAL SOBRE CIF", f"{_ct['total_sobre_cif_pct']:.1f}%")
                    _ci, _cr = st.columns(2)
                    _ci.metric(
                        "No recuperable",
                        f"{_ct['irrecuperable_pct']:.1f}%",
                        help="Sobre CIF — DIE + TE. Costo real definitivo.",
                    )
                    _cr.metric(
                        "Recuperable / crédito fiscal",
                        f"{_ct['recuperable_pct']:.1f}%",
                        help="Sobre base IVA (CIF + Derechos + Tasas) — IVA + IVA Ad. + Ganancias + IIBB. Salida de caja transitoria.",
                    )

                    _flags = _ficha["flags"]
                    _flag_items = []
                    if _flags["dumping"]:
                        _flag_items.append("⚠️ DUMPING")
                    if _flags["seguridad_electrica"]:
                        _flag_items.append("⚡ SEG. ELÉCTRICA")
                    if _flags["bk"]:
                        _flag_items.append("🏭 BK")
                    if _flags["mipyme"]:
                        _flag_items.append("✅ MiPyme")
                    if _flag_items:
                        st.markdown("**Flags regulatorios:**")
                        st.write(" · ".join(_flag_items))

                    if st.button(
                        "✅ Seleccionar esta partida",
                        key=f"hallada_{idx}",
                        use_container_width=True,
                        type="primary",
                        help="Validar esta clasificación. Se crea una carpeta con descripción + documentos.",
                    ):
                        ss[f"_show_form_hallada_{idx}"] = True

                    # Formulario modal de validación (descripción fina + observaciones)
                    if ss.get(f"_show_form_hallada_{idx}"):
                        st.markdown("---")
                        st.markdown(f"#### ✅ Confirmar partida seleccionada — **{_ncm_sug}**")
                        st.caption(
                            "Al confirmar, se crea una carpeta con esta partida + tu descripción "
                            "+ los archivos que subiste. Queda en **Fichas guardadas** y se suma al catálogo."
                        )

                        _archivos_pend = ss.get("archivos_pendientes", []) or []
                        if _archivos_pend:
                            st.markdown(
                                "📎 **Documentos que se guardarán en la carpeta:** "
                                + ", ".join(f"`{a['nombre']}`" for a in _archivos_pend)
                            )

                        with st.form(f"form_hallada_{idx}"):
                            _atrs_h = ss.get("resultado_ia", {}).get("atributos_extraidos", {}) or {}
                            _desc_default = (
                                mercaderia_label
                                or _atrs_h.get("mercaderia", "")
                                or ss.get("resultado_ia", {}).get("resumen_producto", "")
                            )

                            _h_nombre = st.text_input(
                                "🏷️ Nombre de la partida (cómo querés que aparezca en tu carpeta) *",
                                value=_desc_default,
                                placeholder="Ej: Cable HDMI blindado 2m — Marca XYZ",
                                help="Es el nombre con el que vas a encontrar esta partida después.",
                            )
                            _h_desc_fina = st.text_area(
                                "📝 Descripción detallada del producto *",
                                placeholder=(
                                    "Escribí con todo detalle: composición, dimensiones, marca, modelo, "
                                    "presentación, uso específico, características técnicas. "
                                    "Cuanto más detalle pongas, mejor te servirá para el despachante "
                                    "y para futuras coincidencias."
                                ),
                                height=220,
                            )

                            _hc1, _hc2 = st.columns(2)
                            with _hc1:
                                _h_sku = st.text_input(
                                    "SKU / Código interno (opcional)",
                                    placeholder="Tu código interno",
                                )
                            with _hc2:
                                _h_marca = st.text_input(
                                    "Marca (opcional)",
                                    value=_atrs_h.get("marca_modelo", "").split("/")[0].strip() if _atrs_h.get("marca_modelo") else "",
                                )

                            _h_obs = st.text_area(
                                "Observaciones / notas para el despachante (opcional)",
                                placeholder=(
                                    "Particularidades, certificaciones requeridas, "
                                    "preguntas pendientes para el despachante, etc."
                                ),
                                height=100,
                            )

                            _fcol1, _fcol2 = st.columns(2)
                            with _fcol1:
                                _btn_confirmar = st.form_submit_button(
                                    "✅ Confirmar y crear carpeta",
                                    type="primary",
                                    use_container_width=True,
                                )
                            with _fcol2:
                                _btn_cancelar = st.form_submit_button(
                                    "Cancelar",
                                    use_container_width=True,
                                )

                            if _btn_cancelar:
                                ss[f"_show_form_hallada_{idx}"] = False
                                st.rerun()

                            if _btn_confirmar:
                                if not _h_nombre.strip() or not _h_desc_fina.strip():
                                    st.error("El nombre y la descripción detallada son obligatorios.")
                                else:
                                    import re as _re_mod
                                    _slug = _re_mod.sub(r"[^a-zA-Z0-9_-]+", "_", _h_nombre.strip().lower())[:50]
                                    _fid = f"{_ncm_sug.replace('.', '')}_{_slug}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                                    _carpeta = ROOT / "data" / "persistencia" / "partidas_halladas" / _fid
                                    _carpeta_docs = _carpeta / "documentos"
                                    _carpeta_docs.mkdir(parents=True, exist_ok=True)

                                    _archivos_guardados = []
                                    for _a in _archivos_pend:
                                        try:
                                            _ruta = _carpeta_docs / _a["nombre"]
                                            _ruta.write_bytes(_a["bytes"])
                                            _archivos_guardados.append(_a["nombre"])
                                        except Exception as e:
                                            st.warning(f"No se pudo guardar {_a['nombre']}: {e}")

                                    # Materializar docs por tema del refinamiento Tarifar
                                    _docs_tema_save = ss.get(f"_tarifar_docs_{idx}") or {}
                                    _docs_persistidos = {}
                                    for _slug_t, _data_t in _docs_tema_save.items():
                                        _carp_t = _carpeta / "documentacion" / _slug_t
                                        _carp_t.mkdir(parents=True, exist_ok=True)
                                        _archivos_t = []
                                        if _data_t.get("texto_pegado"):
                                            try:
                                                (_carp_t / "notas.txt").write_text(
                                                    _data_t["texto_pegado"], encoding="utf-8"
                                                )
                                            except Exception as e:
                                                st.warning(f"No se pudo guardar notas de {_slug_t}: {e}")
                                        for _arch in _data_t.get("archivos", []):
                                            try:
                                                _ruta_arch = _carp_t / _arch["nombre"]
                                                if _ruta_arch.exists():
                                                    _stem = _ruta_arch.stem
                                                    _suf = _ruta_arch.suffix
                                                    _ts = datetime.datetime.now().strftime("%H%M%S")
                                                    _ruta_arch = _carp_t / f"{_stem}_{_ts}{_suf}"
                                                _ruta_arch.write_bytes(_arch["bytes"])
                                                _archivos_t.append(_ruta_arch.name)
                                            except Exception as e:
                                                st.warning(f"No se pudo guardar {_arch.get('nombre','?')}: {e}")
                                        _docs_persistidos[_slug_t] = {
                                            "label": _data_t.get("label", _slug_t),
                                            "archivos": _archivos_t,
                                            "tiene_notas": bool(_data_t.get("texto_pegado")),
                                        }

                                    _ficha_hallada = {
                                        "id": _fid,
                                        "ncm": _ncm_sug,
                                        "nombre_partida": _h_nombre.strip(),
                                        "mercaderia": mercaderia_label,
                                        "descripcion_fina": _h_desc_fina.strip(),
                                        "sku": _h_sku.strip(),
                                        "marca": _h_marca.strip(),
                                        "observaciones_cliente": _h_obs.strip(),
                                        "confianza": _conf,
                                        "justificacion": sug.get("justificacion", ""),
                                        "rgi_aplicadas": sug.get("rgi_aplicadas", []),
                                        "capitulo": sug.get("capitulo", ""),
                                        "partida": sug.get("partida", ""),
                                        "subpartida_1g": sug.get("subpartida_1g", ""),
                                        "subpartida_2g": sug.get("subpartida_2g", ""),
                                        "apertura_sim": sug.get("apertura_sim", ""),
                                        "tributos": _t,
                                        "flags": _flags,
                                        "carga_tributaria": _ct,
                                        "intervenciones": ss.get("resultado_ia", {}).get("intervenciones_probables", []),
                                        "fecha": datetime.datetime.now().isoformat(),
                                        "validada": True,
                                        "carpeta": str(_carpeta.relative_to(ROOT)),
                                        "archivos": _archivos_guardados,
                                        "refinamiento_tarifar": ss.get(f"_refinamiento_{idx}"),
                                        "documentacion_por_tema": _docs_persistidos,
                                    }

                                    (_carpeta / "ficha.json").write_text(
                                        json.dumps(_ficha_hallada, indent=2, ensure_ascii=False, default=str)
                                    )

                                    ss["fichas_arancelarias"][_fid] = _ficha_hallada
                                    _guardar_fichas()

                                    _atrs_h2 = ss.get("resultado_ia", {}).get("atributos_extraidos", {}) or {}
                                    try:
                                        cat.agregar_producto({
                                            "descripcion": _h_desc_fina.strip(),
                                            "ncm": _ncm_sug,
                                            "sku": _h_sku.strip(),
                                            "marca": _h_marca.strip() or _atrs_h2.get("marca_modelo", "").split("/")[0].strip(),
                                            "materia_constitutiva": _atrs_h2.get("materia_constitutiva", ""),
                                            "funcion_uso_destino": _atrs_h2.get("funcion_uso_destino", ""),
                                            "presentacion": _atrs_h2.get("presentacion", ""),
                                            "observaciones": _h_obs.strip() or sug.get("justificacion", "")[:300],
                                        })
                                    except Exception as e:
                                        st.warning(f"No se pudo agregar al catálogo: {e}")

                                    ss[f"_show_form_hallada_{idx}"] = False
                                    st.success(
                                        f"✅ Carpeta creada: **{_h_nombre.strip()}** ({_ncm_sug}). "
                                        f"{len(_archivos_guardados)} documento(s) guardado(s). "
                                        f"Ya está en Fichas guardadas y en tu catálogo."
                                    )
                                    st.rerun()
                else:
                    st.warning(f"NCM {_ncm_sug} no encontrado en la matriz local.")

        # ─────────────────────────────────────────────────────────────────
        # 🔬 REFINAR CON TARIFAR (full-width, debajo de las columnas)
        # ─────────────────────────────────────────────────────────────────
        st.divider()
        _ref_toggle = st.toggle(
            "🔬 Refinar esta partida con información de Tarifar",
            key=f"_tarifar_toggle_{idx}",
            help=(
                "Adjuntá capturas y/o pegá texto de Tarifar (tabla de aperturas SIM, "
                "Acuerdos, Notas, Resoluciones, Antecedentes, NCMs relacionados, etc.). "
                "Claude vuelve a analizar para afinar la apertura SIM (11 dígitos) y resumir "
                "lo aplicable a tu producto puntual."
            ),
        )

        if _ref_toggle:
            _TEMAS_REF = [
                ("acuerdos", "📄 Acuerdos"),
                ("notas", "📝 Notas"),
                ("resoluciones", "⚖️ Resoluciones"),
                ("sufijos", "💲 Sufijos"),
                ("origen_mercosur", "🌎 Origen MS"),
                ("antecedentes", "📚 Antecedentes"),
                ("desc_encadenada", "📜 Desc. encadenada"),
            ]

            _tarifar_url = st.text_input(
                "🔗 URL de Tarifar consultada (opcional, solo para registro)",
                key=f"_tarifar_url_{idx}",
                placeholder="https://app.tarifar.com/web/nomenclatura/results/...",
            )

            st.caption(
                "Adjuntá por tema lo que tengas (PDF, capturas, TXT, texto pegado). "
                "Claude procesa todo etiquetado por tema y al confirmar la partida queda "
                "guardado automáticamente en `documentacion/{tema}/`."
            )

            _tabs_ref = st.tabs([_lbl for _, _lbl in _TEMAS_REF])
            for _i_t, (_slug, _lbl) in enumerate(_TEMAS_REF):
                with _tabs_ref[_i_t]:
                    st.file_uploader(
                        "Archivos (PDF, capturas, TXT)",
                        type=["pdf", "png", "jpg", "jpeg", "webp", "txt"],
                        accept_multiple_files=True,
                        key=f"_ref_archs_{idx}_{_slug}",
                    )
                    st.text_area(
                        "Texto pegado",
                        key=f"_ref_texto_{idx}_{_slug}",
                        height=130,
                        placeholder=f"Pegá contenido relativo a '{_lbl}' (de Tarifar u otras fuentes).",
                    )

            # Verificar si hay contenido en algún tema
            _hay_contenido = False
            for _slug, _ in _TEMAS_REF:
                if ss.get(f"_ref_archs_{idx}_{_slug}") or (ss.get(f"_ref_texto_{idx}_{_slug}") or "").strip():
                    _hay_contenido = True
                    break

            _btn_refinar = st.button(
                "🔬 Refinar con esta información",
                key=f"_btn_refinar_{idx}",
                type="primary",
                use_container_width=True,
                disabled=not _hay_contenido,
                help=(
                    "Adjuntá archivos o pegá texto en al menos un tema."
                    if not _hay_contenido else None
                ),
            )

            if _btn_refinar:
                from services.clasificador_ncm import refinar_con_tarifar, extraer_texto_pdf

                _docs_por_tema = {}      # para persistir al guardar la ficha
                _texto_consolidado = []  # para enviar a Claude
                _imagenes_consolidado = []

                for _slug, _lbl in _TEMAS_REF:
                    _texto_pegado = (ss.get(f"_ref_texto_{idx}_{_slug}") or "").strip()
                    _archs_widget = ss.get(f"_ref_archs_{idx}_{_slug}") or []

                    _archivos_proc = []
                    _texto_tema_partes = []
                    if _texto_pegado:
                        _texto_tema_partes.append(_texto_pegado)

                    for _f in _archs_widget:
                        try:
                            _b = _f.read()
                            _mime = (_f.type or "").lower()
                            _nombre = _f.name
                            _nl = _nombre.lower()
                            _arch_d = {"nombre": _nombre, "mime": _mime, "bytes": _b}

                            if _mime.startswith("image/") or _nl.endswith((".png", ".jpg", ".jpeg", ".webp")):
                                _imagenes_consolidado.append((_b, _mime or "image/jpeg"))
                            elif _mime == "application/pdf" or _nl.endswith(".pdf"):
                                _txt = extraer_texto_pdf(_b)
                                if _txt:
                                    _arch_d["texto_extraido"] = _txt
                                    _texto_tema_partes.append(f"--- PDF: {_nombre} ---\n{_txt}")
                            elif _nl.endswith(".txt") or _mime.startswith("text/"):
                                try:
                                    _txt = _b.decode("utf-8", errors="ignore")
                                    _arch_d["texto_extraido"] = _txt
                                    if _txt:
                                        _texto_tema_partes.append(f"--- TXT: {_nombre} ---\n{_txt}")
                                except Exception:
                                    pass

                            _archivos_proc.append(_arch_d)
                        except Exception as e:
                            st.warning(f"No se pudo procesar {_f.name}: {e}")

                    if _texto_pegado or _archivos_proc:
                        _docs_por_tema[_slug] = {
                            "label": _lbl,
                            "texto_pegado": _texto_pegado,
                            "archivos": _archivos_proc,
                        }
                        if _texto_tema_partes:
                            _texto_consolidado.append(
                                f"\n\n=== TEMA: {_lbl} ({_slug}) ===\n" + "\n".join(_texto_tema_partes)
                            )

                _texto_final = "".join(_texto_consolidado).strip()

                if not (_texto_final or _imagenes_consolidado):
                    st.error("No quedó información para refinar.")
                else:
                    # Cachear docs para persistir cuando el usuario seleccione la partida
                    ss[f"_tarifar_docs_{idx}"] = _docs_por_tema

                    with st.spinner("Refinando con Claude..."):
                        _atrs_ref = ss.get("resultado_ia", {}).get("atributos_extraidos", {}) or {}
                        _refinado = refinar_con_tarifar(
                            ncm_sugerido=sug.get("ncm", ""),
                            descripcion_producto=mercaderia_label or _atrs_ref.get("mercaderia", ""),
                            atributos=_atrs_ref,
                            justificacion_original=sug.get("justificacion", ""),
                            tarifar_url=(_tarifar_url or "").strip(),
                            tarifar_texto=_texto_final,
                            tarifar_imagenes=_imagenes_consolidado or None,
                        )
                        ss[f"_refinamiento_{idx}"] = _refinado
                        st.rerun()

            # Render del resultado refinado (persistente entre reruns)
            _ref_res = ss.get(f"_refinamiento_{idx}")
            if _ref_res:
                st.markdown("---")
                if _ref_res.get("error"):
                    st.error(f"Error en refinamiento: {_ref_res.get('justificacion_refinamiento', _ref_res['error'])}")
                else:
                    _ncm_ref = _ref_res.get("ncm_refinado", "")
                    _cambio = _ref_res.get("cambio_vs_original", "ninguno")
                    _cambio_lbl = {
                        "ninguno": "✅ La apertura sugerida original es correcta",
                        "apertura_sim_ajustada": "🔧 Apertura SIM ajustada según Tarifar",
                        "partida_distinta": "⚠️ Tarifar sugiere una partida distinta",
                    }.get(_cambio, _cambio)

                    st.markdown(f"### 🔬 Resultado refinado: `{_ncm_ref}`")
                    st.info(_cambio_lbl)

                    if _ref_res.get("justificacion_refinamiento"):
                        st.markdown("**Justificación del refinamiento:**")
                        st.write(_ref_res["justificacion_refinamiento"])

                    _acuerdos = _ref_res.get("acuerdos_aplicables") or []
                    if _acuerdos:
                        st.markdown("**📄 Acuerdos aplicables:**")
                        for _a in _acuerdos:
                            _ap = _a.get("aplicabilidad", "")
                            _ap_icon = {"alta": "🟢", "media": "🟡", "baja": "🔴"}.get(_ap, "⚪")
                            st.markdown(f"- {_ap_icon} **{_a.get('nombre', '?')}** — {_a.get('resumen', '')}")

                    _resoluciones = _ref_res.get("resoluciones_relevantes") or []
                    if _resoluciones:
                        st.markdown("**⚖️ Resoluciones de clasificación:**")
                        for _r in _resoluciones:
                            _ap = _r.get("aplicabilidad", "")
                            _ap_icon = {"alta": "🟢", "media": "🟡", "baja": "🔴"}.get(_ap, "⚪")
                            st.markdown(f"- {_ap_icon} **{_r.get('numero', '?')}** — {_r.get('resumen', '')}")

                    _antec = _ref_res.get("antecedentes_historicos") or []
                    if _antec:
                        st.markdown("**📚 Antecedentes históricos relevantes:**")
                        for _h in _antec:
                            st.markdown(f"- **{_h.get('caso', '?')}** — {_h.get('resumen', '')}")

                    _normas = _ref_res.get("normas_origen_mercosur")
                    if _normas and str(_normas).strip():
                        st.markdown(f"**🌎 Normas de origen Mercosur:** {_normas}")

                    _sufijos = _ref_res.get("sufijos_valor")
                    if _sufijos and str(_sufijos).strip():
                        st.markdown(f"**💲 Sufijos de valor:** {_sufijos}")

                    _desc_enc = _ref_res.get("descripcion_encadenada")
                    if _desc_enc and str(_desc_enc).strip():
                        with st.expander("📜 Descripción encadenada"):
                            st.write(_desc_enc)

                    _alertas = _ref_res.get("riesgos_o_alertas") or []
                    if _alertas:
                        st.markdown("**⚠️ Alertas / riesgos:**")
                        for _al in _alertas:
                            st.markdown(f"- {_al}")

                    _preguntas = _ref_res.get("preguntas_para_despachante") or []
                    if _preguntas:
                        st.markdown("**❓ Preguntas para el despachante:**")
                        for _p in _preguntas:
                            st.markdown(f"- {_p}")

                    # Botón para adoptar el NCM refinado en la sugerencia
                    if _ncm_ref and _ncm_ref != sug.get("ncm"):
                        _bc1, _bc2 = st.columns(2)
                        with _bc1:
                            if st.button(
                                f"📌 Adoptar NCM refinado ({_ncm_ref})",
                                key=f"_adoptar_ref_{idx}",
                                type="primary",
                                use_container_width=True,
                                help="Reemplaza el NCM sugerido por el refinado. Al confirmar la partida se guardará el refinado.",
                            ):
                                sug["ncm"] = _ncm_ref
                                sug["apertura_sim"] = f"{_ncm_ref} — refinado con Tarifar"
                                sug["_refinamiento_aplicado"] = True
                                st.rerun()
                        with _bc2:
                            if st.button(
                                "🗑️ Descartar refinamiento",
                                key=f"_descartar_ref_{idx}",
                                use_container_width=True,
                            ):
                                ss.pop(f"_refinamiento_{idx}", None)
                                st.rerun()
                    else:
                        if st.button(
                            "🗑️ Descartar refinamiento",
                            key=f"_descartar_ref_solo_{idx}",
                            use_container_width=True,
                        ):
                            ss.pop(f"_refinamiento_{idx}", None)
                            st.rerun()


def _renderizar_resultado_ia(res: dict, mercaderia_label: str, descripcion_para_match: str):
    """Renderiza atributos extraídos (si los hay) + matches del catálogo + sugerencias IA."""
    if res.get("error"):
        st.error(f"Error: {res.get('observaciones', res['error'])}")
        return

    sugerencias = res.get("sugerencias", [])
    atributos = res.get("atributos_extraidos") or {}

    # 1) Atributos extraídos (solo Modo Express)
    if atributos and any(v for v in atributos.values()):
        st.divider()
        st.markdown("### 📋 Atributos extraídos de la documentación")
        st.caption("Esto es lo que la IA entendió del producto a partir de los documentos.")

        _ac1, _ac2 = st.columns(2)
        with _ac1:
            if atributos.get("mercaderia"):
                st.write(f"**Mercadería:** {atributos['mercaderia']}")
            if atributos.get("materia_constitutiva"):
                st.write(f"**Materia:** {atributos['materia_constitutiva']}")
            if atributos.get("grado_elaboracion"):
                st.write(f"**Grado de elaboración:** {atributos['grado_elaboracion']}")
            if atributos.get("marca_modelo"):
                st.write(f"**Marca/Modelo:** {atributos['marca_modelo']}")
        with _ac2:
            if atributos.get("funcion_uso_destino"):
                st.write(f"**Uso/Destino:** {atributos['funcion_uso_destino']}")
            if atributos.get("presentacion"):
                st.write(f"**Presentación:** {atributos['presentacion']}")
            if atributos.get("accesorios"):
                st.write(f"**Accesorios:** {atributos['accesorios']}")

    # 2) Cruce contra catálogo del cliente
    catalogo = cat.cargar_catalogo()
    if catalogo and descripcion_para_match:
        # Para el match usamos descripción + atributos extraídos (si los hay)
        texto_match = descripcion_para_match
        for k in ("materia_constitutiva", "funcion_uso_destino", "presentacion"):
            v = atributos.get(k)
            if v:
                texto_match += " " + v
        matches = cat.buscar_similares(texto_match, catalogo, umbral=0.30, top_k=5)
        if matches:
            st.divider()
            _renderizar_matches_catalogo(matches)

    # 3) Sugerencias de la IA
    if sugerencias:
        st.divider()
        st.markdown("### 🤖 Sugerencias de la IA")
        if res.get("resumen_producto"):
            st.info(f"**Producto:** {res['resumen_producto']}")
        for idx, sug in enumerate(sugerencias):
            _renderizar_sugerencia_ia(sug, idx, mercaderia_label)

    # 4) Información complementaria
    _faltante = res.get("informacion_faltante", [])
    if _faltante:
        st.divider()
        st.markdown("### ℹ️ Información que mejoraría la clasificación")
        for _f in _faltante:
            st.write(f"• {_f}")

    _interv = res.get("intervenciones_probables", [])
    if _interv:
        st.markdown("### 🏛️ Intervenciones probables")
        st.write(", ".join(_interv))
        st.caption(
            "Estos organismos podrían requerir certificados o autorizaciones "
            "para importar este producto."
        )

    if res.get("observaciones"):
        st.info(f"**Observaciones:** {res['observaciones']}")

    # 5) Feedback / corrección del usuario
    st.divider()
    st.markdown("### 🧠 ¿Conocés el NCM correcto de este producto?")
    st.caption(
        "Ayudanos a mejorar el motor. Si vos o tu despachante ya lo clasificaron, "
        "indicá la posición exacta. Se guarda como partida hallada en tu base."
    )
    _fb1, _fb2, _fb3 = st.columns([3, 2, 1])
    with _fb1:
        _ncm_correcto = st.text_input(
            "NCM correcto",
            placeholder="Ej: 8471.30.12.110",
            key="ncm_correcto_feedback",
            label_visibility="collapsed",
        )
    with _fb2:
        _desc_correcta = st.text_input(
            "Descripción fina (opcional)",
            placeholder="Descripción comercial precisa",
            key="desc_correcta_feedback",
            label_visibility="collapsed",
        )
    with _fb3:
        _btn_fb = st.button("Enviar", type="primary", use_container_width=True, key="btn_fb_ncm")

    if _btn_fb:
        if not _ncm_correcto.strip():
            st.warning("Indicá el NCM correcto.")
        else:
            _atrs_fb = res.get("atributos_extraidos", {}) or {}
            _ncm_c = _ncm_correcto.strip()
            _ficha_fb = {
                "ncm": _ncm_c,
                "mercaderia": mercaderia_label,
                "descripcion_fina": (_desc_correcta.strip() or mercaderia_label
                                    or _atrs_fb.get("mercaderia", "")
                                    or res.get("resumen_producto", "")),
                "origen": "feedback_usuario",
                "ncm_sugerido_ia": (res.get("sugerencias", [{}])[0].get("ncm")
                                   if res.get("sugerencias") else None),
                "fecha": datetime.datetime.now().isoformat(),
                "validada": True,
            }
            # Si el NCM corregido existe en la matriz, agregamos los tributos
            if _MATRIZ_DISPONIBLE:
                from services.clasificador_ncm import validar_ncm_en_matriz
                _fc = validar_ncm_en_matriz(_ncm_c, _matriz_p, _matriz_m)
                if _fc:
                    _ficha_fb["tributos"] = _fc["tributos"]
                    _ficha_fb["flags"] = _fc["flags"]
                    _ficha_fb["carga_tributaria"] = _fc["carga_tributaria"]
            _fid = f"hallada_{_ncm_c}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            ss["fichas_arancelarias"][_fid] = _ficha_fb
            _guardar_fichas()
            try:
                cat.agregar_producto({
                    "descripcion": _ficha_fb["descripcion_fina"],
                    "ncm": _ncm_c,
                    "materia_constitutiva": _atrs_fb.get("materia_constitutiva", ""),
                    "funcion_uso_destino": _atrs_fb.get("funcion_uso_destino", ""),
                    "presentacion": _atrs_fb.get("presentacion", ""),
                    "observaciones": "Aportado por usuario tras clasificación IA.",
                })
            except Exception as e:
                st.warning(f"Guardado pero no se pudo agregar al catálogo: {e}")
            st.success(
                f"✅ Gracias. NCM **{_ncm_c}** guardado como partida hallada y agregado a tu catálogo."
            )


# ════════════════════════════════════════════════════════════════
# TABS
# ════════════════════════════════════════════════════════════════

tab_clasificador, tab_consulta, tab_catalogo, tab_fichas = st.tabs([
    "🤖 Clasificador IA",
    "🔍 Consulta NCM",
    "📚 Mi catálogo",
    "📋 Fichas guardadas",
])


# ════════════════════════════════════════════════════════════════
# TAB 1 — CLASIFICADOR IA
# ════════════════════════════════════════════════════════════════

with tab_clasificador:
    st.subheader("Clasificación Arancelaria con IA")

    with st.expander("ℹ️ ¿Qué info pedirle al cliente para clasificar?", expanded=False):
        st.caption(
            "Cuanta más información tengas del producto, más precisa será la clasificación. "
            "Pedile al cliente/proveedor estos datos:"
        )
        _plantilla = pd.DataFrame([
            {"Categoría": "Mercadería",            "Información requerida": "Nombre comercial o denominación habitual",                                  "Ejemplo": "Silla plegable, perfil estructural"},
            {"Categoría": "Materia constitutiva",  "Información requerida": "Material principal que lo compone",                                          "Ejemplo": "Acero galvanizado, plástico, aluminio"},
            {"Categoría": "Grado de elaboración", "Información requerida": "Procesos aplicados al material o producto",                                  "Ejemplo": "Laminado en frío, inyectado, anodizado"},
            {"Categoría": "Función / Uso / Destino", "Información requerida": "Para qué se utiliza y en qué estado se presenta",                          "Ejemplo": "Para construcción, en kit de armado"},
            {"Categoría": "Presentación",          "Información requerida": "Forma de entrega / presentación del producto",                              "Ejemplo": "A granel, en cajas, envasado al vacío"},
            {"Categoría": "Accesorios o componentes", "Información requerida": "Si incluye piezas de montaje, accesorios, repuestos o manuales",         "Ejemplo": "Tornillos, patas, instructivo de armado"},
            {"Categoría": "Folletos / Catálogos",  "Información requerida": "Material comercial (si se dispone)",                                         "Ejemplo": "PDF, links, brochures digitales"},
            {"Categoría": "Información técnica",   "Información requerida": "Fichas técnicas, planos, manuales, datos dimensionales, certificados",       "Ejemplo": "Ficha del proveedor, plano con medidas"},
        ])
        st.dataframe(_plantilla, use_container_width=True, hide_index=True)

    _modo = st.radio(
        "¿Cómo querés clasificar?",
        options=["express", "detallado"],
        format_func=lambda x: (
            "⚡ Modo Express — Subo documentación y la IA lee todo"
            if x == "express"
            else "✍️ Modo Detallado — Completo los datos manualmente"
        ),
        horizontal=True,
        key="modo_clasif",
    )

    st.divider()

    # ────────────────────────── MODO EXPRESS ──────────────────────────
    if _modo == "express":
        st.caption(
            "Subí fichas técnicas, catálogos, facturas, listas de precios o imágenes del producto. "
            "La IA extrae los atributos y clasifica en una sola pasada."
        )

        # ── Selector de mail de Gmail ────────────────────────────────
        from services.gmail_service import (
            gmail_configurado, buscar_threads, obtener_hilo_por_id,
        )
        if gmail_configurado():
            st.markdown("**📧 Usar mail de Gmail como base para clasificar**")

            _gs1, _gs2, _gs3 = st.columns([4, 1, 1])
            with _gs1:
                _gmail_q = st.text_input(
                    "Buscar mail",
                    placeholder="Asunto, remitente, palabras clave... (cualquier fecha)",
                    label_visibility="collapsed",
                    key="gmail_query_main",
                )
            with _gs2:
                _btn_buscar = st.button("🔍 Buscar", key="btn_gmail_buscar", use_container_width=True)
            with _gs3:
                _btn_recientes = st.button("📬 Recientes", key="btn_gmail_recientes", use_container_width=True)

            if ss.get("gmail_thread_id"):
                _t_sel = next((t for t in ss.get("gmail_threads", []) if t["id"] == ss["gmail_thread_id"]), None)
                st.success(f"✅ Seleccionado: {_t_sel['subject'][:60] if _t_sel else 'Hilo seleccionado'}")

            if _btn_buscar and _gmail_q.strip():
                with st.spinner("Buscando en Gmail..."):
                    try:
                        ss["gmail_threads"] = buscar_threads(_gmail_q.strip(), max_results=10)
                        if not ss["gmail_threads"]:
                            st.info("Sin resultados. Probá con otras palabras.")
                    except Exception as _eg:
                        st.warning(f"⚠️ {_eg}")

            if _btn_recientes:
                with st.spinner("Cargando..."):
                    try:
                        ss["gmail_threads"] = buscar_threads("in:inbox", max_results=10)
                    except Exception as _eg:
                        st.warning(f"⚠️ {_eg}")

            if ss.get("gmail_threads"):
                _opciones = {"(ninguno)": None} | {
                    f"✉️ {t['subject'][:55]} — {t['from_'][:25]} ({t['date'][:16]})": t["id"]
                    for t in ss["gmail_threads"]
                }
                _sel = st.selectbox("Seleccioná el hilo:", list(_opciones.keys()), key="gmail_sel")
                if _opciones.get(_sel):
                    ss["gmail_thread_id"] = _opciones[_sel]
                else:
                    ss.pop("gmail_thread_id", None)

        st.divider()

        with st.form("form_express", clear_on_submit=False):
            _archivos_x = st.file_uploader(
                "📎 Documentación e imágenes del producto",
                type=TODAS_EXTS,
                accept_multiple_files=True,
                key="archivos_express",
                help=(
                    "Subí cualquier formato: PDF, Word, Excel, imágenes "
                    "(JPG, PNG, WEBP, GIF, HEIC de iPhone, BMP, TIFF), HTML o texto. "
                    "Los PDFs escaneados se mandan como imagen automáticamente."
                ),
            )

            _url_x = st.text_input(
                "🔗 Link web del producto (opcional)",
                placeholder="https://www.proveedor.com/producto/ficha-tecnica",
                help="Pegá la URL de la página del producto, ficha técnica o catálogo online. "
                     "El clasificador descarga y analiza el contenido automáticamente.",
            )

            _mail_x = st.text_area(
                "✉️ Pegá el texto del mail directamente (opcional)",
                placeholder="Pegá acá el texto del mail o cadena de mensajes con la información del producto...",
                height=80,
                help="Alternativa al buscador de Gmail: copiá y pegá el mail completo o la cadena de mensajes.",
            )

            _ctx_extra = st.text_area(
                "💬 Aclaración o contexto adicional (opcional)",
                placeholder="Ej: Es un producto cosmético. La presentación oficial es en envases de 50ml. "
                            "El uso es para tratamiento facial profesional.",
                height=80,
            )

            _btn_x = st.form_submit_button(
                "🤖 Leer y clasificar",
                type="primary",
                use_container_width=True,
            )

        if _btn_x:
            _tiene_input = _archivos_x or _ctx_extra.strip() or _url_x.strip() or _mail_x.strip() or ss.get("gmail_thread_id")
            if not _tiene_input:
                st.warning("Subí al menos un archivo, un link, un mail o escribí un contexto.")
            else:
                with st.spinner("Procesando y analizando con Claude..."):
                    try:
                        # Guardar archivos crudos para poder persistirlos si se valida la partida
                        ss["archivos_pendientes"] = []
                        if _archivos_x:
                            for _a in _archivos_x:
                                _a.seek(0)
                                ss["archivos_pendientes"].append({
                                    "nombre": _a.name,
                                    "bytes": _a.read(),
                                    "mime": _a.type or "",
                                })
                                _a.seek(0)

                        extraccion = procesar_archivos(_archivos_x or [])
                        for w in extraccion.warnings:
                            st.warning(w)

                        # ── Scrapear URL si se proporcionó ──────────────────
                        _texto_extra_partes = []
                        if _url_x.strip():
                            with st.spinner(f"Descargando contenido de {_url_x.strip()}..."):
                                try:
                                    import urllib.request
                                    from bs4 import BeautifulSoup
                                    _headers = {"User-Agent": "Mozilla/5.0 (compatible; NCM-Clasificador/1.0)"}
                                    _req = urllib.request.Request(_url_x.strip(), headers=_headers)
                                    with urllib.request.urlopen(_req, timeout=15) as _resp:
                                        _html = _resp.read()
                                    _soup = BeautifulSoup(_html, "html.parser")
                                    for _tag in _soup(["script", "style", "nav", "footer", "header"]):
                                        _tag.decompose()
                                    _web_text = _soup.get_text(separator="\n", strip=True)
                                    # Limitar a 8000 caracteres para no saturar el contexto
                                    if len(_web_text) > 8000:
                                        _web_text = _web_text[:8000] + "\n[... contenido recortado ...]"
                                    _texto_extra_partes.append(
                                        f"=== CONTENIDO WEB: {_url_x.strip()} ===\n{_web_text}"
                                    )
                                    st.success(f"✅ Página descargada ({len(_web_text)} caracteres extraídos)")
                                except Exception as _e_url:
                                    st.warning(f"⚠️ No se pudo descargar el link: {_e_url}")

                        # ── Leer hilo de Gmail seleccionado ─────────────────
                        if ss.get("gmail_thread_id"):
                            with st.spinner("Leyendo hilo de Gmail (texto + adjuntos)..."):
                                try:
                                    _texto_gmail, _adj_gmail = obtener_hilo_por_id(ss["gmail_thread_id"])
                                    _texto_extra_partes.append(
                                        f"=== HILO DE GMAIL ===\n{_texto_gmail}"
                                    )
                                    for _adj in _adj_gmail:
                                        ss["archivos_pendientes"].append({
                                            "nombre": _adj["nombre"],
                                            "bytes": _adj["bytes"],
                                            "mime": _adj["mime"],
                                        })
                                    _msg_adj = (
                                        f" + {len(_adj_gmail)} adjunto(s): "
                                        + ", ".join(a["nombre"] for a in _adj_gmail)
                                        if _adj_gmail else ""
                                    )
                                    st.success(
                                        f"✅ Hilo leído ({len(_texto_gmail):,} caracteres){_msg_adj}"
                                    )
                                    if _adj_gmail:
                                        _archivos_gmail = []
                                        for _adj in _adj_gmail:
                                            _f_fake = type("F", (), {
                                                "name": _adj["nombre"],
                                                "type": _adj["mime"],
                                                "read": lambda self, b=_adj["bytes"]: b,
                                                "seek": lambda self, x: None,
                                            })()
                                            _archivos_gmail.append(_f_fake)
                                        _ext_gmail = procesar_archivos(_archivos_gmail)
                                        if _ext_gmail.texto:
                                            _texto_extra_partes.append(
                                                f"=== CONTENIDO DE ADJUNTOS DEL MAIL ===\n{_ext_gmail.texto}"
                                            )
                                except Exception as _e_gmail:
                                    st.warning(f"⚠️ No se pudo leer el hilo de Gmail: {_e_gmail}")

                        # ── Agregar contenido del mail pegado manualmente ────
                        if _mail_x.strip():
                            _texto_extra_partes.append(
                                f"=== CADENA DE MAIL DEL CLIENTE ===\n{_mail_x.strip()}"
                            )

                        # Combinar todo el texto adicional con el extraído de archivos
                        _texto_combinado = extraccion.texto
                        if _texto_extra_partes:
                            _texto_combinado = (_texto_combinado + "\n\n" + "\n\n".join(_texto_extra_partes)).strip()

                        from services.clasificador_ncm import clasificar_desde_documentos

                        resultado = clasificar_desde_documentos(
                            catalogo_text=_texto_combinado,
                            contexto_extra=_ctx_extra,
                            imagenes=extraccion.imagenes,
                        )

                        ss["resultado_ia"] = resultado
                        _atrs = resultado.get("atributos_extraidos") or {}
                        ss["mercaderia"] = _atrs.get("mercaderia", "") or resultado.get("resumen_producto", "")

                    except Exception as e:
                        st.error(f"Error al procesar/conectar con Claude: {e}")

    # ────────────────────────── MODO DETALLADO ──────────────────────────
    else:
        st.caption(
            "Completá la mayor cantidad de datos del producto. "
            "Cuanta más información brindes, más precisa será la clasificación."
        )

        with st.form("form_detallado", clear_on_submit=False):
            st.markdown("#### Datos del producto")

            _col1, _col2 = st.columns(2)
            with _col1:
                _mercaderia = st.text_input(
                    "Mercadería *",
                    placeholder="Nombre comercial o denominación habitual",
                    help="Ej: Silla plegable, gel inyectable de ácido hialurónico",
                )
                _materia = st.text_area(
                    "Materia constitutiva o composición",
                    placeholder="Material principal que lo compone",
                    height=80,
                )
                _grado = st.text_input(
                    "Grado de elaboración",
                    placeholder="Procesos aplicados al material",
                )

            with _col2:
                _funcion = st.text_area(
                    "Función / Uso / Destino",
                    placeholder="Para qué se utiliza y en qué estado se presenta",
                    height=80,
                )
                _presentacion = st.text_input(
                    "Presentación",
                    placeholder="Forma de entrega / presentación del producto",
                )
                _accesorios = st.text_input(
                    "Accesorios o componentes",
                    placeholder="Si incluye piezas de montaje, repuestos o manuales",
                )

            _obs = st.text_area(
                "Observaciones adicionales",
                placeholder="Marca, modelo, certificaciones, etc.",
                height=60,
            )

            st.markdown("#### Documentación adjunta (opcional)")
            _archivos_d = st.file_uploader(
                "📎 Folletos / Catálogos / Info técnica / Imágenes",
                type=TODAS_EXTS,
                accept_multiple_files=True,
                key="archivos_det",
                help=(
                    "PDF, Word, Excel, imágenes (JPG, PNG, WEBP, GIF, HEIC, BMP, TIFF), "
                    "HTML o texto plano."
                ),
            )

            _btn_clasificar = st.form_submit_button(
                "🤖 Clasificar producto",
                type="primary",
                use_container_width=True,
            )

        if _btn_clasificar:
            if not _mercaderia.strip():
                st.warning("Ingresá al menos el nombre de la mercadería.")
            else:
                with st.spinner("Procesando archivos y analizando con Claude..."):
                    try:
                        # Guardar archivos crudos por si el usuario valida la partida
                        ss["archivos_pendientes"] = []
                        if _archivos_d:
                            for _a in _archivos_d:
                                _a.seek(0)
                                ss["archivos_pendientes"].append({
                                    "nombre": _a.name,
                                    "bytes": _a.read(),
                                    "mime": _a.type or "",
                                })
                                _a.seek(0)

                        extraccion = procesar_archivos(_archivos_d or [])
                        for w in extraccion.warnings:
                            st.warning(w)

                        from services.clasificador_ncm import clasificar_producto

                        resultado = clasificar_producto(
                            descripcion=_mercaderia,
                            materia_constitutiva=_materia,
                            grado_elaboracion=_grado,
                            funcion_uso_destino=_funcion,
                            presentacion=_presentacion,
                            accesorios=_accesorios,
                            observaciones=_obs,
                            catalogo_text=extraccion.texto,
                            imagenes=extraccion.imagenes,
                        )

                        ss["resultado_ia"] = resultado
                        ss["mercaderia"] = _mercaderia

                    except Exception as e:
                        st.error(f"Error al procesar/conectar con Claude: {e}")

    # ── Resultado (común a ambos modos) ──────────────────────────────
    _res = ss.get("resultado_ia")
    if _res:
        _merc_label = ss.get("mercaderia", "")
        _atrs = _res.get("atributos_extraidos") or {}
        _desc_match = (
            _merc_label or _atrs.get("mercaderia", "") or _res.get("resumen_producto", "")
        )
        _renderizar_resultado_ia(_res, _merc_label, _desc_match)

        # ── Enviar resultado por mail ─────────────────────────────
        st.divider()
        with st.expander("📨 Enviar resultado por mail", expanded=False):
            from services.gmail_service import (
                cargar_destinatarios, guardar_destinatarios,
                gmail_configurado, enviar_email,
            )

            # Estado de destinatarios en sesión
            if "destinatarios_guardados" not in ss:
                ss["destinatarios_guardados"] = cargar_destinatarios()

            # ── Agregar destinatario ────────────────────────────
            st.caption(
                "Guardá los mails a quienes querés enviar resultados de clasificación. "
                "Se persisten entre sesiones."
            )
            _ec1, _ec2 = st.columns([5, 1])
            with _ec1:
                _nuevo_dest = st.text_input(
                    "Agregar destinatario",
                    placeholder="contacto@empresa.com",
                    key="nuevo_dest",
                    label_visibility="collapsed",
                )
            with _ec2:
                _btn_add_dest = st.button("➕ Agregar", key="btn_add_dest", use_container_width=True)

            if _btn_add_dest:
                _nd = _nuevo_dest.strip().lower()
                if _nd and "@" in _nd and _nd not in ss["destinatarios_guardados"]:
                    ss["destinatarios_guardados"].append(_nd)
                    guardar_destinatarios(ss["destinatarios_guardados"])
                    st.success(f"✅ {_nd} agregado.")
                    st.rerun()
                elif _nd in ss["destinatarios_guardados"]:
                    st.info("Ese mail ya está en la lista.")

            # ── Lista de destinatarios ──────────────────────────
            if ss["destinatarios_guardados"]:
                st.markdown("**Destinatarios guardados:**")
                for _d in list(ss["destinatarios_guardados"]):
                    _dl1, _dl2 = st.columns([6, 1])
                    with _dl1:
                        st.write(f"✉️ {_d}")
                    with _dl2:
                        if st.button("🗑️", key=f"del_dest_{_d}", help=f"Eliminar {_d}"):
                            ss["destinatarios_guardados"].remove(_d)
                            guardar_destinatarios(ss["destinatarios_guardados"])
                            st.rerun()

                st.divider()
                _dests_sel = st.multiselect(
                    "Enviar a:",
                    options=ss["destinatarios_guardados"],
                    default=ss["destinatarios_guardados"],
                    key="dests_sel",
                )

                # ── Construir cuerpo del mail ───────────────────
                _sug_email = (
                    _res.get("sugerencias", [{}])[0]
                    if _res.get("sugerencias") else {}
                )
                _atrs_email = _res.get("atributos_extraidos") or {}
                _interv_email = _res.get("intervenciones_probables") or []
                _conf_email = (_sug_email.get("confianza") or "media").lower()
                _conf_color = {"alta": "#22c55e", "media": "#f59e0b", "baja": "#ef4444"}.get(_conf_email, "#6b7280")
                _conf_label = {"alta": "ALTA ✓", "media": "MEDIA", "baja": "BAJA ⚠"}.get(_conf_email, _conf_email.upper())
                _trib_email = _sug_email.get("tributos") or {}
                _rgi_email = ", ".join(_sug_email.get("rgi_aplicadas") or []) or "—"

                # ── Texto plano (fallback) ──────────────────────
                _cuerpo_txt = (
                    f"CLASIFICACIÓN NCM — {_merc_label or '(producto sin nombre)'}\n"
                    f"{'='*60}\n\n"
                    f"NCM sugerido:  {_sug_email.get('ncm','—')}\n"
                    f"Confianza:     {_conf_label}\n"
                    f"Capítulo:      {_sug_email.get('capitulo','—')}\n"
                    f"Apertura SIM:  {_sug_email.get('apertura_sim','—')}\n\n"
                    f"JUSTIFICACIÓN\n{_sug_email.get('justificacion','—')}\n\n"
                    f"RGI aplicadas: {_rgi_email}\n"
                    f"Intervenciones: {', '.join(_interv_email) or '—'}\n\n"
                    f"---\nEnviado desde GP COMEX — Clasificador Arancelario NCM"
                )

                # ── HTML ────────────────────────────────────────
                def _fila_trib(label, val, tipo):
                    if not val and val != 0:
                        return ""
                    return f"<tr><td style='padding:5px 10px;color:#374151;'>{label}</td><td style='padding:5px 10px;font-weight:600;color:#1D284E;text-align:right;'>{val}%</td><td style='padding:5px 10px;color:#6b7280;font-size:0.85em;'>{tipo}</td></tr>"

                _tabla_trib = ""
                if _trib_email:
                    _filas = (
                        _fila_trib("DIE", _trib_email.get("die_pct"), "Irrecuperable") +
                        _fila_trib("TE", _trib_email.get("te_pct"), "Irrecuperable") +
                        _fila_trib("IVA", _trib_email.get("iva_pct"), "Recuperable") +
                        _fila_trib("IVA Adicional", _trib_email.get("iva_ad_pct"), "Recuperable") +
                        _fila_trib("Ganancias", _trib_email.get("ganancias_pct"), "Recuperable") +
                        _fila_trib("IIBB", _trib_email.get("iibb_pct"), "Recuperable")
                    )
                    if _filas:
                        _tabla_trib = f"""
                        <div style="margin:20px 0;">
                          <p style="font-weight:700;color:#1D284E;margin:0 0 8px 0;font-size:0.95em;text-transform:uppercase;letter-spacing:0.05em;">Tributos</p>
                          <table style="width:100%;border-collapse:collapse;background:#f9fafb;border-radius:8px;overflow:hidden;">
                            <thead><tr style="background:#e5e7eb;">
                              <th style="padding:6px 10px;text-align:left;color:#374151;font-size:0.85em;">Concepto</th>
                              <th style="padding:6px 10px;text-align:right;color:#374151;font-size:0.85em;">%</th>
                              <th style="padding:6px 10px;text-align:left;color:#374151;font-size:0.85em;">Tipo</th>
                            </tr></thead>
                            <tbody>{_filas}</tbody>
                          </table>
                        </div>"""

                _interv_html = ""
                if _interv_email:
                    _items = "".join(f"<li style='margin:3px 0;color:#374151;'>{i}</li>" for i in _interv_email)
                    _interv_html = f"""
                    <div style="margin:16px 0;">
                      <p style="font-weight:700;color:#1D284E;margin:0 0 6px 0;font-size:0.95em;text-transform:uppercase;letter-spacing:0.05em;">Intervenciones probables</p>
                      <ul style="margin:0;padding-left:18px;">{_items}</ul>
                    </div>"""

                _atrs_html = ""
                _atrs_items = []
                if _atrs_email.get("materia_constitutiva"):
                    _atrs_items.append(f"<b>Materia:</b> {_atrs_email['materia_constitutiva']}")
                if _atrs_email.get("funcion_uso_destino"):
                    _atrs_items.append(f"<b>Uso / Destino:</b> {_atrs_email['funcion_uso_destino']}")
                if _atrs_email.get("presentacion"):
                    _atrs_items.append(f"<b>Presentación:</b> {_atrs_email['presentacion']}")
                if _atrs_items:
                    _atrs_html = f"""
                    <div style="margin:16px 0;padding:14px;background:#f0f4ff;border-radius:8px;">
                      <p style="font-weight:700;color:#1D284E;margin:0 0 8px 0;font-size:0.95em;text-transform:uppercase;letter-spacing:0.05em;">Producto</p>
                      {"<br>".join(f"<p style='margin:4px 0;color:#374151;font-size:0.93em;'>{a}</p>" for a in _atrs_items)}
                    </div>"""

                import datetime as _dt_mail
                _fecha_mail = _dt_mail.datetime.now().strftime("%d/%m/%Y %H:%M")

                _cuerpo_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- HEADER -->
  <tr><td style="background:linear-gradient(135deg,#415FC3 0%,#364E9B 100%);padding:24px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="background:white;border-radius:8px;padding:8px 12px;display:inline-block;width:44px;text-align:center;">
        <span style="font-weight:800;color:#415FC3;font-size:1rem;letter-spacing:-0.02em;">GP</span>
      </td>
      <td style="padding-left:14px;">
        <div style="color:white;font-size:1.3rem;font-weight:700;letter-spacing:0.04em;">GPCOMEX</div>
        <div style="color:#93A8DC;font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.16em;margin-top:2px;">Global Partner · Clasificador Arancelario NCM</div>
      </td>
    </tr></table>
  </td></tr>

  <!-- BODY -->
  <tr><td style="padding:28px 32px;">

    <!-- Título producto -->
    <h1 style="margin:0 0 20px 0;font-size:1.15rem;color:#1D284E;font-weight:700;line-height:1.3;">{_merc_label or "(producto sin nombre)"}</h1>

    <!-- NCM destacado -->
    <div style="background:#f0f4ff;border-left:5px solid #415FC3;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
      <div style="display:flex;align-items:center;gap:16px;">
        <div>
          <div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">NCM Sugerido</div>
          <div style="font-size:1.8rem;font-weight:800;color:#1D284E;letter-spacing:0.02em;">{_sug_email.get("ncm","—")}</div>
        </div>
        <div style="margin-left:auto;background:{_conf_color};color:white;padding:6px 14px;border-radius:20px;font-size:0.8rem;font-weight:700;letter-spacing:0.05em;">
          {_conf_label}
        </div>
      </div>
    </div>

    <!-- Jerarquía -->
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td width="50%" style="padding:6px 12px 6px 0;vertical-align:top;">
          <span style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Capítulo</span><br>
          <span style="color:#1D284E;font-weight:600;font-size:0.9rem;">{_sug_email.get("capitulo","—")}</span>
        </td>
        <td width="50%" style="padding:6px 0 6px 12px;vertical-align:top;border-left:1px solid #e5e7eb;">
          <span style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;letter-spacing:0.08em;font-weight:600;">Apertura SIM</span><br>
          <span style="color:#1D284E;font-weight:600;font-size:0.9rem;">{_sug_email.get("apertura_sim","—")}</span>
        </td>
      </tr>
    </table>

    <!-- Justificación -->
    <div style="margin:0 0 20px 0;">
      <p style="font-weight:700;color:#1D284E;margin:0 0 8px 0;font-size:0.95em;text-transform:uppercase;letter-spacing:0.05em;">Justificación</p>
      <p style="margin:0;color:#374151;font-size:0.93em;line-height:1.6;">{_sug_email.get("justificacion","—")}</p>
    </div>

    <!-- RGI -->
    <p style="margin:0 0 20px 0;font-size:0.88em;color:#6b7280;"><b style="color:#374151;">RGI aplicadas:</b> {_rgi_email}</p>

    {_tabla_trib}
    {_interv_html}
    {_atrs_html}

  </td></tr>

  <!-- DISCLAIMER -->
  <tr><td style="background:#FEF3C7;border-top:3px solid #F59E0B;padding:14px 32px;">
    <p style="margin:0;font-size:0.82em;color:#92400E;"><b>⚠ IMPORTANTE:</b> Este informe es una sugerencia del sistema. Para la clasificación final consultá con tu despachante de aduana o clasificador habilitado.</p>
  </td></tr>

  <!-- FOOTER -->
  <tr><td style="background:#1D284E;padding:16px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td><span style="color:#93A8DC;font-size:0.8rem;">GPCOMEX · Global Partner · Clasificador Arancelario NCM</span></td></tr>
      <td align="right"><span style="color:#93A8DC;font-size:0.8rem;">{_fecha_mail}</span></td>
    </tr></table>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""

                with st.expander("Ver borrador del mail"):
                    st.code(_cuerpo_html[:300] + "...", language="html")

                # ── Botón de envío ──────────────────────────────
                if not gmail_configurado():
                    st.warning(
                        "⚠️ Gmail no configurado. "
                        "Seguí los pasos en `services/gmail_service.py` para conectar tu cuenta."
                    )
                elif not _dests_sel:
                    st.info("Seleccioná al menos un destinatario.")
                else:
                    _asunto_email = (
                        f"Clasificación NCM: {_merc_label or 'Producto'} "
                        f"→ {_sug_email.get('ncm', '—')}"
                    )
                    if st.button(
                        f"📨 Enviar a {len(_dests_sel)} destinatario(s)",
                        type="primary",
                        use_container_width=True,
                        key="btn_enviar_mail",
                    ):
                        with st.spinner("Enviando..."):
                            try:
                                enviar_email(_dests_sel, _asunto_email, _cuerpo_txt, _cuerpo_html)
                                st.success(
                                    f"✅ Mail enviado a: {', '.join(_dests_sel)}"
                                )
                            except Exception as _e_send:
                                st.error(f"Error al enviar: {_e_send}")
            else:
                st.info("Agregá al menos un destinatario para poder enviar por mail.")


# ════════════════════════════════════════════════════════════════
# TAB 2 — CONSULTA NCM
# ════════════════════════════════════════════════════════════════

with tab_consulta:
    st.subheader("Consulta de Posiciones NCM")
    st.caption("Buscá por código NCM para ver tributos, flags y carga tributaria estimada.")

    if not _MATRIZ_DISPONIBLE:
        st.error("No se pudo cargar la matriz NCM.")
    else:
        _ncm_buscar = st.text_input(
            "Código NCM",
            placeholder="Ej: 3304.99.90 o 8471.30",
            key="ncm_buscar",
        )

        _col_f1, _col_f2, _col_f3 = st.columns(3)
        with _col_f1:
            _filtro_dumping = st.checkbox("Solo con DUMPING", key="f_dump")
        with _col_f2:
            _filtro_bk = st.checkbox("Solo BK", key="f_bk")
        with _col_f3:
            _filtro_mipyme = st.checkbox("Solo MiPyme", key="f_mipyme")

        if _ncm_buscar and _ncm_buscar.strip():
            from services.clasificador_ncm import validar_ncm_en_matriz
            _ficha = validar_ncm_en_matriz(_ncm_buscar.strip(), _matriz_p, _matriz_m)

            if _ficha:
                st.success(f"NCM encontrado: **{_ficha['posicion_sim']}**")

                _tc1, _tc2 = st.columns(2)
                with _tc1:
                    st.markdown("**Tributos:**")
                    _t = _ficha["tributos"]
                    _trib_data = {
                        "Concepto": ["DIE", "AEC", "TE", "DII", "IVA", "IVA Ad.", "Ganancias", "IIBB"],
                        "%": [
                            _t["die_pct"], _t["aec_pct"], _t["te_pct"], _t["dii_pct"],
                            _t["iva_pct"], _t["iva_ad_pct"], _t["ganancias_pct"], _t["iibb_pct"],
                        ],
                        "Tipo": [
                            "Irrecup.", "Ref. Mercosur ℹ️", "Irrecup.", "Irrecup.",
                            "Recup.", "Recup.", "Recup.", "Recup.",
                        ],
                    }
                    st.dataframe(pd.DataFrame(_trib_data), use_container_width=True, hide_index=True)
                    st.caption("ℹ️ AEC = Arancel Externo Común (referencia normativa Mercosur). **No se suma al DIE ni impacta en ningún cálculo.**")

                with _tc2:
                    _flags = _ficha["flags"]
                    st.markdown("**Flags regulatorios:**")
                    st.write(f"DUMPING: {'⚠️ SI' if _flags['dumping'] else '—'}")
                    st.write(f"Seguridad eléctrica: {'⚡ SI' if _flags['seguridad_electrica'] else '—'}")
                    st.write(f"BK: {'🏭 SI' if _flags['bk'] else '—'}")
                    st.write(f"MiPyme: {'✅ SI' if _flags['mipyme'] else '—'}")

                    st.divider()
                    _ct = _ficha["carga_tributaria"]
                    st.metric("CARGA TOTAL SOBRE CIF", f"{_ct['total_sobre_cif_pct']:.1f}%")
                    _ci2, _cr2 = st.columns(2)
                    _ci2.metric(
                        "No recuperable",
                        f"{_ct['irrecuperable_pct']:.1f}%",
                        help="Sobre CIF — DIE + TE.",
                    )
                    _cr2.metric(
                        "Recuperable / crédito fiscal",
                        f"{_ct['recuperable_pct']:.1f}%",
                        help="Sobre base IVA (CIF + Derechos + Tasas).",
                    )

                # Productos del catálogo bajo ese NCM
                _catalogo = cat.cargar_catalogo()
                _productos_ncm = [
                    p for p in _catalogo.values()
                    if str(p.get("ncm", "")).strip() == str(_ficha["posicion_sim"]).strip()
                ]
                if _productos_ncm:
                    st.divider()
                    st.markdown(f"### 📚 Productos de tu catálogo con este NCM ({len(_productos_ncm)})")
                    for _p in _productos_ncm[:20]:
                        st.write(
                            f"• **{_p.get('descripcion', '(sin descripción)')}**"
                            + (f" — SKU: {_p['sku']}" if _p.get('sku') else "")
                        )

            else:
                st.warning(f"NCM **{_ncm_buscar}** no encontrado en la matriz.")

        if _filtro_dumping or _filtro_bk or _filtro_mipyme:
            st.divider()
            st.markdown("### Resultados filtrados")
            _df_filtro = _matriz_p.copy()
            if _filtro_dumping and "DUMPING" in _df_filtro.columns:
                _df_filtro = _df_filtro[_df_filtro["DUMPING"].astype(str).str.strip().str.upper() == "SI"]
            if _filtro_bk and "BK" in _df_filtro.columns:
                _df_filtro = _df_filtro[_df_filtro["BK"].astype(str).str.strip().str.upper() == "SI"]
            if _filtro_mipyme and "My Pyme" in _df_filtro.columns:
                _df_filtro = _df_filtro[_df_filtro["My Pyme"].astype(str).str.strip().str.upper() == "SI"]

            st.write(f"**{len(_df_filtro)}** posiciones encontradas")
            if len(_df_filtro) > 0:
                _cols_mostrar = [c for c in [
                    "Posición SIM", "DIE %", "TE %", "IVA %", "IVA Ad. %",
                    "Ganancias %", "IIBB %", "DUMPING", "BK", "SEGURIDAD ELECTRICA", "My Pyme",
                ] if c in _df_filtro.columns]
                st.dataframe(_df_filtro[_cols_mostrar].head(100), use_container_width=True, hide_index=True)
                if len(_df_filtro) > 100:
                    st.caption(f"Mostrando primeras 100 de {len(_df_filtro)} posiciones.")


# ════════════════════════════════════════════════════════════════
# TAB 3 — MI CATÁLOGO
# ════════════════════════════════════════════════════════════════

with tab_catalogo:
    st.subheader("📚 Mi catálogo de productos clasificados")
    st.caption(
        "Importá tu base de productos ya clasificados. Cuando clasifiques uno nuevo, "
        "el sistema te avisará si encuentra similares acá."
    )

    _catalogo = cat.cargar_catalogo()
    _stats = cat.stats(_catalogo)

    _kc1, _kc2, _kc3 = st.columns(3)
    _kc1.metric("Productos", _stats["total"])
    _kc2.metric("NCMs distintos", _stats["ncms_unicos"])
    if _stats["top_ncms"]:
        _kc3.metric("NCM más usado", f"{_stats['top_ncms'][0][0]}", f"{_stats['top_ncms'][0][1]} prod.")

    _sec_imp, _sec_lista, _sec_agregar = st.tabs([
        "⬆️ Importar Excel/CSV",
        "📋 Ver catálogo",
        "➕ Agregar manualmente",
    ])

    # ─────── SUB-TAB IMPORTAR ───────
    with _sec_imp:
        st.write(
            "Subí tu base de productos en Excel (.xlsx) o CSV. "
            "**Solo NCM es obligatorio.** El resto de las columnas son opcionales pero ayudan al match."
        )
        st.caption(
            "Columnas reconocidas: SKU, Descripción, NCM, Marca, Modelo, "
            "Materia/Composición, Función/Uso, Presentación, Observaciones. "
            "Si tus columnas se llaman distinto el sistema intenta autodetectarlas."
        )

        _archivo = st.file_uploader(
            "Archivo del catálogo",
            type=["xlsx", "xls", "csv"],
            key="cat_upload",
        )

        if _archivo:
            try:
                _preview_bytes = _archivo.read()
                _ext = _archivo.name.lower().rsplit(".", 1)[-1]
                if _ext in ("xlsx", "xls"):
                    _df_prev = pd.read_excel(_preview_bytes if isinstance(_preview_bytes, bytes) else _preview_bytes)
                else:
                    import io as _io
                    _df_prev = pd.read_csv(_io.BytesIO(_preview_bytes))
                _df_prev.columns = [str(c).strip() for c in _df_prev.columns]

                st.markdown("**Previsualización (primeras 5 filas):**")
                st.dataframe(_df_prev.head(5), use_container_width=True)

                _mapeo_auto = cat.detectar_mapeo_columnas(list(_df_prev.columns))
                st.markdown("**Mapeo de columnas detectado:**")
                _cols_disp = ["(no mapear)"] + list(_df_prev.columns)
                _mapeo_user = {}
                _mcol1, _mcol2 = st.columns(2)
                for i, campo in enumerate(cat.CAMPOS_CANONICOS):
                    _target = _mcol1 if i % 2 == 0 else _mcol2
                    with _target:
                        _default = _mapeo_auto.get(campo, "(no mapear)")
                        _idx_default = _cols_disp.index(_default) if _default in _cols_disp else 0
                        _sel = st.selectbox(
                            f"**{campo}**" + (" *" if campo == "ncm" else ""),
                            _cols_disp,
                            index=_idx_default,
                            key=f"map_{campo}",
                        )
                        if _sel != "(no mapear)":
                            _mapeo_user[campo] = _sel

                _reemp = st.checkbox(
                    "Reemplazar el catálogo actual (en vez de hacer merge por SKU)",
                    value=False,
                )

                if st.button("📥 Importar al catálogo", type="primary"):
                    if "ncm" not in _mapeo_user:
                        st.error("Tenés que mapear una columna a **NCM** (es obligatorio).")
                    else:
                        try:
                            _res_imp = cat.importar_desde_archivo(
                                file_bytes=_preview_bytes,
                                nombre_archivo=_archivo.name,
                                mapeo_override=_mapeo_user,
                                reemplazar=_reemp,
                            )
                            st.success(
                                f"✅ Agregados: {_res_imp['agregados']} · "
                                f"Actualizados: {_res_imp['actualizados']} · "
                                f"Descartados (sin NCM): {_res_imp['descartados']} · "
                                f"Total catálogo: {_res_imp['total_final']}"
                            )
                            if _res_imp["errores"]:
                                with st.expander(f"⚠️ {len(_res_imp['errores'])} errores"):
                                    for _e in _res_imp["errores"][:50]:
                                        st.write(_e)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error en la importación: {e}")
            except Exception as e:
                st.error(f"No pude leer el archivo: {e}")

    # ─────── SUB-TAB VER CATÁLOGO ───────
    with _sec_lista:
        if not _catalogo:
            st.info("El catálogo está vacío. Importá un Excel o agregá productos manualmente.")
        else:
            _busq = st.text_input("🔎 Buscar en el catálogo", placeholder="Texto, NCM, SKU...")

            _df_cat = cat.exportar_a_dataframe(_catalogo)

            if _busq and _busq.strip():
                _b_norm = _busq.strip().lower()
                _mask = _df_cat.apply(
                    lambda r: any(_b_norm in str(v).lower() for v in r.values),
                    axis=1,
                )
                _df_show = _df_cat[_mask]
            else:
                _df_show = _df_cat

            st.write(f"Mostrando **{len(_df_show)}** de {len(_df_cat)} productos.")
            st.dataframe(_df_show, use_container_width=True, hide_index=True, height=400)

            _dcol1, _dcol2 = st.columns(2)
            with _dcol1:
                # Descargar Excel
                import io as _io
                _buffer = _io.BytesIO()
                with pd.ExcelWriter(_buffer, engine="openpyxl") as _writer:
                    _df_cat.to_excel(_writer, index=False, sheet_name="Catalogo")
                st.download_button(
                    "⬇️ Descargar catálogo (Excel)",
                    _buffer.getvalue(),
                    file_name="catalogo_cliente.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            with _dcol2:
                # Eliminar productos
                _ids_eliminar = st.multiselect(
                    "Eliminar productos (por id)",
                    options=list(_catalogo.keys()),
                    format_func=lambda pid: f"{pid[:20]}... — {_catalogo[pid].get('descripcion', '')[:40]}",
                    key="ids_del",
                )
                if _ids_eliminar and st.button("🗑️ Eliminar seleccionados"):
                    for _pid in _ids_eliminar:
                        cat.eliminar_producto(_pid)
                    st.success(f"{len(_ids_eliminar)} productos eliminados.")
                    st.rerun()

    # ─────── SUB-TAB AGREGAR MANUAL ───────
    with _sec_agregar:
        st.caption("Agregá un producto puntual al catálogo.")
        with st.form("form_add_cat", clear_on_submit=True):
            _ac1, _ac2 = st.columns(2)
            with _ac1:
                _g_desc = st.text_input("Descripción *")
                _g_ncm = st.text_input("NCM *", placeholder="Ej: 8471.30.12.110")
                _g_sku = st.text_input("SKU / Código interno")
                _g_marca = st.text_input("Marca")
                _g_modelo = st.text_input("Modelo")
            with _ac2:
                _g_materia = st.text_area("Materia constitutiva", height=80)
                _g_uso = st.text_area("Función / Uso / Destino", height=80)
                _g_pres = st.text_input("Presentación")
                _g_obs = st.text_area("Observaciones", height=60)

            _btn_add_cat = st.form_submit_button("💾 Agregar al catálogo", type="primary")

            if _btn_add_cat:
                if not _g_ncm.strip():
                    st.error("El NCM es obligatorio.")
                else:
                    try:
                        cat.agregar_producto({
                            "descripcion": _g_desc,
                            "ncm": _g_ncm.strip(),
                            "sku": _g_sku,
                            "marca": _g_marca,
                            "modelo": _g_modelo,
                            "materia_constitutiva": _g_materia,
                            "funcion_uso_destino": _g_uso,
                            "presentacion": _g_pres,
                            "observaciones": _g_obs,
                        })
                        st.success(f"Producto agregado al catálogo (NCM {_g_ncm.strip()}).")
                    except Exception as e:
                        st.error(f"Error: {e}")


# ════════════════════════════════════════════════════════════════
# TAB 4 — FICHAS GUARDADAS
# ════════════════════════════════════════════════════════════════

with tab_fichas:
    st.subheader("📋 Fichas guardadas — Partidas halladas")
    st.caption(
        "Cada partida que validaste tiene su propia carpeta con descripción, tributos, "
        "intervenciones y documentos originales del producto."
    )

    _fichas = ss.get("fichas_arancelarias", {})
    _halladas = {fid: f for fid, f in _fichas.items() if f.get("validada")}

    if not _halladas:
        st.info(
            "Aún no seleccionaste ninguna partida. Cuando clasifiques un producto y hagas "
            "click en **✅ Seleccionar esta partida**, se crea una carpeta acá."
        )
        _fichas_mostrar = {}
    else:
        _ncm_uniq = {_f.get("ncm") for _f in _halladas.values() if _f.get("ncm")}
        _con_docs = sum(1 for _f in _halladas.values() if _f.get("archivos"))

        _k1, _k2, _k3 = st.columns(3)
        _k1.metric("✅ Partidas halladas", len(_halladas))
        _k2.metric("NCMs distintos", len(_ncm_uniq))
        _k3.metric("Con documentos", _con_docs)

        # ─── Excel maestro consolidado ───
        _filas_excel = []
        for _fid, _f in _halladas.items():
            _t_x = _f.get("tributos") or {}
            _ct_x = _f.get("carga_tributaria") or {}
            _filas_excel.append({
                "NCM": _f.get("ncm", ""),
                "Nombre partida": _f.get("nombre_partida", "") or _f.get("descripcion_fina", "")[:60],
                "Descripción detallada": _f.get("descripcion_fina", ""),
                "SKU": _f.get("sku", ""),
                "Marca": _f.get("marca", ""),
                "Capítulo": _f.get("capitulo", ""),
                "Partida": _f.get("partida", ""),
                "Apertura SIM": _f.get("apertura_sim", ""),
                "DIE %": _t_x.get("die_pct", ""),
                "TE %": _t_x.get("te_pct", ""),
                "IVA %": _t_x.get("iva_pct", ""),
                "IVA Ad. %": _t_x.get("iva_ad_pct", ""),
                "Ganancias %": _t_x.get("ganancias_pct", ""),
                "IIBB %": _t_x.get("iibb_pct", ""),
                "Carga total sobre CIF %": _ct_x.get("total_sobre_cif_pct", ""),
                "Intervenciones": ", ".join(_f.get("intervenciones", []) or []),
                "RGI aplicadas": ", ".join(_f.get("rgi_aplicadas", []) or []),
                "Justificación": _f.get("justificacion", ""),
                "Observaciones": _f.get("observaciones_cliente", ""),
                "Confianza": _f.get("confianza", ""),
                "Documentos": ", ".join(_f.get("archivos", []) or []),
                "Fecha": _f.get("fecha", "")[:19],
            })
        _df_excel = pd.DataFrame(_filas_excel)
        import io as _io_xl
        _buf_xl = _io_xl.BytesIO()
        with pd.ExcelWriter(_buf_xl, engine="openpyxl") as _w:
            _df_excel.to_excel(_w, index=False, sheet_name="Partidas halladas")

        _dlcol1, _dlcol2 = st.columns([2, 1])
        with _dlcol1:
            st.markdown(
                f"📊 Reporte consolidado de las **{len(_halladas)} partidas halladas**"
            )
        with _dlcol2:
            st.download_button(
                "⬇️ Descargar Excel",
                _buf_xl.getvalue(),
                file_name=f"partidas_halladas_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )

        st.divider()
        st.markdown("### 📁 Carpetas de partidas")

        for _fid, _f in sorted(_halladas.items(), key=lambda x: x[1].get("fecha", ""), reverse=True):
            _t = _f.get("tributos", {})
            _nombre_p = _f.get("nombre_partida") or _f.get("descripcion_fina", "")[:60] or _f.get("mercaderia", "?")
            with st.expander(
                f"✅ **{_nombre_p}** — NCM {_f.get('ncm', '?')} "
                f"— {_f.get('fecha', '')[:10]}",
            ):
                _fc1, _fc2 = st.columns([3, 2])
                with _fc1:
                    st.write(f"**NCM:** {_f.get('ncm')}")
                    if _f.get("apertura_sim"):
                        st.write(f"**Apertura SIM:** {_f.get('apertura_sim')}")
                    if _f.get("descripcion_fina"):
                        st.write(f"**Descripción detallada:**")
                        st.write(_f.get("descripcion_fina"))
                    if _f.get("sku"):
                        st.write(f"**SKU:** {_f.get('sku')}")
                    if _f.get("marca"):
                        st.write(f"**Marca:** {_f.get('marca')}")
                    if _f.get("observaciones_cliente"):
                        st.write(f"**Observaciones:**")
                        st.write(_f.get("observaciones_cliente"))
                    if _f.get("intervenciones"):
                        st.write(f"**Intervenciones:** {', '.join(_f['intervenciones'])}")
                    if _f.get("justificacion"):
                        with st.expander("Ver justificación IA"):
                            st.write(_f.get("justificacion"))

                with _fc2:
                    st.markdown("**Tributos:**")
                    st.write(f"DIE: {_t.get('die_pct', 0)}% | TE: {_t.get('te_pct', 0)}%")
                    st.write(f"IVA: {_t.get('iva_pct', 0)}% | IVA Ad.: {_t.get('iva_ad_pct', 0)}%")
                    st.write(f"Ganancias: {_t.get('ganancias_pct', 0)}% | IIBB: {_t.get('iibb_pct', 0)}%")
                    _ct = _f.get("carga_tributaria", {})
                    if _ct:
                        st.metric("CARGA TOTAL SOBRE CIF", f"{_ct.get('total_sobre_cif_pct', 0):.1f}%")
                        _ci3, _cr3 = st.columns(2)
                        _ci3.metric("No recuperable", f"{_ct.get('irrecuperable_pct', 0):.1f}%", help="Sobre CIF")
                        _cr3.metric("Recuperable", f"{_ct.get('recuperable_pct', 0):.1f}%", help="Sobre base IVA")
                    _flags = _f.get("flags", {})
                    _fl = []
                    if _flags.get("dumping"): _fl.append("DUMPING")
                    if _flags.get("seguridad_electrica"): _fl.append("SEG. ELÉCTRICA")
                    if _flags.get("bk"): _fl.append("BK")
                    if _flags.get("mipyme"): _fl.append("MiPyme")
                    if _fl:
                        st.write(f"**Flags:** {' · '.join(_fl)}")

                # ── Documentos guardados ──
                _archivos_fp = _f.get("archivos", []) or []
                _carpeta_rel = _f.get("carpeta", "")
                if _archivos_fp and _carpeta_rel:
                    st.markdown("**📎 Documentos de la carpeta:**")
                    _carpeta_abs = ROOT / _carpeta_rel / "documentos"
                    for _arch_nombre in _archivos_fp:
                        _ruta = _carpeta_abs / _arch_nombre
                        if _ruta.exists():
                            try:
                                _bytes = _ruta.read_bytes()
                                st.download_button(
                                    f"⬇️ {_arch_nombre}",
                                    _bytes,
                                    file_name=_arch_nombre,
                                    key=f"dl_{_fid}_{_arch_nombre}",
                                )
                            except Exception as e:
                                st.write(f"• {_arch_nombre} (no se pudo leer: {e})")
                        else:
                            st.write(f"• {_arch_nombre} (archivo no encontrado en disco)")

                # ── Documentación por tema (referencias arancelarias) ──
                if _carpeta_rel:
                    st.markdown("---")
                    st.markdown("**📚 Documentación arancelaria por tema:**")
                    st.caption(
                        "Adjuntá PDFs, capturas, txt o pegá texto para cada tema. "
                        "Todo queda guardado en la carpeta de esta partida, separado por tema."
                    )

                    _TEMAS_DOC = [
                        ("acuerdos", "📄 Acuerdos"),
                        ("notas", "📝 Notas"),
                        ("resoluciones", "⚖️ Resoluciones"),
                        ("sufijos", "💲 Sufijos de valor"),
                        ("origen_mercosur", "🌎 Origen Mercosur"),
                        ("antecedentes", "📚 Antecedentes"),
                        ("desc_encadenada", "📜 Desc. encadenada"),
                    ]

                    _carpeta_doc_base = ROOT / _carpeta_rel / "documentacion"
                    _tabs_temas = st.tabs([_lbl for _, _lbl in _TEMAS_DOC])

                    for _i_tema, (_slug_tema, _lbl_tema) in enumerate(_TEMAS_DOC):
                        with _tabs_temas[_i_tema]:
                            _carpeta_tema = _carpeta_doc_base / _slug_tema
                            _carpeta_tema.mkdir(parents=True, exist_ok=True)
                            _notas_path = _carpeta_tema / "notas.txt"

                            # Archivos ya guardados
                            try:
                                _archivos_tema = sorted(
                                    p for p in _carpeta_tema.iterdir()
                                    if p.is_file() and p.name != "notas.txt"
                                )
                            except Exception:
                                _archivos_tema = []

                            if _archivos_tema:
                                st.markdown("**Archivos guardados:**")
                                for _arch in _archivos_tema:
                                    _ca, _cd = st.columns([5, 1])
                                    with _ca:
                                        try:
                                            st.download_button(
                                                f"⬇️ {_arch.name}",
                                                _arch.read_bytes(),
                                                file_name=_arch.name,
                                                key=f"dl_t_{_fid}_{_slug_tema}_{_arch.name}",
                                                use_container_width=True,
                                            )
                                        except Exception as e:
                                            st.write(f"• {_arch.name} (error leyendo: {e})")
                                    with _cd:
                                        if st.button("🗑️", key=f"rm_t_{_fid}_{_slug_tema}_{_arch.name}", help="Eliminar"):
                                            try:
                                                _arch.unlink()
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"No se pudo borrar: {e}")
                            else:
                                st.caption("Sin archivos guardados todavía.")

                            # Texto editable (guardado en notas.txt)
                            _texto_actual = ""
                            if _notas_path.exists():
                                try:
                                    _texto_actual = _notas_path.read_text(encoding="utf-8")
                                except Exception:
                                    pass

                            _nuevo_texto = st.text_area(
                                "📋 Texto / notas para este tema",
                                value=_texto_actual,
                                key=f"texto_t_{_fid}_{_slug_tema}",
                                height=120,
                                placeholder="Pegá acá texto copiado de Tarifar u otras fuentes, o tus propias notas sobre este tema.",
                            )

                            _ups_tema = st.file_uploader(
                                "📎 Subir archivos para este tema",
                                type=["pdf", "png", "jpg", "jpeg", "webp", "txt", "docx", "doc"],
                                accept_multiple_files=True,
                                key=f"up_t_{_fid}_{_slug_tema}",
                            )

                            if st.button(
                                f"💾 Guardar {_lbl_tema}",
                                key=f"save_t_{_fid}_{_slug_tema}",
                                type="primary",
                                use_container_width=True,
                            ):
                                _guardados = 0
                                _errores = []
                                if (_nuevo_texto or "") != (_texto_actual or ""):
                                    try:
                                        if _nuevo_texto.strip():
                                            _notas_path.write_text(_nuevo_texto, encoding="utf-8")
                                        elif _notas_path.exists():
                                            _notas_path.unlink()
                                        _guardados += 1
                                    except Exception as e:
                                        _errores.append(f"texto: {e}")
                                if _ups_tema:
                                    for _up in _ups_tema:
                                        try:
                                            _ruta_nueva = _carpeta_tema / _up.name
                                            if _ruta_nueva.exists():
                                                _stem = _ruta_nueva.stem
                                                _suf = _ruta_nueva.suffix
                                                _ts = datetime.datetime.now().strftime("%H%M%S")
                                                _ruta_nueva = _carpeta_tema / f"{_stem}_{_ts}{_suf}"
                                            _ruta_nueva.write_bytes(_up.read())
                                            _guardados += 1
                                        except Exception as e:
                                            _errores.append(f"{_up.name}: {e}")
                                if _errores:
                                    for _err in _errores:
                                        st.warning(_err)
                                if _guardados > 0:
                                    st.success(f"✅ {_guardados} ítem(s) guardado(s)")
                                    st.rerun()
                                elif not _errores:
                                    st.info("Nada nuevo para guardar.")

                # ── Eliminar carpeta ──
                if st.button("🗑️ Eliminar esta partida", key=f"del_{_fid}"):
                    if _carpeta_rel:
                        import shutil
                        _carpeta_full = ROOT / _carpeta_rel
                        if _carpeta_full.exists():
                            try:
                                shutil.rmtree(_carpeta_full)
                            except Exception as e:
                                st.warning(f"No se pudo borrar la carpeta del disco: {e}")
                    del ss["fichas_arancelarias"][_fid]
                    _guardar_fichas()
                    st.rerun()
