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
  workflowSteps: document.getElementById('workflowSteps'),
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
    agent: 'planner',
    reply: '好的，正在为你整理项目进度摘要：今天完成了终端展示初版、Agent 面板和语音交互逻辑。',
    logs: [
      ['blue', '◉', '识别语音：帮我总结今天的项目进度'],
      ['purple', '机', 'dispatcher 路由至 Planner'],
      ['purple', '网', 'Planner：聚合任务信息'],
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
  { id: 'joyinside', name: 'JoyInside', icon: '☺', color: '#5d89ff', desc: '闲聊、语音互动与陪伴式回复' },
  { id: 'dispatcher', name: 'Dispatcher', icon: '⟲', color: '#7d67f7', desc: '任务分发、确认和工具路由' },
  { id: 'hermes', name: 'Hermes / OpenClaw', icon: '∞', color: '#111111', desc: '本地工程任务与多 Agent 执行' },
  { id: 'codex', name: 'Codex', icon: '⌘', color: '#40c47a', desc: '代码阅读、修改与验证' },
  { id: 'claude_code', name: 'Claude Code', icon: '◇', color: '#c98520', desc: '备用代码执行通道' },
  { id: 'visual', name: 'Visual Service', icon: '◔', color: '#4b77ff', desc: '可视化状态页与执行效果展示' },
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
  return state?.mode === 'task'
    || proposal.state === 'pending'
    || workers.some((worker) => ['pending', 'accepted', 'running'].includes(worker.status));
}

function isSpeaking(state) {
  const chat = state?.chat || {};
  return chat.status === 'serving' || isWorking(state);
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

  els.connectionPill.className = `status-pill ${working ? 'working' : connectionStatus === 'connected' ? 'online' : 'offline'}`;
  els.connectionText.textContent = `${working ? '执行中' : statusLabel(connectionStatus)}${device}`;
  els.updatedText.textContent = `更新 ${formatTime(state.updated_at)}`;
  els.modeTag.textContent = `mode: ${mode}`;
  els.providerTag.textContent = `provider: ${provider}`;
  els.taskTag.textContent = `task: ${state.active_task_id || statusLabel(state.proposal?.state)}`;
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
  } else {
    els.heroDesc.textContent = 'PowCoder 是一款面向 Web 4.0 时代的 AI Agent 终端。页面聚焦展示设备在线状态、语音对话、终端输出与 Agent 协作效果。';
  }
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
  els.voiceCard.classList.toggle('is-speaking', speaking);
  els.voiceStatusText.textContent = speaking ? (isWorking(state) ? '任务执行中' : '语音输入中') : statusLabel(chat.status || 'idle');
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
  if (rawId.includes('codex')) return 'codex';
  if (rawId.includes('claude')) return 'claude_code';
  if (rawId.includes('hermes') || rawId.includes('openclaw')) return 'hermes';
  if (rawId.includes('visual')) return 'visual';
  return 'dispatcher';
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

  for (const worker of workers) {
    const id = normalizeWorkerAgent(worker);
    const current = agents.get(id) || {
      id,
      name: worker.display_name || worker.kind || id,
      icon: '机',
      color: '#7966ff',
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

function renderAgents(state) {
  els.agentGrid.innerHTML = mergedAgents(state).map((agent) => `
    <button class="agent-card ${agent.active ? 'active' : ''} ${agent.failed ? 'failed' : ''}" type="button" data-agent="${escapeHtml(agent.id)}">
      <div class="agent-card-head">
        <div class="agent-icon" style="background:${escapeHtml(agent.color)}">${escapeHtml(agent.icon)}</div>
        <div class="agent-meta">
          <h3>${escapeHtml(agent.name)}</h3>
          <span class="agent-chip">${escapeHtml(agent.active ? agent.status || '运行中' : agent.status || '就绪')}</span>
        </div>
      </div>
      <div class="agent-desc">${escapeHtml(agent.desc || '随时待命')}</div>
    </button>
  `).join('');

  els.agentGrid.querySelectorAll('.agent-card').forEach((button) => {
    button.addEventListener('click', () => {
      demoAgent = button.dataset.agent;
      const agentName = button.querySelector('h3')?.textContent || demoAgent;
      pushLocalTerminal('purple', '机', `当前 Agent 已切换为 ${agentName}`);
      renderAgents(lastState || {});
    });
  });
}

function renderWorkflow(state) {
  const connection = state.connection || {};
  const proposal = state.proposal || {};
  const workers = state.workers || [];
  const hasUserText = Boolean(state.last_user_text || state.chat?.last_user_text);
  const hasAssistantText = Boolean(state.last_assistant_text || state.chat?.last_assistant_text);
  const hasRunningWorker = workers.some((worker) => ['pending', 'accepted', 'running'].includes(worker.status));
  const hasFailedWorker = workers.some((worker) => worker.status === 'failed');

  const steps = [
    { icon: '🎙', title: '语音输入', desc: hasUserText ? short(state.last_user_text || state.chat?.last_user_text, '', 42) : '用户发起语音请求', state: hasUserText ? 'done' : 'idle' },
    { icon: '〰', title: 'xiaozhi-server', desc: connection.status === 'connected' ? '设备连接中' : statusLabel(connection.status || 'offline'), state: connection.status === 'connected' ? 'done' : 'idle' },
    { icon: '⟲', title: 'dispatcher', desc: proposal.state === 'pending' ? '等待确认' : '任务分发与路由', state: proposal.state === 'pending' ? 'active' : isWorking(state) ? 'done' : 'idle' },
    { icon: '🤖', title: 'Agent 执行', desc: hasRunningWorker ? '多 Agent 协同处理中' : hasFailedWorker ? '执行失败' : '等待任务', state: hasFailedWorker ? 'failed' : hasRunningWorker ? 'active' : workers.length ? 'done' : 'idle' },
    { icon: '✓', title: '结果返回', desc: hasAssistantText ? short(state.last_assistant_text || state.chat?.last_assistant_text, '', 42) : '生成并语音回复', state: hasAssistantText ? 'done' : 'idle' },
  ];

  els.workflowSteps.innerHTML = steps.map((step) => `
    <div class="workflow-step ${step.state}">
      <div class="step-icon">${step.icon}</div>
      <div>
        <div class="step-title">${escapeHtml(step.title)}</div>
        <div class="step-desc">${escapeHtml(step.desc)}</div>
      </div>
    </div>
  `).join('');
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
  renderConnection(state);
  renderHero(state);
  renderProposal(state);
  renderTerminal(events);
  renderChat(state);
  renderAgents(state);
  renderWorkflow(state);
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
