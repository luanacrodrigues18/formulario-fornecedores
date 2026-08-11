"""Login e cadastro do fornecedor (telas separadas + segurança)."""

from __future__ import annotations

import os

import streamlit as st

from contas_fornecedor import (
    BLOQUEIO_MINUTOS,
    MAX_FALHAS_LOGIN,
    SENHA_VALIDADE_DIAS,
    autenticar_conta,
    conta_bloqueada,
    conta_deve_trocar_senha,
    criar_conta,
    dias_para_expirar,
    garantir_arquivo_contas,
    gerar_otp,
    limpar_falhas_login,
    minutos_bloqueio_restantes,
    obter_conta,
    obter_conta_por_login,
    redefinir_senha,
    registrar_acesso,
    registrar_falha_login,
    senha_expirada,
    validar_email,
    validar_forca_senha,
    validar_usuario,
    verificar_otp,
)
from email_smtp import enviar_email, smtp_configurado
from planilha import (
    buscar_linhas_do_codigo,
    buscar_por_po_e_linha,
    resolver_fornecedor_por_codigo,
    resolver_fornecedor_por_nome,
)

ENABLE_2FA = os.getenv("ENABLE_2FA", "false").strip().lower() in {"1", "true", "yes", "sim"}


def autenticado() -> bool:
    return bool(st.session_state.get("fornecedor_codigo")) and not st.session_state.get(
        "pendente_2fa"
    ) and not st.session_state.get("forcar_troca_senha")


def codigo_atual() -> str:
    return str(st.session_state.get("fornecedor_codigo", "")).strip()


def fornecedor_atual() -> str:
    return str(st.session_state.get("fornecedor_nome", "")).strip()


def autenticar(codigo: str) -> bool:
    info = resolver_fornecedor_por_codigo(codigo)
    if not info:
        return False
    _concluir_login(info)
    return True


def _iniciar_sessao_parcial(info: dict[str, str]) -> None:
    st.session_state.fornecedor_codigo = info["codigo_fornecedor"]
    st.session_state.fornecedor_nome = info["fornecedor"]


def _concluir_login(info: dict[str, str]) -> None:
    st.session_state.fornecedor_codigo = info["codigo_fornecedor"]
    st.session_state.fornecedor_nome = info["fornecedor"]
    st.session_state.autenticado = True
    for chave in (
        "auth_tela",
        "auth_msg",
        "auth_codigo_pref",
        "pendente_2fa",
        "forcar_troca_senha",
        "otp_enviado",
        "reset_passo",
        "reset_codigo",
        "reset_email_mascara",
        "reset_otp_enviado_em",
    ):
        st.session_state.pop(chave, None)
    registrar_acesso(
        info["codigo_fornecedor"],
        "login_ok",
        fornecedor=info["fornecedor"],
    )


def logout() -> None:
    if st.session_state.get("fornecedor_codigo"):
        registrar_acesso(
            str(st.session_state.get("fornecedor_codigo", "")),
            "logout",
            fornecedor=str(st.session_state.get("fornecedor_nome", "")),
        )
    for chave in (
        "fornecedor_codigo",
        "fornecedor_nome",
        "autenticado",
        "linha_selecionada",
        "fila_pedidos",
        "envio_sucesso",
        "ultimo_registro",
        "link_processado",
        "_linhas_cache",
        "mostrar_todos",
        "auth_tela",
        "auth_msg",
        "auth_codigo_pref",
        "auth_tela_link_ok",
        "pendente_2fa",
        "forcar_troca_senha",
        "otp_enviado",
        "reset_passo",
        "reset_codigo",
        "reset_email_mascara",
        "reset_otp_enviado_em",
    ):
        st.session_state.pop(chave, None)
    st.session_state.hora_inicio = None
    st.session_state.auth_tela = "login"


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


def _validar_senha_nova(senha: str, confirmacao: str) -> str | None:
    erro = validar_forca_senha(senha)
    if erro:
        return erro
    if senha != confirmacao:
        return "A confirmação da senha não confere."
    return None


