# Guia de implantação - Formulário de Fornecedores

Documentação passo a passo do que foi configurado neste projeto: **Supabase** (banco + arquivo FUP), **login por código do fornecedor** e **Streamlit Cloud** (formulário público e dashboard).

---

## Visão geral

```
Fornecedor digita ID
        ↓
fornecedores_codigos.json  →  resolve nome da empresa
        ↓
app.py filtra pedidos na FUP (só desse fornecedor)
        ↓
envia resposta → Supabase (tabela formulario + codigo_fornecedor)

Equipe Alcoa  →  dashboard.py  →  lê Supabase
```


| Componente         | Arquivo                         | Função                              |
| ------------------ | ------------------------------- | ----------------------------------- |
| Formulário + login | `app.py`                        | Login por ID, busca e envio         |
| Autenticação       | `auth_fornecedor.py`            | Sessão, tela de login, isolamento   |
| Cadastro de IDs    | `fornecedores_codigos.json`     | Mapa `ID → nome do fornecedor`      |
| Gerador de IDs     | `gerar_codigos_fornecedores.py` | Cria JSON a partir da FUP           |
| Dashboard interno  | `dashboard.py`                  | Visualiza, filtra e exporta         |
| Banco de dados     | `database.py`                   | Supabase, validação e gravação      |
| Planilha FUP       | `planilha.py`                   | Lê pedidos da aba Follow-up-Release |
| Assistente         | `alcoano.py`                    | ALUX — dicas e FAQ                  |


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
    codigo_fornecedor TEXT,
    numero_po_com_release TEXT NOT NULL,
    data_promessa DATE NOT NULL,
    observacoes_coleta TEXT,
    numero_nf TEXT,
    numero_linha TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Obrigatório se a tabela já existir sem essa coluna:
ALTER TABLE formulario ADD COLUMN IF NOT EXISTS codigo_fornecedor TEXT;

ALTER TABLE formulario ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Permitir leitura pública"
ON formulario FOR SELECT
USING (true);

CREATE POLICY "Permitir inserção pública"
ON formulario FOR INSERT
WITH CHECK (true);
```

1. Confirme em **Table Editor** que a tabela `formulario` foi criada **com** a coluna `codigo_fornecedor`.

> Sem essa coluna, o envio falha com erro `PGRST204` / schema cache.  
> Em produção futura, revise as políticas RLS conforme a política de segurança da empresa.



### 1.3 Guardar o arquivo FUP no Storage (para a nuvem)

O formulário precisa do arquivo `relatorio_fup.xlsm` para buscar pedidos. Na nuvem ele não vai no GitHub (é sensível/grande), então fica no **Supabase Storage**.

1. No Supabase, abra **Storage**.
2. Crie um bucket chamado `Form` (ou outro nome — se mudar, atualize o `.env`).
3. Deixe o bucket **público** para leitura **ou** configure política de leitura para a chave `anon`.
4. Faça upload do arquivo com o nome exato: `relatorio_fup.xlsm`
  - Evite acentos e espaços no nome do arquivo.
  - O nome antigo `Relatório - FUP.xlsm` causava erro no Storage.
5. (Opcional) Guarde uma cópia de `fornecedores_codigos.json` no mesmo bucket `Form` como **backup interno**. O app **não** baixa esse arquivo do Storage — o login usa o JSON **na pasta do projeto** (veja seção 2.5 e limitação na nuvem em 4.3).



### 1.4 Copiar URL e chave da API

1. Vá em **Project Settings** (ícone de engrenagem).
2. Abra **API**.
3. Copie na **mesma tela**:
  - **Project URL** → vira `SUPABASE_URL`
  - **anon public** (chave pública) → vira `SUPABASE_KEY`

**Atenção — erros comuns:**


| Problema                                           | Causa                                                          |
| -------------------------------------------------- | -------------------------------------------------------------- |
| `getaddrinfo failed` / `Name or service not known` | URL do Supabase digitada errada (ex.: `taaq` em vez de `taeq`) |
| Dados não salvam / erro de autenticação            | URL de um projeto e chave `anon` de outro                      |
| Formulário na nuvem sem FUP                        | Arquivo não está no Storage ou nome diferente                  |


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

1. Edite o `.env` com seus dados:

```env
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_KEY=sua-chave-anon-publica
SUPABASE_TABLE=formulario
SUPABASE_STORAGE_BUCKET=Form
SUPABASE_FUP_FILE=relatorio_fup.xlsm
FORM_BASE_URL=http://localhost:8501
```

> O arquivo `.env` **nunca** deve ir para o GitHub (já está no `.gitignore`).



### 2.5 Arquivo FUP e códigos de fornecedor (local)

1. Coloque `relatorio_fup.xlsm` na pasta raiz do projeto.
2. Gere o cadastro de IDs:

```powershell
python gerar_codigos_fornecedores.py
```

Isso cria `fornecedores_codigos.json` (mapa ID → nome) e `fornecedores_codigos_lista.txt` (para enviar aos fornecedores).

- **Com FUP local:** o app usa o arquivo da pasta (útil se a rede bloquear Supabase).
- **Sem FUP local:** o app tenta baixar do Supabase Storage.
- **Login por ID:** exige `fornecedores_codigos.json` **na pasta do projeto** (gerado com `gerar_codigos_fornecedores.py`).
- **Sem JSON local:** o login por código não encontra nenhum fornecedor (upload no Storage **não** substitui o arquivo local hoje).



### 2.6 Executar e testar

**Formulário:**

```powershell
streamlit run app.py
```

Abra: `http://localhost:8501`

