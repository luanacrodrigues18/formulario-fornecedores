# Guia de implantação — Formulário de Fornecedores

Documentação passo a passo do que foi configurado neste projeto: **Supabase** (banco + arquivo FUP) e **Streamlit Cloud** (formulário público e dashboard).

---

## Visão geral

```
Fornecedor  →  app.py (Streamlit Cloud)  →  Supabase (tabela formulario)
                      ↓
              relatorio_fup.xlsm (busca de PO/linha)
                      ↓
         Local: arquivo na pasta  |  Nuvem: Supabase Storage

Equipe Alcoa  →  dashboard.py (Streamlit Cloud)  →  lê Supabase
```

| Componente | Arquivo | Função |
|---|---|---|
| Formulário público | `app.py` | Fornecedor busca pedido e envia resposta |
| Dashboard interno | `dashboard.py` | Visualiza, filtra e exporta respostas |
| Banco de dados | `database.py` | Conexão Supabase, validação e gravação |
| Planilha FUP | `planilha.py` | Lê pedidos da aba Follow-up-Release |
| Assistente | `alcoano.py` | ALUX — dicas e FAQ |

**URLs de produção (exemplo deste projeto):**

- Formulário: `https://formulario-fornecedores.streamlit.app`
- Repositório: `https://github.com/luanacrodrigues18/formulario-fornecedores`

---

## Parte 1 — Configurar o Supabase

### 1.1 Criar o projeto

