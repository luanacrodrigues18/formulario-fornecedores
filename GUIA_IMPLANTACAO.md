# Guia de implantação - Formulário de Fornecedores

Documentação passo a passo do **MVP**: **Supabase** (banco + Storage), **cadastro/login**, **reset de senha pela equipe**, **dashboard** (período + PDF), **RLS fechado com service_role** e **Streamlit Cloud**.

> Índice geral: [MAPA_DOCUMENTACAO.md](MAPA_DOCUMENTACAO.md)  
> Produção corporativa e **OTP por e-mail**: [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)

---

## Do zero ao piloto (checklist rápido)

Siga **nesta ordem**:

1. **Supabase → SQL Editor**  
   Cole e rode o SQL completo de tabelas do [README.md](README.md) (seção *Criar tabelas no Supabase*):  
   `formulario` + `contas_fornecedor` + `acessos_log`.

2. **Supabase → Settings → API**  
   Copie:
   - Project URL → `SUPABASE_URL`
   - `anon` `public` → `SUPABASE_KEY`
   - `service_role` `secret` → `SUPABASE_SERVICE_ROLE_KEY`  
   (**Reveal** na service_role; nunca publique essa chave.)

3. **No PC**  
   - `copy .env.example .env` e preencha as três chaves.  
   - `pip install -r requirements.txt`  
   - Coloque `relatorio_fup.xlsm` na pasta.  
   - `python gerar_codigos_fornecedores.py`

4. **Supabase → Storage**  
   Bucket `Form` (preferência: **privado**).  
   Upload: `relatorio_fup.xlsm` e `fornecedores_codigos.json`.

5. **Fechar RLS**  
   Com a `SERVICE_ROLE_KEY` já no `.env`, rode [`sql/fechar_rls.sql`](sql/fechar_rls.sql) no SQL Editor → **Run query**.

6. **Subir o app**  
   `streamlit run app.py` (ou `INICIAR.bat`).

7. **Testar**  
   - Cadastro: usuário + senha + e-mail + código Alcoa.  
   - Login: usuário (ou código) + senha.  
   - Enviar um pedido.  
   - Conferir no Table Editor: `contas_fornecedor`, `acessos_log`, `formulario`.  
   - Dashboard: período → métricas → PDF → reset de senha (aba dedicada).

8. **Streamlit Cloud (opcional)**  
   Secrets iguais ao `.env` (incluindo `SUPABASE_SERVICE_ROLE_KEY`) + deploy de `app.py` / `dashboard.py`.

---

## Visão geral

```
Fornecedor cria usuário + senha (código Alcoa da empresa)
        ↓
fornecedores_codigos.json  →  resolve nome na FUP
        ↓
contas_fornecedor (Supabase) + acessos_log
        ↓
app.py - página única: busca, lista e formulário
        ↓
envia resposta → tabela formulario (+ codigo_fornecedor)

Equipe Alcoa  →  dashboard.py
                 ├─ período (7/15 dias, mês, personalizado…)
                 ├─ métricas / gráficos / PDF
                 ├─ export Excel + retorno FUP
                 └─ reset senha (temporária → fornecedor troca)
```


| Componente         | Arquivo                         | Função                                      |
| ------------------ | ------------------------------- | ------------------------------------------- |
| Formulário         | `app.py`                        | Página única, busca e envio                 |
| Autenticação       | `auth_fornecedor.py`            | Cadastro, login, alterar / esqueci senha    |
| Contas             | `contas_fornecedor.py`          | Hash, bloqueio, reset admin, logs           |
| E-mail (produção)  | `email_smtp.py`                 | Resend / SMTP — OTP quando domínio ok       |
| Cadastro de IDs    | `fornecedores_codigos.json`     | Mapa `ID → nome do fornecedor`              |
| Gerador de IDs     | `gerar_codigos_fornecedores.py` | Cria JSON a partir da FUP                   |
| Dashboard interno  | `dashboard.py`                  | Período, PDF, filtros, export, reset senha  |
| Banco de dados     | `database.py`                   | Supabase (prefere service_role)             |
| Planilha FUP       | `planilha.py`                   | Lê pedidos; exporta retorno sem gravar xlsm |
| Assistente         | `alcoano.py`                    | ALUX - dicas e FAQ                          |
| Fechar RLS         | `sql/fechar_rls.sql`            | Remove políticas públicas abertas           |


**URLs de produção (exemplo deste projeto):**

- Formulário: `https://formulario-fornecedores.streamlit.app`
- Repositório: `https://github.com/luanacrodrigues18/formulario-fornecedores`

---



