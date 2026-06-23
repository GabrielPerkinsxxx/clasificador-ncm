"""
Servicio de integración con Gmail API.
Permite leer hilos de mail por URL y enviar correos.

Setup:
1. Ir a https://console.cloud.google.com/
2. Crear proyecto → Habilitar Gmail API
3. Credenciales → OAuth 2.0 → Aplicación de escritorio
4. Descargar el JSON y guardarlo como: data/gmail_credentials.json
5. La primera vez que uses Gmail desde la app, se abre el navegador para autenticar.
   El token queda guardado en data/persistencia/gmail_token.json para usos posteriores.
"""

import base64
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent

GMAIL_TOKEN_PATH       = ROOT / "data" / "persistencia" / "gmail_token.json"
GMAIL_CREDENTIALS_PATH = ROOT / "data" / "gmail_credentials.json"
DESTINATARIOS_PATH     = ROOT / "data" / "persistencia" / "destinatarios.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


# ════════════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════════════

def _check_deps():
    """Levanta ImportError descriptivo si faltan las librerías de Google."""
    try:
        import google.oauth2.credentials          # noqa
        import google_auth_oauthlib.flow          # noqa
        import google.auth.transport.requests     # noqa
        import googleapiclient.discovery          # noqa
    except ImportError:
        raise ImportError(
            "Instalá las dependencias de Google:\n"
            "  pip install google-auth google-auth-oauthlib "
            "google-auth-httplib2 google-api-python-client"
        )


def _get_gmail_service():
    """Retorna un servicio autenticado de Gmail API v1."""
    _check_deps()

    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if GMAIL_TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GMAIL_CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Archivo de credenciales Gmail no encontrado: {GMAIL_CREDENTIALS_PATH}\n\n"
                    "Seguí los pasos de configuración en services/gmail_service.py (docstring al inicio)."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GMAIL_CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        GMAIL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GMAIL_TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


# ════════════════════════════════════════════════════════════════
# LEER HILO
# ════════════════════════════════════════════════════════════════

def extraer_id_de_url(url: str) -> Optional[str]:
    """
    Extrae el ID (thread o message) de una URL de Gmail.
    La web de Gmail usa el mismo ID en la URL tanto para threads como mensajes.
    """
    match = re.search(
        r"#(?:inbox|sent|all|trash|spam|starred|label/[^/]+)/([a-zA-Z0-9+/=_-]+)",
        url,
    )
    if match:
        return match.group(1)
    # Fallback: último segmento largo
    match = re.search(r"/([a-zA-Z0-9+/=_-]{10,})(?:[?#].*)?$", url)
    if match:
        return match.group(1)
    return None


