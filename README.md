# Formulário de Fornecedores

Sistema em Python com **Streamlit** e **Supabase** para coleta de retorno de fornecedores: cadastro com usuário e senha, formulário em página única, dashboard interno (métricas, período, PDF) e exportação para Excel.

> **Repasse / replicação:** comece pelo [MAPA_DOCUMENTACAO.md](MAPA_DOCUMENTACAO.md).  
> **MVP passo a passo:** [GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md).  
> **Produção (Azure, e-mail OTP, Docker…):** [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md).

## Funcionalidades

### Formulário (`app.py`)

- **Cadastro** — usuário + senha + e-mail + código Alcoa da empresa
- **Login** — usuário ou código Alcoa + senha
- **Alterar senha** — exige a senha atual
- **Esqueci a senha (MVP)** — o fornecedor usa a **senha temporária** gerada pela equipe no dashboard e define a senha definitiva
- Formulário em **página única** (busca + lista + formulário)
- Seleção de **vários pedidos** e preenchimento em sequência
- Assistente **ALUX** (dicas e FAQ na sidebar)

### Dashboard (`dashboard.py`) — uso interno Alcoa

- Três abas: **métricas**, **filtros/tabela**, **reset de senha**
- **Filtro de período:** hoje, ontem, 7 dias, 15 dias, mês atual/anterior, personalizado ou todo o histórico
- Métricas e gráficos alinhados ao período (prazo, completude, top 10, envios)
- **Exportar relatório PDF** formatado (KPIs, envios no período, pendências sem NF/obs)
- Exportação Excel e **retorno FUP** (sem alterar o `.xlsm`)
- **Reset senha de fornecedor:** gera senha temporária → passa por Teams/telefone → fornecedor troca em “Esqueci a senha”

### Dados e segurança

- Contas e logs no Supabase (`contas_fornecedor`, `acessos_log`)
- Respostas na tabela `formulario`
- RLS fechado + `SUPABASE_SERVICE_ROLE_KEY` ([`sql/fechar_rls.sql`](sql/fechar_rls.sql))
- Geração de IDs a partir da FUP (`fornecedores_codigos.json`)

### E-mail / OTP (código pronto; validar em produção)

O módulo [`email_smtp.py`](email_smtp.py) já fala com **Resend** ou **SMTP**. No MVP o fluxo principal de recuperação **não depende** de e-mail (usa reset no dashboard).