## Parte 1 - Configurar o Supabase



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
```

Em seguida, no **mesmo** SQL Editor (ou nova query), cole também do [README.md](README.md) a criação de `contas_fornecedor` (com coluna `usuario`) e `acessos_log`.

Ou rode tudo de uma vez copiando a seção completa **Criar tabelas no Supabase** do README.

1. Confirme em **Table Editor** que `formulario`, `contas_fornecedor` e `acessos_log` existem.

> Sem a coluna `codigo_fornecedor` em `formulario`, o envio falha com erro `PGRST204`.  
> **Não deixe políticas públicas abertas em produção.** Configure `SUPABASE_SERVICE_ROLE_KEY` e rode [`sql/fechar_rls.sql`](sql/fechar_rls.sql).



### 1.3 Guardar o arquivo FUP no Storage (para a nuvem)

O formulário precisa do arquivo `relatorio_fup.xlsm` para buscar pedidos. Na nuvem ele não vai no GitHub (é sensível/grande), então fica no **Supabase Storage**.

1. No Supabase, abra **Storage**.
2. Crie um bucket chamado `Form` (ou outro nome - se mudar, atualize o `.env`).
3. Prefira bucket **privado** (o app usa `service_role` no servidor).
4. Faça upload do arquivo com o nome exato: `relatorio_fup.xlsm`
  - Evite acentos e espaços no nome do arquivo.
5. Faça upload também de `fornecedores_codigos.json` no **mesmo** bucket `Form`.
  - O app baixa o JSON do Storage quando o arquivo não está na pasta do projeto.
  - Localmente, use o JSON gerado com `gerar_codigos_fornecedores.py`.



### 1.4 Copiar URL e chaves da API

1. Vá em **Project Settings** (ícone de engrenagem).
2. Abra **API**.
3. Copie na **mesma tela**:
  - **Project URL** → `SUPABASE_URL`
  - **anon public** → `SUPABASE_KEY`
  - **service_role** (secret) → `SUPABASE_SERVICE_ROLE_KEY` (somente servidor; nunca no Git)

**Atenção - erros comuns:**


| Problema                                           | Causa                                                          |
| -------------------------------------------------- | -------------------------------------------------------------- |
| `getaddrinfo failed` / `Name or service not known` | URL do Supabase digitada errada                                |
| Dados não salvam / erro de autenticação            | URL de um projeto e chave de outro                             |
| Erro de permissão / RLS após fechar políticas      | Falta `SUPABASE_SERVICE_ROLE_KEY` no `.env` ou Secrets         |
| Formulário na nuvem sem FUP                        | Arquivo não está no Storage ou nome diferente                  |


A URL deve ser algo como: `https://xxxxxxxx.supabase.co` (copiada exatamente do painel).

---



## Parte 2 - Rodar localmente (teste antes do deploy)



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
SUPABASE_SERVICE_ROLE_KEY=sua-chave-service-role-secreta
SUPABASE_TABLE=formulario
SUPABASE_STORAGE_BUCKET=Form
SUPABASE_FUP_FILE=relatorio_fup.xlsm
SUPABASE_CODIGOS_FILE=fornecedores_codigos.json
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
- **Login (local):** cadastro com usuário + senha + código Alcoa; JSON de códigos na pasta.
- **Login (nuvem):** mesmo fluxo; o app baixa `fornecedores_codigos.json` do Storage se faltar localmente.
- **Sem JSON (local nem Storage):** o cadastro/login não resolve a empresa (“código não encontrado”).



### 2.6 Executar e testar

**Formulário:**

```powershell
streamlit run app.py
```

Abra: `http://localhost:8501`

1. Na tela de **Cadastro**, crie usuário + senha e informe o código Alcoa (ex.: `6`).
2. Vá ao **Login** e entre com o usuário (ou o código) + senha.
3. Confira que só aparecem pedidos desse fornecedor.
4. Use **Ver todos** ou busque por PO com Release; marque pedidos e envie.
5. Confira no Supabase a coluna `codigo_fornecedor` e a tabela `contas_fornecedor`.

**Dashboard:**

```powershell
streamlit run dashboard.py
```

1. Na aba **Dashboard / métricas**, escolha o **período** (ex.: Últimos 7 dias, 15 dias, mês, personalizado).
2. Confira métricas e gráficos do intervalo.
3. Clique em **Exportar relatório PDF** — o PDF deve trazer o período e as pendências.
4. Na aba **Filtros e tabela**, teste filtros e **Exportar retorno para Excel (sem mexer na FUP)**.
5. Na aba **Reset senha de fornecedor**, gere uma senha temporária de teste e confirme o fluxo “Esqueci a senha” no formulário.



### 2.7 Checklist do teste local

