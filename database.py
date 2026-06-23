import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

ARQUIVO_LOCAL = Path(__file__).parent / "dados_locais.json"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE", "formulario")

_client: Client | None = None

COLUNAS_EXIBICAO = {
    "id": "ID",
    "hora_inicio": "Hora de início",
    "hora_conclusao": "Hora da conclusão",
    "email": "Email",
    "nome": "Nome",
    "numero_po_com_release": "Número do PO com Release",
    "data_promessa": "Data da Promessa",
    "observacoes_coleta": "Observações de Coleta",
    "numero_nf": "Número da NF",
    "numero_linha": "Informe o número da linha",
}

CAMPOS_OBRIGATORIOS = [
    "email",
    "nome",
    "numero_po_com_release",
    "data_promessa",
    "numero_linha",
]


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def email_valido(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def supabase_configurado() -> bool:
    return bool(SUPABASE_URL.strip() and SUPABASE_KEY.strip())


def get_client() -> Client:
    global _client
    if _client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env"
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def criar_tabela() -> bool:
    """
    Verifica se a tabela está acessível no Supabase.
    Execute o SQL do README no painel Supabase para criar a tabela.
    """
    try:
        client = get_client()
        client.table(SUPABASE_TABLE).select("id").limit(1).execute()
        return True
    except Exception as exc:
        raise RuntimeError(
            f"Tabela '{SUPABASE_TABLE}' não encontrada ou inacessível. "
            "Execute o SQL do README no painel Supabase. "
            f"Detalhe: {exc}"
        ) from exc


def _carregar_locais() -> list[dict[str, Any]]:
    if not ARQUIVO_LOCAL.exists():
        return []
    with ARQUIVO_LOCAL.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _salvar_locais(registros: list[dict[str, Any]]) -> None:
    with ARQUIVO_LOCAL.open("w", encoding="utf-8") as arquivo:
        json.dump(registros, arquivo, ensure_ascii=False, indent=2, default=str)


def inserir_registro_local(dados: dict[str, Any]) -> dict[str, Any]:
    registros = _carregar_locais()
    registro = {"id": len(registros) + 1, **dados}
    registros.append(registro)
    _salvar_locais(registros)
    return registro


def buscar_locais() -> list[dict[str, Any]]:
    return list(reversed(_carregar_locais()))


def inserir_registro(dados: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    response = client.table(SUPABASE_TABLE).insert(dados).execute()
    if not response.data:
        raise RuntimeError("Não foi possível inserir o registro.")
    return response.data[0]


def buscar_todos() -> list[dict[str, Any]]:
    from planilha import carregar_respostas

    respostas_excel = carregar_respostas()
    if respostas_excel:
        return respostas_excel

    if not supabase_configurado():
        return buscar_locais()

    client = get_client()
    response = (
        client.table(SUPABASE_TABLE)
        .select("*")
        .order("id", desc=True)
        .execute()
    )
    return response.data or []


def valor_vazio(valor: Any) -> bool:
    texto = str(valor or "").strip()
    return texto in {"", "None", "—", "-", "nan", "NaT"}


def status_registro(registro: dict[str, Any]) -> str:
    sem_nf = valor_vazio(registro.get("numero_nf"))
    sem_obs = valor_vazio(registro.get("observacoes_coleta"))
    if sem_nf and sem_obs:
        return "Sem NF e observação"
    if sem_nf:
        return "Sem NF"
    if sem_obs:
        return "Sem observação"
    return "Completo"


def registro_incompleto(registro: dict[str, Any]) -> bool:
    return status_registro(registro) != "Completo"


def validar_registro(dados: dict[str, Any]) -> list[str]:
    erros: list[str] = []
    for campo in CAMPOS_OBRIGATORIOS:
        valor = dados.get(campo)
        if valor is None or str(valor).strip() == "":
            erros.append(f"O campo '{COLUNAS_EXIBICAO[campo]}' é obrigatório.")

    email = str(dados.get("email", "")).strip()
    if email and not email_valido(email):
        erros.append(
            f"Informe um e-mail válido em '{COLUNAS_EXIBICAO['email']}' "
            "(ex.: fornecedor@empresa.com)."
        )

    return erros


def formatar_datetime(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M:%S")
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return str(valor)
