"""Assistente ALUX — mascote e ajuda contextual do formulário."""

import base64
import re
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent
IMG_ALCOANO = BASE_DIR / "alcoano.png"

MENSAGENS_PASSO = {
    1: (
        "Oi! Sou o **ALUX**, seu assistente Alcoa. "
        "No passo 1, busque seu pedido pelo **nome da empresa** ou pelo **PO com Release** "
        "que você recebeu por e-mail."
    ),
    2: (
        "Ótimo progresso! Agora escolha a **linha correta** do pedido. "
        "Se houver várias linhas, confira a descrição do item antes de continuar."
    ),
    3: (
        "Quase lá! Confira o **e-mail**, a **data de promessa** e, se já tiver, "
        "informe a **NF** e **observações de coleta**. Depois é só enviar."
    ),
}

MENSAGEM_SUCESSO = (
    "Missão cumprida! Seu envio foi registrado com sucesso. "
    "Guarde o **número de protocolo**  ele identifica sua resposta."
)

DICAS_CAMPOS = {
    "email": "Use um e-mail válido da sua empresa. A Alcoa pode usar esse contato para retorno.",
    "nome": "Informe o nome da empresa fornecedora, como consta no pedido.",
    "data_promessa": "Data em que o material estará disponível para coleta ou entrega conforme combinado.",
    "observacoes_coleta": "Detalhes úteis: horário de coleta, restrições de acesso, contato no local, etc.",
    "numero_nf": "Número da Nota Fiscal, se já emitida. Se ainda não tiver, pode deixar em branco e completar depois.",
    "po": "Código completo do pedido, geralmente no formato **4133600-23** (número + release).",
    "linha": "Número da linha do item dentro do PO — aparece no pedido ou no link que você recebeu.",
}

FAQ: list[tuple[str, str]] = [
    (
        "O que é PO com Release?",
        "É o código completo do pedido de compra, formado pelo número do acordo e pelo release "
        "(ex.: **4133600-23**). Você encontra esse código no e-mail ou documento enviado pela Alcoa.",
    ),
    (
        "Onde encontro o número da linha?",
        "Cada item do pedido tem uma **linha** (ex.: 17). Ela aparece na lista de itens do PO "
        "e também no link direto quando a Alcoa envia o formulário pronto.",
    ),
    (
        "Posso enviar mais de uma vez para o mesmo pedido?",
        "Não. O sistema aceita **uma resposta por PO + linha** para evitar duplicidade. "
        "Se precisar corrigir algo, entre em contato com a equipe Alcoa.",
    ),
    (
        "O que colocar em Observações de Coleta?",
        "Informações que ajudem na logística: horário disponível, pessoa de contato, "
        "restrições de acesso à planta, instruções especiais de embarque, etc.",
    ),
    (
        "Preciso informar a Nota Fiscal (NF)?",
        "Se a NF **já foi emitida**, informe o número. Se ainda não emitiu, pode enviar sem NF — "
        "o registro ficará marcado como pendente até você complementar com a equipe Alcoa.",
    ),
    (
        "Qual e-mail devo usar?",
        "Use um e-mail **corporativo válido** da sua empresa (ex.: compras@fornecedor.com.br). "
        "Evite e-mails genéricos ou pessoais que a equipe não consiga identificar.",
    ),
    (
        "Recebi um link por e-mail — como uso?",
        "Clique no link recebido. Ele abre o formulário **já com PO e linha preenchidos**. "
        "Basta revisar os dados e concluir o envio.",
    ),
    (
        "Não encontrei meu pedido na busca",
        "Confira se o **PO com Release** está completo e correto. "
        "Se buscar por fornecedor, selecione o nome **exatamente** como cadastrado. "
        "Persistindo a dúvida, contate a equipe Alcoa.",
    ),
    (
        "Posso alterar uma resposta já enviada?",
        "Pelo formulário, não — o envio fica registrado. Para correções, "
        "informe o **número de protocolo** (ID) à equipe Alcoa responsável.",
    ),
    (
        "Quem recebe os dados que envio?",
        "As respostas ficam disponíveis para a **equipe interna Alcoa** no dashboard de follow-up "
        "e são usadas para acompanhar promessas de entrega e coletas.",
    ),
]