- [ ] Cadastro com usuário + senha + e-mail + código Alcoa válido
- [ ] Login com usuário ou código + senha
- [ ] Código Alcoa inválido mostra erro claro
- [ ] Conta aparece em `contas_fornecedor` (Table Editor)
- [ ] Evento de acesso aparece em `acessos_log`
- [ ] Só pedidos daquele fornecedor aparecem
- [ ] Busca por PO filtra dentro dos pedidos dele
- [ ] Envio grava no Supabase com `codigo_fornecedor`
- [ ] Dashboard mostra o registro
- [ ] Filtro de período altera métricas / gráficos / PDF
- [ ] PDF exporta sem erro (`fpdf2` no `requirements.txt`)
- [ ] Reset admin: senha temporária → “Esqueci a senha” no formulário
- [ ] É possível enviar de novo para o mesmo PO+linha (gera novo registro)
- [ ] Botão **Sair** encerra a sessão

---



## Parte 2.8 - Cadastro de IDs Alcoa

A FUP **não tem coluna de código**. O isolamento funciona assim:


| Item                      | Onde fica                       |
| ------------------------- | ------------------------------- |
| Pedidos (PO, linha, item) | `relatorio_fup.xlsm`            |
| ID / código Alcoa         | `fornecedores_codigos.json`     |
| Conta (usuário + senha)   | tabela `contas_fornecedor`      |
| Logs de acesso            | tabela `acessos_log`             |
| Respostas enviadas        | tabela `formulario` no Supabase |


Quando a FUP for atualizada, rode de novo:

```powershell
python gerar_codigos_fornecedores.py
```

**Atenção:** regenerar o JSON por ordem alfabética pode **mudar os IDs**. Em produção, prefira IDs estáveis (código SAP) e edite o JSON manualmente.

Na nuvem, o JSON **não vai no Git** (`.gitignore`). Faça upload de `fornecedores_codigos.json` no bucket `Form` (o app baixa no startup). Evolução futura: tabela `fornecedores` no Supabase.

---



## Parte 3 - Publicar no GitHub



### 3.1 O que vai (e o que NÃO vai) para o Git

**Vai:**

- `app.py`, `auth_fornecedor.py`, `dashboard.py`, `database.py`, `planilha.py`, `alcoano.py`
- `gerar_codigos_fornecedores.py`, `gerar_template.py`
- `requirements.txt`, `README.md`, `GUIA_IMPLANTACAO.md`, `DEPLOY_PRODUCAO.md`
- `LEIA_PRIMEIRO.txt`, `INICIAR.bat`, scripts `*.bat` de setup
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



## Parte 4 - Deploy no Streamlit Cloud



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
SUPABASE_SERVICE_ROLE_KEY = "sua-chave-service-role-secreta"
SUPABASE_TABLE = "formulario"
SUPABASE_STORAGE_BUCKET = "Form"
SUPABASE_FUP_FILE = "relatorio_fup.xlsm"
SUPABASE_CODIGOS_FILE = "fornecedores_codigos.json"
FORM_BASE_URL = "https://formulario-fornecedores.streamlit.app"