def _limpar_estado_reset() -> None:
    for chave in (
        "reset_passo",
        "reset_codigo",
        "reset_email_mascara",
        "reset_otp_enviado_em",
    ):
        st.session_state.pop(chave, None)


def _ir_para(tela: str, *, msg: str = "", codigo: str = "") -> None:
    if tela != "esqueci":
        _limpar_estado_reset()
    st.session_state.auth_tela = tela
    if msg:
        st.session_state.auth_msg = msg
    elif tela in {"cadastro", "esqueci"}:
        st.session_state.pop("auth_msg", None)
    if codigo:
        st.session_state.auth_codigo_pref = codigo
    st.rerun()


def _codigo_preferido() -> str:
    return (
        str(st.session_state.get("auth_codigo_pref", "")).strip()
        or st.query_params.get("codigo", "").strip()
    )


def _apos_senha_ok(info: dict[str, str], conta: dict) -> None:
    limpar_falhas_login(info["codigo_fornecedor"])
    _iniciar_sessao_parcial(info)

    if conta_deve_trocar_senha(conta) or senha_expirada(conta):
        st.session_state.forcar_troca_senha = True
        st.session_state.auth_tela = "redefinir"
        if conta_deve_trocar_senha(conta):
            st.session_state.auth_msg = (
                "Você entrou com uma senha temporária. "
                "Defina uma nova senha para continuar."
            )
        else:
            st.session_state.auth_msg = (
                f"Sua senha expirou (política de {SENHA_VALIDADE_DIAS} dias). "
                "Defina uma nova senha para continuar."
            )
        st.rerun()
        return

    if ENABLE_2FA and conta.get("email") and smtp_configurado():
        try:
            otp = gerar_otp(info["codigo_fornecedor"], "2fa")
            enviar_email(
                str(conta["email"]),
                "Código de acesso — Formulário Alcoa",
                f"Seu código de verificação é: {otp}\nVálido por poucos minutos.",
            )
            st.session_state.pendente_2fa = True
            st.session_state.otp_enviado = True
            st.session_state.auth_tela = "2fa"
            registrar_acesso(
                info["codigo_fornecedor"],
                "2fa_enviado",
                fornecedor=info["fornecedor"],
                detalhes=str(conta.get("email", "")),
            )
            st.rerun()
            return
        except Exception as exc:
            st.warning(f"Não foi possível enviar 2FA por e-mail ({exc}). Entrando sem 2FA.")

    _concluir_login(info)
    dias = dias_para_expirar(conta)
    if dias is not None and 0 <= dias <= 14:
        st.session_state.auth_msg_pos = (
            f"Sua senha expira em {dias} dia(s). Considere redefinir."
        )
    st.rerun()


def _tratar_falha_login(info: dict[str, str]) -> None:
    conta = registrar_falha_login(info["codigo_fornecedor"])
    registrar_acesso(
        info["codigo_fornecedor"],
        "login_fail",
        fornecedor=info["fornecedor"],
    )
    if conta and conta_bloqueada(conta):
        mins = minutos_bloqueio_restantes(conta)
        st.error(
            f"Muitas tentativas. Conta bloqueada por cerca de {mins} minuto(s) "
            f"(limite: {MAX_FALHAS_LOGIN} erros / {BLOQUEIO_MINUTOS} min)."
        )
        return
    restantes = MAX_FALHAS_LOGIN - int((conta or {}).get("falhas_login") or 0)
    st.error(f"Senha incorreta. Tentativas restantes antes do bloqueio: {max(restantes, 0)}.")


