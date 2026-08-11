# Mapa da documentação — repasse e replicação

Use este índice para achar o documento certo. Tudo está alinhado ao estado atual do código (login, reset de senha, dashboard com período/PDF, deploy MVP e caminho até produção).

---

## Por objetivo

| Você precisa… | Abra |
|---|---|
| Entender o projeto em 5 minutos | [README.md](README.md) |
| Instalar e publicar o **MVP** (Supabase + Streamlit Cloud) | [GUIA_IMPLANTACAO.md](GUIA_IMPLANTACAO.md) |
| Planejar **produção corporativa** (Azure, Docker, e-mail OTP, SSO) | [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md) |
| Visão executiva MVP → produção (HTML / PDF) | [roadmap_mvp_producao.html](roadmap_mvp_producao.html) |
| Segurança e observabilidade por fase | [seguranca_observabilidade_mvp.html](seguranca_observabilidade_mvp.html) |
| Apresentar o sistema (slides no navegador) | [APRESENTACAO.html](APRESENTACAO.html) |
| Passar o projeto para alguém **sem programar** | [LEIA_PRIMEIRO.txt](LEIA_PRIMEIRO.txt) |
| Rodar em outro PC Alcoa | [COMO_RODAR_OUTRO_PC.txt](COMO_RODAR_OUTRO_PC.txt) |
| Instalar Python | [COMO_INSTALAR_PYTHON.txt](COMO_INSTALAR_PYTHON.txt) |
| Variáveis de ambiente | [.env.example](.env.example) |

---

## O que já está no MVP (hoje)

1. Cadastro / login (usuário + senha + código Alcoa)
2. Formulário isolado por fornecedor + ALUX
3. Dashboard: métricas, **filtro de período**, gráficos, **PDF formatado**, export Excel / retorno FUP
4. **Reset de senha pela equipe** (senha temporária no dashboard → “Esqueci a senha” no formulário)
5. Contas e logs no Supabase; RLS fechado com `service_role`
6. Deploy em Streamlit Cloud + GitHub

## O que fica para produção (depende de TI / DNS / provedor)

- Envio de **código OTP / senha temporária por e-mail** (Resend ou SMTP corporativo)
- Domínio verificado (`@alcoa.com` ou remetente aprovado)
- VPN / SSO no dashboard, domínio `*.alcoa.com.br`, Docker/Azure, etc.

Detalhes e checklist: seção **“Validação: troca de senha por e-mail”** em [DEPLOY_PRODUCAO.md](DEPLOY_PRODUCAO.md).

---

## Ordem sugerida para quem vai replicar o desenvolvimento

```
1. README.md                 → visão + stack
2. .env.example              → secrets
3. GUIA_IMPLANTACAO.md       → Supabase → local → Cloud
4. Testar formulário + dashboard
5. LEIA_PRIMEIRO.txt         → repasse operacional
6. DEPLOY_PRODUCAO.md        → roadmap produção + e-mail
7. roadmap_mvp_producao.html → alinhamento com gestores
```

---

*Atualizado: agosto/2026 — alinhado às features de período, PDF e reset admin.*