# Opcional no MVP (reset de senha usa o dashboard).
# Obrigatório só se for ativar OTP por e-mail em produção — ver DEPLOY_PRODUCAO.md
# RESEND_API_KEY = "re_xxxxx"
# EMAIL_FROM = "noreply@seu-dominio-verificado.com"
```

1. Salve e clique em **Reboot app**.
2. Confirme no Storage o upload de `relatorio_fup.xlsm` **e** `fornecedores_codigos.json`.
3. Confirme no SQL Editor que existe a coluna `codigo_fornecedor`.

> **Login na nuvem:** com o JSON no bucket `Form` e a `SUPABASE_SERVICE_ROLE_KEY` nos Secrets, o app baixa o cadastro e grava contas/respostas com RLS fechado.

> Local usa `.env`. Na nuvem usa **Secrets** - são a mesma configuração, em lugares diferentes.

> **Reset de senha no MVP:** não precisa de Resend. Use a aba **Reset senha de fornecedor** no dashboard.



### 4.4 Deploy do dashboard (`dashboard.py`)

O dashboard é um **segundo app** no Streamlit Cloud:

1. **Create app** novamente.
2. Mesmo repositório e branch.
3. **Main file path:** `dashboard.py`
4. Use os **mesmos Secrets** do formulário.
5. Deploy e **Reboot**.
6. Confirme: filtro de período, botão de PDF e aba de reset de senha.



### 4.5 Atualizar depois de mudanças no código

```powershell
git add .
git commit -m "Descrição da mudança"
git push
```

No Streamlit Cloud: **⋮** → **Reboot app** (ou aguarde o redeploy automático). Se o PDF falhar com “No module named fpdf”, faça **Reboot** para reinstalar `requirements.txt` (`fpdf2`).

---



## Parte 5 - Verificação em produção



### Formulário (`app.py`)

1. Abra a URL pública do formulário.
2. Faça cadastro (usuário + senha + e-mail + código) e login.
3. Confira isolamento (só pedidos daquele fornecedor).
4. Preencha e envie.
5. Confirme no Supabase (**Table Editor** → `formulario`) que o registro apareceu com `codigo_fornecedor`.
6. Teste **Esqueci a senha** com uma senha temporária gerada no dashboard.



### Dashboard (`dashboard.py`)

1. Abra a URL do dashboard (**não divulgue** publicamente).
2. Verifique se aparece a mensagem de dados carregados do Supabase.
3. Escolha um **período** e confira métricas / gráficos.
4. Exporte o **PDF** e abra o arquivo (deve trazer o rótulo do período).
5. Use filtros e **Exportar retorno para Excel (sem mexer na FUP)**.
6. Na aba **Reset senha**, gere temporária e valide o ciclo completo com um usuário de teste.

---



## Parte 5.1 - Reset de senha (MVP) vs e-mail (produção)

| Situação | Como funciona hoje |
|---|---|
| Fornecedor esqueceu a senha | Equipe gera **senha temporária** no dashboard → passa por Teams/telefone → fornecedor usa **Esqueci a senha** |
| Login com senha temporária / forçada | App exige **nova senha** antes de continuar |
| Enviar OTP / link por e-mail | Código em `email_smtp.py` pronto; **não é o fluxo principal do MVP** |

Para ativar e **validar** envio por e-mail (domínio DNS, Resend/SMTP corporativo, testes de caixa de entrada), siga a seção dedicada em [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md#validação-troca-de-senha-por-e-mail-produção).

---



## Problemas frequentes e soluções



### Código / usuário não encontrado no login

**Causa:** `fornecedores_codigos.json` ausente na pasta do projeto **e** no Storage, ou nome do fornecedor diferente do FUP.

**Solução:** rode `python gerar_codigos_fornecedores.py`, use um ID da lista e, na nuvem, faça upload do JSON no bucket `Form` (nome `fornecedores_codigos.json`).

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



### PDF indisponível / `No module named 'fpdf'`

**Causa:** ambiente Cloud ainda sem reinstalar dependências após incluir `fpdf2`.

**Solução:** **Reboot** do app `dashboard.py` no Streamlit Cloud. O código também tem fallback sem `fpdf`, mas o ideal é o pacote instalado.

### Reset de senha / “Esqueci a senha” sem e-mail

**Causa esperada no MVP:** recuperação por e-mail ainda não é o fluxo principal.

**Solução:** use a aba **Reset senha de fornecedor** no dashboard. OTP por e-mail = produção ([DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)).

---



## Estrutura final do projeto

```
Project Form/
├── app.py
├── auth_fornecedor.py
├── contas_fornecedor.py
├── dashboard.py
├── database.py
├── planilha.py
├── alcoano.py
├── email_smtp.py
├── prazo_resposta.py
├── gerar_codigos_fornecedores.py
├── requirements.txt          # inclui fpdf2
├── .env.example
├── .streamlit/config.toml
├── MAPA_DOCUMENTACAO.md
├── GUIA_IMPLANTACAO.md
├── DEPLOY_PRODUCAO.md
├── roadmap_mvp_producao.html
├── APRESENTACAO.html
├── LEIA_PRIMEIRO.txt
├── fornecedores_codigos.json.example
├── fornecedores_codigos.json     # Apenas local / Storage (não vai pro Git)
└── relatorio_fup.xlsm            # Apenas local / Storage (não vai pro Git)
```

---



## Resumo rápido (cola)

1. **Supabase:** tabelas `formulario`, `contas_fornecedor`, `acessos_log` + `fechar_rls.sql` + Storage (FUP e JSON) + `SERVICE_ROLE_KEY`.
2. **Local:** `.env` + `pip install` + gerar códigos + `streamlit run app.py` / `dashboard.py`.
3. **Login:** cadastro → login → só pedidos da empresa → envio.
4. **Senha esquecida (MVP):** dashboard gera temporária → fornecedor redefine.
5. **Dashboard:** período → PDF → Excel / retorno FUP.
6. **GitHub:** push sem `.env`, sem FUP e sem `fornecedores_codigos.json`.
7. **Streamlit Cloud:** deploy com Secrets (incluindo `SUPABASE_SERVICE_ROLE_KEY`) + Reboot.
8. **E-mail OTP:** só validar em produção (domínio + Resend/SMTP) — ver DEPLOY_PRODUCAO.md.

---

*Guia de implantação MVP — Formulário de Fornecedores Alcoa. Atualizado agosto/2026.*

*Documentação do Formulário de Fornecedores Alcoa - atualizada em julho/2026.*

**Próximo passo:** para evoluir a produção formal, consulte **[DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md)**.