# Clasificador Arancelario NCM

Aplicación standalone de clasificación arancelaria con IA para Argentina (NCM 11 dígitos / Posición SIM).

Independiente — no requiere GP TRADELINK ni ningún otro sistema.

## Funcionalidad

1. **Clasificador IA**: describís el producto + opcionalmente subís fichas técnicas (PDF) e imágenes; Claude propone 2-3 NCMs con justificación, RGI aplicadas y nivel de confianza.
2. **Consulta NCM**: buscás un código y obtenés tributos (DIE/AEC/TE/IVA/Ganancias/IIBB), flags regulatorios (DUMPING, BK, seguridad eléctrica, MiPyme) y carga tributaria estimada sobre CIF.
3. **Fichas guardadas**: histórico local de clasificaciones realizadas.

## Instalación

```bash
cd "/Users/noorus/Desktop/IA FULL/CLASIFICADOR NCM"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editá .env y poné tu ANTHROPIC_API_KEY
```

## Uso

```bash
source .venv/bin/activate
streamlit run app.py
```

Abrí http://localhost:8501 en el navegador.

## Estructura

```
CLASIFICADOR NCM/
├── app.py                       # Entrypoint Streamlit (3 tabs)
├── lector_matriz.py             # Carga y búsqueda en matriz NCM
├── services/
│   └── clasificador_ncm.py      # Motor IA (Claude) + cruce con matriz
├── data/
│   ├── matriz_ncm.xlsx          # Matriz NCM (origen: Tarifar)
│   └── persistencia/
│       └── fichas_arancelarias.json   # Histórico local de fichas
├── .streamlit/config.toml       # Tema visual
├── .env                         # ANTHROPIC_API_KEY (no se commitea)
└── requirements.txt
```

## Actualización de la matriz NCM

La matriz `data/matriz_ncm.xlsx` proviene de Tarifar. Cuando haya cambios (DIE, IVA, intervenciones, etc.), reemplazá ese archivo manteniendo las hojas:

- `MATRIZ DE BUSQUEDA` — columnas: Posición SIM, AEC %, DIE %, TE %, DII %, IVA %, IVA Ad. %, Ganancias %, IIBB %, LNA, CHAS, SEGURIDAD ELECTRICA, DUMPING, DJCP, ACEROS PARA CONSTRUCCION, ESTAMPILLADO, BK, My Pyme
- `MY PYME` — listado de NCMs con beneficio MiPyme

## Roadmap

- Cargar descripciones oficiales del NCM (capítulo/partida/subpartida) y pasárselas al modelo como contexto
- Usar el histórico de fichas guardadas como ejemplos few-shot (RAG)
- Validación post-IA: si el modelo propone un NCM inexistente, sugerir el más cercano
- Notas de Sección y Capítulo + RGI completo en el prompt
- Export PDF de la justificación legal para auditoría ARCA
