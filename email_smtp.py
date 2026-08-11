"""Envio de e-mail para reset de senha / 2FA.

Suporta:
- Resend (API key) — preferencial, sem senha de Outlook/Gmail
- SMTP clássico (host + usuário + senha)
"""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import urllib.error
import urllib.request
from email.message import EmailMessage


def _ler_config(chave: str, padrao: str = "") -> str:
    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner_utils.script_run_context import (
            get_script_run_ctx,
        )

        if get_script_run_ctx() is not None and hasattr(st, "secrets"):
            if chave in st.secrets:
                return str(st.secrets[chave]).strip()
    except Exception:
        pass
    return os.getenv(chave, padrao).strip() or padrao


def _remetente() -> str:
    return _ler_config("EMAIL_FROM") or _ler_config("SMTP_FROM")


def _resend_configurado() -> bool:
    return bool(_ler_config("RESEND_API_KEY") and _remetente())


def _smtp_host_configurado() -> bool:
    return bool(_ler_config("SMTP_HOST") and _remetente())


def email_configurado() -> bool:
    return _resend_configurado() or _smtp_host_configurado()


def smtp_configurado() -> bool:
    """Compatível com o nome antigo: True se houver algum provedor de e-mail."""
    return email_configurado()


def _enviar_resend(destino: str, assunto: str, corpo: str) -> None:
    api_key = _ler_config("RESEND_API_KEY")
    remetente = _remetente()
    payload = {
        "from": remetente,
        "to": [destino],
        "subject": assunto,
        "text": corpo,
    }
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status >= 400:
                body = resp.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Resend HTTP {resp.status}: {body}")
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Resend HTTP {exc.code}: {detalhe}") from exc


def _enviar_smtp(destino: str, assunto: str, corpo: str) -> None:
    host = _ler_config("SMTP_HOST")
    port = int(_ler_config("SMTP_PORT", "587") or "587")
    user = _ler_config("SMTP_USER")
    password = _ler_config("SMTP_PASSWORD")
    remetente = _remetente()
    usar_tls = _ler_config("SMTP_TLS", "true").lower() in {"1", "true", "yes", "sim"}

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destino
    msg.set_content(corpo)

    if usar_tls:
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.starttls(context=context)
            if user:
                server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port, timeout=30) as server:
            if user:
                server.login(user, password)
            server.send_message(msg)


def enviar_email(destino: str, assunto: str, corpo: str) -> None:
    destino = (destino or "").strip()
    if not destino or "@" not in destino:
        raise ValueError("E-mail de destino inválido.")
    if not email_configurado():
        raise RuntimeError(
            "E-mail não configurado. Use Resend (RESEND_API_KEY + EMAIL_FROM "
            "ou SMTP_FROM) ou SMTP (SMTP_HOST + SMTP_FROM) no .env / Secrets."
        )

    if _resend_configurado():
        _enviar_resend(destino, assunto, corpo)
        return
    _enviar_smtp(destino, assunto, corpo)
