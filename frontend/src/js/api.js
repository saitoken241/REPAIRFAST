/* ════════════════════════════════════════════════════
   api.js — RepairFast
   Camada de comunicação com o backend FastAPI.
   Centraliza config, mock e todos os endpoints.

   Importar antes do script da página:
   <script src="../src/js/api.js"></script>

   ─────────────────────────────────────────────────
   Para ativar a API real:
     1. Mude USE_MOCK para false
     2. Defina API_BASE com a URL do FastAPI
   ─────────────────────────────────────────────────

   Rotas pendentes (backend cria amanhã) — forçam mock:
     • GET  /reports/me/resumo      → getResumoFuncionario
     • GET  /reports/setor/resumo   → getResumoSetor
     • GET  /reports/setor/criticos → getReportesCriticos
     • GET  /notificacoes/me        → getNotificacoes
     • PATCH /notificacoes/:id/lida → patchNotificacaoLida
     • GET  /dashboard/*            → getDashboard
════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════
   CONFIG
══════════════════════════════════════════ */
const USE_MOCK = false;
const API_BASE = "http://localhost:8000";

/** Headers padrão — inclui token JWT salvo no login.
 *  Lê do sessionStorage (padrão atual). Se não encontrar,
 *  migra automaticamente do localStorage (sessões antigas). */