1. Na tela de login, digite um ID (ex.: `6` para ACOS VITAL, conforme a lista gerada).
2. Confira que só aparecem pedidos desse fornecedor.
3. Use **Ver todos os meus pedidos** ou busque por PO com Release.
4. Preencha e envie; confira no Supabase a coluna `codigo_fornecedor`.

**Dashboard:**

```powershell
streamlit run dashboard.py
```



### 2.7 Checklist do teste local

- [ ] Login com ID válido entra e mostra o nome do fornecedor
- [ ] ID inválido mostra “Código não encontrado”
- [ ] Só pedidos daquele fornecedor aparecem
- [ ] Busca por PO filtra dentro dos pedidos dele
- [ ] Envio grava no Supabase com `codigo_fornecedor`
- [ ] Dashboard mostra o registro
- [ ] Segundo envio para o mesmo PO+linha é bloqueado
- [ ] Botão **Sair** encerra a sessão

---



## Parte 2.8 — Cadastro de IDs (passo 1)

A FUP **não tem coluna de código**. O isolamento funciona assim:


| Item                      | Onde fica                       |
| ------------------------- | ------------------------------- |
| Pedidos (PO, linha, item) | `relatorio_fup.xlsm`            |
| ID de login               | `fornecedores_codigos.json`     |
| Respostas enviadas        | tabela `formulario` no Supabase |


Quando a FUP for atualizada, rode de novo:

```powershell
python gerar_codigos_fornecedores.py
```

**Atenção:** regenerar o JSON por ordem alfabética pode **mudar os IDs**. Em produção, prefira IDs estáveis (código SAP) e edite o JSON manualmente.

Na nuvem (Streamlit Cloud), o JSON **não vai no Git** (`.gitignore`). Para o login funcionar em produção, planeje: tabela `fornecedores` no Supabase, ou disponibilizar o JSON no deploy de forma controlada (repositório privado / pipeline interno).

---



## Parte 3 — Publicar no GitHub



### 3.1 O que vai (e o que NÃO vai) para o Git

**Vai:**

- `app.py`, `auth_fornecedor.py`, `dashboard.py`, `database.py`, `planilha.py`, `alcoano.py`
- `gerar_codigos_fornecedores.py`, `gerar_template.py`
- `requirements.txt`, `README.md`, `GUIA_IMPLANTACAO.md`, `DEPLOY_PRODUCAO.md`
- `.streamlit/config.toml`, `fornecedores_codigos.json.example`

**NÃO vai** (`.gitignore`):

