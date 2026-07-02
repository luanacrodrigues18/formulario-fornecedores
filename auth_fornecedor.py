"""Login do fornecedor por código e isolamento dos dados da sessão."""

from __future__ import annotations

import streamlit as st

from planilha import (
    buscar_linhas_do_codigo,
    buscar_respostas_do_codigo,
    resolver_fornecedor_por_codigo,
)


def autenticado() -> bool:
    return bool(st.session_state.get("fornecedor_codigo"))


def codigo_atual() -> str:
    return str(st.session_state.get("fornecedor_codigo", "")).strip()


def fornecedor_atual() -> str:
    return str(st.session_state.get("fornecedor_nome", "")).strip()


def autenticar(codigo: str) -> bool:
    info = resolver_fornecedor_por_codigo(codigo)
    if not info:
        return False
    st.session_state.fornecedor_codigo = info["codigo_fornecedor"]
    st.session_state.fornecedor_nome = info["fornecedor"]
    st.session_state.autenticado = True
    return True


def logout() -> None:
    for chave in (
        "fornecedor_codigo",
        "fornecedor_nome",
        "autenticado",
        "passo",
        "linha_selecionada",
        "envio_sucesso",
        "ultimo_registro",
        "link_processado",
        "_linhas_cache",
    ):
        st.session_state.pop(chave, None)
    st.session_state.hora_inicio = None


def linhas_do_fornecedor_logado() -> list[dict]:
    if not autenticado():
        return []
    return buscar_linhas_do_codigo(codigo_atual())


def filtrar_linhas_do_fornecedor(linhas: list[dict]) -> list[dict]:
    if not autenticado():
        return linhas

    permitidas = {
        (linha["numero_po_com_release"], linha["numero_linha"])
        for linha in buscar_linhas_do_codigo(codigo_atual())
    }
    return [
        linha
        for linha in linhas
        if (linha["numero_po_com_release"], linha["numero_linha"]) in permitidas
    ]


def render_tela_login() -> None:
    codigo_url = st.query_params.get("codigo", "").strip()

    st.markdown(
        """
        <div class="login-box">
            <h2>🔐 Acesso do fornecedor</h2>
            <p>Informe o <strong>código</strong> enviado pela Alcoa para ver apenas os seus pedidos.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_fornecedor"):
        codigo = st.text_input(
            "Código do fornecedor",
            value=codigo_url,
            placeholder="Ex: 123",
            help="Código exclusivo da sua empresa no cadastro Alcoa.",
        )
        entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    if entrar:
        if autenticar(codigo):
            st.query_params.pop("codigo", None)
            st.rerun()
        st.error("Código não encontrado. Verifique com a equipe Alcoa e tente novamente.")

    st.caption(
        "Cada fornecedor enxerga somente pedidos e respostas vinculados ao seu código."
    )


def render_resumo_sessao_sidebar() -> None:
    if not autenticado():
        return

    st.markdown(
        f"""
        <div class="sidebar-fornecedor">
            <div class="sidebar-fornecedor-label">Fornecedor</div>
            <div class="sidebar-fornecedor-nome">{fornecedor_atual()}</div>
            <div class="sidebar-fornecedor-codigo">Código {codigo_atual()}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    respostas = buscar_respostas_do_codigo(codigo_atual(), fornecedor_atual())
    with st.expander(f"📬 Minhas respostas ({len(respostas)})", expanded=False):
        if not respostas:
            st.caption("Nenhum envio registrado ainda.")
        else:
            for reg in respostas[:20]:
                st.markdown(
                    f"**PO** {reg.get('numero_po_com_release', '—')} "
                    f"| **Linha** {reg.get('numero_linha', '—')}"
                )
                st.caption(f"Protocolo #{reg.get('id', '—')}")

    if st.button("Sair", use_container_width=True, key="logout_fornecedor"):
        logout()
        st.rerun()
