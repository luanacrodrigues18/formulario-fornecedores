"""Login e cadastro do fornecedor (telas separadas + segurança)."""

from __future__ import annotations

import os
from time import time

import streamlit as st

from contas_fornecedor import (
    BLOQUEIO_MINUTOS,
    MAX_FALHAS_LOGIN,
    OTP_VALIDADE_MINUTOS,
    SENHA_VALIDADE_DIAS,
    autenticar_conta,
    conta_bloqueada,
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
RESET_OTP_REENVIAR_SEGUNDOS = 60


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


def _mascarar_email(email: str) -> str:
    valor = str(email or "").strip()
    if "@" not in valor:
        return "***"
    local, dominio = valor.split("@", 1)
    if len(local) <= 1:
        local_m = "*"
    else:
        local_m = local[0] + "***"
    return f"{local_m}@{dominio}"


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

    if senha_expirada(conta):
        st.session_state.forcar_troca_senha = True
        st.session_state.auth_tela = "redefinir"
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
        if st.button("Esqueci / alterar senha", use_container_width=True, key="btn_ir_esqueci"):
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
    """Só usada na troca obrigatória (senha expirada) — ainda exige senha atual."""
    forcar = bool(st.session_state.get("forcar_troca_senha"))
    if not forcar:
        # Alterar senha sem estar logado = recuperação por e-mail (sem senha atual)
        _ir_para("esqueci", codigo=_codigo_preferido() or codigo_atual())
        return

    st.markdown(
        """
        <div class="login-box">
            <h2>🔄 Troca obrigatória de senha</h2>
            <p>Sua senha expirou. Informe a <strong>senha atual</strong>
            e a <strong>nova senha</strong> (mín. 8, letra e número).</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("auth_msg"):
        st.warning(st.session_state.auth_msg)
        st.session_state.pop("auth_msg", None)

    with st.form("form_redefinir_senha"):
        codigo = st.text_input(
            "Código do fornecedor",
            value=_codigo_preferido() or codigo_atual(),
            placeholder="Ex: 123",
        )
        senha_atual = st.text_input("Senha atual", type="password")
        nova = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button(
            "Salvar nova senha",
            type="primary",
            use_container_width=True,
        )

    if not salvar:
        return

    info = resolver_fornecedor_por_codigo(codigo)
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
        redefinir_senha(info["codigo_fornecedor"], nova, senha_atual=senha_atual)
        registrar_acesso(
            info["codigo_fornecedor"],
            "senha_redefinida",
            fornecedor=info["fornecedor"],
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    st.session_state.pop("forcar_troca_senha", None)
    _concluir_login(info)
    st.rerun()


def _enviar_otp_reset(conta: dict, info: dict[str, str]) -> None:
    email = str(conta.get("email") or "").strip().lower()
    otp = gerar_otp(info["codigo_fornecedor"], "reset")
    enviar_email(
        email,
        "Código para redefinir senha — Formulário Alcoa",
        (
            f"Olá,\n\n"
            f"Seu código para redefinir a senha é: {otp}\n"
            f"Válido por cerca de {OTP_VALIDADE_MINUTOS} minuto(s).\n\n"
            f"Se você não pediu isso, ignore este e-mail.\n"
        ),
    )
    st.session_state.reset_passo = 2
    st.session_state.reset_codigo = info["codigo_fornecedor"]
    st.session_state.reset_email_mascara = _mascarar_email(email)
    st.session_state.reset_otp_enviado_em = time()
    registrar_acesso(
        info["codigo_fornecedor"],
        "senha_reset_otp",
        fornecedor=info["fornecedor"],
        detalhes=_mascarar_email(email),
    )


def _render_tela_esqueci() -> None:
    st.markdown(
        """
        <div class="login-box">
            <h2>🔑 Esqueci / alterar senha</h2>
            <p>Enviaremos um <strong>código de 6 dígitos</strong> para o e-mail
            cadastrado. Com ele você define a <strong>nova senha</strong>
            — <strong>não precisa</strong> da senha atual.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not smtp_configurado():
                st.warning(
            "Recuperação por e-mail indisponível no momento "
            "(configure RESEND_API_KEY + EMAIL_FROM, ou SMTP). "
            "Contate a equipe Alcoa."
        )
        if st.button("Voltar para login", use_container_width=True, key="esqueci_smtp_voltar"):
            _ir_para("login", codigo=_codigo_preferido())
        return

    if st.session_state.get("auth_msg"):
        st.info(st.session_state.auth_msg)
        st.session_state.pop("auth_msg", None)

    passo = int(st.session_state.get("reset_passo") or 1)

    if passo < 2:
        with st.form("form_esqueci_passo1"):
            login = st.text_input(
                "Usuário ou código Alcoa",
                value=_codigo_preferido(),
                placeholder="Ex: compras.ars ou 123",
            )
            email = st.text_input(
                "E-mail cadastrado",
                placeholder="compras@empresa.com",
                help="Deve ser o mesmo e-mail informado no cadastro.",
            )
            enviar = st.form_submit_button(
                "Enviar código",
                type="primary",
                use_container_width=True,
            )
        if st.button("Voltar para login", use_container_width=True, key="esqueci_voltar1"):
            _ir_para("login", codigo=_codigo_preferido())
        if not enviar:
            return

        erro_email = validar_email(email)
        if erro_email:
            st.error(erro_email)
            return

        conta = obter_conta_por_login(login)
        email_norm = email.strip().lower()
        # Mensagem genérica para não revelar se a conta existe
        msg_generica = (
            "Se os dados estiverem corretos, enviaremos um código para o e-mail informado. "
            "Verifique a caixa de entrada."
        )
        if not conta:
            st.info(msg_generica)
            return
        email_conta = str(conta.get("email") or "").strip().lower()
        if not email_conta:
            st.error(
                "Esta conta não tem e-mail cadastrado. "
                "Cadastre um e-mail ou peça suporte à equipe Alcoa."
            )
            return
        if email_conta != email_norm:
            st.info(msg_generica)
            return

        info = {
            "codigo_fornecedor": conta["codigo_fornecedor"],
            "fornecedor": conta["fornecedor"],
        }
        try:
            _enviar_otp_reset(conta, info)
        except Exception as exc:
            st.error(f"Não foi possível enviar o e-mail: {exc}")
            return
        st.session_state.auth_msg = (
            f"Código enviado para {_mascarar_email(email_conta)}. "
            f"Válido por cerca de {OTP_VALIDADE_MINUTOS} minuto(s)."
        )
        st.rerun()
        return

    mascara = st.session_state.get("reset_email_mascara", "***")
    st.success(f"Código enviado para **{mascara}**.")

    with st.form("form_esqueci_passo2"):
        otp = st.text_input("Código de 6 dígitos")
        nova = st.text_input("Nova senha", type="password")
        confirmar = st.text_input("Confirmar nova senha", type="password")
        salvar = st.form_submit_button(
            "Salvar nova senha",
            type="primary",
            use_container_width=True,
        )

    c_re, c_vol = st.columns(2)
    with c_re:
        if st.button("Reenviar código", use_container_width=True, key="esqueci_reenviar"):
            ultimo = float(st.session_state.get("reset_otp_enviado_em") or 0)
            faltam = RESET_OTP_REENVIAR_SEGUNDOS - (time() - ultimo)
            if faltam > 0:
                st.warning(f"Aguarde {int(faltam)} segundo(s) antes de reenviar.")
            else:
                codigo = str(st.session_state.get("reset_codigo") or "")
                conta = obter_conta(codigo)
                info = resolver_fornecedor_por_codigo(codigo)
                if conta and info:
                    try:
                        _enviar_otp_reset(conta, info)
                        st.session_state.auth_msg = "Novo código enviado."
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Falha ao reenviar: {exc}")
                else:
                    st.error("Sessão de recuperação inválida. Comece de novo.")
                    _limpar_estado_reset()
    with c_vol:
        if st.button("Voltar para login", use_container_width=True, key="esqueci_voltar2"):
            _ir_para("login", codigo=_codigo_preferido())

    if not salvar:
        return

    codigo = str(st.session_state.get("reset_codigo") or "")
    info = resolver_fornecedor_por_codigo(codigo)
    if not info:
        st.error("Sessão de recuperação inválida. Comece de novo.")
        _limpar_estado_reset()
        return

    erro = _validar_senha_nova(nova, confirmar)
    if erro:
        st.error(erro)
        return

    if not verificar_otp(info["codigo_fornecedor"], otp, "reset"):
        st.error("Código inválido ou expirado.")
        registrar_acesso(
            info["codigo_fornecedor"],
            "senha_reset_otp_fail",
            fornecedor=info["fornecedor"],
        )
        return

    try:
        redefinir_senha(info["codigo_fornecedor"], nova, via_otp=True)
        registrar_acesso(
            info["codigo_fornecedor"],
            "senha_redefinida_otp",
            fornecedor=info["fornecedor"],
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    _limpar_estado_reset()
    _ir_para(
        "login",
        msg="Senha redefinida com sucesso! Entre com a nova senha.",
        codigo=info["codigo_fornecedor"],
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
    if st.button("Esqueci / alterar senha", key="link_esqueci"):
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
