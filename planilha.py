from __future__ import annotations

import warnings
from datetime import date, datetime
from urllib.parse import quote
from functools import lru_cache
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")


def _sem_avisos_openpyxl():
    return warnings.catch_warnings()


def _load_workbook(caminho: Path | str, **kwargs):
    with _sem_avisos_openpyxl():
        warnings.simplefilter("ignore", UserWarning)
        return load_workbook(caminho, **kwargs)

BASE_DIR = Path(__file__).parent
ARQUIVO_FUP = BASE_DIR / "relatorio_fup.xlsm"
ARQUIVO_RESPOSTAS = BASE_DIR / "formulario_respostas.xlsx"

ABA_BASE = "Follow-up-Release"
ABA_FORM = "Form1"
ABA_FORM_ALT = "Formulario_Respostas"
LINHA_CABECALHO_BASE = 10
LINHA_INICIO_DADOS = 11

COLUNAS_FORM = [
    "ID",
    "Hora de início",
    "Hora da conclusão",
    "Email",
    "Nome",
    "Número do PO com Release",
    "Data da Promessa",
    "Observações de Coleta",
    "Número da NF",
    "Informe o número da linha",
]

LARGURAS_COLUNAS = [8, 22, 22, 30, 25, 28, 18, 35, 18, 22]


def _normalizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _po_com_release(linha: tuple[Any, ...]) -> str:
    pedidos = _normalizar_texto(linha[30] if len(linha) > 30 else "")
    if pedidos and pedidos != "-":
        return pedidos

    acordo = _normalizar_texto(linha[0] if len(linha) > 0 else "")
    release = linha[1] if len(linha) > 1 else ""
    if acordo and release is not None and _normalizar_texto(release) != "":
        return f"{acordo}-{release}"
    return acordo


def _linha_para_registro(indice: int, linha: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "indice_base": indice,
        "acordo": _normalizar_texto(linha[0] if len(linha) > 0 else ""),
        "release": _normalizar_texto(linha[1] if len(linha) > 1 else ""),
        "numero_linha": _normalizar_texto(linha[6] if len(linha) > 6 else ""),
        "fornecedor": _normalizar_texto(linha[11] if len(linha) > 11 else ""),
        "email_fornecedor": _normalizar_texto(linha[26] if len(linha) > 26 else ""),
        "numero_po_com_release": _po_com_release(linha),
        "data_promessa_base": linha[31] if len(linha) > 31 else None,
        "observacoes_base": _normalizar_texto(linha[32] if len(linha) > 32 else ""),
        "descricao_item": _normalizar_texto(linha[9] if len(linha) > 9 else ""),
    }


def garantir_arquivo_fup() -> None:
    if ARQUIVO_FUP.exists():
        return

    from database import baixar_fup_storage, supabase_configurado, supabase_fup_file, supabase_storage_bucket

    if not supabase_configurado():
        raise RuntimeError(
            "Planilha base não encontrada e Supabase não configurado. "
            "Adicione SUPABASE_URL e SUPABASE_KEY no .env (local) ou nos Secrets (Streamlit Cloud)."
        )

    baixar_fup_storage(ARQUIVO_FUP)
    if not ARQUIVO_FUP.exists():
        raise RuntimeError(
            f"Não foi possível baixar {supabase_fup_file()} do bucket {supabase_storage_bucket()}."
        )
    carregar_base_fup.cache_clear()


@lru_cache(maxsize=1)
def carregar_base_fup() -> list[dict[str, Any]]:
    if not ARQUIVO_FUP.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {ARQUIVO_FUP}")

    with _sem_avisos_openpyxl():
        warnings.simplefilter("ignore", UserWarning)

        wb = _load_workbook(ARQUIVO_FUP, read_only=True, data_only=True)
        ws = wb[ABA_BASE]
        registros: list[dict[str, Any]] = []

        for indice, linha in enumerate(
            ws.iter_rows(min_row=LINHA_INICIO_DADOS, values_only=True),
            start=LINHA_INICIO_DADOS,
        ):
            if not linha or not any(linha):
                continue

            registro = _linha_para_registro(indice, linha)
            if registro["fornecedor"] and registro["numero_po_com_release"]:
                registros.append(registro)

        wb.close()

    return registros


