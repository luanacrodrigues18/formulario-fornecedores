"""Contas de fornecedor: Supabase (preferencial) + fallback JSON local."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ARQUIVO_CONTAS = Path(__file__).resolve().parent / "contas_fornecedor.json"
ARQUIVO_LOGS = Path(__file__).resolve().parent / "acessos_log.json"
TABELA_CONTAS = "contas_fornecedor"
TABELA_LOGS = "acessos_log"

MAX_FALHAS_LOGIN = int(os.getenv("MAX_FALHAS_LOGIN", "5"))
BLOQUEIO_MINUTOS = int(os.getenv("BLOQUEIO_LOGIN_MINUTOS", "15"))
SENHA_VALIDADE_DIAS = int(os.getenv("SENHA_VALIDADE_DIAS", "90"))
OTP_VALIDADE_MINUTOS = int(os.getenv("OTP_VALIDADE_MINUTOS", "10"))


def validar_forca_senha(senha: str) -> str | None:
    if len(senha) < 8:
        return "A senha deve ter pelo menos 8 caracteres."
    if not any(c.isalpha() for c in senha):
        return "A senha deve conter pelo menos uma letra."
    if not any(c.isdigit() for c in senha):
        return "A senha deve conter pelo menos um número."
    return None


def validar_email(email: str) -> str | None:
    valor = str(email or "").strip().lower()
    if not valor:
        return "Informe o e-mail corporativo."
    if "@" not in valor or "." not in valor.split("@")[-1]:
        return "E-mail inválido."
    if len(valor) < 6:
        return "E-mail inválido."
    return None


def validar_usuario(usuario: str) -> str | None:
    u = str(usuario or "").strip().lower()
    if len(u) < 3:
        return "O usuário deve ter pelo menos 3 caracteres."
    if len(u) > 40:
        return "O usuário deve ter no máximo 40 caracteres."
    if not u.replace("_", "").replace(".", "").replace("-", "").isalnum():
        return "Use só letras, números, ponto, hífen ou underline."
    return None


def _agora() -> datetime:
    return datetime.now(timezone.utc)


def _agora_iso() -> str:
    return _agora().isoformat()


def _parse_dt(valor: Any) -> datetime | None:
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    texto = str(valor).strip()
    if not texto:
        return None
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None


def _hash_senha(senha: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        salt_hex, _digest_hex = senha_hash.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    candidato = _hash_senha(senha, salt)
    return secrets.compare_digest(candidato, senha_hash)


def _usar_supabase() -> bool:
    try:
        from database import supabase_configurado

        return bool(supabase_configurado())
    except Exception:
        return False


def _client():
    from database import get_client

    return get_client()


def _tabela_disponivel(nome: str) -> bool:
    if not _usar_supabase():
        return False
    try:
        _client().table(nome).select("*").limit(1).execute()
        return True
    except Exception:
        return False


# ── JSON fallback ────────────────────────────────────────────────────────────


def _carregar_bruto() -> dict[str, Any]:
    if not ARQUIVO_CONTAS.is_file():
        return {}
    try:
        with ARQUIVO_CONTAS.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _salvar_bruto(dados: dict[str, Any]) -> None:
    with ARQUIVO_CONTAS.open("w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    try:
        from database import enviar_arquivo_storage, supabase_configurado, supabase_contas_file

        if supabase_configurado() and not _tabela_disponivel(TABELA_CONTAS):
            enviar_arquivo_storage(supabase_contas_file(), ARQUIVO_CONTAS)
    except Exception:
        pass


def garantir_arquivo_contas() -> None:
    if ARQUIVO_CONTAS.is_file() or _tabela_disponivel(TABELA_CONTAS):
        return
    try:
        from database import baixar_arquivo_storage, supabase_configurado, supabase_contas_file

        if not supabase_configurado():
            return
        baixar_arquivo_storage(supabase_contas_file(), ARQUIVO_CONTAS)
    except Exception:
        return


def _normalizar_conta(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "codigo_fornecedor": str(row.get("codigo_fornecedor", "")).strip(),
        "fornecedor": str(row.get("fornecedor", "")).strip(),
        "usuario": str(row.get("usuario", "") or "").strip().lower(),
        "senha_hash": str(row.get("senha_hash", "")),
        "email": str(row.get("email", "") or "").strip(),
        "falhas_login": int(row.get("falhas_login") or 0),
        "bloqueado_ate": row.get("bloqueado_ate"),
        "otp_hash": str(row.get("otp_hash", "") or ""),
        "otp_expira": row.get("otp_expira"),
        "otp_tipo": str(row.get("otp_tipo", "") or ""),
        "criado_em": row.get("criado_em"),
        "atualizado_em": row.get("atualizado_em") or row.get("criado_em"),
    }


def obter_conta(codigo_fornecedor: str) -> dict[str, Any] | None:
    codigo = str(codigo_fornecedor or "").strip()
    if not codigo:
        return None

    if _tabela_disponivel(TABELA_CONTAS):
        try:
            resp = (
                _client()
                .table(TABELA_CONTAS)
                .select("*")
                .eq("codigo_fornecedor", codigo)
                .limit(1)
                .execute()
            )
            if resp.data:
                conta = _normalizar_conta(resp.data[0])
                return conta if conta.get("senha_hash") else None
        except Exception:
            pass

    conta = _carregar_bruto().get(codigo)
    if isinstance(conta, dict) and conta.get("senha_hash"):
        return _normalizar_conta(conta)
    return None


def obter_conta_por_usuario(usuario: str) -> dict[str, Any] | None:
    u = str(usuario or "").strip().lower()
    if not u:
        return None

    if _tabela_disponivel(TABELA_CONTAS):
        try:
            resp = (
                _client()
                .table(TABELA_CONTAS)
                .select("*")
                .eq("usuario", u)
                .limit(1)
                .execute()
            )
            if resp.data:
                conta = _normalizar_conta(resp.data[0])
                return conta if conta.get("senha_hash") else None
        except Exception:
            pass

    for conta in _carregar_bruto().values():
        if not isinstance(conta, dict):
            continue
        if str(conta.get("usuario", "")).strip().lower() == u and conta.get("senha_hash"):
            return _normalizar_conta(conta)
    return None


def obter_conta_por_login(login: str) -> dict[str, Any] | None:
    """Aceita código do fornecedor ou nome de usuário."""
    login = str(login or "").strip()
    if not login:
        return None
    conta = obter_conta(login)
    if conta:
        return conta
    return obter_conta_por_usuario(login)


def usuario_em_uso(usuario: str, *, exceto_codigo: str = "") -> bool:
    conta = obter_conta_por_usuario(usuario)
    if not conta:
        return False
    if exceto_codigo and mesmo_codigo(conta.get("codigo_fornecedor", ""), exceto_codigo):
        return False
    return True


def mesmo_codigo(a: str, b: str) -> bool:
    return str(a or "").strip() == str(b or "").strip()


def _gravar_conta(conta: dict[str, Any]) -> dict[str, Any]:
    codigo = conta["codigo_fornecedor"]
    payload = {
        "codigo_fornecedor": codigo,
        "fornecedor": conta.get("fornecedor", ""),
        "usuario": str(conta.get("usuario", "") or "").strip().lower() or None,
        "senha_hash": conta.get("senha_hash", ""),
        "email": conta.get("email") or None,
        "falhas_login": int(conta.get("falhas_login") or 0),
        "bloqueado_ate": conta.get("bloqueado_ate"),
        "otp_hash": conta.get("otp_hash") or None,
        "otp_expira": conta.get("otp_expira"),
        "otp_tipo": conta.get("otp_tipo") or None,
        "criado_em": conta.get("criado_em") or _agora_iso(),
        "atualizado_em": conta.get("atualizado_em") or _agora_iso(),
    }

    if _tabela_disponivel(TABELA_CONTAS):
        try:
            _client().table(TABELA_CONTAS).upsert(payload, on_conflict="codigo_fornecedor").execute()
            return _normalizar_conta(payload)
        except Exception:
            pass

    dados = _carregar_bruto()
    dados[codigo] = payload
    _salvar_bruto(dados)
    return _normalizar_conta(payload)


def criar_conta(
    codigo_fornecedor: str,
    fornecedor: str,
    senha: str,
    *,
    usuario: str,
    email: str = "",
) -> dict[str, Any]:
    codigo = str(codigo_fornecedor or "").strip()
    if not codigo:
        raise ValueError("Código do fornecedor inválido.")
    erro_user = validar_usuario(usuario)
    if erro_user:
        raise ValueError(erro_user)
    erro_email = validar_email(email)
    if erro_email:
        raise ValueError(erro_email)
    erro = validar_forca_senha(senha)
    if erro:
        raise ValueError(erro)
    if obter_conta(codigo):
        raise ValueError("Esta empresa já possui senha cadastrada. Faça login.")
    usuario_norm = str(usuario).strip().lower()
    if usuario_em_uso(usuario_norm):
        raise ValueError("Este usuário já está em uso. Escolha outro.")

    agora = _agora_iso()
    conta = {
        "codigo_fornecedor": codigo,
        "fornecedor": str(fornecedor or "").strip(),
        "usuario": usuario_norm,
        "senha_hash": _hash_senha(senha),
        "email": str(email or "").strip().lower(),
        "falhas_login": 0,
        "bloqueado_ate": None,
        "otp_hash": "",
        "otp_expira": None,
        "otp_tipo": "",
        "criado_em": agora,
        "atualizado_em": agora,
    }
    return _gravar_conta(conta)


def conta_bloqueada(conta: dict[str, Any]) -> bool:
    ate = _parse_dt(conta.get("bloqueado_ate"))
    if not ate:
        return False
    return _agora() < ate


def minutos_bloqueio_restantes(conta: dict[str, Any]) -> int:
    ate = _parse_dt(conta.get("bloqueado_ate"))
    if not ate:
        return 0
    restante = ate - _agora()
    return max(0, int(restante.total_seconds() // 60) + 1)


def registrar_falha_login(codigo_fornecedor: str) -> dict[str, Any] | None:
    conta = obter_conta(codigo_fornecedor)
    if not conta:
        return None
    falhas = int(conta.get("falhas_login") or 0) + 1
    conta["falhas_login"] = falhas
    if falhas >= MAX_FALHAS_LOGIN:
        conta["bloqueado_ate"] = (_agora() + timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat()
        conta["falhas_login"] = 0
    return _gravar_conta(conta)


def limpar_falhas_login(codigo_fornecedor: str) -> None:
    conta = obter_conta(codigo_fornecedor)
    if not conta:
        return
    if int(conta.get("falhas_login") or 0) == 0 and not conta.get("bloqueado_ate"):
        return
    conta["falhas_login"] = 0
    conta["bloqueado_ate"] = None
    _gravar_conta(conta)


def autenticar_conta(codigo_fornecedor: str, senha: str) -> bool:
    conta = obter_conta(codigo_fornecedor)
    if not conta:
        return False
    if conta_bloqueada(conta):
        return False
    return verificar_senha(senha, str(conta.get("senha_hash", "")))


def senha_expirada(conta: dict[str, Any]) -> bool:
    if SENHA_VALIDADE_DIAS <= 0:
        return False
    base = _parse_dt(conta.get("atualizado_em")) or _parse_dt(conta.get("criado_em"))
    if not base:
        return False
    return _agora() > base + timedelta(days=SENHA_VALIDADE_DIAS)


def dias_para_expirar(conta: dict[str, Any]) -> int | None:
    if SENHA_VALIDADE_DIAS <= 0:
        return None
    base = _parse_dt(conta.get("atualizado_em")) or _parse_dt(conta.get("criado_em"))
    if not base:
        return None
    limite = base + timedelta(days=SENHA_VALIDADE_DIAS)
    return int((limite - _agora()).total_seconds() // 86400)


def redefinir_senha(
    codigo_fornecedor: str,
    nova_senha: str,
    *,
    senha_atual: str | None = None,
    via_otp: bool = False,
) -> dict[str, Any]:
    codigo = str(codigo_fornecedor or "").strip()
    if not codigo:
        raise ValueError("Código do fornecedor inválido.")
    erro = validar_forca_senha(nova_senha)
    if erro:
        raise ValueError(erro)

    conta = obter_conta(codigo)
    if not conta:
        raise ValueError("Não há senha cadastrada para este código. Faça o cadastro primeiro.")

    if via_otp:
        pass
    else:
        if not str(senha_atual or "").strip():
            raise ValueError("Informe a senha atual.")
        if not verificar_senha(str(senha_atual), str(conta["senha_hash"])):
            raise ValueError("Senha atual incorreta.")

    conta["senha_hash"] = _hash_senha(nova_senha)
    conta["atualizado_em"] = _agora_iso()
    conta["falhas_login"] = 0
    conta["bloqueado_ate"] = None
    conta["otp_hash"] = ""
    conta["otp_expira"] = None
    conta["otp_tipo"] = ""
    return _gravar_conta(conta)


def atualizar_email(codigo_fornecedor: str, email: str) -> dict[str, Any]:
    conta = obter_conta(codigo_fornecedor)
    if not conta:
        raise ValueError("Conta não encontrada.")
    conta["email"] = str(email or "").strip().lower()
    conta["atualizado_em"] = conta.get("atualizado_em") or _agora_iso()
    return _gravar_conta(conta)


def gerar_otp(codigo_fornecedor: str, tipo: str) -> str:
    """Gera OTP de 6 dígitos, grava hash na conta e devolve o código em claro (para e-mail)."""
    conta = obter_conta(codigo_fornecedor)
    if not conta:
        raise ValueError("Conta não encontrada.")
    codigo_otp = f"{secrets.randbelow(1_000_000):06d}"
    conta["otp_hash"] = _hash_senha(codigo_otp)
    conta["otp_expira"] = (_agora() + timedelta(minutes=OTP_VALIDADE_MINUTOS)).isoformat()
    conta["otp_tipo"] = tipo
    _gravar_conta(conta)
    return codigo_otp


def verificar_otp(codigo_fornecedor: str, codigo_otp: str, tipo: str) -> bool:
    conta = obter_conta(codigo_fornecedor)
    if not conta:
        return False
    if str(conta.get("otp_tipo", "")) != tipo:
        return False
    expira = _parse_dt(conta.get("otp_expira"))
    if not expira or _agora() > expira:
        return False
    ok = verificar_senha(str(codigo_otp).strip(), str(conta.get("otp_hash", "")))
    if ok:
        conta["otp_hash"] = ""
        conta["otp_expira"] = None
        conta["otp_tipo"] = ""
        _gravar_conta(conta)
    return ok


# ── Logs de acesso ───────────────────────────────────────────────────────────


def registrar_acesso(
    codigo_fornecedor: str,
    evento: str,
    *,
    fornecedor: str = "",
    detalhes: str = "",
) -> None:
    registro = {
        "codigo_fornecedor": str(codigo_fornecedor or "").strip(),
        "fornecedor": str(fornecedor or "").strip(),
        "evento": evento,
        "detalhes": detalhes[:500],
        "criado_em": _agora_iso(),
    }

    if _tabela_disponivel(TABELA_LOGS):
        try:
            _client().table(TABELA_LOGS).insert(registro).execute()
            return
        except Exception:
            pass

    logs: list[dict[str, Any]] = []
    if ARQUIVO_LOGS.is_file():
        try:
            with ARQUIVO_LOGS.open(encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
            if isinstance(dados, list):
                logs = dados
        except (OSError, json.JSONDecodeError):
            logs = []
    logs.append(registro)
    logs = logs[-500:]
    with ARQUIVO_LOGS.open("w", encoding="utf-8") as arquivo:
        json.dump(logs, arquivo, ensure_ascii=False, indent=2)
