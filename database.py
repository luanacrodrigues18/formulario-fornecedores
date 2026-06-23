import json
import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

ARQUIVO_LOCAL = Path(__file__).parent / "dados_locais.json"

_client: Client | None = None


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

    valor = os.getenv(chave, "").strip()
    if valor:
        return valor
    return padrao


def supabase_url() -> str:
    return _ler_config("SUPABASE_URL")


def supabase_key() -> str:
    return _ler_config("SUPABASE_KEY")


def supabase_table() -> str:
    return _ler_config("SUPABASE_TABLE", "formulario")


def supabase_storage_bucket() -> str:
    return _ler_config("SUPABASE_STORAGE_BUCKET", "Form")


def supabase_fup_file() -> str:
    return _ler_config("SUPABASE_FUP_FILE", "relatorio_fup.xlsm")

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

CAMPOS_TABELA = [
    "hora_inicio",
    "hora_conclusao",
    "email",
    "nome",
    "numero_po_com_release",
    "data_promessa",
    "observacoes_coleta",
    "numero_nf",
    "numero_linha",
]


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def email_valido(email: str) -> bool:
    return bool(EMAIL_REGEX.match(email.strip()))


def supabase_configurado() -> bool:
    return bool(supabase_url() and supabase_key())


def get_client() -> Client:
    global _client
    url = supabase_url()
    key = supabase_key()
    if _client is None:
        if not url or not key:
            raise ValueError(
                "Configure SUPABASE_URL e SUPABASE_KEY no .env ou nos Secrets do Streamlit."
            )
        _client = create_client(url, key)
    return _client


def baixar_fup_storage(destino: Path) -> None:
    url = supabase_url()
    if not url.startswith("https://") or "supabase.co" not in url:
        raise ValueError(
            f"SUPABASE_URL inválida: {url!r}. "
            "Use o Project URL copiado do painel Supabase."
        )
    client = get_client()
    bucket = supabase_storage_bucket()
    arquivo = supabase_fup_file()
    try:
        dados = client.storage.from_(bucket).download(arquivo)
    except Exception as exc:
        mensagem = str(exc)
        if "11001" in mensagem or "getaddrinfo" in mensagem.lower() or "name or service not known" in mensagem.lower():
            raise RuntimeError(
                f"Não foi possível conectar ao Supabase em {url}. "
                "Confira SUPABASE_URL nos Secrets (copie do painel, sem digitar)."
            ) from exc
        raise
    destino.write_bytes(dados)


def criar_tabela() -> bool:
    """
    Verifica se a tabela está acessível no Supabase.
    Execute o SQL do README no painel Supabase para criar a tabela.
    """
    try:
        client = get_client()
        client.table(supabase_table()).select("id").limit(1).execute()
        return True
    except Exception as exc:
        raise RuntimeError(
            f"Tabela '{supabase_table()}' não encontrada ou inacessível. "
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


def _dados_para_supabase(dados: dict[str, Any]) -> dict[str, Any]:
    return {campo: dados[campo] for campo in CAMPOS_TABELA if campo in dados}


def _chave_po_linha(numero_po: str, numero_linha: str) -> tuple[str, str]:
    return str(numero_po or "").strip().lower(), str(numero_linha or "").strip().lower()


def _buscar_supabase() -> list[dict[str, Any]]:
    client = get_client()
    response = (
        client.table(supabase_table())
        .select("*")
        .order("id", desc=True)
        .execute()
    )
    return response.data or []


def buscar_locais() -> list[dict[str, Any]]:
    return list(reversed(_carregar_locais()))


def inserir_registro(dados: dict[str, Any]) -> dict[str, Any]:
    client = get_client()
    response = client.table(supabase_table()).insert(dados).execute()
    if not response.data:
        raise RuntimeError("Não foi possível inserir o registro.")
    return response.data[0]


def salvar_registro(dados: dict[str, Any]) -> dict[str, Any]:
    if supabase_configurado():
        return inserir_registro(_dados_para_supabase(dados))

    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner_utils.script_run_context import (
            get_script_run_ctx,
        )

        if get_script_run_ctx() is not None:
            raise RuntimeError(
                "Supabase não configurado nos Secrets deste app. "
                "Adicione SUPABASE_URL e SUPABASE_KEY e salve novamente."
            )
    except RuntimeError:
        raise
    except Exception:
        pass

    from planilha import append_resposta_formulario

    return append_resposta_formulario(dados)


def buscar_resposta_por_po_linha(
    numero_po: str, numero_linha: str
) -> dict[str, Any] | None:
    chave = _chave_po_linha(numero_po, numero_linha)

    if supabase_configurado():
        try:
            for registro in _buscar_supabase():
                if _chave_po_linha(
                    registro.get("numero_po_com_release", ""),
                    registro.get("numero_linha", ""),
                ) == chave:
                    return registro
        except Exception:
            pass

    from planilha import carregar_respostas

    for registro in carregar_respostas():
        if _chave_po_linha(
            registro.get("numero_po_com_release", ""),
            registro.get("numero_linha", ""),
        ) == chave:
            return registro
    return None


def buscar_todos() -> list[dict[str, Any]]:
    if supabase_configurado():
        try:
            return _buscar_supabase()
        except Exception:
            pass

    from planilha import carregar_respostas

    respostas_excel = carregar_respostas()
    if respostas_excel:
        return respostas_excel

    return buscar_locais()


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


FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")


def agora_brasil() -> datetime:
    return datetime.now(FUSO_BRASIL)


def parse_datetime(valor: Any) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, date):
        dt = datetime.combine(valor, datetime.min.time())
    else:
        try:
            dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(FUSO_BRASIL)


def formatar_datetime(valor: Any) -> str:
    dt = parse_datetime(valor)
    if dt is None:
        return "" if valor is None else str(valor)
    return dt.strftime("%d/%m/%Y %H:%M:%S")
