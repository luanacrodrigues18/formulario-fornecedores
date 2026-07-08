# Formulário de Fornecedores

Sistema em Python com **Streamlit** e **Supabase** para coleta de dados de fornecedores, com **login por código (ID)**, visualização em dashboard e exportação para Excel.

## Funcionalidades

- **Login por código do fornecedor** — cada fornecedor vê só os próprios pedidos
- Formulário em 3 passos (buscar → escolher linha → enviar)
- Assistente **ALUX** (dicas e FAQ na sidebar)
- Dashboard interno para filtrar e exportar registros
- Respostas salvas no Supabase (com fallback local)
- Geração de IDs sequenciais a partir da planilha FUP

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
SUPABASE_TABLE=formulario
SUPABASE_STORAGE_BUCKET=Form
SUPABASE_FUP_FILE=relatorio_fup.xlsm
FORM_BASE_URL=http://localhost:8501
```

Credenciais em **Project Settings → API** no Supabase.

## Criar / atualizar a tabela no Supabase

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

-- Se a tabela já existir sem a coluna:
ALTER TABLE formulario ADD COLUMN IF NOT EXISTS codigo_fornecedor TEXT;

ALTER TABLE formulario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir leitura pública"
ON formulario FOR SELECT
USING (true);

CREATE POLICY "Permitir inserção pública"
ON formulario FOR INSERT
WITH CHECK (true);
```

## Login por código do fornecedor

A planilha FUP tem o **nome** do fornecedor, mas **não tem ID**. O projeto usa um cadastro separado:

```
ID (login)  →  fornecedores_codigos.json  →  Nome do fornecedor
                                                   ↓
                                           Pedidos filtrados na FUP
```

### 1. Gerar os códigos (local)

Com `relatorio_fup.xlsm` na pasta do projeto:

```bash
python gerar_codigos_fornecedores.py
```

Isso cria:

| Arquivo | Conteúdo |
|---|---|
| `fornecedores_codigos.json` | Mapa `ID → nome` (ex.: `"6": "ACOS VITAL..."`) |
| `fornecedores_codigos_lista.txt` | Lista para envio / conferência |

Esses arquivos **não vão para o Git** (dados internos).

### 2. Fluxo do fornecedor

1. Recebe o **ID** por e-mail (ex.: `6`)
2. Entra no formulário com o ID
3. Vê só os pedidos da empresa dele
4. Busca por PO/Release **ou** clica em “Ver todos os meus pedidos”
5. Escolhe a linha, preenche e envia
6. A resposta grava `codigo_fornecedor` no Supabase

### 3. Exemplo do JSON

```json
{
  "1": "A C NETO COMERCIO E REPRESENTACAO TECNICA EIRELI",
  "6": "ACOS VITAL COMERCIO DE TUBOS HIDRAULICOS EIRELI"
}
```

O **nome** precisa ser **igual** ao da coluna `FORNECEDOR` na FUP.

### 4. Na nuvem (Streamlit Cloud)

Coloque `fornecedores_codigos.json` no **Supabase Storage** (mesmo bucket da FUP) ou mantenha um processo interno para disponibilizar o arquivo. Em etapas futuras, o ideal é uma tabela `fornecedores` no Supabase.

## Como executar

> **Deploy (Supabase + Streamlit):** [GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md)  
> **Produção real (Azure, AWS, Docker…):** [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)

### Formulário

```bash
streamlit run app.py
```

`http://localhost:8501`

### Dashboard

```bash
streamlit run dashboard.py
```

### Gerar IDs dos fornecedores

```bash
python gerar_codigos_fornecedores.py
```

### Gerar template Excel

```bash
python gerar_template.py
```

## Campos do formulário / banco

| Campo                         | Nome técnico           |
|-------------------------------|------------------------|
| ID                            | id                     |
| Hora de início                | hora_inicio            |
| Hora da conclusão             | hora_conclusao         |
| Email                         | email                  |
| Nome                          | nome                   |
| Código do fornecedor          | codigo_fornecedor      |
| Número do PO com Release      | numero_po_com_release  |
| Data da Promessa              | data_promessa          |
| Observações de Coleta         | observacoes_coleta     |
| Número da NF                  | numero_nf              |
| Número da linha               | numero_linha           |

## Estrutura do projeto

```
projeto/
├── app.py                          # Formulário + login
├── auth_fornecedor.py              # Sessão e tela de login
├── dashboard.py                    # Dashboard interno
├── database.py                     # Supabase + validações
├── planilha.py                     # Leitura do FUP
├── alcoano.py                      # ALUX (dicas / FAQ)
├── gerar_codigos_fornecedores.py   # Gera IDs a partir da FUP
├── gerar_template.py
├── fornecedores_codigos.json       # Cadastro ID → nome (local, não vai ao Git)
├── relatorio_fup.xlsm              # Base de pedidos (local / Storage)
├── GUIA_IMPLANTACAO.md
├── DEPLOY_PRODUCAO.md
├── .env.example
├── requirements.txt
└── README.md
```

## Observações

- `hora_inicio` e `hora_conclusao` são preenchidos automaticamente.
- Campos obrigatórios: Email, Nome, PO com Release, Data da Promessa e Número da linha.
- Um envio por **PO + linha** (bloqueia duplicata).
- Login por **ID interno**; CNPJ pode ser adicionado depois como dado cadastral.
- Regenerar códigos após atualizar a FUP: `python gerar_codigos_fornecedores.py`.
