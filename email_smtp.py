"""Envio de e-mail opcional (SMTP) para reset/2FA."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def smtp_configurado() -> bool:
    return bool(os.getenv("SMTP_HOST", "").strip() and os.getenv("SMTP_FROM", "").strip())


def enviar_email(destino: str, assunto: str, corpo: str) -> None:
    destino = (destino or "").strip()
    if not destino or "@" not in destino:
        raise ValueError("E-mail de destino inválido.")
    if not smtp_configurado():
        raise RuntimeError(
            "SMTP não configurado. Defina SMTP_HOST, SMTP_PORT, SMTP_USER, "
            "SMTP_PASSWORD e SMTP_FROM no .env / Secrets."
        )

    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    remetente = os.getenv("SMTP_FROM", "").strip()
    usar_tls = os.getenv("SMTP_TLS", "true").strip().lower() in {"1", "true", "yes", "sim"}

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
