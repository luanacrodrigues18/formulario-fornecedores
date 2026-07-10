from datetime import date, datetime
from pathlib import Path
import html
import warnings

import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

from database import (
    COLUNAS_EXIBICAO,
    buscar_resposta_por_po_linha,
    formatar_datetime,
    salvar_registro,
    validar_registro,
)
from alcoano import (
    ALCOANO_CSS,
    help_campo,
    render_dicas_formulario,
    render_faq,
    render_mensagem_passo,
    render_mensagem_sucesso,
)
from planilha import (
    ARQUIVO_FUP,
    buscar_por_po_e_linha,
    data_promessa_inicial,
    garantir_arquivo_fup,
    listar_fornecedores,
    rotulo_linha,
)
import planilha as planilha_mod
from auth_fornecedor import (
    autenticado,
    codigo_atual,
    filtrar_linhas_do_fornecedor,
    fornecedor_atual,
    linhas_do_fornecedor_logado,
    render_resumo_sessao_sidebar,
    render_tela_login,
)

st.set_page_config(
    page_title="Formulário de Fornecedores",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 100%;
        }
        .fornecedor-destaque {
            background: linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
            border: 1px solid #b8cfe8;
            border-radius: 12px;
            padding: 0.9rem 1.15rem;
            margin: 0.75rem 0 1rem 0;
        }
        .pedido-resumo-h {
            display: flex;
            gap: 1rem;
            margin: 0.75rem 0 1.25rem 0;
            flex-wrap: wrap;
        }
        .pedido-card {
            flex: 1;
            min-width: 160px;
            background: linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
            border: 1px solid #b8cfe8;
            border-radius: 12px;
            padding: 0.85rem 1.1rem;
        }
        .pedido-card-wide {
            flex: 2.2;
            min-width: 260px;
        }
        .pedido-card .label {
            display: block;
            font-size: 0.76rem;
            color: #64748b !important;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.35rem;
        }
        .pedido-card .valor {
            display: block;
            font-size: 1.15rem;
            font-weight: 700;
            color: #1e3a5f !important;
            line-height: 1.4;
            word-break: break-word;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1e3a5f 0%, #152a45 100%);
        }
        section[data-testid="stSidebar"] > div {
            background: transparent;
        }
        [data-testid="stSidebar"] .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.25rem 0 0.75rem 0;
        }
        [data-testid="stSidebar"] .sidebar-brand-icon {
            font-size: 1.75rem;
            line-height: 1;
        }
        [data-testid="stSidebar"] .sidebar-brand-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #f8fafc;
            line-height: 1.2;
        }
        [data-testid="stSidebar"] .sidebar-brand-sub {
            font-size: 0.78rem;
            color: #94a3b8;
            margin-top: 0.1rem;
        }
        [data-testid="stSidebar"] .sidebar-nav-label {
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #94a3b8;
            margin: 0.5rem 0 0.35rem 0;
        }
        [data-testid="stSidebar"] hr {
            border-color: rgba(255, 255, 255, 0.12);
            margin: 0.85rem 0;
        }
        [data-testid="stSidebar"] label[data-baseweb="radio"],
        [data-testid="stSidebar"] .stRadio label,
        [data-testid="stSidebar"] .stRadio label p,
        [data-testid="stSidebar"] .stRadio label span,
        [data-testid="stSidebar"] .stRadio [data-testid="stMarkdown"] p {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stRadio > div {
            gap: 0.35rem;
        }
        [data-testid="stSidebar"] .stRadio label {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 0.5rem 0.65rem !important;
        }
        [data-testid="stSidebar"] .stRadio label:hover {
            background: rgba(255, 255, 255, 0.12);
        }
        [data-testid="stSidebar"] .alcoano-wrap {
            margin: 0.5rem 0 1rem 0;
        }
        [data-testid="stSidebar"] .alcoano-bubble {
            background: rgba(255, 255, 255, 0.1);
            border-color: rgba(255, 255, 255, 0.18);
            color: #f1f5f9;
            box-shadow: none;
        }
        [data-testid="stSidebar"] .alcoano-bubble strong,
        [data-testid="stSidebar"] .alcoano-nome {
            color: #e2e8f0;
        }
        [data-testid="stSidebar"] .stExpander {
            background: rgba(255, 255, 255, 0.07) !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            border-radius: 10px;
        }
        [data-testid="stSidebar"] .streamlit-expanderHeader {
            background-color: rgba(255, 255, 255, 0.08) !important;
            color: #f8fafc !important;
            border-radius: 10px;
        }
        [data-testid="stSidebar"] .streamlit-expanderHeader p,
        [data-testid="stSidebar"] .streamlit-expanderHeader span,
        [data-testid="stSidebar"] .stExpander summary,
        [data-testid="stSidebar"] .stExpander summary p,
        [data-testid="stSidebar"] .stExpander summary span {
            color: #f8fafc !important;
        }
        [data-testid="stSidebar"] [data-testid="stExpanderDetails"] {
            background: rgba(0, 0, 0, 0.18) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        [data-testid="stSidebar"] .stExpander [data-testid="stMarkdown"] p,
        [data-testid="stSidebar"] .stExpander [data-testid="stMarkdown"] strong,
        [data-testid="stSidebar"] .stExpander [data-testid="stMarkdown"] li {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] .stExpander .stCaption,
        [data-testid="stSidebar"] .stExpander small,
        [data-testid="stSidebar"] .stExpander label {
            color: #cbd5e1 !important;
        }
        [data-testid="stSidebar"] .stExpander [data-testid="stSelectbox"] label {
            color: #e2e8f0 !important;
        }
        [data-testid="stSidebar"] .stExpander [data-baseweb="select"] > div {
            background-color: rgba(255, 255, 255, 0.1) !important;
            color: #f8fafc !important;
            border-color: rgba(255, 255, 255, 0.2) !important;
        }
        [data-testid="stSidebar"] .stExpander [data-testid="stAlert"],
        [data-testid="stSidebar"] .stExpander [data-testid="stNotificationContentInfo"] {
            background-color: rgba(255, 255, 255, 0.12) !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            color: #f1f5f9 !important;
        }
        [data-testid="stSidebar"] .stExpander [data-testid="stAlert"] p {
            color: #f1f5f9 !important;
        }
        [data-testid="stSidebar"] .stSelectbox label,
        [data-testid="stSidebar"] .stCaption,
        [data-testid="stSidebar"] small {
            color: #cbd5e1 !important;
        }
        .busca-horizontal {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 1.25rem 1.5rem 0.5rem 1.5rem;
            margin-bottom: 0.5rem;
        }
        /* Lista e cards: cores fixas (não dependem do tema do Windows) */
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio > div {
            max-height: min(58vh, 540px);
            overflow-y: auto;
            padding: 0.85rem 1rem;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            background: #f1f5f9 !important;
            color: #0f172a !important;
        }
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio label,
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio label p,
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio label span,
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio [data-testid="stMarkdown"] p {
            color: #0f172a !important;
        }
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio > div::-webkit-scrollbar {
            width: 8px;
        }
        div[data-testid="stVerticalBlock"]:has(.lista-pedidos-marker) .stRadio > div::-webkit-scrollbar-thumb {
            background: #94a3b8;
            border-radius: 4px;
        }
        .painel-selecao-lateral {
            background: #f8fafc !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 14px;
            padding: 1.15rem 1.25rem;
            position: sticky;
            top: 1.25rem;
        }
        .painel-selecao-lateral .painel-selecao-titulo {
            font-size: 0.95rem;
            font-weight: 700;
            color: #1e3a5f !important;
            margin-bottom: 0.85rem;
        }
        .pedido-card {
            background: #eef4fb !important;
            border: 1px solid #b8cfe8 !important;
        }
        .pedido-card .label {
            color: #64748b !important;
            opacity: 1 !important;
        }
        .pedido-card .valor {
            color: #1e3a5f !important;
        }
        .painel-selecao-lateral .pedido-resumo-h {
            flex-direction: column;
            margin-top: 0;
            margin-bottom: 0.75rem;
        }
        .painel-selecao-lateral .pedido-card,
        .painel-selecao-lateral .pedido-card-wide {
            min-width: 0;
            flex: none;
            width: 100%;
        }
        .secao-titulo {
            color: #1e3a5f;
            margin-bottom: 0.75rem;
        }
        .step-row { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        div[data-testid="column"] .step { margin-bottom: 0.25rem; }
        div[data-testid="stHorizontalBlock"]:has(.step) {
            margin-top: 1.5rem;
            margin-bottom: 1.25rem;
        }
        .alcoano-fluxo .alcoano-wrap {
            margin: 0.35rem 0 0.75rem 0;
            gap: 0.6rem;
            align-items: center;
            max-width: 820px;
        }
        .alcoano-fluxo .alcoano-avatar {
            width: 36px;
            height: 36px;
            border-width: 1px;
            box-shadow: 0 2px 6px rgba(30, 58, 95, 0.18);
        }
        .alcoano-fluxo .alcoano-bubble {
            flex: 1;
            padding: 0.55rem 0.8rem;
            font-size: 0.86rem;
            line-height: 1.45;
            border-radius: 10px;
            box-shadow: none;
        }
        .alcoano-fluxo .alcoano-nome {
            font-size: 0.72rem;
            margin-bottom: 0.15rem;
        }
        .step {
            flex: 1;
            text-align: center;
            padding: 0.75rem 0.5rem;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 600;
            border: 2px solid #e2e8f0;
            background: #f8fafc;
            color: #64748b;
        }
        .step.active {
            border-color: #2d5a8e;
            background: #eef4fb;
            color: #1e3a5f;
        }
        .step.done {
            border-color: #22c55e;
            background: #f0fdf4;
            color: #15803d;
        }
        .card-pedido {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.5rem;
            transition: box-shadow 0.2s;
        }
        .card-pedido:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        .badge {
            display: inline-block;
            background: #1e3a5f;
            color: white;
            padding: 0.2rem 0.6rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        div[data-testid="stForm"] {
            background: #f8fafc !important;
            padding: 1.5rem;
            border-radius: 14px;
            border: 1px solid #e2e8f0;
            color: #0f172a !important;
        }
        div[data-testid="stForm"] label,
        div[data-testid="stForm"] p,
        div[data-testid="stForm"] span,
        div[data-testid="stForm"] [data-testid="stMarkdown"] p,
        div[data-testid="stForm"] [data-testid="stMarkdown"] strong {
            color: #0f172a !important;
        }
        div[data-testid="stForm"] input,
        div[data-testid="stForm"] textarea,
        div[data-testid="stForm"] [data-baseweb="input"] input,
        div[data-testid="stForm"] [data-baseweb="textarea"] textarea,
        div[data-testid="stForm"] [data-baseweb="base-input"] {
            color: #0f172a !important;
            background-color: #ffffff !important;
            caret-color: #0f172a !important;
        }
        div[data-testid="stForm"] [data-baseweb="input"],
        div[data-testid="stForm"] [data-baseweb="textarea"] {
            background-color: #ffffff !important;
        }
        /* Área principal: evita texto invisível no Windows dark mode */
        .stApp [data-testid="stMain"] {
            color: #0f172a;
        }
        .stApp [data-testid="stMain"] h1,
        .stApp [data-testid="stMain"] h2,
        .stApp [data-testid="stMain"] h3,
        .stApp [data-testid="stMain"] p,
        .stApp [data-testid="stMain"] label,
        .stApp [data-testid="stMain"] span {
            color: inherit;
        }
        .stApp [data-testid="stMain"] .pedido-card .label {
            color: #64748b !important;
            background: transparent !important;
        }
        .stApp [data-testid="stMain"] .pedido-card .valor {
            color: #1e3a5f !important;
            background: transparent !important;
            -webkit-text-fill-color: #1e3a5f !important;
        }
        .sucesso-box {
            background: linear-gradient(135deg, #f0fdf4, #dcfce7);
            border: 1px solid #86efac;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
        }
        .sucesso-box h2 { color: #15803d; margin-bottom: 0.5rem; }
        .detalhe-tabela [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
        }
        .login-box {
            background: linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
            border: 1px solid #b8cfe8;
            border-radius: 16px;
            padding: 1.75rem 2rem;
            max-width: 520px;
            margin: 2rem auto 1.5rem auto;
            text-align: center;
        }
        .login-box h2 { color: #1e3a5f; margin: 0 0 0.5rem 0; }
        .login-box p { color: #475569; margin: 0; }
        [data-testid="stSidebar"] .sidebar-fornecedor {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 10px;
            padding: 0.75rem 0.85rem;
            margin-bottom: 0.75rem;
        }
        [data-testid="stSidebar"] .sidebar-fornecedor-label {
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
        }
        [data-testid="stSidebar"] .sidebar-fornecedor-nome {
            color: #f8fafc;
            font-weight: 700;
            font-size: 0.92rem;
            margin-top: 0.15rem;
        }
        [data-testid="stSidebar"] .sidebar-fornecedor-codigo {
            color: #cbd5e1;
            font-size: 0.8rem;
            margin-top: 0.1rem;
        }
        """
        + ALCOANO_CSS
        + """
    </style>
    """,
    unsafe_allow_html=True,
)


def _inicializar_estado() -> None:
    defaults = {
        "hora_inicio": datetime.now().isoformat(),
        "passo": 1,
        "linha_selecionada": None,
        "envio_sucesso": False,
        "ultimo_registro": None,
        "link_processado": False,
    }
    for chave, valor in defaults.items():
        if chave not in st.session_state:
            st.session_state[chave] = valor


def _render_cabecalho_fluxo(passo: int, sucesso: bool = False) -> None:
    nomes = ["1 · Buscar pedido", "2 · Escolher linha", "3 · Preencher e enviar"]
    cols = st.columns(3)
    for idx, (col, nome) in enumerate(zip(cols, nomes), start=1):
        classe = "step"
        if sucesso or idx < passo:
            classe += " done"
            icone = "✓ "
        elif idx == passo:
            classe += " active"
            icone = "→ "
        else:
            icone = ""
        with col:
            st.markdown(
                f'<div class="{classe}">{icone}{nome}</div>',
                unsafe_allow_html=True,
            )

    st.markdown('<div class="alcoano-fluxo">', unsafe_allow_html=True)
    if sucesso:
        render_mensagem_sucesso()
    else:
        render_mensagem_passo(passo)
    st.markdown("</div>", unsafe_allow_html=True)


def _filtrar_linhas(linhas: list[dict], termo: str) -> list[dict]:
    if not termo.strip():
        return linhas
    busca = termo.strip().lower()
    return [
        linha
        for linha in linhas
        if busca in linha["numero_po_com_release"].lower()
        or busca in linha["numero_linha"].lower()
        or busca in linha["descricao_item"].lower()
        or busca in linha["fornecedor"].lower()
    ]


def _render_resumo_pedido(linha: dict, rotulo_po: str = "PO com Release") -> None:
    po = html.escape(str(linha["numero_po_com_release"]))
    linha_num = html.escape(str(linha["numero_linha"]))
    fornecedor = html.escape(str(linha.get("fornecedor", "—")))
    st.markdown(
        f"""
        <div class="pedido-resumo-h">
            <div class="pedido-card">
                <span class="label" style="color:#64748b !important;">{html.escape(rotulo_po)}</span>
                <span class="valor" style="color:#1e3a5f !important;">{po}</span>
            </div>
            <div class="pedido-card">
                <span class="label" style="color:#64748b !important;">Linha</span>
                <span class="valor" style="color:#1e3a5f !important;">{linha_num}</span>
            </div>
            <div class="pedido-card pedido-card-wide">
                <span class="label" style="color:#64748b !important;">Fornecedor</span>
                <span class="valor" style="color:#1e3a5f !important;">{fornecedor}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <span class="sidebar-brand-icon">📋</span>
                <div>
                    <div class="sidebar-brand-title">Fornecedores</div>
                    <div class="sidebar-brand-sub">Formulário Alcoa</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<p class="sidebar-nav-label">Navegação</p>', unsafe_allow_html=True)
        secao = st.radio(
            "Menu",
            ["💡 Dicas", "❓ FAQ"],
            label_visibility="collapsed",
            key="sidebar_menu",
        )

        st.divider()

        render_resumo_sessao_sidebar()

        if secao.startswith("💡"):
            render_dicas_formulario()
        else:
            render_faq()


def _formatar_valor_detalhe(campo: str, valor) -> str:
    if valor is None or str(valor).strip() == "":
        return "—"
    if campo in ("hora_inicio", "hora_conclusao"):
        return formatar_datetime(valor)
    if campo == "data_promessa":
        if isinstance(valor, date):
            return valor.strftime("%d/%m/%Y")
        try:
            return datetime.fromisoformat(str(valor)[:10]).strftime("%d/%m/%Y")
        except ValueError:
            return str(valor)
    return str(valor)


def _tabela_detalhes_envio(registro: dict) -> pd.DataFrame:
    linhas = []
    for campo, titulo in COLUNAS_EXIBICAO.items():
        linhas.append(
            {
                "Campo": titulo,
                "Valor": _formatar_valor_detalhe(campo, registro.get(campo)),
            }
        )
    return pd.DataFrame(linhas)


def _resetar_fluxo() -> None:
    st.session_state.passo = 1
    st.session_state.linha_selecionada = None
    st.session_state.envio_sucesso = False
    st.session_state.ultimo_registro = None
    st.session_state.hora_inicio = datetime.now().isoformat()
    st.session_state.link_processado = False


def _aplicar_link_direto() -> None:
    if st.session_state.get("link_processado") or st.session_state.envio_sucesso:
        return

    po_link = st.query_params.get("po", "").strip()
    linha_link = st.query_params.get("linha", "").strip()
    if not po_link or not linha_link:
        return

    linhas = filtrar_linhas_do_fornecedor(buscar_por_po_e_linha(po_link, linha_link))
    st.session_state.link_processado = True

    if len(linhas) == 1:
        st.session_state.linha_selecionada = linhas[0]
        st.session_state.passo = 3
    elif len(linhas) > 1:
        st.session_state._linhas_cache = linhas
        st.session_state.passo = 2
    else:
        st.session_state._link_invalido = (po_link, linha_link)


_inicializar_estado()

_pasta_app = Path(__file__).resolve().parent
_fup_local = _pasta_app / "relatorio_fup.xlsm"
if _fup_local.is_file():
    planilha_mod.ARQUIVO_FUP = _fup_local
else:
    try:
        garantir_arquivo_fup()
    except Exception as exc:
        mensagem = str(exc)
        if "11001" in mensagem or "getaddrinfo" in mensagem.lower() or "name or service not known" in mensagem.lower():
            st.error(
                "Não foi possível conectar ao Supabase (rede da empresa pode bloquear). "
                "Coloque o arquivo **relatorio_fup.xlsm** na pasta do projeto e reinicie o app."
            )
        else:
            st.error(f"Erro ao carregar planilha base: {exc}")
        st.stop()

if not planilha_mod.ARQUIVO_FUP.exists():
    st.error(
        f"Arquivo base não encontrado: {planilha_mod.ARQUIVO_FUP.name}. "
        "Coloque o arquivo na pasta do projeto ou configure o Supabase Storage."
    )
    st.stop()

try:
    listar_fornecedores()
except Exception as exc:
    st.error(f"Erro ao ler a aba Follow-up-Release: {exc}")
    st.stop()

if not autenticado():
    _render_sidebar()
    render_tela_login()
    st.stop()

_aplicar_link_direto()

if st.session_state.get("_link_invalido"):
    po_inv, linha_inv = st.session_state._link_invalido
    st.error(
        f"Pedido não encontrado para PO **{po_inv}** e linha **{linha_inv}**. "
        "Use a busca abaixo ou verifique o link recebido."
    )
    del st.session_state._link_invalido

if (
    st.session_state.passo == 3
    and st.session_state.linha_selecionada
    and st.query_params.get("po")
    and st.query_params.get("linha")
):
    linha_link = st.session_state.linha_selecionada
    st.success(
        f"Pedido identificado pelo link: **{linha_link['numero_po_com_release']}** "
        f"| Linha **{linha_link['numero_linha']}**"
    )

_sucesso = bool(st.session_state.envio_sucesso and st.session_state.ultimo_registro)
_render_sidebar()

if _sucesso:
    reg = st.session_state.ultimo_registro
    _render_cabecalho_fluxo(3, sucesso=True)
    st.markdown(
        """
        <div class="sucesso-box">
            <h2>✅ Envio realizado com sucesso!</h2>
            <p>Seu registro foi salvo. Obrigado pelo retorno.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("PO com Release", reg.get("numero_po_com_release", ""))
    c2.metric("Linha", reg.get("numero_linha", ""))
    c3.metric("Protocolo", f"#{reg.get('id', '')}")

    with st.expander("Ver detalhes do envio", expanded=True):
        st.markdown('<div class="detalhe-tabela">', unsafe_allow_html=True)
        st.dataframe(
            _tabela_detalhes_envio(reg),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Campo": st.column_config.TextColumn("Campo", width="medium"),
                "Valor": st.column_config.TextColumn("Valor", width="large"),
            },
        )
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("➕ Enviar nova resposta", type="primary", use_container_width=True):
        _resetar_fluxo()
        st.rerun()
    st.stop()

_render_cabecalho_fluxo(st.session_state.passo)

with st.container():

    # ── PASSO 1: Busca ──────────────────────────────────────────────────────
    if st.session_state.passo == 1:
        st.markdown(f"### 👋 Olá, **{fornecedor_atual()}**")
        st.caption(f"Código do fornecedor: **{codigo_atual()}**")

        minhas_linhas = linhas_do_fornecedor_logado()
        st.info(f"Você tem **{len(minhas_linhas)}** pedido(s) vinculado(s) ao seu código.")

        st.markdown('<div class="busca-horizontal">', unsafe_allow_html=True)
        numero_po_busca = st.text_input(
            "📄 Buscar por PO com Release",
            placeholder="Ex: 4133600-23",
            help=help_campo("po"),
        )
        st.markdown("</div>", unsafe_allow_html=True)

        linhas_disponiveis: list[dict] = []
        termo_po = numero_po_busca.strip().lower()
        if termo_po:
            linhas_disponiveis = [
                linha
                for linha in minhas_linhas
                if termo_po in linha["numero_po_com_release"].lower()
            ]
        elif st.button("📦 Ver todos os meus pedidos", type="primary", use_container_width=True):
            st.session_state._linhas_cache = minhas_linhas
            st.session_state.passo = 2
            st.rerun()

        if linhas_disponiveis:
            st.session_state.passo = 2
            st.session_state._linhas_cache = linhas_disponiveis
            st.rerun()
        elif termo_po:
            st.warning("Nenhum pedido seu encontrado com esse PO. Verifique o código digitado.")

    # ── PASSO 2: Escolher linha ─────────────────────────────────────────────
    elif st.session_state.passo == 2:
        linhas_disponiveis = filtrar_linhas_do_fornecedor(
            st.session_state.get("_linhas_cache", [])
        )

        st.markdown("### 📦 Selecione a linha do pedido")
        st.markdown(
            f'<span class="badge">{len(linhas_disponiveis)} resultado(s)</span>',
            unsafe_allow_html=True,
        )

        if len(linhas_disponiveis) > 3:
            filtro = st.text_input(
                "🔎 Refinar busca",
                placeholder="Filtrar por PO, linha ou descrição do item...",
            )
            linhas_disponiveis = _filtrar_linhas(linhas_disponiveis, filtro)

        col_lista, col_detalhe = st.columns([3, 2], gap="large")

        with col_lista:
            if len(linhas_disponiveis) == 1:
                st.session_state.linha_selecionada = linhas_disponiveis[0]
                st.success("Pedido identificado automaticamente.")
            elif linhas_disponiveis:
                opcoes = {rotulo_linha(linha): linha for linha in linhas_disponiveis}
                st.markdown('<div class="lista-pedidos-marker"></div>', unsafe_allow_html=True)
                st.caption("Clique no pedido correto:")
                escolha = st.radio(
                    "Pedidos",
                    list(opcoes.keys()),
                    label_visibility="collapsed",
                )
                st.session_state.linha_selecionada = opcoes[escolha]
            else:
                st.session_state.linha_selecionada = None
                st.warning("Nenhum resultado com esse filtro.")

        with col_detalhe:
            if st.session_state.linha_selecionada:
                linha = st.session_state.linha_selecionada
                st.markdown('<div class="painel-selecao-lateral">', unsafe_allow_html=True)
                st.markdown(
                    '<p class="painel-selecao-titulo">📌 Pedido selecionado</p>',
                    unsafe_allow_html=True,
                )
                _render_resumo_pedido(linha)

                if linha.get("descricao_item"):
                    st.caption(f"📦 {linha['descricao_item']}")

                col_voltar, col_avancar = st.columns(2)
                with col_voltar:
                    if st.button("← Voltar", use_container_width=True, key="voltar_passo2"):
                        st.session_state.passo = 1
                        st.session_state.linha_selecionada = None
                        st.rerun()
                with col_avancar:
                    if st.button(
                        "Continuar →",
                        type="primary",
                        use_container_width=True,
                        key="avancar_passo2",
                    ):
                        st.session_state.passo = 3
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            elif not linhas_disponiveis:
                st.markdown('<div class="painel-selecao-lateral">', unsafe_allow_html=True)
                st.info("Ajuste o filtro ou volte para fazer uma nova busca.")
                if st.button("← Voltar à busca", use_container_width=True, key="voltar_busca_vazio"):
                    st.session_state.passo = 1
                    st.session_state.linha_selecionada = None
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # ── PASSO 3: Formulário ─────────────────────────────────────────────────
    elif st.session_state.passo == 3 and st.session_state.linha_selecionada:
        linha = st.session_state.linha_selecionada
        permitidas = {
            (item["numero_po_com_release"], item["numero_linha"])
            for item in linhas_do_fornecedor_logado()
        }
        if (linha["numero_po_com_release"], linha["numero_linha"]) not in permitidas:
            st.error("Este pedido não pertence ao seu código de fornecedor.")
            if st.button("← Voltar", type="primary", use_container_width=True):
                _resetar_fluxo()
                st.rerun()
            st.stop()

        resposta_anterior = buscar_resposta_por_po_linha(
            linha["numero_po_com_release"],
            linha["numero_linha"],
        )
        if resposta_anterior:
            st.error(
                f"Este pedido já possui resposta registrada "
                f"(ID {resposta_anterior.get('id', '—')}, "
                f"enviada em {formatar_datetime(resposta_anterior.get('hora_conclusao'))}). "
                "Não é possível enviar novamente para o mesmo PO e linha."
            )
            if st.button("← Voltar à busca", type="primary", use_container_width=True):
                _resetar_fluxo()
                st.rerun()
            st.stop()

        st.markdown("### ✍️ Complete suas informações")
        _render_resumo_pedido(linha, rotulo_po="PO")

        with st.form("formulario_fornecedor", clear_on_submit=True):
            col_contato, col_entrega, col_extra = st.columns(3)
            with col_contato:
                st.markdown("**Contato**")
                email = st.text_input(
                    f"📧 {COLUNAS_EXIBICAO['email']} *",
                    value=linha.get("email_fornecedor", ""),
                    placeholder="fornecedor@empresa.com",
                    help=help_campo("email"),
                )
                nome = st.text_input(
                    f"👤 {COLUNAS_EXIBICAO['nome']} *",
                    value=linha.get("fornecedor", ""),
                    help=help_campo("nome"),
                )
            with col_entrega:
                st.markdown("**Entrega**")
                data_promessa = st.date_input(
                    f"📅 {COLUNAS_EXIBICAO['data_promessa']} *",
                    value=data_promessa_inicial(linha),
                    format="DD/MM/YYYY",
                    help=help_campo("data_promessa"),
                )
                numero_nf = st.text_input(
                    f"🧾 {COLUNAS_EXIBICAO['numero_nf']}",
                    placeholder="Ex: 5862",
                    help=help_campo("numero_nf"),
                )
            with col_extra:
                st.markdown("**Coleta**")
                observacoes = st.text_area(
                    f"📝 {COLUNAS_EXIBICAO['observacoes_coleta']}",
                    value=linha.get("observacoes_base", ""),
                    height=148,
                    help=help_campo("observacoes_coleta"),
                )

            col_voltar, col_enviar = st.columns([1, 2])
            with col_voltar:
                voltar = st.form_submit_button("← Voltar", use_container_width=True)
            with col_enviar:
                enviar = st.form_submit_button(
                    "✅ Enviar resposta",
                    type="primary",
                    use_container_width=True,
                )

        if voltar:
            st.session_state.passo = 2
            st.rerun()

        if enviar:
            dados = {
                "hora_inicio": st.session_state.hora_inicio,
                "hora_conclusao": datetime.now().isoformat(),
                "email": email.strip(),
                "nome": nome.strip(),
                "codigo_fornecedor": codigo_atual(),
                "numero_po_com_release": linha["numero_po_com_release"],
                "data_promessa": data_promessa.isoformat(),
                "observacoes_coleta": observacoes.strip(),
                "numero_nf": numero_nf.strip(),
                "numero_linha": linha["numero_linha"],
                "indice_base": linha["indice_base"],
            }

            erros = validar_registro(dados)
            if buscar_resposta_por_po_linha(
                linha["numero_po_com_release"], linha["numero_linha"]
            ):
                st.error(
                    "Já existe uma resposta para este PO e linha. "
                    "Atualize a página ou entre em contato com a equipe Alcoa."
                )
            elif erros:
                for erro in erros:
                    st.error(erro)
            else:
                try:
                    registro = salvar_registro(dados)
                    st.session_state.ultimo_registro = registro
                    st.session_state.envio_sucesso = True
                    st.balloons()
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao salvar: {exc}")
