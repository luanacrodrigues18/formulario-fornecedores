# Formulário de Fornecedores

Sistema em Python com **Streamlit** e **Supabase** para coleta de retorno de fornecedores: cadastro com usuário e senha, formulário em página única, dashboard interno e exportação para Excel.

## Funcionalidades

- **Cadastro** - o fornecedor cria **usuário** + **senha** (vinculado ao código Alcoa da empresa)
- **Login** - entra com **usuário ou código Alcoa** + senha
- **Redefinir senha** - exige a senha atual (sem recuperação por e-mail no fluxo atual)
- Formulário em **página única** (busca + lista + formulário lado a lado)
- Seleção de **vários pedidos** e preenchimento em sequência
- Assistente **ALUX** (dicas e FAQ na sidebar)
- Dashboard interno para filtrar, exportar e gerar retorno FUP (sem alterar o `.xlsm`)
- Contas e logs no Supabase (`contas_fornecedor`, `acessos_log`)
- Respostas na tabela `formulario`
- Geração de IDs a partir da planilha FUP (`fornecedores_codigos.json`)

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
- **service_role (`SUPABASE_SERVICE_ROLE_KEY`)**: chave secreta do servidor - **nunca** publique no Git nem no front. Necessária com o RLS fechado (`sql/fechar_rls.sql`).

No Streamlit Cloud, use as mesmas chaves em **Secrets**.

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

Depois de configurar `SUPABASE_SERVICE_ROLE_KEY`, rode o script [`sql/fechar_rls.sql`](sql/fechar_rls.sql). Ele remove políticas públicas abertas. O app acessa as tabelas só pelo servidor com a `service_role`.

## Login e contas

A FUP tem o **nome** do fornecedor, mas **não tem ID**. O isolamento usa:

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
| Hash | PBKDF2 - senha não fica em texto puro |
| Bloqueio | Após falhas de login (padrão: 5 / 15 min) |
| Rotação | Troca obrigatória após 90 dias (configurável) |
| Redefinir | Exige senha atual |
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

Esses arquivos **não vão para o Git**. Contas novas preferem a tabela Supabase; há fallback local em `contas_fornecedor.json`.

### 2. Fluxo do fornecedor

1. Abre o formulário (ou o link `?po=...&linha=...`).
2. **Cadastro:** cria **usuário** + **senha** + informa o **código Alcoa** da empresa.
3. **Login:** entra com **usuário ou código** + senha.
4. Busca pedidos / Ver todos → marca na lista → preenche e envia.
5. A resposta grava `codigo_fornecedor` na tabela `formulario`.

### 3. Exemplo do JSON de códigos

```json
{
  "1": "A C NETO COMERCIO E REPRESENTACAO TECNICA EIRELI",
  "6": "ACOS VITAL COMERCIO DE TUBOS HIDRAULICOS EIRELI"
}
```

O **nome** precisa ser **igual** ao da coluna `FORNECEDOR` na FUP.

### 4. Na nuvem (Streamlit Cloud)

Upload no bucket **Form** (Storage):

| Arquivo | Nome no Storage |
|---------|-----------------|
| Planilha FUP | `relatorio_fup.xlsm` |
| Cadastro de IDs | `fornecedores_codigos.json` |

Secrets mínimos: `SUPABASE_URL`, `SUPABASE_KEY`, **`SUPABASE_SERVICE_ROLE_KEY`**, bucket e nomes dos arquivos. Prefira bucket **privado**.

## Como executar

> **Deploy passo a passo (do zero):** comece pelo checklist em [GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md).  
> **Produção (Azure, AWS, Docker…):** [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)  
> **Outro PC Alcoa (sem terminal):** [LEIA_PRIMEIRO.txt](LEIA_PRIMEIRO.txt) / `INICIAR.bat`

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

No dashboard: **Exportar retorno para Excel (sem mexer na FUP)** gera um `.xlsx` com chaves PO+linha e campos de retorno, **sem gravar** no `.xlsm`.

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
├── auth_fornecedor.py              # Cadastro, login, redefinir senha
├── contas_fornecedor.py            # Contas, hash, bloqueio, logs
├── database.py                     # Supabase (service_role) + validações
├── planilha.py                     # Leitura FUP / export retorno
├── alcoano.py                      # ALUX (dicas / FAQ)
├── email_smtp.py                   # SMTP opcional (2FA)
├── sql/fechar_rls.sql              # Fecha políticas públicas
├── dashboard.py                    # Dashboard + export retorno FUP
├── gerar_codigos_fornecedores.py
├── INICIAR.bat
├── LEIA_PRIMEIRO.txt
├── GUIA_IMPLANTACAO.md
├── DEPLOY_PRODUCAO.md
├── .env.example
├── requirements.txt
└── README.md
```

## Observações

- `hora_inicio` e `hora_conclusao` são preenchidos automaticamente.
- Campos obrigatórios do envio: e-mail, nome, PO com Release, data da promessa e número da linha.
- Vários envios são permitidos (inclusive para o mesmo PO + linha).
- Na lista, é possível marcar vários pedidos e preenchê-los em sequência.
- Pedidos duplicados idênticos na FUP (mesmo PO + linha) aparecem só uma vez na lista.
- CNPJ como login ainda não está na FUP; evolução futura possível.
- Após atualizar a FUP: `python gerar_codigos_fornecedores.py`.