const authHeaders = () => {
  let token = sessionStorage.getItem('token');
  if (!token) {
    const legacy = localStorage.getItem('token');
    if (legacy) {
      // Migra para sessionStorage e limpa localStorage
      sessionStorage.setItem('token', legacy);
      const perfil = localStorage.getItem('perfil');
      if (perfil) sessionStorage.setItem('perfil', perfil);
      localStorage.removeItem('token');
      localStorage.removeItem('perfil');
      token = legacy;
    }
  }
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token || ""}`
  };
};

/* ══════════════════════════════════════════
   MOCK DATA
   Espelha exatamente o contrato de resposta
   que a API real vai retornar.
══════════════════════════════════════════ */
const MOCK = {

  /* ── Funcionário ── */
  funcionario: {
    nome: "João", sobrenome: "Lima",
    cargo: "Operador", setor: "Produção", turno: "Turno A"
  },

  resumoFuncionario: {
    total: 12, aberto: 4, andamento: 5, resolvido: 3
  },

  reportesFuncionario: [
    { id:1248, titulo:"Falta de sinalização em área de risco — Corredor B",       setor:"Segurança",  prioridade:"alta",  status:"aberto",    data:"21/03/2025" },
    { id:1241, titulo:"Equipamento de esteira com trepidação anormal",             setor:"Produção",   prioridade:"alta",  status:"andamento", data:"19/03/2025" },
    { id:1227, titulo:"EPI ausente no posto de laminação — Linha 3",               setor:"Qualidade",  prioridade:"media", status:"resolvido", data:"15/03/2025" },
    { id:1219, titulo:"Vazamento de óleo próximo à máquina CNC-04",                setor:"Manutenção", prioridade:"alta",  status:"andamento", data:"12/03/2025" },
    { id:1210, titulo:"Iluminação insuficiente no corredor de saída emergencial",   setor:"Segurança",  prioridade:"baixa", status:"resolvido", data:"08/03/2025" }
  ],

  notificacoes: [
    { id:1, emoji:"💬", msg:"Seu reporte <strong>#1241</strong> foi atualizado para <em>Em andamento</em>.", tempo:"há 2h",     lida:false, cor:"var(--blue)"   },
    { id:2, emoji:"✅", msg:"Reporte <strong>#1227</strong> foi resolvido pelo técnico responsável.",        tempo:"há 1 dia",  lida:false, cor:"var(--green)"  },
    { id:3, emoji:"🏅", msg:"Você ganhou a conquista <strong>Vigilante</strong> por 10 reportes!",           tempo:"há 2 dias", lida:false, cor:"var(--yellow)" },
    { id:4, emoji:"⚠️", msg:"Reporte <strong>#1219</strong> aguarda sua confirmação de ação.",              tempo:"há 3 dias", lida:true,  cor:"var(--orange)" }
  ],

  /* ── Analista ── */
  analista: {
    nome: "Ricardo", sobrenome: "Santos", setor: "Segurança do Trabalho"
  },

  resumoAnalista: {
    total: 38, aberto: 12, andamento: 5, resolvido: 18
  },

  criticos: [
    { id:1248, titulo:"Falta de sinalização em área de risco — Corredor B", setor:"Segurança", status:"aberto",    reporter:"João Lima",  data:"21/03/2025" },
    { id:1241, titulo:"Equipamento de esteira com trepidação anormal",       setor:"Segurança", status:"aberto",    reporter:"Carlos F.",  data:"19/03/2025" },
    { id:1235, titulo:"Vazamento de produto químico na Linha 2",             setor:"Segurança", status:"aberto",    reporter:"Ana Paula",  data:"17/03/2025" },
    { id:1230, titulo:"Bloqueio de rota de fuga no Galpão C",                setor:"Segurança", status:"andamento", reporter:"Marcos V.",  data:"15/03/2025" },
  ],

  reportesAnalista: [
    { id:1248, titulo:"Falta de sinalização em área de risco — Corredor B",        reporter:"João Lima",   prioridade:"alta",  status:"aberto",    data:"21/03/2025" },
    { id:1247, titulo:"EPI ausente no posto de laminação — Linha 3",               reporter:"Ana Paula",   prioridade:"alta",  status:"aberto",    data:"21/03/2025" },
    { id:1245, titulo:"Iluminação inadequada no corredor de saída emergencial",     reporter:"Pedro R.",    prioridade:"media", status:"andamento", data:"20/03/2025" },
    { id:1241, titulo:"Equipamento de esteira com trepidação anormal",             reporter:"Carlos F.",   prioridade:"alta",  status:"aberto",    data:"19/03/2025" },
    { id:1238, titulo:"Ruído excessivo próximo à área de manutenção",              reporter:"Marcos V.",   prioridade:"media", status:"andamento", data:"18/03/2025" },
    { id:1235, titulo:"Vazamento de produto químico na Linha 2",                   reporter:"Ana Paula",   prioridade:"alta",  status:"aberto",    data:"17/03/2025" },
    { id:1232, titulo:"Falta de equipamento de combate a incêndio no Galpão A",    reporter:"João Lima",   prioridade:"alta",  status:"andamento", data:"16/03/2025" },
    { id:1230, titulo:"Bloqueio de rota de fuga no Galpão C",                      reporter:"Marcos V.",   prioridade:"alta",  status:"andamento", data:"15/03/2025" },
    { id:1227, titulo:"Piso escorregadio na entrada do refeitório",                reporter:"Fernanda S.", prioridade:"media", status:"resolvido", data:"15/03/2025" },
    { id:1224, titulo:"Ausência de protetor auricular na área de britagem",        reporter:"Pedro R.",    prioridade:"alta",  status:"resolvido", data:"14/03/2025" },
    { id:1220, titulo:"Risco de queda em plataforma elevada — Setor B2",           reporter:"João Lima",   prioridade:"alta",  status:"andamento", data:"13/03/2025" },
    { id:1218, titulo:"Descarte irregular de resíduos químicos",                   reporter:"Carlos F.",   prioridade:"media", status:"resolvido", data:"12/03/2025" },
  ],

  /* ── Gestor ── */
  gestor: {
    nome: "Felipe", sobrenome: "Moura", setor: "Operações"
  },

  dashboardEmpresa: {
    kpis: { total:850, totalDelta:"+12%", tempo:58.6, sla:55.3, slaN:470, slaD:850, criticos:12, criticosSub:"em 4 setores" },
    setor: [
      { nome:"Produção",   val:270, pct:100, cor:"#E85C1A" },
      { nome:"Manutenção", val:216, pct:80,  cor:"#4A9EE8" },
      { nome:"Logística",  val:155, pct:57,  cor:"#2EC4B6" },
      { nome:"Qualidade",  val:85,  pct:31,  cor:"#9B6FE8" },
      { nome:"Segurança",  val:74,  pct:27,  cor:"#E8504A" },
      { nome:"TI",         val:50,  pct:18,  cor:"#F5C842" },
    ],
    prio:    { alta_total:67, alta:241, media:357, baixa:185 },
    mensal:  [161, 76, 142, 155, 157, 159],
    meses:   ["Mai","Jun","Jul","Ago","Set","Out"],
    ranking: [
      { nome:"Logística",  reportes:155, sla:91, slaClass:"sla-ok"   },
      { nome:"Qualidade",  reportes:85,  sla:84, slaClass:"sla-ok"   },
      { nome:"Manutenção", reportes:216, sla:71, slaClass:"sla-warn" },
      { nome:"Produção",   reportes:270, sla:58, slaClass:"sla-warn" },
      { nome:"Segurança",  reportes:74,  sla:42, slaClass:"sla-bad"  },
      { nome:"TI",         reportes:50,  sla:38, slaClass:"sla-bad"  },
    ],
    recentes: [
      { id:1248, titulo:"Falta de sinalização — Corredor B",            setor:"Segurança",  prioridade:"alta",  status:"aberto",    data:"21/03" },
      { id:1247, titulo:"EPI ausente no posto de laminação",            setor:"Qualidade",  prioridade:"alta",  status:"aberto",    data:"21/03" },
      { id:1245, titulo:"Iluminação inadequada no corredor emergencial", setor:"Segurança",  prioridade:"media", status:"andamento", data:"20/03" },
      { id:1241, titulo:"Esteira com trepidação anormal",               setor:"Produção",   prioridade:"alta",  status:"aberto",    data:"19/03" },
      { id:1238, titulo:"Ruído excessivo — área de manutenção",         setor:"Manutenção", prioridade:"media", status:"andamento", data:"18/03" },
    ]
  },

  dashboardSetor: {
    kpis: { total:74, totalDelta:"+5%", tempo:52.1, sla:42, slaN:31, slaD:74, criticos:4, criticosSub:"todos em aberto" },
    setor: [
      { nome:"NR-35 — Altura",   val:28, pct:100, cor:"#E85C1A" },
      { nome:"NR-10 — Elétrica", val:19, pct:68,  cor:"#4A9EE8" },
      { nome:"NR-12 — Máquinas", val:15, pct:54,  cor:"#2EC4B6" },
      { nome:"NR-6 — EPI",       val:12, pct:43,  cor:"#9B6FE8" },
    ],
    prio:    { alta_total:4, alta:18, media:32, baixa:20 },
    mensal:  [14, 8, 11, 13, 15, 13],
    meses:   ["Mai","Jun","Jul","Ago","Set","Out"],
    ranking: [
      { nome:"Subsetor A", reportes:28, sla:55, slaClass:"sla-warn" },
      { nome:"Subsetor B", reportes:19, sla:42, slaClass:"sla-bad"  },
      { nome:"Subsetor C", reportes:27, sla:30, slaClass:"sla-bad"  },
    ],
    recentes: [
      { id:1248, titulo:"Falta de sinalização — Corredor B",    setor:"Segurança", prioridade:"alta", status:"aberto",    data:"21/03" },
      { id:1235, titulo:"Vazamento de produto químico Linha 2", setor:"Segurança", prioridade:"alta", status:"aberto",    data:"17/03" },
      { id:1230, titulo:"Bloqueio de rota de fuga Galpão C",    setor:"Segurança", prioridade:"alta", status:"andamento", data:"15/03" },
    ]
  }
};

/* ══════════════════════════════════════════
   NORMALIZAÇÃO
   Converte a resposta do backend (campos em inglês)
   para o formato esperado pelo frontend (campos em pt-BR).
   Chamada apenas nas funções que usam a API real.
   O mock já retorna os campos no formato correto.
══════════════════════════════════════════ */

/**
 * Converte um objeto Report do backend para o formato do frontend.
 *
 * Mapeamentos aplicados:
 *   title       → titulo
 *   description → descricao
 *   category    → setor  (backend não tem campo "setor" separado ainda)
 *   priority    → prioridade  (low→baixa, medium→media, high→alta)
 *   status      → status      (open→aberto, in_progress→andamento, closed→resolvido)
 *   created_at  → data        (formatado como DD/MM/AAAA)
 */
function normalizarReport(r) {
  const statusMap = {
    open:        'aberto',
    in_progress: 'andamento',
    closed:      'resolvido',
  };
  const prioMap = {
    low:    'baixa',
    medium: 'media',
    high:   'alta',
  };
  const tipoMap = {
    failure:     'Falha',
    risk:        'Risco',
    improvement: 'Melhoria',
  };

  return {
    id:               r.id,
    titulo:           r.title,
    descricao:        r.description,
    categoria:        r.category,
    setor:            r.department_name || null,
    department_id:    r.department_id   || null,
    prioridade:       prioMap[r.priority]  || r.priority,
    status:           statusMap[r.status]  || r.status,
    tipo:             tipoMap[r.occurrence_type] || null,
    data:             r.created_at
                        ? new Date(r.created_at).toLocaleDateString('pt-BR')
                        : '—',
    updated_at:       r.updated_at || null,
    attachment:       r.attachment || null,
    reporter:         r.reporter_name || null,
    assigned_to:      r.assigned_to   || null,
    assigned_to_name: r.assigned_to_name || null,
  };
}

/* ══════════════════════════════════════════
   ENDPOINTS — USUÁRIO
══════════════════════════════════════════ */

/** GET /auth/me — dados do usuário logado */
async function getUsuarioMe() {
  if (USE_MOCK) return MOCK.funcionario;
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar usuário");
  return res.json();
}

/** GET /auth/me — dados do analista logado */
async function getAnalistaMe() {
  if (USE_MOCK) return MOCK.analista;
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar analista");
  return res.json();
}

/** GET /auth/me — dados do gestor logado */
async function getGestorMe() {
  if (USE_MOCK) return MOCK.gestor;
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar gestor");
  return res.json();
}

/* ══════════════════════════════════════════
   ENDPOINTS — FUNCIONÁRIO
══════════════════════════════════════════ */

/**
 * GET /reports/me/resumo — resumo dos reportes do funcionário.
 * PENDENTE: rota ainda não existe no backend → força mock.
 * TODO: remover "|| true" quando backend criar GET /reports/me/resumo
 */
async function getResumoFuncionario() {
  if (USE_MOCK) return MOCK.resumoFuncionario;
  const res = await fetch(`${API_BASE}/reports/me/resumo`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar resumo");
  return res.json();
}

/**
 * GET /reports/ — lista de reportes do funcionário logado.
 * O backend filtra automaticamente por user_id quando role = employee.
 */
async function getReportesFuncionario() {
  if (USE_MOCK) return MOCK.reportesFuncionario;
  const res = await fetch(`${API_BASE}/reports/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar reportes");
  const data = await res.json();
  return data.map(normalizarReport);
}

