# Opções de deploy para produção real

Documento de referência para evoluir o **Formulário de Fornecedores** do MVP (Streamlit Cloud + Supabase gratuito) para um **ambiente de produção corporativo**, com segurança, controle e sustentabilidade.

> Para o passo a passo do MVP já implementado, veja **[GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md)**.

---

## 1. O que precisa existir em produção

Este sistema tem **4 peças** que podem ser hospedadas de formas diferentes:

| Peça | Tecnologia atual | Função |
|---|---|---|
| **Formulário público** | `app.py` (Streamlit) | Interface para o fornecedor |
| **Dashboard interno** | `dashboard.py` (Streamlit) | Uso da equipe Alcoa |
| **Banco de respostas** | Supabase (PostgreSQL) | Armazena envios do formulário |
| **Arquivo FUP** | `relatorio_fup.xlsm` | Consulta de PO, linha e fornecedor |

Em produção real, além de “subir o app”, normalmente se exige:

- Domínio corporativo (`forms.alcoa.com.br`)
- HTTPS e certificado
- Controle de acesso no dashboard (não público)
- Secrets em cofre (não em arquivo `.env`)
- Backup e retenção de dados
- Logs e monitoramento
- Política de segurança (RLS, firewall, rede)
- SLA e suporte interno

---

## 2. Comparativo rápido das opções

| Opção | Complexidade | Custo inicial | Controle | Melhor para |
|---|---|---|---|---|
| **A. Streamlit Cloud (atual)** | Baixa | Grátio / baixo | Baixo | MVP, piloto, poucos usuários |
| **B. Streamlit em Docker (VM/Cloud)** | Média | Médio | Alto | Produção com equipe de infra |
| **C. Azure App Service / Container Apps** | Média | Médio | Alto | Empresas já em Microsoft/Azure |
| **D. AWS (ECS / EC2 / Beanstalk)** | Média–alta | Médio | Alto | Empresas já em AWS |
| **E. Google Cloud Run** | Média | Baixo–médio | Alto | App containerizado com escala automática |
| **F. Kubernetes (AKS/EKS/GKE)** | Alta | Alto | Muito alto | Grande escala, padrão corporativo |
| **G. Servidor on-premises / VM interna** | Média | Variável | Total | Rede fechada, política de dados local |
| **H. Reescrita (API + frontend)** | Muito alta | Alto | Total | Produto de longo prazo, UX customizada |

**Legenda de adequação:**

- ✅ Viável e comum
- ⚠️ Viável com ressalvas
- ❌ Pouco recomendado para este caso

---

## 3. Opção A — Streamlit Community Cloud (MVP / piloto)

