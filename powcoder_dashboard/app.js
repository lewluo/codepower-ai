const els = {
  connectionText: document.getElementById('connectionText'),
  updatedText: document.getElementById('updatedText'),
  modeDot: document.getElementById('modeDot'),
  modeText: document.getElementById('modeText'),
  sessionList: document.getElementById('sessionList'),
  stageTitle: document.getElementById('stageTitle'),
  stageSubtitle: document.getElementById('stageSubtitle'),
  proposalPanel: document.getElementById('proposalPanel'),
  proposalText: document.getElementById('proposalText'),
  proposalTask: document.getElementById('proposalTask'),
  chatCard: document.getElementById('chatCard'),
  chatTitle: document.getElementById('chatTitle'),
  chatStatus: document.getElementById('chatStatus'),
  chatSummary: document.getElementById('chatSummary'),
  activeWorkers: document.getElementById('activeWorkers'),
  workerPool: document.getElementById('workerPool'),
};

const statusText = {
  idle: '闲置',
  serving: '服务中',
  pending: '待确认',
  accepted: '已采纳',
  running: '执行中',
  success: '已完成',
  failed: '失败',
  rejected: '已拒绝',
  canceled: '已取消',
  offline: '离线',
  connected: '已连接',
};

const modeText = {
  idle: 'idle',
  auto: 'auto',
  chat: 'chat',
  task: 'task',
};

function cls(status) {
  return `status-${status || 'idle'}`;
}

function short(value, fallback = '') {
  const text = String(value || fallback || '').trim();
  return text.length > 86 ? `${text.slice(0, 86)}...` : text;
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function formatUpdatedAt(value) {
  if (!value) return '--';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '--';
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function setStatusClass(node, base, status) {
  node.className = `${base} ${cls(status)}`;
}

function renderConnection(state) {
  const connection = state.connection || {};
  const mode = state.mode || 'idle';
  const status = connection.status || 'offline';
  els.connectionText.textContent = `${statusText[status] || status}${connection.device_id ? ` · ${connection.device_id}` : ''}`;
  els.updatedText.textContent = `更新 ${formatUpdatedAt(state.updated_at)}`;
  els.modeText.textContent = modeText[mode] || mode;
  setStatusClass(els.modeDot, 'mode-dot', mode === 'chat' ? 'serving' : mode === 'task' ? 'running' : status);
}

function renderSessions(state) {
  const sessions = state.sessions || [];
  if (!sessions.length) {
    els.sessionList.innerHTML = '<div class="session-item"><span class="status-dot status-idle"></span><div><div class="session-title">暂无 session</div><div class="session-meta">waiting</div></div></div>';
    return;
  }
  els.sessionList.innerHTML = sessions.slice(0, 24).map((item) => `
    <button class="session-item" type="button">
      <span class="status-dot ${cls(item.status)}"></span>
      <div>
        <div class="session-title">${escapeHtml(short(item.title, item.session_id))}</div>
        <div class="session-meta">${escapeHtml(item.type || 'session')} · ${escapeHtml(statusText[item.status] || item.status || 'idle')}</div>
      </div>
    </button>
  `).join('');
}

function renderProposal(state) {
  const proposal = state.proposal || {};
  const visible = proposal.state && proposal.state !== 'none' && proposal.state !== 'completed';
  els.proposalPanel.classList.toggle('is-hidden', !visible);
  if (!visible) return;
  els.proposalText.textContent = proposal.proposal_text || `${proposal.function_name || '工具'} · ${proposal.state}`;
  els.proposalTask.textContent = proposal.task || '';
  setStatusClass(els.proposalPanel, 'proposal-panel', proposal.state);
}

function workerCard(worker, compact = false) {
  const status = worker.status || 'idle';
  const title = short(worker.display_name || worker.kind || worker.worker_id, 'worker');
  const task = short(worker.task || worker.result_preview || worker.last_message || '', statusText[status] || status);
  if (compact) {
    return `
      <article class="worker-chip ${cls(status)}">
        <div class="chip-title">${escapeHtml(title)}</div>
        <div class="chip-state">${escapeHtml(statusText[status] || status)}</div>
        <p>${escapeHtml(task)}</p>
      </article>
    `;
  }
  return `
    <article class="worker-card ${cls(status)}">
      <div class="card-handle"></div>
      <div class="card-title">${escapeHtml(title)}</div>
      <div class="card-state">${escapeHtml(statusText[status] || status)}</div>
      <p>${escapeHtml(task)}</p>
    </article>
  `;
}

function renderWorkers(state) {
  const workers = state.workers || [];
  const active = workers.filter((worker) => ['pending', 'accepted', 'running', 'success', 'failed'].includes(worker.status));
  els.activeWorkers.innerHTML = active.length
    ? active.map((worker) => workerCard(worker)).join('')
    : '<div class="worker-card status-idle"><div class="card-handle"></div><div class="card-title">任务队列</div><div class="card-state">闲置</div><p>暂无任务</p></div>';

  const pool = workers.length ? workers : [
    { worker_id: 'joyinside', display_name: 'JoyInside', status: (state.chat || {}).status || 'idle', task: (state.chat || {}).last_user_text || '' },
    { worker_id: 'hermes', display_name: 'Hermes', status: 'idle' },
    { worker_id: 'openclaw', display_name: 'OpenClaw', status: 'idle' },
    { worker_id: 'codex', display_name: 'Codex', status: 'idle' },
    { worker_id: 'claude_code', display_name: 'Claude Code', status: 'idle' },
  ];
  els.workerPool.innerHTML = pool.map((worker) => workerCard(worker, true)).join('');
}

function renderStage(state) {
  const mode = state.mode || 'idle';
  const chat = state.chat || {};
  if (mode === 'chat' || mode === 'auto') {
    els.stageTitle.textContent = '闲聊一下';
    els.stageSubtitle.textContent = chat.provider || (mode === 'chat' ? 'JoyInside' : 'PowCoder');
  } else if (mode === 'task') {
    els.stageTitle.textContent = '执行任务';
    els.stageSubtitle.textContent = state.active_task_id || 'task mode';
  } else {
    els.stageTitle.textContent = '等待连接';
    els.stageSubtitle.textContent = 'PowCoder visual service';
  }

  const chatStatus = chat.status || 'idle';
  setStatusClass(els.chatCard, 'worker-card joyinside', chatStatus);
  els.chatTitle.textContent = chat.provider || (mode === 'chat' ? 'JoyInside' : 'PowCoder');
  els.chatStatus.textContent = statusText[chatStatus] || chatStatus;
  els.chatSummary.textContent = short(
    chat.last_assistant_text || chat.last_user_text || state.last_assistant_text || state.last_user_text,
    '暂无闲聊',
  );
}

function render(state) {
  renderConnection(state);
  renderSessions(state);
  renderProposal(state);
  renderStage(state);
  renderWorkers(state);
}

async function loadState() {
  const response = await fetch('/api/state', { cache: 'no-store' });
  if (!response.ok) throw new Error(`state ${response.status}`);
  return response.json();
}

async function tick() {
  try {
    render(await loadState());
  } catch (error) {
    els.connectionText.textContent = `服务不可用 · ${error.message}`;
    setStatusClass(els.modeDot, 'mode-dot', 'failed');
  }
}

tick();
setInterval(tick, 1000);
