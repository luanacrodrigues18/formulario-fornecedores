"""Diagnóstico rápido no Streamlit Cloud. Main file: diagnostico.py"""
import sys
import traceback

import streamlit as st

st.set_page_config(page_title="Diagnóstico", page_icon="🩺")
st.title("Diagnóstico Streamlit Cloud")
st.write("Se você vê esta tela, o deploy básico funciona.")
st.write(f"Python: `{sys.version}`")
st.write(f"Streamlit: `{st.__version__}`")

st.subheader("API de botão")
try:
    st.button("teste width=stretch", width="stretch", key="btn_width")
    st.success("width='stretch' OK")
except TypeError as exc:
    st.warning(f"width não suportado: {exc}")
    try:
        st.button("teste use_container_width", use_container_width=True, key="btn_ucw")
        st.success("use_container_width OK")
    except TypeError as exc2:
        st.error(f"Nenhuma API de largura funcionou: {exc2}")

st.subheader("Dependências")
for nome in ("streamlit", "supabase", "pandas", "openpyxl", "altair", "tzdata", "dotenv"):
    try:
        mod = __import__("dotenv" if nome == "dotenv" else nome)
        st.success(f"{nome}: OK ({getattr(mod, '__version__', 'sem versão')})")
    except Exception as exc:
        st.error(f"{nome}: FALHOU — {exc}")

st.subheader("Secrets / ambiente")
chaves = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_TABLE",
    "SUPABASE_STORAGE_BUCKET",
    "SUPABASE_FUP_FILE",
    "SUPABASE_CODIGOS_FILE",
    "FORM_BASE_URL",
]
for chave in chaves:
    valor = ""
    try:
        if chave in st.secrets:
            valor = str(st.secrets[chave]).strip()
    except Exception:
        pass
    if not valor:
        import os

        valor = os.getenv(chave, "").strip()
    if valor:
        st.write(f"✅ `{chave}` definida ({len(valor)} caracteres)")
    else:
        st.write(f"❌ `{chave}` ausente")

st.subheader("Teste Supabase")
try:
    from database import get_client, supabase_table, usa_service_role

    client = get_client()
    resp = client.table(supabase_table()).select("id").limit(1).execute()
    st.success(
        f"Conexão OK · service_role={usa_service_role()} · "
        f"linhas retornadas no teste: {len(resp.data or [])}"
    )
except Exception:
    st.error("Falha ao conectar no Supabase:")
    st.code(traceback.format_exc())

st.subheader("Teste Storage (FUP)")
try:
    from pathlib import Path
    from database import baixar_arquivo_storage, supabase_fup_file

    destino = Path("/tmp") / supabase_fup_file()
    baixar_arquivo_storage(supabase_fup_file(), destino)
    st.success(f"Download OK: {destino} ({destino.stat().st_size} bytes)")
except Exception:
    st.error("Falha ao baixar FUP do Storage:")
    st.code(traceback.format_exc())
