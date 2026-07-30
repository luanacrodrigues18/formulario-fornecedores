-- Fecha RLS: anon/authenticated NÃO leem/gravam tabelas sensíveis.
-- O app Streamlit deve usar SUPABASE_SERVICE_ROLE_KEY (bypassa RLS no servidor).
-- Rode no SQL Editor do Supabase.

-- ── formulario ──────────────────────────────────────────────────────────────
ALTER TABLE IF EXISTS formulario ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Permitir leitura pública" ON formulario;
DROP POLICY IF EXISTS "Permitir inserção pública" ON formulario;
DROP POLICY IF EXISTS "formulario_select" ON formulario;
DROP POLICY IF EXISTS "formulario_insert" ON formulario;
DROP POLICY IF EXISTS "formulario_update" ON formulario;
DROP POLICY IF EXISTS "formulario_delete" ON formulario;

-- Sem políticas para anon = negado. service_role continua com acesso total.

-- ── contas_fornecedor ───────────────────────────────────────────────────────
ALTER TABLE IF EXISTS contas_fornecedor ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "contas_select" ON contas_fornecedor;
DROP POLICY IF EXISTS "contas_insert" ON contas_fornecedor;
DROP POLICY IF EXISTS "contas_update" ON contas_fornecedor;
DROP POLICY IF EXISTS "contas_delete" ON contas_fornecedor;

-- ── acessos_log ─────────────────────────────────────────────────────────────
ALTER TABLE IF EXISTS acessos_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "acessos_select" ON acessos_log;
DROP POLICY IF EXISTS "acessos_insert" ON acessos_log;
DROP POLICY IF EXISTS "acessos_update" ON acessos_log;
DROP POLICY IF EXISTS "acessos_delete" ON acessos_log;

-- Conferência (deve retornar 0 políticas abertas nessas tabelas):
-- SELECT schemaname, tablename, policyname FROM pg_policies
-- WHERE tablename IN ('formulario', 'contas_fornecedor', 'acessos_log');
