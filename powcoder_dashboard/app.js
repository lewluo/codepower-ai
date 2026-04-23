const els = {
  connectionPill: document.getElementById('connectionPill'),
  connectionText: document.getElementById('connectionText'),
  updatedText: document.getElementById('updatedText'),
  autoModeBtn: document.getElementById('autoModeBtn'),
  manualModeBtn: document.getElementById('manualModeBtn'),
  heroDesc: document.getElementById('heroDesc'),
  modeTag: document.getElementById('modeTag'),
  providerTag: document.getElementById('providerTag'),
  taskTag: document.getElementById('taskTag'),
  terminalStatus: document.getElementById('terminalStatus'),
  terminalLog: document.getElementById('terminalLog'),
  voiceCard: document.getElementById('voiceCard'),
  voiceTimer: document.getElementById('voiceTimer'),
  voiceStatusText: document.getElementById('voiceStatusText'),
  proposalPanel: document.getElementById('proposalPanel'),
  proposalText: document.getElementById('proposalText'),
  proposalTask: document.getElementById('proposalTask'),
  chatList: document.getElementById('chatList'),
  agentGrid: document.getElementById('agentGrid'),
  sessionList: document.getElementById('sessionList'),
};

const statusText = {
  idle: '闲置',
  serving: '服务中',
  pending: '待确认',
  accepted: '已采纳',
  running: '执行中',
  success: '已完成',
  completed: '已完成',
  failed: '失败',
  rejected: '已拒绝',
  canceled: '已取消',
  offline: '离线',
  connected: '已连接',
};

const demoPresets = {
  '帮我总结今天的项目进度': {
    agent: 'dispatcher',
    reply: '好的，正在为你整理项目进度摘要：今天完成了终端展示初版、Agent 面板和语音交互逻辑。',
    logs: [
      ['blue', '◉', '识别语音：帮我总结今天的项目进度'],
      ['purple', '机', 'dispatcher 路由至任务后端'],
      ['purple', '网', '任务后端：聚合任务信息'],
      ['green', '✓', '总结结果已返回 JoyInside'],
    ],
  },
  '生成一份前端页面优化建议': {
    agent: 'visual',
    reply: '收到。我会从结构层次、组件统一、视觉节奏和状态交互四个方向给出优化建议。',
    logs: [
      ['blue', '◉', '识别语音：生成一份前端页面优化建议'],
      ['purple', '机', 'dispatcher 路由至 Visual Service'],
      ['purple', '眼', 'Visual Service：分析界面结构'],
      ['green', '✓', '已输出页面优化建议'],
    ],
  },
  '切换到 Visual Service 并生成可视化摘要': {
    agent: 'visual',
    reply: '已切换到 Visual Service，正在生成可视化摘要卡片与展示结构。',
    logs: [
      ['blue', '◉', '识别语音：切换到 Visual Service 并生成可视化摘要'],
      ['purple', '机', '当前 Agent 切换为 Visual Service'],
      ['purple', '眼', 'Visual Service：生成可视化摘要'],
      ['green', '✓', '摘要生成完成'],
    ],
  },
};

const defaultAgents = [
  { id: 'joyinside', mode: 'chat', name: 'JoyInside', icon: '☺', color: '#3867ff', desc: '闲聊、语音互动与陪伴式回复' },
  { id: 'dispatcher', mode: 'task', name: 'Task Router', icon: '⟲', color: '#7d67f7', desc: '任务分发、确认和工具路由' },
  { id: 'hermes', mode: 'task', name: 'Hermes', icon: '∞', color: '#111111', desc: '默认任务后端，承接工程执行与结果整理' },
  { id: 'openclaw', mode: 'task', name: 'OpenClaw', icon: '⌁', color: '#1f6feb', desc: '备用任务后端，可显式接管本机 Agent 任务' },
  { id: 'codex', mode: 'task', name: 'Codex', icon: '⌘', color: '#2d9f6d', desc: '代码阅读、修改与验证' },
  { id: 'claude_code', mode: 'task', name: 'Claude Code', icon: '◇', color: '#b36a16', desc: '备用代码执行通道' },
  { id: 'visual', mode: 'task', name: 'Visual Service', icon: '◔', color: '#4b77ff', desc: '可视化状态页与执行效果展示' },
];

