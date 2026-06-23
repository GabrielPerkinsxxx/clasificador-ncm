import pandas as pd


def cargar_matriz(ruta_excel: str):
    matriz_principal = pd.read_excel(
        ruta_excel,
        sheet_name="MATRIZ DE BUSQUEDA"
    )

    matriz_mipyme = pd.read_excel(
        ruta_excel,
        sheet_name="MY PYME"
    )

    matriz_principal.columns = [str(col).strip() for col in matriz_principal.columns]
    matriz_mipyme.columns = [str(col).strip() for col in matriz_mipyme.columns]

    return matriz_principal, matriz_mipyme


def _solo_digitos(s: str) -> str:
    """Retorna solo los dígitos de un string. Ej: '8703.10.00.900' → '87031000900'."""
    return "".join(ch for ch in str(s) if ch.isdigit())


def buscar_ncm(matriz_principal, matriz_mipyme, ncm):
    ncm = str(ncm).strip()

    # Intento de búsqueda por columna principal
    posibles_columnas_principal = ["Posición SIM", "NCM", "Posicion SIM"]

    columna_principal = None
    for col in posibles_columnas_principal:
        if col in matriz_principal.columns:
            columna_principal = col
            break

    if columna_principal is None:
        raise ValueError(
            "No se encontró una columna válida de NCM en la hoja MATRIZ DE BUSQUEDA"
        )

    matriz_principal[columna_principal] = (
        matriz_principal[columna_principal].astype(str).str.strip()
    )

    # Limpiar el NCM de búsqueda (quitar punto final si lo tiene)
    ncm_clean = ncm.rstrip(".")

    # Columna auxiliar con solo dígitos (cacheada): permite matchear cualquier formato
    _DIGITS_COL = "_ncm_digits_cache"
    if _DIGITS_COL not in matriz_principal.columns:
        matriz_principal[_DIGITS_COL] = matriz_principal[columna_principal].apply(_solo_digitos)

    ncm_digits = _solo_digitos(ncm_clean)

    # 1. Búsqueda exacta por formato original
    fila = matriz_principal[matriz_principal[columna_principal] == ncm]

    # 2. Sin punto final
    if fila.empty and ncm_clean != ncm:
        fila = matriz_principal[matriz_principal[columna_principal] == ncm_clean]

    # 3. Búsqueda por dígitos (ignora puntos) — match exacto numérico
    if fila.empty and ncm_digits:
        fila = matriz_principal[matriz_principal[_DIGITS_COL] == ncm_digits]

    # 4. Prefijo por formato original
    if fila.empty and ncm_clean:
        mask = matriz_principal[columna_principal].str.startswith(ncm_clean)
        fila = matriz_principal[mask]

    # 5. Prefijo por dígitos (si el usuario puso un NCM corto, ej "8703" → match todos los que arrancan con eso)
    if fila.empty and ncm_digits:
        mask = matriz_principal[_DIGITS_COL].str.startswith(ncm_digits)
        fila = matriz_principal[mask]

    # 6. Último segmento truncado
    if fila.empty and "." in ncm_clean:
        _parts = ncm_clean.rsplit(".", 1)
        if len(_parts) == 2:
            mask2 = matriz_principal[columna_principal].str.startswith(_parts[0])
            fila = matriz_principal[mask2]

    if fila.empty:
        return None

    resultado = fila.iloc[0].to_dict()

    # Búsqueda MiPyme en hoja auxiliar
    posibles_columnas_mipyme = ["NCM", "Posición SIM", "Posicion SIM"]

    columna_mipyme = None
    for col in posibles_columnas_mipyme:
        if col in matriz_mipyme.columns:
            columna_mipyme = col
            break

    if columna_mipyme:
        matriz_mipyme[columna_mipyme] = (
            matriz_mipyme[columna_mipyme].astype(str).str.strip()
        )

        tiene_mipyme = (matriz_mipyme[columna_mipyme] == ncm).any()
        resultado["MiPyme_detectado"] = "SI" if tiene_mipyme else "NO"
    else:
        resultado["MiPyme_detectado"] = "NO"

    # Verificación adicional desde matriz principal
    if "My Pyme" in fila.columns:
        valor_mipyme = fila["My Pyme"].values[0]

        if str(valor_mipyme).strip().upper() == "SI":
            resultado["MiPyme_detectado"] = "SI"

    return resultado