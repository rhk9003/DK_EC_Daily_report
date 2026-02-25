const STATUS_MAP = {
  pending:     { label: '暫緩', cls: 'badge-pending' },
  in_progress: { label: '進行中', cls: 'badge-in-progress' },
  completed:   { label: '已完成', cls: 'badge-completed' },
  cancelled:   { label: '終止', cls: 'badge-cancelled' }
};

const PRIORITY_MAP = {
  urgent: { label: '緊急', cls: 'priority-urgent' },
  high:   { label: '高', cls: 'priority-high' },
  medium: { label: '中', cls: 'priority-medium' },
  low:    { label: '低', cls: 'priority-low' }
};

const STATUS_ORDER = { in_progress: 0, pending: 1, completed: 2, cancelled: 3 };
const PRIORITY_ORDER = { urgent: 0, high: 1, medium: 2, low: 3 };

let lastUpdated = null;

async function loadDashboard() {
  try {
    const [dataRes, summaryRes] = await Promise.all([
      fetch('/api/data'),
      fetch('/api/summary')
    ]);
    const data = await dataRes.json();
    const summary = await summaryRes.json();

    if (data.meta.last_updated === lastUpdated) return;
    lastUpdated = data.meta.last_updated;

    renderStats(summary);
    renderProjects(data.projects);
    renderWeeklyLog(data.weekly_log);

    const dt = new Date(data.meta.last_updated);
    document.getElementById('last-updated').textContent =
      `最後更新: ${dt.toLocaleString('zh-TW')}`;
  } catch (e) {
    console.error('Failed to load dashboard:', e);
  }
}

function renderStats(s) {
  document.getElementById('stat-total').textContent = s.total;
  document.getElementById('stat-in-progress').textContent = s.in_progress;
  document.getElementById('stat-completed').textContent = s.completed;
  document.getElementById('stat-pending').textContent = s.pending;
  document.getElementById('stat-rate').textContent = s.completion_rate + '%';
}

function renderProjects(projects) {
  const container = document.getElementById('projects-container');
  if (!projects || projects.length === 0) {
    container.innerHTML = `
      <div class="bg-white rounded-lg shadow-sm p-8 text-center text-gray-400">
        尚無專案。透過 Claude Code 對話新增專案和任務。
      </div>`;
    return;
  }

  container.innerHTML = projects
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    .map(p => renderProject(p))
    .join('');
}

function renderProject(project) {
  const tasks = (project.tasks || []).sort((a, b) => {
    const sd = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9);
    if (sd !== 0) return sd;
    return (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9);
  });

  const activeTasks = tasks.filter(t => t.status !== 'cancelled');
  const avgProgress = activeTasks.length > 0
    ? Math.round(activeTasks.reduce((sum, t) => sum + (t.progress || 0), 0) / activeTasks.length)
    : 0;

  const taskRows = tasks.map(t => renderTask(t)).join('');

  return `
    <div class="bg-white rounded-lg shadow-sm mb-4 overflow-hidden">
      <div class="project-header p-4 cursor-pointer flex items-center justify-between border-l-4"
           style="border-left-color: ${project.color || '#3B82F6'}"
           onclick="toggleProject(this)">
        <div class="flex items-center gap-3">
          <span class="project-chevron text-gray-400 transition-transform">&#9654;</span>
          <div>
            <h3 class="font-semibold text-gray-800">${esc(project.name)}</h3>
            ${project.description ? `<p class="text-sm text-gray-500">${esc(project.description)}</p>` : ''}
          </div>
        </div>
        <div class="flex items-center gap-3 min-w-[180px]">
          ${renderProgressBar(avgProgress)}
        </div>
      </div>
      <div class="project-body">
        <div class="divide-y divide-gray-50">
          ${taskRows || '<div class="p-4 text-sm text-gray-400 text-center">此專案尚無任務</div>'}
        </div>
      </div>
    </div>`;
}

function renderTask(task) {
  const status = STATUS_MAP[task.status] || STATUS_MAP.pending;
  const priority = PRIORITY_MAP[task.priority] || PRIORITY_MAP.medium;
  const today = new Date().toISOString().slice(0, 10);
  const isOverdue = task.status === 'in_progress' &&
    task.estimated_completion && task.estimated_completion < today;
  const isCancelled = task.status === 'cancelled';

  let dateInfo = '';
  if (task.status === 'completed' && task.completed_at) {
    dateInfo = `<span class="text-green-600">完成於 ${task.completed_at}</span>`;
  } else if (task.status === 'in_progress' && task.estimated_completion) {
    dateInfo = isOverdue
      ? `<span class="text-red-600 font-medium">逾期 (預計 ${task.estimated_completion})</span>`
      : `<span class="text-blue-600">預計完成 ${task.estimated_completion}</span>`;
  } else if (task.status === 'pending' && task.estimated_restart) {
    dateInfo = `<span class="text-gray-500">預計重啟 ${task.estimated_restart}</span>`;
  } else if (task.status === 'cancelled' && task.cancelled_reason) {
    dateInfo = `<span class="text-gray-400">原因: ${esc(task.cancelled_reason)}</span>`;
  }

  const tags = (task.tags || [])
    .map(t => `<span class="tag">${esc(t)}</span>`)
    .join('');

  return `
    <div class="task-row p-4 hover:bg-gray-50 transition ${isCancelled ? 'opacity-50' : ''} ${isOverdue ? 'overdue-highlight' : ''}">
      <div class="flex items-start justify-between gap-4">
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <span class="priority-dot ${priority.cls}" title="${priority.label}"></span>
            <span class="font-medium text-gray-800 ${isCancelled ? 'line-through' : ''}">${esc(task.title)}</span>
            <span class="badge ${status.cls}">${status.label}</span>
          </div>
          ${task.description ? `<p class="text-sm text-gray-500 mb-1">${esc(task.description)}</p>` : ''}
          <div class="flex items-center gap-3 text-xs">
            ${dateInfo ? `<span>${dateInfo}</span>` : ''}
            ${tags ? `<span class="flex gap-1">${tags}</span>` : ''}
          </div>
        </div>
        ${task.status === 'in_progress' ? `
        <div class="flex items-center gap-2 min-w-[140px]">
          ${renderProgressBar(task.progress || 0)}
        </div>` : ''}
      </div>
    </div>`;
}