let lastState = null;
let lastEvents = [];
let localEvents = [];
let clearAfterSeq = 0;
let demoAgent = '';
let activityStartedAt = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function short(value, fallback = '', limit = 96) {
  const text = String(value || fallback || '').trim();
  return text.length > limit ? `${text.slice(0, limit)}...` : text;
}

function parseDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatTime(value) {
  const date = value instanceof Date ? value : parseDate(value);
  if (!date) return '--:--:--';
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function formatElapsed(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function statusLabel(status) {
  return statusText[status] || status || '闲置';
}

function isWorking(state) {
  const workers = state?.workers || [];
  const proposal = state?.proposal || {};
  return proposal.state === 'pending'
    || proposal.state === 'accepted'
    || workers.some((worker) => ['pending', 'accepted', 'running'].includes(worker.status));
}

function isSpeaking(state) {
  const chat = state?.chat || {};
  return chat.status === 'serving';
}

function setModeToggle(mode) {
  const manual = mode === 'task';
  els.autoModeBtn.classList.toggle('active', !manual);
  els.manualModeBtn.classList.toggle('active', manual);
}

function renderConnection(state) {
  const connection = state.connection || {};
  const working = isWorking(state);
  const connectionStatus = connection.status || 'offline';
  const mode = state.mode || 'idle';
  const provider = state.chat?.provider || (mode === 'chat' ? 'JoyInside' : 'PowCoder');
  const device = connection.device_id ? ` · ${connection.device_id}` : '';
  const modeLabel = mode === 'chat' ? 'JoyInside 闲聊' : mode === 'task' ? 'GPT 任务' : mode;

  els.connectionPill.className = `status-pill ${working ? 'working' : connectionStatus === 'connected' ? 'online' : 'offline'}`;
  els.connectionText.textContent = `${working ? '执行中' : statusLabel(connectionStatus)}${device}`;
  els.updatedText.textContent = `更新 ${formatTime(state.updated_at)}`;
  els.modeTag.textContent = `mode: ${modeLabel}`;
  els.providerTag.textContent = `provider: ${provider}`;
  els.taskTag.textContent = `task: ${state.active_task_id || (mode === 'task' ? 'waiting' : statusLabel(state.proposal?.state))}`;
  els.terminalStatus.className = `status-pill subtle-dark ${working ? 'working' : 'online'}`;
  els.terminalStatus.innerHTML = `<span class="dot"></span>${working ? '执行中' : '在线'}`;
  setModeToggle(mode);
}

function renderHero(state) {
  const mode = state.mode || 'idle';
  const chat = state.chat || {};
  if (mode === 'chat') {
    els.heroDesc.textContent = `${chat.provider || 'JoyInside'} 正在处理闲聊与语音互动，页面会同步展示用户输入、回复和状态变化。`;
  } else if (isWorking(state)) {
    const task = state.proposal?.task || state.workers?.[0]?.task || state.active_task_id || '当前任务';
    els.heroDesc.textContent = `PowCoder 正在执行任务：${short(task, '当前任务', 120)}`;
  } else if (mode === 'task') {
    els.heroDesc.textContent = '当前已切到 GPT 任务模式。Hermes 默认待命，OpenClaw 可显式接手，页面会同步展示派活、确认和执行状态。';
  } else {
    els.heroDesc.textContent = 'PowCoder 用一个页面同时展示闲聊模式和任务模式，方便你在真实硬件接入后观察对话、调度和执行效果。';
  }
}

function titleCaseId(value) {
  return String(value || '')
    .split(/[_-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ') || 'Task Worker';
}

function eventToTerminalLine(event) {
  const payload = event.payload || {};
  const ts = formatTime(event.ts);
  switch (event.event) {
    case 'conversation.updated':
      return [ts, payload.status === 'connected' ? 'green' : 'red', payload.status === 'connected' ? '●' : '×', `${statusLabel(payload.status)} ${payload.device_id || ''}`.trim()];
    case 'mode.changed':
      return [ts, 'lime', '⋯', `模式切换为 ${payload.mode || 'auto'}`];
    case 'conversation.message':
      if (payload.user_text) return [ts, 'blue', '人', `用户：${payload.user_text}`];
      if (payload.assistant_text) return [ts, 'green', '机', `回复：${payload.assistant_text}`];
      return [ts, 'purple', '机', '对话状态更新'];
    case 'chat.serving':
      return [ts, 'blue', '◉', `${payload.provider || 'JoyInside'} 处理中：${payload.text || ''}`];
    case 'chat.finished':
      return [ts, payload.status === 'failed' ? 'red' : 'green', payload.status === 'failed' ? '×' : '✓', `${payload.provider || 'JoyInside'} 回复完成`];
    case 'proposal.pending':
      return [ts, 'amber', '?', `待确认：${payload.proposal_text || payload.task || payload.function_name || '任务'}`];
    case 'proposal.accepted':
      return [ts, 'blue', '✓', `已采纳任务：${payload.task || payload.function_name || '任务'}`];
    case 'proposal.rejected':
      return [ts, 'red', '×', `已拒绝任务：${payload.task || payload.function_name || '任务'}`];
    case 'proposal.completed':
      return [ts, 'green', '✓', `任务确认链路完成：${payload.task || payload.function_name || '任务'}`];
    case 'worker.running':
      return [ts, 'purple', '网', `${payload.display_name || payload.kind || 'Agent'}：${payload.task || '开始执行'}`];
    case 'worker.success':
      return [ts, 'green', '✓', `${payload.display_name || payload.kind || 'Agent'} 已完成：${payload.result_preview || payload.last_message || ''}`];
    case 'worker.failed':
      return [ts, 'red', '×', `${payload.display_name || payload.kind || 'Agent'} 失败：${payload.result_preview || payload.last_message || ''}`];
    default:
      return [ts, 'purple', '⋯', `${event.event}: ${short(JSON.stringify(payload), '', 120)}`];
  }
}

function terminalLineHtml([time, color, icon, text]) {
  return `
    <div class="terminal-line">
      <div class="terminal-time">${escapeHtml(time)}</div>
      <div class="terminal-icon icon-${escapeHtml(color)}">${escapeHtml(icon)}</div>
      <div>${escapeHtml(short(text, '', 180))}</div>
    </div>
  `;
}

function renderTerminal(events) {
  const realLines = events
    .filter((event) => Number(event.seq || 0) > clearAfterSeq)
    .slice(-80)
    .map(eventToTerminalLine);
  const lines = [...realLines, ...localEvents].slice(-90);
  if (!lines.length) {
    els.terminalLog.innerHTML = terminalLineHtml([formatTime(new Date()), 'green', '●', 'PowCoder visual service 已连接，等待新的状态事件...']);
    return;
  }
  els.terminalLog.innerHTML = lines.map(terminalLineHtml).join('');
  els.terminalLog.scrollTop = els.terminalLog.scrollHeight;
}

function conversationEventsForActive(state) {
  const activeId = state.active_conversation_id;
  return lastEvents
    .filter((event) => event.event === 'conversation.message' && (!activeId || event.conversation_id === activeId))
    .slice(-8);
}

function renderChat(state) {
  const messages = [];
  for (const event of conversationEventsForActive(state)) {
    const payload = event.payload || {};
    if (payload.user_text) messages.push({ type: 'user', text: payload.user_text });
    if (payload.assistant_text) messages.push({ type: 'agent', text: payload.assistant_text });
  }

  const chat = state.chat || {};
  if (!messages.length && (chat.last_user_text || chat.last_assistant_text || state.last_user_text || state.last_assistant_text)) {
    if (chat.last_user_text || state.last_user_text) messages.push({ type: 'user', text: chat.last_user_text || state.last_user_text });
    if (chat.last_assistant_text || state.last_assistant_text) messages.push({ type: 'agent', text: chat.last_assistant_text || state.last_assistant_text });
  }

  if (!messages.length) {
    messages.push({ type: 'agent', text: '等待小智测试页或设备发起对话。' });
  }

  const speaking = isSpeaking(state);
  const working = isWorking(state);
  els.voiceCard.classList.toggle('is-speaking', speaking);
  els.voiceStatusText.textContent = speaking ? '语音播放中' : working ? '任务执行中' : statusLabel(chat.status || 'idle');
  els.chatList.innerHTML = messages.slice(-6).map((message, index, arr) => `
    <div class="chat-item">
      <div class="chat-avatar ${message.type === 'agent' ? 'agent' : ''}">${message.type === 'agent' ? '☺' : '人'}</div>
      <div class="chat-text">${escapeHtml(message.text)}</div>
      ${speaking && index === arr.length - 1 && message.type === 'agent' ? '<div class="chat-typing">•••</div>' : ''}
    </div>
  `).join('');

  if (speaking && !activityStartedAt) activityStartedAt = Date.now();
  if (!speaking) activityStartedAt = null;
  els.voiceTimer.textContent = activityStartedAt ? formatElapsed(Date.now() - activityStartedAt) : '00:00';
}

function renderProposal(state) {
  const proposal = state.proposal || {};
  const visible = proposal.state && !['none', 'completed'].includes(proposal.state);
  els.proposalPanel.classList.toggle('is-hidden', !visible);
  if (!visible) return;
  els.proposalText.textContent = proposal.proposal_text || `${proposal.function_name || '工具'} · ${statusLabel(proposal.state)}`;
  els.proposalTask.textContent = proposal.task || '';
}

function normalizeWorkerAgent(worker) {
  const rawId = String(worker.worker_id || worker.kind || worker.display_name || '').toLowerCase();
  if (rawId.includes('joyinside')) return 'joyinside';
  if (rawId.includes('openclaw')) return 'openclaw';
  if (rawId.includes('hermes')) return 'hermes';
  if (rawId.includes('codex')) return 'codex';
  if (rawId.includes('claude')) return 'claude_code';
  if (rawId.includes('visual')) return 'visual';
  if (rawId.includes('dispatcher')) return 'dispatcher';
  return rawId.replace(/[^a-z0-9_-]+/g, '_') || 'task_backend';
}

function mergedAgents(state) {
  const agents = new Map(defaultAgents.map((agent) => [agent.id, { ...agent, status: '就绪', active: false }]));
  const chat = state.chat || {};
  const workers = state.workers || [];

  if (state.mode === 'chat' || chat.status === 'serving') {
    const joyinside = agents.get('joyinside');
    joyinside.status = statusLabel(chat.status || 'serving');
    joyinside.active = chat.status === 'serving' || state.mode === 'chat';
    joyinside.desc = short(chat.last_user_text || chat.last_assistant_text, joyinside.desc, 120);
  }

  if (state.mode === 'task') {
    const dispatcher = agents.get('dispatcher');
    dispatcher.desc = short(state.proposal?.proposal_text || '任务模式已就绪，等待派活或确认。', dispatcher.desc, 120);
  }

  for (const worker of workers) {
    const id = normalizeWorkerAgent(worker);
    const current = agents.get(id) || {
      id,
      mode: 'task',
      name: worker.display_name || titleCaseId(worker.kind || id),
      icon: '机',
      color: '#5b6d92',
      desc: '',
      status: '就绪',
      active: false,
    };
    current.name = worker.display_name || current.name;
    current.status = statusLabel(worker.status);
    current.active = ['pending', 'accepted', 'running'].includes(worker.status);
    current.failed = worker.status === 'failed';
    current.desc = short(worker.task || worker.result_preview || worker.last_message, current.desc, 120);
    agents.set(id, current);
  }

  if (state.proposal?.state === 'pending') {
    const dispatcher = agents.get('dispatcher');
    dispatcher.status = '待确认';
    dispatcher.active = true;
    dispatcher.desc = short(state.proposal.proposal_text || state.proposal.task, dispatcher.desc, 120);
  }

  if (demoAgent && agents.has(demoAgent)) {
    agents.get(demoAgent).active = true;
  }

  return Array.from(agents.values());
}

function agentCardHtml(agent) {
  return `
    <button class="agent-card ${agent.active ? 'active' : ''} ${agent.failed ? 'failed' : ''}" type="button" data-agent="${escapeHtml(agent.id)}" aria-pressed="${agent.active ? 'true' : 'false'}">
      <div class="agent-card-head">
        <div class="agent-icon" style="background:${escapeHtml(agent.color)}">${escapeHtml(agent.icon)}</div>
        <div class="agent-meta">
          <h3>${escapeHtml(agent.name)}</h3>
          <span class="agent-chip">${escapeHtml(agent.active ? `当前 · ${agent.status || '运行中'}` : agent.status || '就绪')}</span>
        </div>
      </div>
      <div class="agent-desc">${escapeHtml(agent.desc || '随时待命')}</div>
    </button>
  `;
}

function renderAgents(state) {
  const agents = mergedAgents(state);
  const chatAgents = agents.filter((agent) => agent.mode === 'chat');
  const taskAgents = agents.filter((agent) => agent.mode !== 'chat');
  const chatActive = chatAgents.some((agent) => agent.active);
  const taskActive = taskAgents.some((agent) => agent.active);
  const chatCurrent = state.mode === 'chat';
  const taskCurrent = state.mode === 'task';
  els.agentGrid.classList.toggle('has-active', chatActive || taskActive);
  els.agentGrid.innerHTML = `
    <section class="agent-mode-column chat-mode ${chatCurrent ? 'is-current' : ''} ${chatActive ? 'is-active' : ''}" aria-label="闲聊模式">
      <div class="agent-mode-head">
        <div>
          <div class="agent-mode-kicker">Chat Mode</div>
          <h3>闲聊模式</h3>
        </div>
        <span class="mode-state">${chatActive ? '工作中' : chatCurrent ? '当前模式' : '待命'}</span>
      </div>
      <div class="agent-stack">${chatAgents.map(agentCardHtml).join('')}</div>
    </section>
    <section class="agent-mode-column task-mode ${taskCurrent ? 'is-current' : ''} ${taskActive ? 'is-active' : ''}" aria-label="任务模式">
      <div class="agent-mode-head">
        <div>
          <div class="agent-mode-kicker">Task Mode</div>
          <h3>任务模式</h3>
        </div>
        <span class="mode-state">${taskActive ? '工作中' : taskCurrent ? '当前模式' : '待命'}</span>
      </div>
      <div class="agent-stack task-stack">${taskAgents.map(agentCardHtml).join('')}</div>
    </section>
  `;

  els.agentGrid.querySelectorAll('.agent-card').forEach((button) => {
    button.addEventListener('click', () => {
      demoAgent = button.dataset.agent;
      const agentName = button.querySelector('h3')?.textContent || demoAgent;
      pushLocalTerminal('purple', '机', `当前 Agent 已切换为 ${agentName}`);
      renderAgents(lastState || {});
    });
  });
}

function renderPageState(state) {
  const working = isWorking(state);
  document.body.classList.toggle('is-working', working);
  document.body.classList.toggle('is-chatting', !working && state?.mode === 'chat');
  document.body.classList.toggle('is-chat-mode', state?.mode === 'chat');
  document.body.classList.toggle('is-task-mode', state?.mode === 'task');
}

function renderSessions(state) {
  const sessions = state.sessions || [];
  if (!sessions.length) {
    els.sessionList.innerHTML = `
      <div class="session-item">
        <span class="session-dot idle"></span>
        <div>
          <div class="session-title">暂无 session</div>
          <div class="session-meta">waiting</div>
        </div>
        <div class="session-type">idle</div>
      </div>
    `;
    return;
  }
  els.sessionList.innerHTML = sessions.slice(0, 8).map((session) => `
    <div class="session-item">
      <span class="session-dot ${escapeHtml(session.status || 'idle')}"></span>
      <div>
        <div class="session-title">${escapeHtml(short(session.title || session.session_id, 'session', 70))}</div>
        <div class="session-meta">${escapeHtml(formatTime(session.updated_at || session.created_at))} · ${escapeHtml(statusLabel(session.status))}</div>
      </div>
      <div class="session-type">${escapeHtml(session.type || 'session')}</div>
    </div>
  `).join('');
}

function pushLocalTerminal(color, icon, text) {
  localEvents.push([formatTime(new Date()), color, icon, text]);
  localEvents = localEvents.slice(-20);
  renderTerminal(lastEvents);
}

function runCommand(command) {
  const preset = demoPresets[command];
  if (!preset) return;
  demoAgent = preset.agent;
  pushLocalTerminal('blue', '◉', `原型演示：${command}`);
  els.chatList.innerHTML = `
    <div class="chat-item">
      <div class="chat-avatar">人</div>
      <div class="chat-text">${escapeHtml(command)}</div>
    </div>
    <div class="chat-item">
      <div class="chat-avatar agent">☺</div>
      <div class="chat-text">${escapeHtml(preset.reply)}</div>
      <div class="chat-typing">•••</div>
    </div>
  `;
  els.voiceStatusText.textContent = '原型演示中';
  els.voiceCard.classList.add('is-speaking');
  activityStartedAt = Date.now();
  preset.logs.forEach(([color, icon, text], index) => {
    setTimeout(() => pushLocalTerminal(color, icon, text), 300 * (index + 1));
  });
  setTimeout(() => {
    els.voiceStatusText.textContent = '演示完成';
    els.voiceCard.classList.remove('is-speaking');
    activityStartedAt = null;
    renderAgents(lastState || {});
  }, 1800);
}

function bindPrototypeActions() {
  document.getElementById('startDemoBtn').addEventListener('click', () => runCommand('帮我总结今天的项目进度'));
  document.getElementById('runSummaryBtn').addEventListener('click', () => runCommand('生成一份前端页面优化建议'));
  document.getElementById('randomTaskBtn').addEventListener('click', () => {
    const keys = Object.keys(demoPresets);
    runCommand(keys[Math.floor(Math.random() * keys.length)]);
  });
  document.getElementById('clearLogBtn').addEventListener('click', () => {
    clearAfterSeq = Math.max(0, ...lastEvents.map((event) => Number(event.seq || 0)));
    localEvents = [];
    pushLocalTerminal('green', '✓', '终端展示已清空，等待新的状态事件...');
  });
  document.querySelectorAll('.preset-btn').forEach((button) => {
    button.addEventListener('click', () => runCommand(button.dataset.command));
  });
  document.querySelectorAll('.mode-btn').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach((item) => item.classList.remove('active'));
      button.classList.add('active');
      pushLocalTerminal('lime', '⋯', `原型模式已切换为 ${button.textContent.trim()}，真实模式仍由小智消息决定`);
    });
  });
  document.getElementById('focusActiveAgentBtn').addEventListener('click', () => {
    pushLocalTerminal('purple', '机', '当前页面已展示全部 Agent，真实运行状态会自动高亮');
  });
}

async function loadJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${url} ${response.status}`);
  return response.json();
}

async function loadState() {
  const [state, eventsPayload] = await Promise.all([
    loadJson('/api/state'),
    loadJson('/api/events'),
  ]);
  return { state, events: eventsPayload.events || [] };
}

function render(state, events) {
  lastState = state;
  lastEvents = events;
  renderPageState(state);
  renderConnection(state);
  renderHero(state);
  renderProposal(state);
  renderTerminal(events);
  renderChat(state);
  renderAgents(state);
  renderSessions(state);
}

async function tick() {
  try {
    const { state, events } = await loadState();
    render(state, events);
  } catch (error) {
    els.connectionPill.className = 'status-pill offline';
    els.connectionText.textContent = `服务不可用 · ${error.message}`;
    els.terminalLog.innerHTML = terminalLineHtml([formatTime(new Date()), 'red', '×', `PowCoder visual service 不可用：${error.message}`]);
  }
}

bindPrototypeActions();
tick();
setInterval(tick, 1000);
setInterval(() => {
  if (activityStartedAt) {
    els.voiceTimer.textContent = formatElapsed(Date.now() - activityStartedAt);
  }
}, 250);