def listar_fornecedores() -> list[str]:
    fornecedores = sorted({r["fornecedor"] for r in carregar_base_fup()})
    return fornecedores


def buscar_por_fornecedor(fornecedor: str) -> list[dict[str, Any]]:
    fornecedor = fornecedor.strip()
    return [r for r in carregar_base_fup() if r["fornecedor"] == fornecedor]


def buscar_por_po(numero_po: str) -> list[dict[str, Any]]:
    termo = numero_po.strip().lower()
    if not termo:
        return []

    return [
        r
        for r in carregar_base_fup()
        if termo in r["numero_po_com_release"].lower()
    ]


def buscar_por_po_e_linha(numero_po: str, numero_linha: str) -> list[dict[str, Any]]:
    po = numero_po.strip().lower()
    linha = numero_linha.strip()
    if not po or not linha:
        return []

    exatos = [
        r
        for r in carregar_base_fup()
        if r["numero_po_com_release"].lower() == po and r["numero_linha"] == linha
    ]
    if exatos:
        return exatos

    return [
        r
        for r in carregar_base_fup()
        if po in r["numero_po_com_release"].lower() and r["numero_linha"] == linha
    ]


def rotulo_linha(registro: dict[str, Any]) -> str:
    return (
        f"PO {registro['numero_po_com_release']} | "
        f"Linha {registro['numero_linha']} | "
        f"{registro['descricao_item'][:60]}"
    )


def _converter_data(valor: Any) -> date | None:
    if valor is None or _normalizar_texto(valor) in {"", "-"}:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.fromisoformat(str(valor)).date()
    except ValueError:
        return None


def _linha_para_registro_resposta(row: tuple[Any, ...]) -> dict[str, Any]:
    if len(row) >= 10:
        numero_nf = row[8]
        numero_linha = row[9]
    else:
        numero_nf = ""
        numero_linha = row[8] if len(row) > 8 else ""

    return {
        "id": row[0],
        "hora_inicio": row[1],
        "hora_conclusao": row[2],
        "email": row[3],
        "nome": row[4],
        "numero_po_com_release": row[5],
        "data_promessa": row[6],
        "observacoes_coleta": row[7],
        "numero_nf": numero_nf,
        "numero_linha": numero_linha,
    }