/**
 * POST /reports/ — cria um novo reporte.
 * Chamado pelo report_create.html no submit do formulário.
 * @param {{ title, description, category, priority, attachment }} payload
 * @returns {Promise<{ id, title, status, priority, ... }>} reporte criado
 */
async function criarReport(payload) {
  if (USE_MOCK) {
    await new Promise(r => setTimeout(r, 800));
    return { id: 2000 + Math.floor(Math.random() * 999), ...payload };
  }
  const res = await fetch(`${API_BASE}/reports/`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Erro ao criar reporte');
  return res.json();
}

/**
 * GET /departments/ — lista todos os departamentos.
 */
async function listarDepartamentos() {
  const res = await fetch(`${API_BASE}/departments/`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Erro ao listar departamentos');
  return res.json();
}

/**
 * PUT /reports/:id — atualiza dados do reporte (ex: priority pelo analyst).
 */
async function atualizarPrioridade(reportId, priority) {
  const res = await fetch(`${API_BASE}/reports/${reportId}`, {
    method: 'PUT',
    headers: authHeaders(),
    body: JSON.stringify({ priority }),
  });
  if (!res.ok) throw new Error('Erro ao atualizar prioridade');
  return res.json();
}

/**
 * GET /notificacoes/me — notificações do usuário.
 * PENDENTE: rota ainda não existe no backend → força mock.
 * TODO: remover "|| true" quando backend criar GET /notificacoes/me
 */
async function getNotificacoes() {
  if (USE_MOCK || true) return MOCK.notificacoes;
  const res = await fetch(`${API_BASE}/notificacoes/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar notificações");
  return res.json();
}

/**
 * PATCH /notificacoes/:id/lida — marca notificação como lida.
 * PENDENTE: rota ainda não existe no backend → no-op.
 * TODO: implementar quando backend criar PATCH /notificacoes/:id/lida
 */
async function patchNotificacaoLida(id) {
  if (USE_MOCK || true) return;
  await fetch(`${API_BASE}/notificacoes/${id}/lida`, {
    method: "PATCH",
    headers: authHeaders()
  });
}

/* ══════════════════════════════════════════
   ENDPOINTS — ANALISTA
══════════════════════════════════════════ */

/**
 * GET /reports/setor/resumo — resumo do setor.
 * PENDENTE: rota ainda não existe no backend → força mock.
 * TODO: remover "|| true" quando backend criar GET /reports/setor/resumo
 */
async function getResumoSetor() {
  if (USE_MOCK) return MOCK.resumoAnalista;
  const res = await fetch(`${API_BASE}/reports/department/resume`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar resumo do setor");
  return res.json();
}

/**
 * GET /reports/setor/criticos — reportes críticos do setor.
 * PENDENTE: rota ainda não existe no backend → força mock.
 * TODO: remover "|| true" quando backend criar GET /reports/setor/criticos
 */
async function getReportesCriticos() {
  if (USE_MOCK) return MOCK.criticos;
  const res = await fetch(`${API_BASE}/reports/department/critical`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar críticos");
  return res.json();
}

/**
 * GET /reports/me — reportes criados pelo próprio analista logado.
 */
async function getMeusReportes() {
  if (USE_MOCK) return MOCK.reportesFuncionario;
  const res = await fetch(`${API_BASE}/reports/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar meus reportes");
  const data = await res.json();
  return data.map(normalizarReport);
}

/**
 * GET /reports/ — todos os reportes do setor (analista/gestor).
 * O backend filtra automaticamente por department_id quando role = analyst ou manager.
 */
async function getReportesSetor() {
  if (USE_MOCK) return MOCK.reportesAnalista;
  const res = await fetch(`${API_BASE}/reports/`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar reportes do setor");
  const data = await res.json();
  return data.map(normalizarReport);
}

/** GET /reports/me — reportes criados pelo analista logado (qualquer setor). */
async function getReportesCriados() {
  if (USE_MOCK) return MOCK.reportesFuncionario;
  const res = await fetch(`${API_BASE}/reports/me`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar meus reportes");
  const data = await res.json();
  return data.map(normalizarReport);
}

/** GET /reports/company/resume — resumo de toda a empresa (apenas gestor). */
async function getResumoEmpresa() {
  if (USE_MOCK) return { total: 850, aberto: 241, andamento: 357, resolvido: 185 };
  const res = await fetch(`${API_BASE}/reports/company/resume`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar resumo da empresa");
  return res.json();
}

/** GET /reports/company/reports — todos os reportes da empresa (apenas gestor). */
async function getReportesEmpresa() {
  if (USE_MOCK) return MOCK.reportesAnalista;
  const res = await fetch(`${API_BASE}/reports/company/reports`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar reportes da empresa");
  const data = await res.json();
  return data.map(normalizarReport);
}

/**
 * GET /reports/:id — busca um reporte completo pelo ID.
 * @param {number} id
 */
async function getReportePorId(id) {
  if (USE_MOCK) return null;
  const res = await fetch(`${API_BASE}/reports/${id}`, { headers: authHeaders() });
  if (!res.ok) throw new Error('Erro ao buscar reporte');
  const r = await res.json();
  return normalizarReport(r);
}

/**
 * PUT /reports/:id — atualiza um reporte completo.
 * O backend usa PUT (não PATCH), por isso é necessário enviar o objeto completo.
 *
 * @param {number} id            — ID do reporte
 * @param {object} reportCompleto — { title, description, category, priority, attachment? }
 */
/**
 * GET /users/analysts — lista analistas e gestores do mesmo departamento.
 * Usado para popular selects de atribuição no report_detail_analyst.html.
 */
async function getUsuariosDepartamento() {
  if (USE_MOCK) {
    return [
      { id: 1, name: "Ricardo Santos",  role: "analyst" },
      { id: 2, name: "Ana Paula Lima",  role: "analyst" },
      { id: 3, name: "Felipe Moura",    role: "manager" },
    ];
  }
  const res = await fetch(`${API_BASE}/users/analysts`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar usuários do departamento");
  return res.json();
}

/**
 * GET /reports/:id/history — busca histórico de eventos do reporte.
 * PENDENTE: rota ainda não existe no backend → retorna array vazio.
 * TODO: remover mock quando backend criar GET /reports/:id/history
 */
async function getHistoricoReporte(id) {
  if (USE_MOCK) return [];
  const res = await fetch(`${API_BASE}/reports/${id}/history`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar histórico");
  return res.json();
}

/**
 * POST /reports/:id/history — registra um evento no histórico do reporte.
 * PENDENTE: rota ainda não existe no backend → no-op.
 * TODO: implementar quando backend criar POST /reports/:id/history
 * @param {number} id
 * @param {{ action: string, description?: string, comment?: string, color?: string }} payload
 */
async function registrarHistoricoReporte(id, payload) {
  if (USE_MOCK) return;
  await fetch(`${API_BASE}/reports/${id}/history`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
}

/**
 * GET /reports/:id/plan — busca plano de ação do reporte.
 */
async function getPlanoReporte(id) {
  const res = await fetch(`${API_BASE}/reports/${id}/plan`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar plano de ação");
  return res.json();
}

/**
 * POST /reports/:id/plan — adiciona item ao plano de ação.
 */
async function adicionarItemPlano(id, payload) {
  const res = await fetch(`${API_BASE}/reports/${id}/plan`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Erro ao adicionar item ao plano");
  return res.json();
}

/**
 * PUT /reports/:id/plan/:itemId — atualiza item do plano (marcar done, editar).
 */
async function atualizarItemPlano(reportId, itemId, payload) {
  const res = await fetch(`${API_BASE}/reports/${reportId}/plan/${itemId}`, {
    method: "PUT",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Erro ao atualizar item do plano");
  return res.json();
}

/**
 * DELETE /reports/:id/plan/:itemId — remove item do plano.
 */
async function excluirItemPlano(reportId, itemId) {
  const res = await fetch(`${API_BASE}/reports/${reportId}/plan/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Erro ao excluir item do plano");
  return res.json();
}


async function patchReporteStatus(id, novoStatus) {
  if (USE_MOCK) return;
  const res = await fetch(`${API_BASE}/reports/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify({ status: novoStatus })
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.status);
    throw new Error(`Erro ao atualizar status: ${detail}`);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

/**
 * Atribui reporte a um responsável.
 * PENDENTE: rota ainda não existe no backend → no-op.
 * TODO: implementar quando backend criar rota de atribuição
 */
async function patchReporteAtribuir(id, usuario) {
  const res = await fetch(`${API_BASE}/reports/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify({ assigned_to: usuario })
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.status);
    throw new Error(`Erro ao atribuir responsável: ${detail}`);
  }
  // Tenta parsear JSON; se vier vazio, retorna null (não é erro)
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

/**
 * Adiciona comentário a um reporte.
 * PENDENTE: rota ainda não existe no backend → no-op.
 * TODO: implementar quando backend criar rota de comentários
 */
async function postComentario(id, texto) {
  if (USE_MOCK || true) return;
  await fetch(`${API_BASE}/reports/${id}/comentarios`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ texto })
  });
}

/* ══════════════════════════════════════════
   ENDPOINTS — GESTOR
══════════════════════════════════════════ */

/**
 * GET /dashboard/empresa | /dashboard/setor
 * PENDENTE: rotas ainda não existem no backend → força mock.
 * TODO: remover "|| true" quando backend criar GET /dashboard/*
 * @param {'empresa'|'setor'} escopo
 */
async function getDashboard(escopo = 'empresa') {
  if (USE_MOCK || true) {
    return escopo === 'empresa'
      ? MOCK.dashboardEmpresa
      : MOCK.dashboardSetor;
  }
  const endpoint = escopo === 'empresa' ? '/dashboard/empresa' : '/dashboard/setor';
  const res = await fetch(`${API_BASE}${endpoint}`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Erro ao buscar dashboard");
  return res.json();
}

/* ══════════════════════════════════════════
   ENDPOINTS — AUTH
══════════════════════════════════════════ */

/**
 * POST /auth/login — autentica o usuário.
 *
 * O backend usa OAuth2PasswordRequestForm (form-data), por isso
 * enviamos application/x-www-form-urlencoded com os campos
 * "username" (email) e "password".
 *
 * Após receber o token, consultamos GET /auth/me para obter o
 * role do usuário e mapeamos para o campo "perfil" usado pelo frontend.
 *
 * Mapeamento de roles:
 *   employee  → funcionario
 *   analyst   → analista
 *   manager   → gestor
 *
 * @param {string} email
 * @param {string} senha
 */
async function postLogin(email, senha) {
  if (USE_MOCK) {
    // ── Perfis de teste (mock) ──────────────────────────
    // funcionario@teste.com  → home_employee.html
    // analista@teste.com     → home_analyst.html
    // gestor@teste.com       → home_manager.html
    // qualquer outro e-mail  → home_employee.html
    // ────────────────────────────────────────────────────
    await new Promise(r => setTimeout(r, 1200)); // simula latência
    const perfis = {
      'funcionario@teste.com': 'funcionario',
      'analista@teste.com':    'analista',
      'gestor@teste.com':      'gestor'
    };
    const perfil = perfis[email.toLowerCase()] || 'funcionario';
    const token  = `mock-token-${perfil}-12345`;
    sessionStorage.setItem('token',  token);
    sessionStorage.setItem('perfil', perfil);
    return { token, perfil };
  }

  // ── API real ──
  // 1. Faz login com form-data (padrão OAuth2 do backend)
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password: senha })
  });
  if (!res.ok) throw new Error('Credenciais inválidas');

  const data = await res.json();
  // Backend retorna: { access_token: "...", token_type: "bearer" }
  sessionStorage.setItem('token', data.access_token);

  // 2. Busca o role do usuário em /auth/me
  const meRes = await fetch(`${API_BASE}/auth/me`, {
    headers: { 'Authorization': `Bearer ${data.access_token}` }
  });
  if (!meRes.ok) throw new Error('Erro ao buscar dados do usuário');
  const me = await meRes.json();

  // 3. Mapeia role do backend → perfil do frontend
  const roleMap = {
    'employee': 'funcionario',
    'analyst':  'analista',
    'manager':  'gestor'
  };
  const perfil = roleMap[me.role] || 'funcionario';
  sessionStorage.setItem('perfil', perfil);

  return { token: data.access_token, perfil };
}

/** Remove o token e redireciona para o login */
function logout() {
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('perfil');
  window.location.href = "login.html";
}