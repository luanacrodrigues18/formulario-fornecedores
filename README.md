# Formulário de Fornecedores

Sistema em Python com **Streamlit** e **Supabase** para coleta de dados de fornecedores, visualização em dashboard local e exportação para Excel.

## Funcionalidades

- Formulário público para fornecedores preencherem dados
- Dashboard local para visualizar e filtrar registros
- Exportação dos dados para Excel (.xlsx)
- Geração de template Excel com os mesmos campos do formulário

## Requisitos

- Python 3.11+
- Conta no [Supabase](https://supabase.com)

## Instalação

```bash
# Clone ou acesse a pasta do projeto
cd projeto

# Crie um ambiente virtual (recomendado)
python -m venv venv

# Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

## Configuração do .env

1. Copie o arquivo de exemplo:

```bash
copy .env.example .env
```

2. Edite o arquivo `.env` com suas credenciais do Supabase:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon-ou-service-role
SUPABASE_TABLE=formulario
```

As credenciais estão em **Project Settings → API** no painel do Supabase.

## Criar a tabela no Supabase

No painel do Supabase, acesse **SQL Editor** e execute:

```sql
CREATE TABLE IF NOT EXISTS formulario (
    id BIGSERIAL PRIMARY KEY,
    hora_inicio TIMESTAMPTZ,
    hora_conclusao TIMESTAMPTZ,
    email TEXT NOT NULL,
    nome TEXT NOT NULL,
    numero_po_com_release TEXT NOT NULL,
    data_promessa DATE NOT NULL,
    observacoes_coleta TEXT,
    numero_nf TEXT,
    numero_linha TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE formulario ADD COLUMN IF NOT EXISTS codigo_fornecedor TEXT;

ALTER TABLE formulario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir leitura pública"
ON formulario FOR SELECT
USING (true);

CREATE POLICY "Permitir inserção pública"
ON formulario FOR INSERT
WITH CHECK (true);
```

> Ajuste as políticas RLS conforme a segurança desejada em produção.

## Como executar

> **Deploy completo (Supabase + Streamlit Cloud):** veja **[GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md)**.  
> **Opções para produção real (Azure, AWS, Docker, on-prem, etc.):** veja **[DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)**.

### Formulário público

```bash
streamlit run app.py
```

Acesse `http://localhost:8501` no navegador.

### Dashboard

```bash
streamlit run dashboard.py
```

### Gerar template Excel

```bash
python gerar_template.py
```

O arquivo `template_fornecedores.xlsx` será criado na raiz do projeto.

## Campos do formulário

| Campo na planilha              | Nome técnico no banco   |
|--------------------------------|-------------------------|
| ID                             | id                      |
| Hora de início                 | hora_inicio             |
| Hora da conclusão              | hora_conclusao          |
| Email                          | email                   |
| Nome                           | nome                    |
| Número do PO com Release       | numero_po_com_release   |
| Data da Promessa               | data_promessa           |
| Observações de Coleta          | observacoes_coleta      |
| Número da NF                   | numero_nf               |
| Informe o número da linha      | numero_linha            |

## Estrutura do projeto

```
projeto/
├── app.py
├── dashboard.py
├── gerar_template.py
├── database.py
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## Observações

- `hora_inicio` e `hora_conclusao` são preenchidos automaticamente pelo sistema.
- Campos obrigatórios: Email, Nome, Número do PO com Release, Data da Promessa e Número da linha.
- O dashboard exporta os registros filtrados para Excel.