1. Acesse [https://supabase.com](https://supabase.com) e crie uma conta (se ainda não tiver).
2. Clique em **New project**.
3. Escolha nome, senha do banco e região.
4. Aguarde o projeto ficar **Active**.

### 1.2 Criar a tabela de respostas

1. No menu lateral, abra **SQL Editor**.
2. Clique em **New query**.
3. Cole e execute o script abaixo:

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

ALTER TABLE formulario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir leitura pública"
ON formulario FOR SELECT
USING (true);

CREATE POLICY "Permitir inserção pública"
ON formulario FOR INSERT
WITH CHECK (true);
```

4. Confirme em **Table Editor** que a tabela `formulario` foi criada.

> Em produção futura, revise as políticas RLS conforme a política de segurança da empresa.

### 1.3 Guardar o arquivo FUP no Storage (para a nuvem)

O formulário precisa do arquivo **`relatorio_fup.xlsm`** para buscar pedidos. Na nuvem ele não vai no GitHub (é sensível/grande), então fica no **Supabase Storage**.

1. No Supabase, abra **Storage**.
2. Crie um bucket chamado **`Form`** (ou outro nome — se mudar, atualize o `.env`).
3. Deixe o bucket **público** para leitura **ou** configure política de leitura para a chave `anon`.
4. Faça upload do arquivo com o nome exato: **`relatorio_fup.xlsm`**
   - Evite acentos e espaços no nome do arquivo.
   - O nome antigo `Relatório - FUP.xlsm` causava erro no Storage.

### 1.4 Copiar URL e chave da API

1. Vá em **Project Settings** (ícone de engrenagem).
2. Abra **API**.
3. Copie na **mesma tela**:
   - **Project URL** → vira `SUPABASE_URL`
   - **anon public** (chave pública) → vira `SUPABASE_KEY`

**Atenção — erros comuns:**

| Problema | Causa |
|---|---|
| `getaddrinfo failed` / `Name or service not known` | URL do Supabase digitada errada (ex.: `taaq` em vez de `taeq`) |
| Dados não salvam / erro de autenticação | URL de um projeto e chave `anon` de outro |
| Formulário na nuvem sem FUP | Arquivo não está no Storage ou nome diferente |

A URL deve ser algo como: `https://xxxxxxxx.supabase.co` (copiada exatamente do painel).

---

## Parte 2 — Rodar localmente (teste antes do deploy)

### 2.1 Pré-requisitos

- Python 3.11 ou superior
- Git instalado

### 2.2 Clonar / abrir o projeto

```powershell
cd "C:\caminho\para\Project Form"
```

### 2.3 Ambiente virtual e dependências

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2.4 Arquivo `.env` (uso local)

1. Copie o exemplo:

```powershell
copy .env.example .env
```

2. Edite o `.env` com seus dados:

```env
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=sua-chave-anon-publica
SUPABASE_TABLE=formulario
SUPABASE_STORAGE_BUCKET=Form
SUPABASE_FUP_FILE=relatorio_fup.xlsm
FORM_BASE_URL=http://localhost:8501
```

> O arquivo `.env` **nunca** deve ir para o GitHub (já está no `.gitignore`).

### 2.5 Arquivo FUP local

Coloque **`relatorio_fup.xlsm`** na pasta raiz do projeto.

- **Com o arquivo local:** o app usa ele direto (útil se a rede da empresa bloquear Supabase).
- **Sem arquivo local:** o app tenta baixar do Supabase Storage.

### 2.6 Executar e testar

**Formulário:**

```powershell
streamlit run app.py
```

Abra: `http://localhost:8501`

**Dashboard:**

```powershell
streamlit run dashboard.py
```

Abra: `http://localhost:8501` (use outra porta se o formulário já estiver aberto).

### 2.7 Checklist do teste local

- [ ] Busca por fornecedor ou PO encontra pedidos
- [ ] Seleção de linha funciona
- [ ] Envio grava registro no Supabase (ver em **Table Editor**)
- [ ] Dashboard mostra o registro
- [ ] Segundo envio para o mesmo PO+linha é bloqueado

---

## Parte 3 — Publicar no GitHub

### 3.1 O que vai (e o que NÃO vai) para o Git

**Vai:**

- `app.py`, `dashboard.py`, `database.py`, `planilha.py`, `alcoano.py`
- `requirements.txt`, `README.md`, `.streamlit/config.toml`

**NÃO vai** (`.gitignore`):

- `.env` (senhas)
- `venv/`
- `relatorio_fup.xlsm` (dados internos)
- `formulario_respostas.xlsx` (fallback local)

### 3.2 Enviar código

```powershell
cd "C:\caminho\para\Project Form"
git status
git add .
git commit -m "Sua mensagem de commit"
git push origin main
```

---

## Parte 4 — Deploy no Streamlit Cloud

### 4.1 Criar conta e conectar GitHub

1. Acesse [https://share.streamlit.io](https://share.streamlit.io).
2. Entre com a conta **GitHub**.
3. Autorize o Streamlit a acessar seus repositórios.

### 4.2 Deploy do formulário (`app.py`)

1. Clique em **Create app**.
2. Preencha:
   - **Repository:** `luanacrodrigues18/formulario-fornecedores` (ou o seu)
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. Clique em **Deploy**.

### 4.3 Configurar Secrets no Streamlit (obrigatório)

1. No app publicado, abra **⋮** → **Settings** → **Secrets**.
2. Cole no formato TOML:

```toml
SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
SUPABASE_KEY = "sua-chave-anon-publica"
SUPABASE_TABLE = "formulario"
SUPABASE_STORAGE_BUCKET = "Form"
SUPABASE_FUP_FILE = "relatorio_fup.xlsm"
FORM_BASE_URL = "https://formulario-fornecedores.streamlit.app"
```

3. Salve e clique em **Reboot app**.

> Local usa `.env`. Na nuvem usa **Secrets** — são a mesma configuração, em lugares diferentes.

### 4.4 Deploy do dashboard (`dashboard.py`)

O dashboard é um **segundo app** no Streamlit Cloud:

1. **Create app** novamente.
2. Mesmo repositório e branch.
3. **Main file path:** `dashboard.py`
4. Use os **mesmos Secrets** do formulário.
5. Deploy e **Reboot**.

### 4.5 Atualizar depois de mudanças no código

```powershell
git add .
git commit -m "Descrição da mudança"
git push origin main
```

No Streamlit Cloud: **⋮** → **Reboot app** (ou aguarde o redeploy automático).

---

## Parte 5 — Verificação em produção

### Formulário (`app.py`)

1. Abra a URL pública do formulário.
2. Busque um pedido de teste.
3. Preencha e envie.
4. Confirme no Supabase (**Table Editor** → `formulario`) que o registro apareceu.

### Dashboard (`dashboard.py`)

1. Abra a URL do dashboard.
2. Verifique se aparece a mensagem de dados carregados do Supabase.
3. Confira métricas, filtros e exportação Excel.

---

## Problemas frequentes e soluções

### Rede da empresa bloqueia Supabase no PC local

**Sintoma:** `getaddrinfo failed` ao rodar local.

**Solução:** Coloque `relatorio_fup.xlsm` na pasta do projeto e teste local sem depender do Storage. O deploy na nuvem (Streamlit + Supabase) costuma funcionar normalmente.

### Formulário na nuvem salva mas dashboard vazio

**Causa:** Secrets diferentes entre os dois apps, ou dashboard sem reboot após configurar Secrets.

**Solução:** Confira Secrets iguais nos dois apps e reinicie ambos.

### Erro ao carregar planilha base na nuvem

**Causa:** `relatorio_fup.xlsm` ausente no Storage ou nome errado.

**Solução:** Upload no bucket `Form` com o nome exato `relatorio_fup.xlsm`.

### URL do Supabase com typo

**Sintoma:** DNS não resolve, app não conecta.

**Solução:** Copie de novo **Project URL** em **Settings → API**. Não digite manualmente.

---

## Estrutura final do projeto

```
Project Form/
├── app.py                  # Formulário público
├── dashboard.py            # Dashboard interno
├── database.py             # Supabase + validações
├── planilha.py             # Leitura do FUP
├── alcoano.py              # ALUX (dicas e FAQ)
├── requirements.txt
├── .env.example            # Modelo de configuração local
├── .streamlit/config.toml
├── GUIA_IMPLANTACAO.md     # Este guia
└── relatorio_fup.xlsm      # Apenas local (não vai pro Git)
```

---

## Resumo rápido (cola)

1. **Supabase:** criar tabela `formulario` + RLS + upload `relatorio_fup.xlsm` no Storage.
2. **Local:** `.env` + `pip install` + `streamlit run app.py`.
3. **GitHub:** push sem `.env` e sem `relatorio_fup.xlsm`.
4. **Streamlit Cloud:** deploy `app.py` e `dashboard.py` com os mesmos Secrets.
5. **Testar:** envio no form → registro no Supabase → aparece no dashboard.

---

*Documentação gerada para o MVP do Formulário de Fornecedores Alcoa — junho/2026.*

**Próximo passo:** para evoluir a produção formal, consulte **[DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)**.