def _id_web_a_hex(web_id: str) -> str:
    """
    Convierte el ID en formato web de Gmail (base64url) al formato hex que usa la API.
    Si ya es hex o no se puede convertir, devuelve el original.
    """
    # Si ya parece hex (solo 0-9 y a-f), lo devolvemos tal cual
    if re.match(r'^[0-9a-f]+$', web_id, re.IGNORECASE):
        return web_id
    # Intentar decodificar base64url → bytes → hex
    try:
        padding = 4 - len(web_id) % 4
        padded = web_id + "=" * (padding % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return decoded.hex()
    except Exception:
        return web_id


def _decodificar_payload(payload: dict) -> str:
    """Extrae texto plano del payload de un mensaje Gmail de forma recursiva."""
    partes: list[str] = []

    def _recorrer(part):
        mime = part.get("mimeType", "")
        if mime == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                try:
                    text = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
                    partes.append(text)
                except Exception:
                    pass
        elif mime.startswith("multipart/"):
            for sub in part.get("parts", []):
                _recorrer(sub)

    _recorrer(payload)
    return "\n\n".join(p.strip() for p in partes if p.strip())


def _extraer_adjuntos(service, message_id: str, payload: dict) -> list[dict]:
    """
    Descarga los adjuntos de un mensaje Gmail.
    Retorna lista de dicts con 'nombre', 'mime', 'bytes'.
    """
    adjuntos = []

    def _recorrer(part):
        filename = part.get("filename", "")
        mime = part.get("mimeType", "")
        body = part.get("body", {})

        if filename and (body.get("attachmentId") or body.get("data")):
            try:
                if body.get("attachmentId"):
                    att = service.users().messages().attachments().get(
                        userId="me",
                        messageId=message_id,
                        id=body["attachmentId"],
                    ).execute()
                    data = att.get("data", "")
                else:
                    data = body.get("data", "")

                if data:
                    raw = base64.urlsafe_b64decode(data + "==")
                    adjuntos.append({
                        "nombre": filename,
                        "mime": mime,
                        "bytes": raw,
                    })
            except Exception:
                pass

        for sub in part.get("parts", []):
            _recorrer(sub)

    _recorrer(payload)
    return adjuntos


def buscar_threads(query: str, max_results: int = 8) -> list[dict]:
    """
    Busca hilos en Gmail usando la misma sintaxis que el buscador de Gmail.
    Retorna lista de dicts con id, subject, from_, date, snippet.
    """
    service = _get_gmail_service()
    results = service.users().threads().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    threads = results.get("threads", [])
    enriched = []
    for t in threads:
        try:
            td = service.users().threads().get(
                userId="me",
                id=t["id"],
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()
            msgs = td.get("messages", [])
            if msgs:
                headers = {
                    h["name"]: h["value"]
                    for h in msgs[0].get("payload", {}).get("headers", [])
                }
                enriched.append({
                    "id": t["id"],
                    "subject": headers.get("Subject", "(sin asunto)"),
                    "from_": headers.get("From", "—"),
                    "date": headers.get("Date", "—")[:25],
                    "snippet": t.get("snippet", ""),
                    "num_mensajes": len(msgs),
                })
        except Exception:
            continue
    return enriched


def obtener_hilo_por_id(thread_id: str) -> tuple[str, list[dict]]:
    """
    Dado el ID de hilo (formato API hex), retorna texto completo + adjuntos.
    """
    service = _get_gmail_service()
    thread = service.users().threads().get(
        userId="me",
        id=thread_id,
        format="full",
    ).execute()

    mensajes = thread.get("messages", [])
    if not mensajes:
        return "(El hilo no contiene mensajes)", []

    bloques: list[str] = []
    todos_adjuntos: list[dict] = []

    for i, msg in enumerate(mensajes, 1):
        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        remitente = headers.get("From", "—")
        fecha     = headers.get("Date", "—")
        asunto    = headers.get("Subject", "—")
        cuerpo    = _decodificar_payload(msg.get("payload", {}))
        adj_msg   = _extraer_adjuntos(service, msg["id"], msg.get("payload", {}))
        todos_adjuntos.extend(adj_msg)
        adj_nombres = ", ".join(a["nombre"] for a in adj_msg) if adj_msg else "ninguno"

        bloques.append(
            f"--- Mensaje {i}/{len(mensajes)} ---\n"
            f"De: {remitente}\n"
            f"Fecha: {fecha}\n"
            f"Asunto: {asunto}\n"
            f"Adjuntos: {adj_nombres}\n\n"
            f"{cuerpo or '(sin cuerpo de texto plano)'}"
        )

    return "\n\n".join(bloques), todos_adjuntos


def obtener_hilo_por_url(url: str) -> tuple[str, list[dict]]:
    """
    Dado un link de Gmail, devuelve el texto completo del hilo + adjuntos.

    Returns:
        (texto_hilo, lista_adjuntos)
        - texto_hilo: todos los mensajes con cabeceras
        - lista_adjuntos: lista de dicts con 'nombre', 'mime', 'bytes'

    Raises:
        ValueError: Si no se puede extraer el thread ID.
        FileNotFoundError: Si no hay credenciales configuradas.
    """
    web_id = extraer_id_de_url(url)
    if not web_id:
        raise ValueError(
            f"No se pudo extraer el ID del hilo de la URL: {url}\n"
            "Asegurate de copiar el link completo desde Gmail."
        )

    service = _get_gmail_service()

    # Estrategia 1: usar el ID tal cual como thread ID
    # Estrategia 2: convertir a hex y reintentar
    # Estrategia 3: buscar el mensaje y obtener su thread ID
    thread = None
    for id_a_probar in [web_id, _id_web_a_hex(web_id)]:
        try:
            thread = service.users().threads().get(
                userId="me",
                id=id_a_probar,
                format="full",
            ).execute()
            break
        except Exception:
            continue

    # Estrategia 3: buscar como message ID y obtener el thread
    if thread is None:
        try:
            msg = service.users().messages().get(
                userId="me",
                id=web_id,
                format="full",
            ).execute()
            thread_id_real = msg.get("threadId")
            if thread_id_real:
                thread = service.users().threads().get(
                    userId="me",
                    id=thread_id_real,
                    format="full",
                ).execute()
        except Exception:
            pass

    if thread is None:
        raise ValueError(
            "No se pudo recuperar el hilo de Gmail. "
            "Copiá el link directamente desde la barra del navegador mientras tenés el mail abierto."
        )

    mensajes = thread.get("messages", [])
    if not mensajes:
        return "(El hilo no contiene mensajes)", []

    bloques: list[str] = []
    todos_adjuntos: list[dict] = []

    for i, msg in enumerate(mensajes, 1):
        headers = {
            h["name"]: h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        remitente = headers.get("From", "—")
        fecha     = headers.get("Date", "—")
        asunto    = headers.get("Subject", "—")
        cuerpo    = _decodificar_payload(msg.get("payload", {}))

        # Adjuntos de este mensaje
        adj_msg = _extraer_adjuntos(service, msg["id"], msg.get("payload", {}))
        todos_adjuntos.extend(adj_msg)
        adj_nombres = ", ".join(a["nombre"] for a in adj_msg) if adj_msg else "ninguno"

        bloques.append(
            f"--- Mensaje {i}/{len(mensajes)} ---\n"
            f"De: {remitente}\n"
            f"Fecha: {fecha}\n"
            f"Asunto: {asunto}\n"
            f"Adjuntos: {adj_nombres}\n\n"
            f"{cuerpo or '(sin cuerpo de texto plano)'}"
        )

    return "\n\n".join(bloques), todos_adjuntos


# ════════════════════════════════════════════════════════════════
# ENVIAR MAIL
# ════════════════════════════════════════════════════════════════

def enviar_email(
    destinatarios: list[str],
    asunto: str,
    cuerpo: str,
    cuerpo_html: Optional[str] = None,
) -> None:
    """
    Envía un mail desde la cuenta Gmail autenticada.

    Args:
        destinatarios: Lista de direcciones de correo.
        asunto: Línea de asunto.
        cuerpo: Cuerpo en texto plano.
        cuerpo_html: Cuerpo HTML opcional (si se provee, se envía multipart).
    """
    service = _get_gmail_service()

    if cuerpo_html:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))
    else:
        msg = MIMEText(cuerpo, "plain", "utf-8")

    msg["to"]      = ", ".join(destinatarios)
    msg["subject"] = asunto

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ════════════════════════════════════════════════════════════════
# DESTINATARIOS PERSISTENTES
# ════════════════════════════════════════════════════════════════

def cargar_destinatarios() -> list[str]:
    """Carga la lista de destinatarios guardados desde disco."""
    if DESTINATARIOS_PATH.exists():
        try:
            import json
            return json.loads(DESTINATARIOS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def guardar_destinatarios(lista: list[str]) -> None:
    """Persiste la lista de destinatarios en disco."""
    import json
    DESTINATARIOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    DESTINATARIOS_PATH.write_text(
        json.dumps(lista, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ════════════════════════════════════════════════════════════════
# HELPERS DE ESTADO
# ════════════════════════════════════════════════════════════════

def gmail_configurado() -> bool:
    """True si hay credenciales OAuth o token guardado."""
    return GMAIL_CREDENTIALS_PATH.exists() or GMAIL_TOKEN_PATH.exists()


def gmail_autenticado() -> bool:
    """True si hay un token de acceso válido (no verifica expiración exacta)."""
    return GMAIL_TOKEN_PATH.exists()