def _render_tela_cadastro() -> None:
    st.markdown(
        """
        <div class="login-box">
            <h2>📝 Cadastro</h2>
            <p>Crie seu <strong>usuário</strong> e <strong>senha</strong>.</p>
            <p>Informe também o <strong>código Alcoa</strong> da sua empresa
            (para ver só os seus pedidos).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("form_cadastro_fornecedor"):
        usuario = st.text_input(
            "Usuário (login)",
            placeholder="Ex: compras.ars",
            help="Você escolhe. Mín. 3 caracteres; letras, números, . _ -",
        )
        codigo = st.text_input(
            "Código Alcoa da empresa",
            value=_codigo_preferido(),
            placeholder="Ex: 123",
            help="Código da sua empresa no cadastro Alcoa.",
        )
        email = st.text_input(
            "E-mail corporativo *",
            placeholder="compras@empresa.com",
            help="Obrigatório. Usado para recuperar a senha se você esquecer.",
        )
        senha = st.text_input(
            "Senha",
            type="password",
            help="Mínimo 8 caracteres, com letra e número.",
        )
        confirmar = st.text_input("Confirmar senha", type="password")
        cadastrar = st.form_submit_button(
            "Criar usuário e senha",
            type="primary",
            use_container_width=True,
        )

    if st.button("Já tenho conta — ir para login", use_container_width=True):
        _ir_para("login")

    if not cadastrar:
        return

    erro_user = validar_usuario(usuario)
    if erro_user:
        st.error(erro_user)
        return

    erro_email = validar_email(email)
    if erro_email:
        st.error(erro_email)
        return

    info = resolver_fornecedor_por_codigo(codigo)
    if not info:
        st.error("Código Alcoa não encontrado. Verifique com a equipe Alcoa.")
        return

    if obter_conta(info["codigo_fornecedor"]):
        st.warning("Esta empresa já tem conta. Use a tela de login.")
        if st.button("Ir para login", type="primary"):
            _ir_para("login", codigo=info["codigo_fornecedor"])
        return

    erro = _validar_senha_nova(senha, confirmar)
    if erro:
        st.error(erro)
        return

    try:
        criar_conta(
            info["codigo_fornecedor"],
            info["fornecedor"],
            senha,
            usuario=usuario,
            email=email,
        )
        registrar_acesso(
            info["codigo_fornecedor"],
            "cadastro",
            fornecedor=info["fornecedor"],
            detalhes=f"usuario={usuario.strip().lower()};email={email}",
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    _ir_para(
        "login",
        msg="Usuário criado! Entre com seu usuário (ou código) e a senha.",
        codigo=usuario.strip().lower(),
    )


def _render_tela_login_form() -> None:
    st.markdown(
        """
        <div class="login-box">
            <h2>🔐 Login</h2>
            <p>Entre com seu <strong>usuário</strong> (ou código Alcoa) e a <strong>senha</strong>.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("auth_msg"):
        st.success(st.session_state.auth_msg)
        st.session_state.pop("auth_msg", None)

    with st.form("form_login_fornecedor"):
        login = st.text_input(
            "Usuário ou código Alcoa",
            value=_codigo_preferido(),
            placeholder="Ex: compras.ars ou 123",
        )
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Criar conta", use_container_width=True):
            _ir_para("cadastro", codigo=_codigo_preferido())
    with c2:
        if st.button("Esqueci a senha", use_container_width=True, key="btn_ir_esqueci"):
            _ir_para("esqueci", codigo=_codigo_preferido())

    if not entrar:
        return

    conta = obter_conta_por_login(login)
    if not conta:
        # Pode ser código Alcoa sem conta ainda
        info_codigo = resolver_fornecedor_por_codigo(login)
        if info_codigo and not obter_conta(info_codigo["codigo_fornecedor"]):
            st.warning("Ainda não há conta para esta empresa. Faça o cadastro primeiro.")
            if st.button("Ir para cadastro", type="primary", key="btn_ir_cadastro"):
                _ir_para("cadastro", codigo=info_codigo["codigo_fornecedor"])
            return
        st.error("Usuário/código não encontrado.")
        return

    info = {
        "codigo_fornecedor": conta["codigo_fornecedor"],
        "fornecedor": conta["fornecedor"],
    }

    if conta_bloqueada(conta):
        mins = minutos_bloqueio_restantes(conta)
        st.error(f"Conta temporariamente bloqueada. Tente de novo em ~{mins} minuto(s).")
        return

    if autenticar_conta(info["codigo_fornecedor"], senha):
        st.query_params.pop("codigo", None)
        _apos_senha_ok(info, conta)
        return

    _tratar_falha_login(info)


def _render_tela_redefinir() -> None:
    """Troca obrigatória após senha temporária/expirada — não pede senha atual."""
    forcar = bool(st.session_state.get("forcar_troca_senha"))
    if not forcar:
        # Alterar senha sem estar logado = recuperação por e-mail (sem senha atual)
        _ir_para("esqueci", codigo=_codigo_preferido() or codigo_atual())
        return

    st.markdown(
        """
        <div class="login-box">
            <h2>🔄 Defina sua nova senha</h2>
            <p>Por segurança, escolha uma <strong>nova senha</strong>
            (mín. 8 caracteres, com letra e número) antes de continuar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("auth_msg"):
        st.warning(st.session_state.auth_msg)
        st.session_state.pop("auth_msg", None)

    codigo_fix = _codigo_preferido() or codigo_atual()
    with st.form("form_redefinir_senha"):
        st.text_input(
            "Código do fornecedor",
            value=codigo_fix,
            disabled=True,
        )
        nova = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button(
            "Salvar nova senha e entrar",
            type="primary",
            use_container_width=True,
        )

    if not salvar:
        return

    info = resolver_fornecedor_por_codigo(codigo_fix)
    if not info:
        st.error("Código não encontrado.")
        return
    if not obter_conta(info["codigo_fornecedor"]):
        st.warning("Não há senha cadastrada. Faça o cadastro primeiro.")
        return

    erro = _validar_senha_nova(nova, confirmar)
    if erro:
        st.error(erro)
        return

    try:
        # Já autenticou com a senha temporária — troca sem pedir a atual de novo
        redefinir_senha(info["codigo_fornecedor"], nova, via_otp=True)
        registrar_acesso(
            info["codigo_fornecedor"],
            "senha_redefinida",
            fornecedor=info["fornecedor"],
            detalhes="apos_temporaria_ou_expirada",
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    st.session_state.pop("forcar_troca_senha", None)
    _concluir_login(info)
    st.rerun()


def _render_tela_esqueci() -> None:
    """Usa a senha temporária do dashboard e define a senha definitiva."""
    _limpar_estado_reset()
    st.markdown(
        """
        <div class="login-box">
            <h2>🔑 Esqueci a senha</h2>
            <p>Se a equipe Alcoa já te passou uma <strong>senha temporária</strong>,
            informe abaixo e escolha a <strong>sua nova senha</strong>.</p>
            <p>Ainda não tem senha temporária? Peça o reset à equipe Alcoa
            (eles geram no dashboard).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("auth_msg"):
        st.info(st.session_state.auth_msg)
        st.session_state.pop("auth_msg", None)

    with st.form("form_esqueci_temp"):
        login = st.text_input(
            "Usuário ou código Alcoa",
            value=_codigo_preferido(),
            placeholder="Ex: compras.ars ou 123",
        )
        senha_temp = st.text_input(
            "Senha temporária (recebida da Alcoa)",
            type="password",
        )
        nova = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button(
            "Salvar nova senha",
            type="primary",
            use_container_width=True,
        )

    if st.button("Voltar para login", use_container_width=True, key="esqueci_voltar"):
        _ir_para("login", codigo=_codigo_preferido())

    if not salvar:
        return

    conta = obter_conta_por_login(login)
    if not conta:
        st.error("Usuário/código não encontrado.")
        return

    info = {
        "codigo_fornecedor": conta["codigo_fornecedor"],
        "fornecedor": conta["fornecedor"],
    }

    if conta_bloqueada(conta):
        mins = minutos_bloqueio_restantes(conta)
        st.error(f"Conta temporariamente bloqueada. Tente de novo em ~{mins} minuto(s).")
        return

    if not autenticar_conta(info["codigo_fornecedor"], senha_temp):
        _tratar_falha_login(info)
        return

    erro = _validar_senha_nova(nova, confirmar)
    if erro:
        st.error(erro)
        return

    if senha_temp.strip() == nova.strip():
        st.error("A nova senha deve ser diferente da senha temporária.")
        return

    try:
        redefinir_senha(info["codigo_fornecedor"], nova, via_otp=True)
        registrar_acesso(
            info["codigo_fornecedor"],
            "senha_redefinida",
            fornecedor=info["fornecedor"],
            detalhes="via_senha_temporaria_esqueci",
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    limpar_falhas_login(info["codigo_fornecedor"])
    _ir_para(
        "login",
        msg="Senha alterada! Entre com a sua nova senha.",
        codigo=str(conta.get("usuario") or info["codigo_fornecedor"]),
    )


def _render_tela_2fa() -> None:
    info_codigo = codigo_atual() or _codigo_preferido()
    st.markdown(
        """
        <div class="login-box">
            <h2>🔐 Verificação em duas etapas</h2>
            <p>Digite o código enviado para o e-mail cadastrado.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("form_2fa"):
        otp = st.text_input("Código de 6 dígitos")
        ok = st.form_submit_button("Confirmar", type="primary", use_container_width=True)
    if st.button("Cancelar", use_container_width=True):
        logout()
        st.rerun()
    if not ok:
        return
    info = resolver_fornecedor_por_codigo(info_codigo)
    if not info or not verificar_otp(info["codigo_fornecedor"], otp, "2fa"):
        st.error("Código inválido ou expirado.")
        registrar_acesso(info_codigo, "2fa_fail", fornecedor=fornecedor_atual())
        return
    registrar_acesso(info["codigo_fornecedor"], "2fa_ok", fornecedor=info["fornecedor"])
    _concluir_login(info)
    st.rerun()


def _render_criar_senha_link(info: dict[str, str], po: str, linha: str) -> None:
    st.markdown(
        f"""
        <div class="login-box">
            <h2>📝 Cadastro</h2>
            <p>Pedido: <strong>{po}</strong> · linha <strong>{linha}</strong></p>
            <p>Empresa: <strong>{info["fornecedor"]}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("criar_senha_link_fornecedor"):
        usuario = st.text_input("Usuário (login)", placeholder="Ex: compras.ars")
        email = st.text_input(
            "E-mail corporativo *",
            placeholder="compras@empresa.com",
            help="Obrigatório para recuperar a senha se esquecer.",
        )
        senha = st.text_input("Senha", type="password")
        confirmacao = st.text_input("Confirmar senha", type="password")
        criar = st.form_submit_button(
            "Criar usuário e senha",
            type="primary",
            use_container_width=True,
        )
    if st.button("Já tenho conta — login", use_container_width=True, key="link_ir_login"):
        _ir_para("login", codigo=info["codigo_fornecedor"])
    if not criar:
        return
    erro_user = validar_usuario(usuario)
    if erro_user:
        st.error(erro_user)
        return
    erro_email = validar_email(email)
    if erro_email:
        st.error(erro_email)
        return
    erro = _validar_senha_nova(senha, confirmacao)
    if erro:
        st.error(erro)
        return
    try:
        criar_conta(
            info["codigo_fornecedor"],
            info["fornecedor"],
            senha,
            usuario=usuario,
            email=email,
        )
        registrar_acesso(info["codigo_fornecedor"], "cadastro", fornecedor=info["fornecedor"])
    except ValueError as exc:
        st.error(str(exc))
        return
    _ir_para(
        "login",
        msg="Usuário criado! Entre com usuário ou código e a senha.",
        codigo=usuario.strip().lower(),
    )


def _render_entrar_com_senha_link(info: dict[str, str], po: str, linha: str) -> None:
    st.markdown(
        f"""
        <div class="login-box">
            <h2>🔐 Login</h2>
            <p>Empresa: <strong>{info["fornecedor"]}</strong></p>
            <p>Pedido: <strong>{po}</strong> · linha <strong>{linha}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login_senha_link_fornecedor"):
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar", type="primary", use_container_width=True)
    if st.button("Esqueci a senha", key="link_esqueci"):
        _ir_para("esqueci", codigo=info["codigo_fornecedor"])
    if not entrar:
        return
    conta = obter_conta(info["codigo_fornecedor"])
    if not conta:
        st.error("Conta não encontrada.")
        return
    if conta_bloqueada(conta):
        st.error(f"Conta bloqueada ~{minutos_bloqueio_restantes(conta)} min.")
        return
    if autenticar_conta(info["codigo_fornecedor"], senha):
        _apos_senha_ok(info, conta)
        return
    _tratar_falha_login(info)


def _render_login_por_link(po: str, linha: str) -> None:
    linhas = buscar_por_po_e_linha(po, linha)
    if not linhas:
        st.error(f"Pedido não encontrado para PO **{po}** e linha **{linha}**.")
        return
    fornecedor = str(linhas[0].get("fornecedor", "")).strip()
    info = resolver_fornecedor_por_nome(fornecedor)
    if not info:
        st.error(
            f"O fornecedor **{fornecedor}** ainda não está no cadastro Alcoa."
        )
        return
    st.session_state.auth_codigo_pref = info["codigo_fornecedor"]
    tem_conta = bool(obter_conta(info["codigo_fornecedor"]))
    tela = st.session_state.get("auth_tela", "login")
    if not tem_conta:
        if tela == "login":
            st.warning("Ainda não há senha. Faça o cadastro.")
            if st.button("Ir para cadastro", type="primary", key="link_sem_conta"):
                _ir_para("cadastro", codigo=info["codigo_fornecedor"])
            return
        _render_criar_senha_link(info, po, linha)
        return
    _render_entrar_com_senha_link(info, po, linha)


def render_tela_login() -> None:
    garantir_arquivo_contas()

    if st.session_state.get("forcar_troca_senha"):
        _render_tela_redefinir()
        return
    if st.session_state.get("pendente_2fa"):
        _render_tela_2fa()
        return

    if "auth_tela" not in st.session_state:
        st.session_state.auth_tela = "login"

    tela = st.session_state.auth_tela
    if tela == "redefinir":
        _render_tela_redefinir()
        return
    if tela == "esqueci":
        _render_tela_esqueci()
        return
    if tela == "2fa":
        _render_tela_2fa()
        return
    if tela == "cadastro":
        po_link = st.query_params.get("po", "").strip()
        linha_link = st.query_params.get("linha", "").strip()
        if po_link and linha_link:
            _render_login_por_link(po_link, linha_link)
        else:
            _render_tela_cadastro()
        return

    # Link direto PO/linha: se o usuário pediu esqueci/alterar, respeita a tela
    po_link = st.query_params.get("po", "").strip()
    linha_link = st.query_params.get("linha", "").strip()
    if po_link and linha_link and tela in {"login"}:
        if "auth_tela_link_ok" not in st.session_state:
            linhas = buscar_por_po_e_linha(po_link, linha_link)
            if linhas:
                info = resolver_fornecedor_por_nome(
                    str(linhas[0].get("fornecedor", "")).strip()
                )
                if info:
                    st.session_state.auth_codigo_pref = info["codigo_fornecedor"]
                    st.session_state.auth_tela = (
                        "login" if obter_conta(info["codigo_fornecedor"]) else "cadastro"
                    )
                    if st.session_state.auth_tela == "cadastro":
                        st.session_state.auth_tela_link_ok = True
                        st.rerun()
            st.session_state.auth_tela_link_ok = True
        _render_login_por_link(po_link, linha_link)
        return

    _render_tela_login_form()


def render_resumo_sessao_sidebar() -> None:
    if not autenticado():
        return
    if st.button("Sair", use_container_width=True, key="logout_fornecedor"):
        logout()
        st.rerun()