**Como é hoje:** `app.py` e `dashboard.py` em apps separados no [share.streamlit.io](https://share.streamlit.io), Secrets no painel, Supabase na nuvem.

### Vantagens
- Deploy em minutos
- Sem servidor para gerenciar
- Integração direta com GitHub
- Custo zero ou muito baixo no início

### Limitações para produção real
- Avatar/conta do desenvolvedor visível no app (plano gratuito)
- Pouco controle de rede e firewall
- Sem SSO corporativo nativo no dashboard
- Dependência de serviço externo (Streamlit + Supabase)
- Secrets no painel Streamlit (não integrado a cofre corporativo)
- Escala e SLA limitados

### Quando usar
- Piloto com fornecedores
- Validação de processo
- Até ~dezenas de envios/dia com equipe pequena

### Quando migrar
- Exigência de domínio `*.alcoa.com`
- Auditoria / compliance
- Autenticação corporativa (Azure AD)
- Remover branding de terceiros

**Adequação produção Alcoa:** ⚠️ Piloto sim, produção formal não.

---

## 4. Opção B — Streamlit em Docker (recomendada como primeiro passo “sério”)

Empacota `app.py` e `dashboard.py` em containers e roda em qualquer nuvem ou servidor interno.

### Arquitetura

```
Internet / VPN
    → Reverse Proxy (Nginx / Azure Front Door / ALB)
        → Container app.py  (porta 8501)
        → Container dashboard.py  (porta 8502)
    → Supabase ou PostgreSQL corporativo
    → Storage (FUP): blob S3 / Azure Files / share interno
```

### Exemplo de `Dockerfile` (formulário)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

Para o dashboard, use outro container com `dashboard.py` na porta 8502.

### Variáveis de ambiente (produção)

```env
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_TABLE=formulario
SUPABASE_STORAGE_BUCKET=Form
SUPABASE_FUP_FILE=relatorio_fup.xlsm
FORM_BASE_URL=https://forms.alcoa.com.br
```

### Vantagens
- Mesmo código atual, pouca mudança
- Controle total de domínio, SSL e rede
- Pode rodar em Azure, AWS, GCP ou VM interna
- Fácil integrar com CI/CD

### Desvantagens
- Precisa de equipe para manter containers
- Streamlit não é otimizado para milhares de usuários simultâneos
- Dois apps = dois containers (form + dashboard)

**Adequação produção Alcoa:** ✅ Boa opção intermediária.

---

## 5. Opção C — Microsoft Azure

Indicada se a Alcoa já usa ecossistema Microsoft (Azure AD, políticas, billing centralizado).

### C1. Azure App Service (Web App for Containers)

| Item | Detalhe |
|---|---|
| **Como** | Imagem Docker no App Service |
| **SSL** | Certificado gerenciado + domínio customizado |
| **Secrets** | Azure Key Vault + referências no App Service |
| **Auth dashboard** | **Easy Auth** com Azure AD (Microsoft Entra ID) |
| **FUP** | Azure Blob Storage ou montagem de arquivo |

**Prós:** Integração forte com AD corporativo, operação simples.  
**Contras:** Custo mensal por app; cold start leve em planos menores.

### C2. Azure Container Apps

| Item | Detalhe |
|---|---|
| **Como** | Containers gerenciados, escala automática |
| **Ideal** | Tráfego variável, deploy moderno |
| **Rede** | VNET interna, private endpoints para banco |

**Prós:** Escala automática, modelo moderno.  
**Contras:** Configuração de rede um pouco mais complexa.

### C3. Máquina Virtual (VM) Windows/Linux

| Item | Detalhe |
|---|---|
| **Como** | VM + Docker ou serviço systemd rodando Streamlit |
| **Ideal** | Ambiente totalmente controlado, legado, rede interna |

**Prós:** Máximo controle.  
**Contras:** Patch, backup e HA por conta da equipe.

### C4. Azure Static Web Apps + API

Não se aplica diretamente ao Streamlit. Seria caminho de **reescrita** (frontend estático + API).

**Adequação produção Alcoa:** ✅ **App Service** ou **Container Apps** são as mais viáveis.

---

## 6. Opção D — Amazon Web Services (AWS)

### D1. ECS Fargate (containers sem gerenciar servidor)

- Dois serviços: `form` e `dashboard`
- Load Balancer (ALB) com HTTPS
- Secrets no **AWS Secrets Manager**
- FUP no **S3**

**Prós:** Escalável, padrão de mercado.  
**Contras:** Curva de aprendizado IAM/VPC.

### D2. EC2 (máquina virtual)

- Similar à VM Azure
- Docker Compose com nginx na frente

**Prós:** Simples de entender.  
**Contras:** Manutenção manual de SO.

### D3. Elastic Beanstalk

- Deploy de container com menos configuração que ECS

**Prós:** Mais simples que ECS puro.  
**Contras:** Menos flexível em redes corporativas complexas.

**Adequação produção Alcoa:** ✅ Se a empresa padroniza AWS.

---

## 7. Opção E — Google Cloud Run

- Container Docker publicado no Cloud Run
- Escala a zero (paga por uso)
- Domínio customizado + Cloud Load Balancing
- Secrets no Secret Manager

**Prós:** Custo eficiente para tráfego moderado, deploy rápido.  
**Contras:** Menos comum em ambientes 100% Microsoft; cold start.

**Adequação produção Alcoa:** ⚠️ Viável se GCP for aprovado internamente.

---

## 8. Opção F — Kubernetes (AKS / EKS / GKE)

Para ambientes com **plataforma corporativa** já existente.

```
Ingress (HTTPS)
  ├── Deployment: formulario-app (app.py)
  ├── Deployment: dashboard-app (dashboard.py)
  ├── Secret: credenciais Supabase
  └── PVC ou objeto externo: FUP (preferir Storage/API)
```

**Prós:** Padrão enterprise, HA, observabilidade, GitOps.  
**Contras:** Alto custo operacional; overkill para um único formulário.

**Adequação produção Alcoa:** ⚠️ Só se já houver cluster e time de plataforma.

---

## 9. Opção G — On-premises / rede interna Alcoa

### Cenários

| Cenário | Descrição |
|---|---|
| **G1. Formulário na internet, dashboard interno** | Fornecedor acessa URL pública; dashboard só na VPN |
| **G2. Tudo interno** | Fornecedores acessam via portal/link autenticado |
| **G3. Híbrido** | App na nuvem, banco PostgreSQL on-premises |

### Infra típica
- VM Windows Server ou Linux em datacenter
- IIS/nginx como proxy reverso
- PostgreSQL interno **ou** Supabase com aprovação de segurança
- Arquivo FUP em share de rede (`\\servidor\FUP\relatorio_fup.xlsm`)

**Prós:** Dados e rede sob política interna.  
**Contras:** Acesso externo de fornecedores exige VPN, portal ou DMZ.

**Adequação produção Alcoa:** ✅ Muito comum em empresas industriais.

---

## 10. Banco de dados em produção

### 10.1 Manter Supabase (evolução do MVP)

| Plano | Uso |
|---|---|
| **Free** | MVP / testes |
| **Pro** | Produção leve com backup, mais conexões |
| **Team / Enterprise** | SSO, SLA, compliance, suporte |

**Ajustes obrigatórios para produção:**

```sql
-- Exemplo: restringir INSERT com validações extras
-- Revisar políticas RLS (não deixar tudo público sem análise)
-- Índice para busca por PO + linha (evitar duplicidade no app E no banco)

CREATE UNIQUE INDEX IF NOT EXISTS idx_formulario_po_linha
ON formulario (numero_po_com_release, numero_linha);
```

- Habilitar **backups automáticos**
- Restringir leitura do dashboard via **service role** apenas no backend (se migrar para API)
- Rotacionar chaves `anon` / `service_role`

### 10.2 PostgreSQL corporativo (Azure Database / RDS / on-prem)

Substitui Supabase mantendo SQL parecido.

| Mudança no código | Esforço |
|---|---|
| Trocar `supabase-py` por `psycopg2` / SQLAlchemy | Médio |
| Autenticação e Storage separados | Médio |
| Migrations com Flyway/Alembic | Baixo–médio |

**Prós:** Controle total, auditoria, rede privada.  
**Contras:** Mais trabalho de desenvolvimento e operação.

### 10.3 SQL Server / SAP / data lake

Integração futura para enviar respostas ao ERP — não substitui o formulário diretamente, mas alimenta o processo de follow-up.

**Adequação:** ✅ Caminho natural em empresa grande (ETL após o formulário).

---

## 11. Arquivo FUP (`relatorio_fup.xlsm`) em produção

| Estratégia | Como funciona | Prós | Contras |
|---|---|---|---|
| **Storage na nuvem** (atual) | Supabase Storage / S3 / Blob | Simples, igual ao MVP | Arquivo sensível na nuvem |
| **Share de rede** | VM lê `\\servidor\...\relatorio_fup.xlsm` | Dados ficam on-prem | App precisa estar na mesma rede |
| **Atualização agendada** | Job copia FUP para o container 1x/dia | FUP sempre atualizado | Pipeline extra |
| **API interna** | Microserviço consulta SAP/Excel | Mais seguro e escalável | Desenvolvimento adicional |
| **Eliminar Excel** | Dados do FUP vêm de banco/API | Melhor solução de longo prazo | Projeto maior |

**Recomendação produção:** curto prazo = Storage ou share; longo prazo = **API ou view no banco corporativo**.

---

## 12. Segurança do dashboard em produção

O **formulário** pode ser público. O **dashboard não deve**.

| Mecanismo | Onde usar | Esforço |
|---|---|---|
| **VPN corporativa** | Dashboard só na rede interna | Baixo (infra) |
| **Azure AD / SSO** | App Service Easy Auth, proxy OAuth | Médio |
| **streamlit-authenticator** | Usuário/senha simples no `dashboard.py` | Baixo |
| **IP allowlist** | Firewall só IPs da Alcoa | Baixo |
| **App separado não publicado** | URL secreta + auth | Baixo (fraco) |

**Mínimo aceitável em produção:** autenticação corporativa **ou** VPN + dashboard sem URL pública.

---

## 13. Domínio, HTTPS e rede

### Checklist
- [ ] Domínio corporativo (ex.: `fornecedores.alcoa.com.br`)
- [ ] Certificado TLS (Let's Encrypt, certificado interno ou gerenciado pela cloud)
- [ ] WAF / proteção DDoS (Azure Front Door, Cloudflare, AWS WAF)
- [ ] Rate limiting no formulário (evitar abuso)
- [ ] Logs de acesso centralizados (Splunk, Azure Monitor, CloudWatch)

### Exemplo nginx (proxy reverso)

```nginx
server {
    listen 443 ssl;
    server_name fornecedores.alcoa.com.br;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

---

## 14. CI/CD (entrega contínua)

| Ferramenta | Uso |
|---|---|
| **GitHub Actions** | Build Docker → push registry → deploy |
| **Azure DevOps** | Pipelines corporativos Alcoa |
| **GitLab CI** | Alternativa em alguns grupos |

### Pipeline típico

```
1. Push na branch main
2. Rodar testes / lint
3. Build imagem Docker
4. Scan de vulnerabilidades
5. Deploy em homologação
6. Aprovação manual
7. Deploy em produção
8. Smoke test (abrir form + envio de teste)
```

---

## 15. Monitoramento, backup e continuidade

| Item | Sugestão |
|---|---|
| **Backup banco** | Diário automático (Supabase Pro ou PostgreSQL corporativo) |
| **Retenção** | Política de 1–7 anos conforme compliance |
| **Logs de erro** | Sentry, Azure App Insights, CloudWatch |
| **Alertas** | Falha de deploy, app fora do ar, erro de conexão Supabase |
| **RTO/RPO** | Definir com TI (ex.: recuperar em 4h, perda máxima 1h de dados) |
| **Health check** | Endpoint ou script que valida Supabase + leitura do FUP |

---

## 16. Opção H — Reescrita para produção de longo prazo

Se o formulário virar **produto permanente** com muitos fornecedores e integrações:

### Arquitetura alvo

```
Frontend (React / Angular / Power Apps)
        ↓
API (FastAPI / .NET)
        ↓
PostgreSQL / SQL Server  ←→  SAP / FUP API
```

| Aspecto | Streamlit (hoje) | API + Frontend |
|---|---|---|
| UX customizada | Limitada | Total |
| SSO / roles | Difícil | Nativo |
| Performance | Moderada | Alta |
| Manutenção por devs | Python only | Time full-stack |
| Tempo para produzir | Já pronto | Meses |

**Adequação:** ✅ Para roadmap 12–24 meses se o processo for crítico.

---

## 17. Caminhos recomendados por cenário

### Cenário 1 — “Está funcionando, quero oficializar com pouco esforço”

```
Streamlit Cloud (ou Docker em 1 VM)
+ Supabase Pro
+ Domínio customizado (CNAME)
+ RLS revisada + índice único PO+linha
+ Dashboard atrás de VPN ou senha
```

**Prazo estimado:** 2–4 semanas (aprovações internas).

---

### Cenário 2 — “Produção Alcoa padrão Azure”

```
Azure Container Apps (2 containers)
+ Azure Key Vault (secrets)
+ Azure Database for PostgreSQL (ou Supabase aprovado)
+ Azure Blob (FUP)
+ Azure AD no dashboard
+ domínio *.alcoa.com.br
+ GitHub Actions ou Azure DevOps
```

**Prazo estimado:** 1–3 meses (infra + segurança + homologação).

---

### Cenário 3 — “Dados não podem sair da rede”

```
VM on-premises
+ PostgreSQL interno
+ FUP em share de rede
+ Formulário na DMZ ou portal de fornecedores
+ Dashboard só intranet
```

**Prazo estimado:** 2–4 meses.

---

### Cenário 4 — “Integração total com SAP / follow-up”

```
API intermediária
+ Formulário web (Streamlit ou frontend)
+ Respostas gravadas em SQL Server
+ Job noturno sincroniza com FUP/SAP
+ Dashboard em Power BI ou app interno
```

**Prazo estimado:** 6–12 meses.

---

## 18. Estimativa de custo mensal (ordem de grandeza)

| Opção | Custo aproximado (USD/mês) |
|---|---|
| MVP Streamlit Cloud + Supabase Free | $0 |
| Streamlit Cloud Teams + Supabase Pro | $50 – $200 |
| 1 VM cloud pequena + Supabase Pro | $80 – $250 |
| Azure App Service (2 apps) + PostgreSQL básico | $150 – $400 |
| Azure Container Apps + Key Vault + monitoramento | $200 – $600 |
| Kubernetes enterprise (cluster compartilhado) | $500+ (depende do que já existe) |

*Valores variam por região, tráfego e contratos corporativos.*

---

## 19. Matriz de decisão (resumo executivo)

| Critério | MVP atual | Docker + Cloud | Azure corporativo | On-prem |
|---|---|---|---|---|
| Time to market | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Segurança | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Custo inicial | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Escalabilidade | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Compliance Alcoa | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 20. Próximos passos sugeridos

### Fase 1 — Estabilizar o MVP (agora)
- [ ] Supabase Pro ou revisão de RLS
- [ ] Índice único `PO + linha` no banco
- [ ] Domínio amigável (mesmo no Streamlit)
- [ ] Proteger dashboard (senha ou VPN)

### Fase 2 — Produção controlada (1–3 meses)
- [ ] Dockerizar `app.py` e `dashboard.py`
- [ ] Deploy em Azure/AWS aprovado pela TI
- [ ] Secrets no Key Vault / Secrets Manager
- [ ] CI/CD e monitoramento

### Fase 3 — Integração corporativa (6+ meses)
- [ ] Substituir Excel FUP por API ou banco
- [ ] SSO corporativo
- [ ] Integração com SAP / follow-up
- [ ] Avaliar reescrita frontend se o volume crescer

---

## 21. Documentos relacionados

| Arquivo | Conteúdo |
|---|---|
| [GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md) | Passo a passo do MVP (Supabase + Streamlit Cloud) |
| [README.md](README.md) | Visão técnica e execução local |
| `.env.example` | Variáveis de configuração |

---

## 22. Contatos e aprovações internas (preencher)

| Área | Responsável | Aprovação necessária |
|---|---|---|
| TI / Infraestrutura | | Hospedagem, VM, Azure |
| Segurança da informação | | Dados de fornecedores, URL pública |
| Compras / Supply Chain | | Processo e campos do formulário |
| DBA | | Banco PostgreSQL / Supabase |
| Jurídico / Privacidade | | Dados pessoais (e-mail fornecedor) |

---

*Documento de arquitetura e deploy — Formulário de Fornecedores Alcoa. Junho/2026.*