ALCOANO_CSS = """
.alcoano-wrap {
    display: flex;
    gap: 1rem;
    align-items: flex-start;
    margin: 2rem 0 1.75rem 0;
}
.alcoano-avatar {
    flex-shrink: 0;
    width: 52px;
    height: 52px;
    border-radius: 50%;
    background: #ffffff;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(30, 58, 95, 0.25);
    border: 2px solid #ffffff;
}
.alcoano-avatar .alcoano-img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.alcoano-bubble {
    flex: 1;
    background: linear-gradient(135deg, #eef4fb 0%, #f8fafc 100%);
    border: 1px solid #b8cfe8;
    border-radius: 14px;
    padding: 0.95rem 1.15rem;
    color: #1e3a5f;
    font-size: 0.98rem;
    line-height: 1.55;
    box-shadow: 0 2px 8px rgba(30, 58, 95, 0.06);
}
.alcoano-bubble strong { color: #1e3a5f; }
.alcoano-nome {
    font-weight: 700;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #2d5a8e;
    margin-bottom: 0.35rem;
}
.alcoano-dica {
    background: #fff;
    border-left: 3px solid #2d5a8e;
    padding: 0.65rem 0.85rem;
    margin: 0.35rem 0;
    border-radius: 0 8px 8px 0;
    font-size: 0.9rem;
    color: #334155;
}
"""


def _formatar_negrito(texto: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", texto)


def imagem_alcoano_b64() -> str | None:
    if IMG_ALCOANO.exists():
        return base64.b64encode(IMG_ALCOANO.read_bytes()).decode()
    return None


def html_avatar_alcoano() -> str:
    b64 = imagem_alcoano_b64()
    if b64:
        return f'<img src="data:image/png;base64,{b64}" alt="ALUX" class="alcoano-img" />'
    return "🤖"


def html_logo_hero() -> str:
    b64 = imagem_alcoano_b64()
    if not b64:
        return ""
    return (
        f'<div class="hero-logo hero-logo-alcoano">'
        f'<img src="data:image/png;base64,{b64}" alt="ALUX" />'
        f"</div>"
    )


def render_bubble(mensagem: str, nome: str = "ALUX") -> None:
    avatar = html_avatar_alcoano()
    corpo = _formatar_negrito(mensagem)
    st.markdown(
        f"""
        <div class="alcoano-wrap">
            <div class="alcoano-avatar" title="{nome}">{avatar}</div>
            <div class="alcoano-bubble">
                <div class="alcoano-nome">{nome}</div>
                {corpo}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mensagem_passo(passo: int, compact: bool = False) -> None:
    mensagem = MENSAGENS_PASSO.get(passo)
    if mensagem:
        render_bubble(mensagem)


def render_mensagem_sucesso(compact: bool = False) -> None:
    render_bubble(MENSAGEM_SUCESSO)


def render_dicas_formulario() -> None:
    with st.expander("💡 Dicas do ALUX: o que preencher em cada campo", expanded=False):
        st.markdown(
            """
            <style>
            .alcoano-dica-label { font-weight: 600; color: #1e3a5f; margin-bottom: 0.15rem; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        for rotulo, chave in [
            ("📧 E-mail", "email"),
            ("👤 Nome / Fornecedor", "nome"),
            ("📅 Data da Promessa", "data_promessa"),
            ("📝 Observações de Coleta", "observacoes_coleta"),
            ("🧾 Número da NF", "numero_nf"),
        ]:
            st.markdown(f"**{rotulo}**")
            st.caption(DICAS_CAMPOS[chave])


def render_faq() -> None:
    with st.expander("❓ Perguntas frequentes ALUX", expanded=False):
        opcoes = [pergunta for pergunta, _ in FAQ]
        escolha = st.selectbox(
            "Selecione uma dúvida:",
            opcoes,
            index=0,
            label_visibility="collapsed",
        )
        for pergunta, resposta in FAQ:
            if pergunta == escolha:
                st.info(resposta)
                break


def help_campo(chave: str) -> str:
    return f"ALUX: {DICAS_CAMPOS.get(chave, '')}"
