"""Prazo para o fornecedor preencher o formulário (definido no dashboard)."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from database import agora_brasil, parse_datetime

ARQUIVO_PRAZO = Path(__file__).resolve().parent / "prazo_resposta.json"
ARQUIVO_STORAGE_PADRAO = "prazo_resposta.json"


def _arquivo_storage() -> str:
    from database import _ler_config

    return _ler_config("SUPABASE_PRAZO_FILE", ARQUIVO_STORAGE_PADRAO)


def _sincronizar_storage() -> None:
    if not ARQUIVO_PRAZO.is_file():
        return
    try:
        from database import enviar_arquivo_storage, supabase_configurado

        if supabase_configurado():
            enviar_arquivo_storage(_arquivo_storage(), ARQUIVO_PRAZO)
    except Exception:
        pass


def garantir_arquivo_prazo() -> None:
    if ARQUIVO_PRAZO.is_file():
        return
    try:
        from database import baixar_arquivo_storage, supabase_configurado

        if supabase_configurado():
            baixar_arquivo_storage(_arquivo_storage(), ARQUIVO_PRAZO)
    except Exception:
        pass


def carregar_prazo() -> dict[str, Any] | None:
    garantir_arquivo_prazo()
    if not ARQUIVO_PRAZO.is_file():
        return None
    try:
        dados = json.loads(ARQUIVO_PRAZO.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(dados, dict) or not dados.get("data_limite"):
        return None
    return dados


def data_limite_atual() -> date | None:
    cfg = carregar_prazo()
    if not cfg:
        return None
    try:
        return date.fromisoformat(str(cfg["data_limite"])[:10])
    except ValueError:
        return None


def salvar_prazo(
    data_limite: date,
    *,
    dias_origem: int | None = None,
    observacao: str = "",
) -> dict[str, Any]:
    dados = {
        "data_limite": data_limite.isoformat(),
        "dias_origem": dias_origem,
        "observacao": (observacao or "").strip(),
        "atualizado_em": agora_brasil().isoformat(),
    }
    ARQUIVO_PRAZO.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _sincronizar_storage()
    return dados


def limpar_prazo() -> None:
    if ARQUIVO_PRAZO.is_file():
        ARQUIVO_PRAZO.unlink()
    try:
        from database import get_client, supabase_configurado, supabase_storage_bucket

        if supabase_configurado():
            get_client().storage.from_(supabase_storage_bucket()).remove([_arquivo_storage()])
    except Exception:
        pass


def dias_restantes(limite: date | None = None) -> int | None:
    limite = limite or data_limite_atual()
    if limite is None:
        return None
    return (limite - agora_brasil().date()).days


def status_prazo_envio(registro: dict[str, Any], limite: date | None = None) -> str:
    """Status do envio em relação à data limite do formulário."""
    limite = limite if limite is not None else data_limite_atual()
    if limite is None:
        return "Sem prazo"
    dt = parse_datetime(registro.get("hora_conclusao"))
    if dt is None:
        return "Sem data"
    if dt.date() <= limite:
        return "No prazo"
    return "Atrasado"


def contar_por_prazo(registros: list[dict[str, Any]], limite: date | None = None) -> dict[str, int]:
    limite = limite if limite is not None else data_limite_atual()
    contagem = {"No prazo": 0, "Atrasado": 0, "Sem data": 0, "Sem prazo": 0}
    for reg in registros:
        status = status_prazo_envio(reg, limite)
        contagem[status] = contagem.get(status, 0) + 1
    return contagem


def texto_aviso_fornecedor() -> str | None:
    limite = data_limite_atual()
    if limite is None:
        return None
    dias = dias_restantes(limite)
    data_fmt = limite.strftime("%d/%m/%Y")
    cfg = carregar_prazo() or {}
    obs = (cfg.get("observacao") or "").strip()
    extra = f" {obs}" if obs else ""

    if dias is None:
        return None
    if dias < 0:
        return (
            f"O prazo para preencher o formulário era **{data_fmt}** "
            f"({abs(dias)} dia(s) atrás). Ainda é possível enviar o retorno."
            f"{extra}"
        )
    if dias == 0:
        return (
            f"Hoje é o **último dia** para preencher o formulário "
            f"(limite: **{data_fmt}**). Informe a Data da Promessa e envie o retorno."
            f"{extra}"
        )
    return (
        f"Prazo para preencher o formulário: até **{data_fmt}** "
        f"(faltam **{dias}** dia(s)). Depois informe a Data da Promessa no retorno."
        f"{extra}"
    )


def data_limite_em_dias(dias: int, base: date | None = None) -> date:
    base = base or agora_brasil().date()
    return base + timedelta(days=max(0, int(dias)))