def _aplicar_estilo_cabecalho(ws) -> None:
    fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    font = Font(bold=True, color="FFFFFF")

    for col_idx, titulo in enumerate(COLUNAS_FORM, start=1):
        cell = ws.cell(row=1, column=col_idx, value=titulo)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for idx, largura in enumerate(LARGURAS_COLUNAS, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = largura

    ws.freeze_panes = "A2"


def _migrar_coluna_nf(ws) -> None:
    cabecalhos = [cell.value for cell in ws[1]]
    if not cabecalhos or "Número da NF" in cabecalhos:
        return

    ws.insert_cols(9)
    fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    font = Font(bold=True, color="FFFFFF")
    cell = ws.cell(row=1, column=9, value="Número da NF")
    cell.fill = fill
    cell.font = font
    cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.column_dimensions[get_column_letter(9)].width = 18


def _nome_aba_respostas(sheetnames: list[str]) -> str | None:
    if ABA_FORM in sheetnames:
        return ABA_FORM
    if ABA_FORM_ALT in sheetnames:
        return ABA_FORM_ALT
    return None


def _garantir_arquivo_respostas() -> None:
    if ARQUIVO_RESPOSTAS.exists():
        wb = _load_workbook(ARQUIVO_RESPOSTAS)
        nome_aba = _nome_aba_respostas(wb.sheetnames)
        if nome_aba:
            ws = wb[nome_aba]
        else:
            ws = wb.active
            ws.title = ABA_FORM
        _migrar_coluna_nf(ws)
        wb.save(ARQUIVO_RESPOSTAS)
        wb.close()
        return

    wb = Workbook()
    ws = wb.active
    ws.title = ABA_FORM
    _aplicar_estilo_cabecalho(ws)
    wb.save(ARQUIVO_RESPOSTAS)
    wb.close()


def _proximo_id() -> int:
    ids: list[int] = []

    if ARQUIVO_RESPOSTAS.exists():
        wb = _load_workbook(ARQUIVO_RESPOSTAS, read_only=True, data_only=True)
        nome_aba = _nome_aba_respostas(wb.sheetnames)
        if nome_aba:
            ws = wb[nome_aba]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and row[0] is not None:
                    try:
                        ids.append(int(row[0]))
                    except (TypeError, ValueError):
                        pass
        wb.close()

    if ARQUIVO_FUP.exists():
        wb = _load_workbook(ARQUIVO_FUP, read_only=True, data_only=True)
        if ABA_FORM in wb.sheetnames:
            ws = wb[ABA_FORM]
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row and row[0] is not None:
                    try:
                        ids.append(int(row[0]))
                    except (TypeError, ValueError):
                        pass
        wb.close()

    return max(ids, default=0) + 1


def append_resposta_formulario(dados: dict[str, Any]) -> dict[str, Any]:
    _garantir_arquivo_respostas()

    registro_id = dados.get("id") or _proximo_id()
    hora_inicio = dados.get("hora_inicio")
    hora_conclusao = dados.get("hora_conclusao")
    data_promessa = dados.get("data_promessa")

    if isinstance(hora_inicio, str):
        hora_inicio = datetime.fromisoformat(hora_inicio)
    if isinstance(hora_conclusao, str):
        hora_conclusao = datetime.fromisoformat(hora_conclusao)
    if isinstance(data_promessa, str):
        data_promessa = datetime.fromisoformat(data_promessa).date()

    linha_excel = [
        registro_id,
        hora_inicio,
        hora_conclusao,
        dados.get("email", ""),
        dados.get("nome", ""),
        dados.get("numero_po_com_release", ""),
        data_promessa,
        dados.get("observacoes_coleta", ""),
        dados.get("numero_nf", ""),
        dados.get("numero_linha", ""),
    ]

    wb = _load_workbook(ARQUIVO_RESPOSTAS)
    nome_aba = _nome_aba_respostas(wb.sheetnames) or ABA_FORM
    ws = wb[nome_aba]
    ws.append(linha_excel)
    wb.save(ARQUIVO_RESPOSTAS)
    wb.close()

    return {
        "id": registro_id,
        "hora_inicio": hora_inicio,
        "hora_conclusao": hora_conclusao,
        "email": dados.get("email", ""),
        "nome": dados.get("nome", ""),
        "numero_po_com_release": dados.get("numero_po_com_release", ""),
        "data_promessa": data_promessa.isoformat() if data_promessa else "",
        "observacoes_coleta": dados.get("observacoes_coleta", ""),
        "numero_nf": dados.get("numero_nf", ""),
        "numero_linha": dados.get("numero_linha", ""),
    }


def _chave_po_linha(numero_po: str, numero_linha: str) -> tuple[str, str]:
    return str(numero_po or "").strip().lower(), str(numero_linha or "").strip().lower()


def resposta_existe(numero_po: str, numero_linha: str) -> dict[str, Any] | None:
    chave = _chave_po_linha(numero_po, numero_linha)
    for registro in carregar_respostas():
        if _chave_po_linha(
            registro.get("numero_po_com_release", ""),
            registro.get("numero_linha", ""),
        ) == chave:
            return registro
    return None


def montar_link_formulario(base_url: str, numero_po: str, numero_linha: str) -> str:
    base = base_url.rstrip("/")
    po = quote(str(numero_po).strip())
    linha = quote(str(numero_linha).strip())
    return f"{base}?po={po}&linha={linha}"


def carregar_respostas() -> list[dict[str, Any]]:
    if not ARQUIVO_RESPOSTAS.exists():
        return []

    wb = _load_workbook(ARQUIVO_RESPOSTAS, read_only=True, data_only=True)
    nome_aba = _nome_aba_respostas(wb.sheetnames)
    if not nome_aba:
        wb.close()
        return []

    ws = wb[nome_aba]
    registros: list[dict[str, Any]] = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not any(row):
            continue
        registros.append(_linha_para_registro_resposta(row))

    wb.close()
    return list(reversed(registros))


def data_promessa_inicial(registro: dict[str, Any]) -> date:
    data_base = _converter_data(registro.get("data_promessa_base"))
    return data_base or date.today()