A **validação completa de troca de senha por e-mail** (OTP no inbox do fornecedor) fica para **produção**, porque depende de domínio DNS, remetente aprovado, política de spam e Secrets — ver [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md#validação-troca-de-senha-por-e-mail-produção).

## Requisitos

- Python 3.11+
- Conta no [Supabase](https://supabase.com)
- Arquivo base `relatorio_fup.xlsm` (local ou Storage)

## Instalação

```bash
cd projeto
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

## Configuração do .env

```bash
copy .env.example .env
```

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon-publica
SUPABASE_SERVICE_ROLE_KEY=sua-chave-service-role-secreta
SUPABASE_TABLE=formulario
SUPABASE_STORAGE_BUCKET=Form
SUPABASE_FUP_FILE=relatorio_fup.xlsm
SUPABASE_CODIGOS_FILE=fornecedores_codigos.json
FORM_BASE_URL=http://localhost:8501
```

- **anon (`SUPABASE_KEY`)**: chave pública (Settings → API).
- **service_role (`SUPABASE_SERVICE_ROLE_KEY`)**: chave secreta do servidor — **nunca** no Git. Necessária com RLS fechado.

No Streamlit Cloud, use as mesmas chaves em **Secrets**.

### E-mail (opcional no MVP; obrigatório se for OTP em produção)

**Resend (recomendado):**
```toml
RESEND_API_KEY = "re_xxxxx"
EMAIL_FROM = "onboarding@resend.dev"   # teste; em produção use domínio verificado
```

**Ou SMTP:**
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`.

## Criar tabelas no Supabase

No **SQL Editor**, execute:

```sql
CREATE TABLE IF NOT EXISTS formulario (
    id BIGSERIAL PRIMARY KEY,
    hora_inicio TIMESTAMPTZ,
    hora_conclusao TIMESTAMPTZ,
    email TEXT NOT NULL,
    nome TEXT NOT NULL,
    codigo_fornecedor TEXT,
    numero_po_com_release TEXT NOT NULL,
    data_promessa DATE NOT NULL,
    observacoes_coleta TEXT,
    numero_nf TEXT,
    numero_linha TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE formulario ADD COLUMN IF NOT EXISTS codigo_fornecedor TEXT;
ALTER TABLE formulario ENABLE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS contas_fornecedor (
    codigo_fornecedor TEXT PRIMARY KEY,
    fornecedor TEXT NOT NULL,
    usuario TEXT,
    senha_hash TEXT NOT NULL,
    email TEXT,
    falhas_login INT DEFAULT 0,
    bloqueado_ate TIMESTAMPTZ,
    otp_hash TEXT,
    otp_expira TIMESTAMPTZ,
    otp_tipo TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE contas_fornecedor ENABLE ROW LEVEL SECURITY;
ALTER TABLE contas_fornecedor ADD COLUMN IF NOT EXISTS usuario TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS contas_usuario_unique
ON contas_fornecedor (usuario)
WHERE usuario IS NOT NULL AND usuario <> '';

CREATE TABLE IF NOT EXISTS acessos_log (
    id BIGSERIAL PRIMARY KEY,
    codigo_fornecedor TEXT,
    fornecedor TEXT,
    evento TEXT NOT NULL,
    detalhes TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE acessos_log ENABLE ROW LEVEL SECURITY;
```

### Fechar o RLS (recomendado)

Com `SUPABASE_SERVICE_ROLE_KEY` configurada, rode [`sql/fechar_rls.sql`](sql/fechar_rls.sql).

## Login e contas

```
Código Alcoa  →  fornecedores_codigos.json  →  Nome na FUP
                         ↓
              contas_fornecedor (usuário + senha em hash)
                         ↓
                   acessos_log (auditoria)
```

### Segurança incluída

| Recurso | Detalhe |
|---------|---------|
| Senha forte | Mínimo 8 caracteres, com letra e número |
| Hash | PBKDF2 — senha não fica em texto puro |
| Bloqueio | Após falhas de login (padrão: 5 / 15 min) |
| Rotação | Troca obrigatória após 90 dias (configurável) |
| Alterar senha | Exige senha atual |
| Esqueci a senha (MVP) | Senha temporária gerada no dashboard |
| Esqueci a senha (produção) | OTP / e-mail — validar com domínio e provedor |
| RLS | Fechado com `fechar_rls.sql` + `service_role` |
| HTTPS | Streamlit Cloud |

### 1. Gerar os códigos (local)

Com `relatorio_fup.xlsm` na pasta:

```bash
python gerar_codigos_fornecedores.py
```

| Arquivo | Conteúdo |
|---------|----------|
| `fornecedores_codigos.json` | Mapa `ID → nome` |
| `fornecedores_codigos_lista.txt` | Lista para conferência |

Esses arquivos **não vão para o Git**.

### 2. Fluxo do fornecedor

1. Abre o formulário (ou o link `?po=...&linha=...`).
2. **Cadastro:** usuário + senha + e-mail + código Alcoa.
3. **Login:** usuário ou código + senha.
4. Busca / Ver todos → marca → preenche e envia.
5. A resposta grava `codigo_fornecedor` na tabela `formulario`.

### 3. Fluxo de reset de senha (MVP)

1. Equipe Alcoa abre o **dashboard** → aba **Reset senha de fornecedor**.
2. Busca a conta e gera **senha temporária**.
3. Passa a senha ao fornecedor (Teams / telefone).
4. Fornecedor em **Esqueci a senha** informa a temporária e define a nova.
5. Se a conta estiver marcada para troca forçada, o próximo login exige nova senha.

### 4. Na nuvem (Streamlit Cloud)

Upload no bucket **Form**:

| Arquivo | Nome no Storage |
|---------|-----------------|
| Planilha FUP | `relatorio_fup.xlsm` |
| Cadastro de IDs | `fornecedores_codigos.json` |

Secrets mínimos: `SUPABASE_URL`, `SUPABASE_KEY`, **`SUPABASE_SERVICE_ROLE_KEY`**, bucket e nomes dos arquivos.

## Como executar

### Formulário

```bash
venv\Scripts\activate
streamlit run app.py
```

`http://localhost:8501`

### Dashboard

```bash
streamlit run dashboard.py
```

No dashboard:

- Escolha o **período** (7 / 15 dias, mês, personalizado…)
- **Exportar relatório PDF** (respeita o período)
- **Exportar retorno para Excel (sem mexer na FUP)**
- Aba **Reset senha de fornecedor**

### Atalhos Windows

```text
INICIAR.bat              # menu (formulário / dashboard / setup)
setup_outro_pc.bat       # primeira instalação
mapear_rede_alcoa.bat    # mapeia V: na pasta InfoShare
```

## Campos do formulário / banco

| Campo                    | Nome técnico          |
|--------------------------|------------------------|
| ID                       | id                     |
| Hora de início           | hora_inicio            |
| Hora da conclusão        | hora_conclusao         |
| E-mail                   | email                  |
| Nome                     | nome                   |
| Código do fornecedor     | codigo_fornecedor      |
| Número do PO com Release | numero_po_com_release  |
| Data da Promessa         | data_promessa          |
| Observações de Coleta    | observacoes_coleta     |
| Número da NF             | numero_nf              |
| Número da linha          | numero_linha           |

## Estrutura do projeto

```
projeto/
├── app.py                          # Formulário + fluxo
├── auth_fornecedor.py              # Cadastro, login, alterar / esqueci senha
├── contas_fornecedor.py            # Contas, hash, bloqueio, reset admin, logs
├── database.py                     # Supabase (service_role) + validações
├── planilha.py                     # Leitura FUP / export retorno
├── alcoano.py                      # ALUX (dicas / FAQ)
├── email_smtp.py                   # Resend / SMTP (OTP em produção)
├── prazo_resposta.py               # Prazo do formulário
├── sql/fechar_rls.sql              # Fecha políticas públicas
├── dashboard.py                    # Dashboard + PDF + período + reset senha
├── gerar_codigos_fornecedores.py
├── MAPA_DOCUMENTACAO.md            # Índice para repasse
├── GUIA_IMPLANTACAO.md
├── DEPLOY_PRODUCAO.md
├── roadmap_mvp_producao.html
├── APRESENTACAO.html
├── LEIA_PRIMEIRO.txt
├── INICIAR.bat
├── .env.example
├── requirements.txt
└── README.md
```

## Observações

- `hora_inicio` e `hora_conclusao` são preenchidos automaticamente.
- Campos obrigatórios do envio: e-mail, nome, PO com Release, data da promessa e número da linha.
- Vários envios são permitidos (inclusive para o mesmo PO + linha).
- Pedidos duplicados idênticos na FUP (mesmo PO + linha) aparecem só uma vez na lista.
- Após atualizar a FUP: `python gerar_codigos_fornecedores.py`.
- Dependência de PDF: `fpdf2` (já em `requirements.txt`; há fallback se o pacote faltar).