- `.env` (senhas)
- `venv/`
- `relatorio_fup.xlsm` (dados internos)
- `fornecedores_codigos.json` e `fornecedores_codigos_lista.txt` (cadastro interno)
- `formulario_respostas.xlsx` (fallback local)



### 3.2 Enviar código

```powershell
cd "C:\caminho\para\Project Form"
git status
git add .
git commit -m "Sua mensagem de commit"
git push -u origin login-fornecedor
# ou: git push origin main
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
  - **Branch:** `main` (ou `login-fornecedor` se ainda estiver em PR)
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

1. Salve e clique em **Reboot app**.
2. Confirme no Storage o upload de `relatorio_fup.xlsm`.
3. Confirme no SQL Editor que existe a coluna `codigo_fornecedor`.

> **Login na nuvem:** o app lê `fornecedores_codigos.json` só da pasta do projeto. Como o arquivo não vai no Git, o **login por ID não funciona no Streamlit Cloud** com o código atual — use o formulário local para testar login, ou evolua para tabela `fornecedores` no Supabase.

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
git push
```

No Streamlit Cloud: **⋮** → **Reboot app** (ou aguarde o redeploy automático).

---



## Parte 5 — Verificação em produção



### Formulário (`app.py`)

1. Abra a URL pública do formulário.
2. Faça login com um ID de teste.
3. Confira isolamento (só pedidos daquele fornecedor).
4. Preencha e envie.
5. Confirme no Supabase (**Table Editor** → `formulario`) que o registro apareceu com `codigo_fornecedor`.



### Dashboard (`dashboard.py`)

1. Abra a URL do dashboard.
2. Verifique se aparece a mensagem de dados carregados do Supabase.
3. Confira métricas, filtros e exportação Excel.

---



## Problemas frequentes e soluções



### Código não encontrado no login

**Causa:** `fornecedores_codigos.json` ausente na pasta do projeto, ou nome do fornecedor diferente do FUP.

**Solução:** rode `python gerar_codigos_fornecedores.py` e use um ID da lista gerada. Na nuvem, o login só funcionará quando o JSON estiver disponível no ambiente de deploy (hoje não é baixado do Storage).

### Erro `Could not find the 'codigo_fornecedor' column` (PGRST204)

**Causa:** coluna ainda não criada no Supabase.

**Solução:**

```sql
ALTER TABLE formulario ADD COLUMN IF NOT EXISTS codigo_fornecedor TEXT;
```



### Rede da empresa bloqueia Supabase no PC local

**Sintoma:** `getaddrinfo failed` ao rodar local.

**Solução:** Coloque `relatorio_fup.xlsm` e `fornecedores_codigos.json` na pasta do projeto. O deploy na nuvem costuma funcionar normalmente.

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
├── app.py
├── auth_fornecedor.py
├── dashboard.py
├── database.py
├── planilha.py
├── alcoano.py
├── gerar_codigos_fornecedores.py
├── requirements.txt
├── .env.example
├── .streamlit/config.toml
├── GUIA_IMPLANTACAO.md
├── DEPLOY_PRODUCAO.md
├── fornecedores_codigos.json.example
├── fornecedores_codigos.json     # Apenas local / Storage (não vai pro Git)
└── relatorio_fup.xlsm            # Apenas local / Storage (não vai pro Git)
```

---



## Resumo rápido (cola)

1. **Supabase:** criar tabela `formulario` + coluna `codigo_fornecedor` + RLS + upload FUP (e JSON de códigos) no Storage.
2. **Local:** `.env` + `pip install` + gerar códigos + `streamlit run app.py`.
3. **Login:** fornecedor digita ID → vê só seus pedidos → envia.
4. **GitHub:** push sem `.env`, sem FUP e sem `fornecedores_codigos.json`.
5. **Streamlit Cloud:** deploy `app.py` e `dashboard.py` com os mesmos Secrets.
6. **Testar:** login → envio → registro no Supabase com `codigo_fornecedor` → dashboard.

---

*Documentação gerada para o MVP do Formulário de Fornecedores Alcoa — junho/2026.*

**Próximo passo:** para evoluir a produção formal, consulte **[DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)**.