/* ════════════════════════════════════════════════════
   utils.js — RepairFast
   Funções utilitárias compartilhadas entre todas
   as páginas. Importar antes do script da página:
   <script src="../src/js/utils.js"></script>
════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════
   DOM
══════════════════════════════════════════ */

/**
 * Atualiza o textContent de um elemento pelo ID.
 * @param {string} id
 * @param {string|number} val
 */
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

/**
 * Atualiza apenas o valor numérico de um elemento,
 * preservando filhos (ex: <span> de unidade "h" ou "%").
 * @param {string} id
 * @param {string|number} val
 */
function setValComUnidade(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  [...el.childNodes]
    .filter(n => n.nodeType === Node.TEXT_NODE)
    .forEach(n => n.remove());
  el.insertBefore(document.createTextNode(val), el.firstChild);
}

/* ══════════════════════════════════════════
   DATA E HORA
══════════════════════════════════════════ */

/**
 * Retorna o nome do dia da semana atual em português.
 * @returns {string} Ex: "Segunda-feira"
 */
function diaSemana() {
  return ['Domingo','Segunda-feira','Terça-feira','Quarta-feira',
          'Quinta-feira','Sexta-feira','Sábado'][new Date().getDay()];
}

/**
 * Retorna a data de hoje formatada em português.
 * @returns {string} Ex: "22 de março de 2025"
 */
function dataHoje() {
  return new Date().toLocaleDateString('pt-BR', {
    day: '2-digit', month: 'long', year: 'numeric'
  });
}

/**
 * Retorna a saudação correta com base no horário.
 * @returns {string} "BOM DIA" | "BOA TARDE" | "BOA NOITE"
 */
function saudacao() {
  const hr = new Date().getHours();
  if (hr < 12) return 'BOM DIA';
  if (hr < 18) return 'BOA TARDE';
  return 'BOA NOITE';
}

/* ══════════════════════════════════════════
   SKELETON / LOADING
══════════════════════════════════════════ */

/**
 * Injeta N linhas de skeleton num container.
 * @param {string} id       - ID do elemento container
 * @param {number} n        - Quantidade de linhas (default 3)
 * @param {string} height   - Altura de cada linha (default "66px")
 */
function showSkeleton(id, n = 3, height = '66px') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = Array(n)
    .fill(`<div class="sk" style="height:${height};margin-bottom:10px"></div>`)
    .join('');
}

/**
 * Renderiza o estado de erro num container.
 * @param {string} id       - ID do elemento container
 * @param {string} cols     - colspan para uso em tabelas (opcional)
 */
function showError(id, cols = null) {
  const el = document.getElementById(id);
  if (!el) return;
  const content = `
    <div class="empty-state">
      <div class="empty-icon">⚠️</div>
      <div class="empty-title">Erro ao carregar</div>
      <div class="empty-desc">Não foi possível conectar à API. Tente novamente.</div>
    </div>`;
  el.innerHTML = cols
    ? `<tr><td colspan="${cols}">${content}</td></tr>`
    : content;
}

/**
 * Renderiza o estado vazio num container.
 * @param {string} id    - ID do elemento container
 * @param {string} msg   - Mensagem principal
 * @param {string} desc  - Descrição complementar
 */
function showEmpty(id, msg = 'Nenhum item encontrado', desc = '') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `
    <div class="empty-state">
      <div class="empty-icon">📭</div>
      <div class="empty-title">${msg}</div>
      ${desc ? `<div class="empty-desc">${desc}</div>` : ''}
    </div>`;
}

/* ══════════════════════════════════════════
   SIDEBAR DRAWER (mobile)
   Inicializar chamando: initSidebar()
══════════════════════════════════════════ */

/**
 * Inicializa o comportamento do drawer da sidebar
 * em telas mobile (hamburger + overlay).
 * Deve ser chamado após o DOM estar pronto.
 */
function initSidebar() {
  const sidebar   = document.getElementById('sidebar');
  const overlay   = document.getElementById('overlay');
  const hamburger = document.getElementById('hamburger');

  if (!sidebar || !overlay || !hamburger) return;

  hamburger.addEventListener('click', () => {
    sidebar.classList.add('open');
    overlay.classList.add('open');
  });

  overlay.addEventListener('click', () => {
    sidebar.classList.remove('open');
    overlay.classList.remove('open');
  });

  window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    }
  });

  document.querySelectorAll('.sb-item').forEach(item => {
    item.addEventListener('click', function () {
      document.querySelectorAll('.sb-item').forEach(n => n.classList.remove('active'));
      this.classList.add('active');
      if (window.innerWidth <= 768) {
        sidebar.classList.remove('open');
        overlay.classList.remove('open');
      }
    });
  });
}

/* ══════════════════════════════════════════
   FILTROS
══════════════════════════════════════════ */

/**
 * Ativa o pill clicado e desativa os demais
 * dentro do mesmo grupo (seletor CSS).
 * @param {HTMLElement} btn    - Botão clicado
 * @param {string} grupo       - Seletor do grupo (default '.filter-pill')
 */
function ativarFiltro(btn, grupo = '.filter-pill') {
  document.querySelectorAll(grupo).forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
}

/* ══════════════════════════════════════════
   MAPAS GLOBAIS (status e prioridade)
   Compartilhados entre todas as páginas.
══════════════════════════════════════════ */

const STATUS_MAP = {
  aberto:    { cls: 's-aberto',    label: 'Aberto',        bg: 'var(--orange-dim)', emoji: '⚠️' },
  andamento: { cls: 's-andamento', label: 'Em andamento',  bg: 'var(--blue-dim)',   emoji: '🔧' },
  resolvido: { cls: 's-resolvido', label: 'Resolvido',     bg: 'var(--green-dim)',  emoji: '✅' },
  pendente:  { cls: 's-pendente',  label: 'Pendente',      bg: 'var(--yellow-dim)', emoji: '⏳' },
};

const PRIORIDADE_MAP = {
  critica: { cls: 'p-critica', label: 'Crítica', bg: 'var(--red-dim)'    },
  alta:    { cls: 'p-alta',    label: 'Alta',    bg: 'var(--orange-dim)' },
  media:   { cls: 'p-media',   label: 'Média',   bg: 'var(--yellow-dim)' },
  baixa:   { cls: 'p-baixa',   label: 'Baixa',   bg: 'var(--blue-dim)'   },
};

/* ══════════════════════════════════════════
   NAVEGAÇÃO
══════════════════════════════════════════ */

/**
 * Redireciona para a página de detalhe de um reporte.
 * Quando o backend estiver pronto, substituir pelo
 * caminho real: window.location.href = `/reporte/${id}`
 * @param {number} id
 */
function abrirReporte(id) {
  // TODO: window.location.href = `/reporte/${id}`;
  alert(`Abrir reporte #${id}`);
}

/**
 * Redireciona para o formulário de novo reporte.
 * Quando o backend estiver pronto, substituir pelo
 * caminho real: window.location.href = '/reportes/novo'
 */
function abrirNovoReporte() {
  // TODO: window.location.href = '/reportes/novo';
  alert('Abrir formulário de novo reporte');
}