function renderProgressBar(progress) {
  let color = 'bg-gray-300';
  if (progress >= 80) color = 'bg-green-500';
  else if (progress >= 50) color = 'bg-blue-500';
  else if (progress >= 20) color = 'bg-yellow-500';

  return `
    <div class="flex items-center gap-2 w-full">
      <div class="flex-1 bg-gray-200 rounded-full h-2">
        <div class="${color} h-2 rounded-full progress-bar" style="width: ${progress}%"></div>
      </div>
      <span class="text-sm text-gray-500 w-10 text-right">${progress}%</span>
    </div>`;
}

function renderWeeklyLog(weeklyLog) {
  const container = document.getElementById('weekly-log');
  if (!weeklyLog || weeklyLog.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-400">本週尚無工作紀錄</p>';
    return;
  }

  const now = new Date();
  const day = now.getDay();
  const diff = now.getDate() - day + (day === 0 ? -6 : 1);
  const weekStart = new Date(now.setDate(diff)).toISOString().slice(0, 10);

  const currentWeek = weeklyLog.find(w => w.week_start === weekStart);
  if (!currentWeek || !currentWeek.entries || currentWeek.entries.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-400">本週尚無工作紀錄</p>';
    return;
  }

  const entriesByDate = {};
  currentWeek.entries.forEach(e => {
    if (!entriesByDate[e.date]) entriesByDate[e.date] = [];
    entriesByDate[e.date].push(e);
  });

  const dates = Object.keys(entriesByDate).sort().reverse();
  container.innerHTML = dates.map(date => {
    const entries = entriesByDate[date];
    return `
      <div class="mb-3">
        <div class="text-sm font-medium text-gray-600 mb-1">${date}</div>
        ${entries.map(e => `
          <div class="flex items-start gap-2 ml-4 mb-1">
            <span class="text-xs text-gray-400 mt-0.5 w-12 shrink-0">${e.time || ''}</span>
            <span class="text-sm text-gray-700">${esc(e.content)}</span>
            ${e.task_id ? `<span class="text-xs text-blue-400">[${e.task_id}]</span>` : ''}
          </div>
        `).join('')}
      </div>`;
  }).join('');
}

function toggleProject(header) {
  const body = header.nextElementSibling;
  const chevron = header.querySelector('.project-chevron');
  body.classList.toggle('collapsed');
  chevron.classList.toggle('rotated');
}

async function showWeeklyReport() {
  try {
    const res = await fetch('/api/weekly-report');
    const report = await res.json();
    const content = formatWeeklyReport(report);
    document.getElementById('report-content').textContent = content;
    document.getElementById('report-modal').classList.remove('hidden');
  } catch (e) {
    console.error('Failed to load report:', e);
  }
}

function formatWeeklyReport(r) {
  let text = `=== 本週工作報告 (${r.week_start}) ===\n\n`;

  if (r.completed_tasks.length > 0) {
    text += `【已完成】\n`;
    r.completed_tasks.forEach(t => {
      text += `  - [${t.project_name}] ${t.title}`;
      if (t.completed_at) text += ` (${t.completed_at} 完成)`;
      text += '\n';
    });
    text += '\n';
  }

  if (r.in_progress_tasks.length > 0) {
    text += `【進行中】\n`;
    r.in_progress_tasks.forEach(t => {
      text += `  - [${t.project_name}] ${t.title} (${t.progress}%)`;
      if (t.estimated_completion) text += ` 預計 ${t.estimated_completion} 完成`;
      if (t.overdue) text += ' [逾期]';
      text += '\n';
      if (t.notes) text += `    備註: ${t.notes}\n`;
    });
    text += '\n';
  }

  if (r.pending_tasks.length > 0) {
    text += `【暫緩中】\n`;
    r.pending_tasks.forEach(t => {
      text += `  - [${t.project_name}] ${t.title}`;
      if (t.estimated_restart) text += ` 預計 ${t.estimated_restart} 重啟`;
      text += '\n';
    });
    text += '\n';
  }

  if (r.cancelled_tasks.length > 0) {
    text += `【已終止】\n`;
    r.cancelled_tasks.forEach(t => {
      text += `  - [${t.project_name}] ${t.title}`;
      if (t.cancelled_reason) text += ` (${t.cancelled_reason})`;
      text += '\n';
    });
    text += '\n';
  }

  if (r.log_entries.length > 0) {
    text += `【工作紀錄】\n`;
    r.log_entries.forEach(e => {
      text += `  ${e.date} ${e.time || ''} - ${e.content}\n`;
    });
  }

  return text;
}

function copyReport() {
  const content = document.getElementById('report-content').textContent;
  navigator.clipboard.writeText(content).then(() => {
    const btn = document.querySelector('#report-modal button');
    const orig = btn.textContent;
    btn.textContent = '已複製!';
    setTimeout(() => { btn.textContent = orig; }, 1500);
  });
}

function closeReport() {
  document.getElementById('report-modal').classList.add('hidden');
}

function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// Init
loadDashboard();
setInterval(loadDashboard, 30000);
