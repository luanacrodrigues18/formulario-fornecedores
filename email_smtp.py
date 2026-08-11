"""Envio de e-mail (SMTP) para reset de senha / 2FA."""

from __future__ import annotations

import os
import smtplib
import ssl
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


def smtp_configurado() -> bool:
    return bool(_ler_config("SMTP_HOST") and _ler_config("SMTP_FROM"))


def enviar_email(destino: str, assunto: str, corpo: str) -> None:
    destino = (destino or "").strip()
    if not destino or "@" not in destino:
        raise ValueError("E-mail de destino inválido.")
    if not smtp_configurado():
        raise RuntimeError(
            "SMTP não configurado. Defina SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD e SMTP_FROM no .env / Secrets."
        )

    host = _ler_config("SMTP_HOST")
    port = int(_ler_config("SMTP_PORT", "587") or "587")
    user = _ler_config("SMTP_USER")
    password = _ler_config("SMTP_PASSWORD")
    remetente = _ler_config("SMTP_FROM")
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
