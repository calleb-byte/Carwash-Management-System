/* ── Extremeclean Carwash - Frontend App ── */

const API = '';  // same origin
let authToken = localStorage.getItem('ec_token') || '';
let currentModal = null;
let modalData = {};
let refreshInterval = null;

// ── Utilities ────────────────────────────────────────────────

async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` }
  };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(API + path, opts);
    const data = await res.json();
    return data;
  } catch (e) {
    return { success: false, error: e.message };
  }
}

function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  setTimeout(() => { el.className = 'toast'; }, 3200);
}

function fmtCurrency(n) {
  return 'KES ' + parseFloat(n || 0).toLocaleString('en-KE', { minimumFractionDigits: 0 });
}

function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-KE', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtTime(t) {
  if (!t) return '—';
  if (typeof t === 'string' && t.includes(':')) {
    const [h, m] = t.split(':');
    const hr = parseInt(h);
    return `${hr > 12 ? hr - 12 : hr || 12}:${m} ${hr >= 12 ? 'PM' : 'AM'}`;
  }
  return t;
}

function fmtDateTime(dt) {
  if (!dt) return '—';
  return new Date(dt).toLocaleString('en-KE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function badge(status) {
  const icons = { pending: '⏳', confirmed: '✅', in_progress: '🔄', completed: '🏁', cancelled: '✕', active: '●', off_duty: '○', on_leave: '⏸', low: '↓', medium: '→', high: '↑' };
  return `<span class="badge badge-${status}">${icons[status] || ''} ${status.replace('_', ' ')}</span>`;
}

function initClock() {
  const update = () => {
    const now = new Date();
    document.getElementById('current-time').textContent =
      now.toLocaleTimeString('en-KE', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };
  update();
  setInterval(update, 1000);
}

// ── Auth ──────────────────────────────────────────────────────

async function doLogin() {
  const user = document.getElementById('login-user').value.trim();
  const pass = document.getElementById('login-pass').value;
  const btn = document.querySelector('.btn-login');
  const errEl = document.getElementById('login-error');
  errEl.style.display = 'none';
  btn.textContent = 'Signing in...';
  btn.disabled = true;

  const res = await api('POST', '/api/auth/login', { username: user, password: pass });
  btn.disabled = false;
  btn.innerHTML = '<span>Sign In</span><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>';

  if (res.success) {
    authToken = res.data.token;
    localStorage.setItem('ec_token', authToken);
    document.getElementById('user-name').textContent = res.data.username;
    document.getElementById('user-role').textContent = res.data.role;
    document.getElementById('user-avatar').textContent = res.data.username[0].toUpperCase();
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app').style.display = 'flex';
    initApp();
  } else {
    errEl.textContent = res.error || 'Login failed';
    errEl.style.display = 'block';
  }
}

document.addEventListener('keypress', (e) => {
  if (e.key === 'Enter' && document.getElementById('login-screen').style.display !== 'none') {
    doLogin();
  }
});

async function doLogout() {
  await api('POST', '/api/auth/logout');
  authToken = '';
  localStorage.removeItem('ec_token');
  clearInterval(refreshInterval);
  document.getElementById('app').style.display = 'none';
  document.getElementById('login-screen').style.display = 'flex';
}

function checkAuth() {
  if (authToken) {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app').style.display = 'flex';
    initApp();
  }
}

// ── Navigation ────────────────────────────────────────────────

const PAGE_TITLES = {
  dashboard: 'Dashboard', bookings: 'Bookings', tracking: 'Live Tracking',
  customers: 'Customers', employees: 'Employees', tasks: 'Tasks',
  services: 'Services', notifications: 'Notifications', analytics: 'Analytics',
  settings: 'System Settings'
};

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const page = document.getElementById(`page-${name}`);
  if (page) page.classList.add('active');

  const nav = document.querySelector(`[data-page="${name}"]`);
  if (nav) nav.classList.add('active');

  document.getElementById('page-title').textContent = PAGE_TITLES[name] || name;

  // Load page data
  const loaders = {
    dashboard: loadDashboard,
    bookings: loadBookings,
    tracking: loadTracking,
    customers: loadCustomers,
    employees: loadEmployees,
    tasks: loadTasks,
    services: loadServices,
    notifications: loadNotifications,
    analytics: loadAnalytics,
    settings: loadSettings
  };
  if (loaders[name]) loaders[name]();

  // Close sidebar on mobile
  if (window.innerWidth <= 768) {
    document.getElementById('sidebar').classList.remove('open');
  }
}

function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  if (window.innerWidth <= 768) {
    sb.classList.toggle('open');
  } else {
    sb.classList.toggle('collapsed');
  }
}

// ── Dashboard ─────────────────────────────────────────────────

async function loadDashboard() {
  const res = await api('GET', '/api/dashboard');
  if (!res.success) return;
  const d = res.data;

  document.getElementById('stat-today').textContent = d.total_bookings_today;
  document.getElementById('stat-completed').textContent = d.completed_today;
  document.getElementById('stat-progress').textContent = d.in_progress;
  document.getElementById('stat-pending').textContent = d.pending;
  document.getElementById('stat-customers').textContent = d.total_customers;
  document.getElementById('stat-employees').textContent = d.active_employees;
  document.getElementById('stat-revenue').textContent = fmtCurrency(d.revenue_today);

  // Badge updates
  if (d.pending > 0) {
    document.getElementById('badge-bookings').style.display = 'inline';
    document.getElementById('badge-bookings').textContent = d.pending;
  } else {
    document.getElementById('badge-bookings').style.display = 'none';
  }
  if (d.unread_notifications > 0) {
    document.getElementById('badge-notif').style.display = 'inline';
    document.getElementById('badge-notif').textContent = d.unread_notifications;
    document.getElementById('top-notif-badge').style.display = 'inline';
    document.getElementById('top-notif-badge').textContent = d.unread_notifications;
  } else {
    document.getElementById('badge-notif').style.display = 'none';
    document.getElementById('top-notif-badge').style.display = 'none';
  }

  // Today's bookings
  const container = document.getElementById('today-bookings');
  if (!d.recent_bookings || d.recent_bookings.length === 0) {
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:30px;font-size:13px;">No bookings today</div>';
    return;
  }
  container.innerHTML = d.recent_bookings.map(b => `
    <div class="booking-item">
      <div class="bk-time">${fmtTime(b.booking_time)}</div>
      <div class="bk-info">
        <div class="bk-name">${b.customer}</div>
        <div class="bk-svc">${b.service} · ${b.employee}</div>
      </div>
      <div>${badge(b.status)}</div>
      <div style="font-size:12px;color:var(--accent);font-weight:600;">${fmtCurrency(b.total_price)}</div>
    </div>
  `).join('');
}

// ── Bookings ──────────────────────────────────────────────────

let allBookings = [];

async function loadBookings() {
  const res = await api('GET', '/api/bookings');
  allBookings = res.success ? res.data : [];
  renderBookings(allBookings);
}

function filterBookings() {
  const search = document.getElementById('booking-search').value.toLowerCase();
  const status = document.getElementById('booking-status-filter').value;
  const dateF = document.getElementById('booking-date-filter').value;
  let filtered = allBookings;
  if (search) filtered = filtered.filter(b =>
    (b.customer_name || '').toLowerCase().includes(search) ||
    (b.service_name || '').toLowerCase().includes(search) ||
    (b.vehicle_reg || '').toLowerCase().includes(search) ||
    (b.customer_phone || '').includes(search)
  );
  if (status) filtered = filtered.filter(b => b.status === status);
  if (dateF) filtered = filtered.filter(b => b.booking_date && b.booking_date.startsWith(dateF));
  renderBookings(filtered);
}

function renderBookings(bookings) {
  const tbody = document.getElementById('bookings-body');
  if (!bookings.length) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;padding:32px;color:var(--text-muted);">No bookings found</td></tr>';
    return;
  }
  tbody.innerHTML = bookings.map(b => `
    <tr>
      <td style="font-weight:600;color:var(--text-muted)">#${b.id}</td>
      <td>
        <div style="font-weight:500">${b.customer_name}</div>
        <div style="font-size:11px;color:var(--text-muted)">${b.customer_phone}</div>
      </td>
      <td>${b.service_name}</td>
      <td>${fmtDate(b.booking_date)}</td>
      <td style="color:var(--accent);font-weight:600">${fmtTime(b.booking_time)}</td>
      <td style="font-family:monospace;font-size:12px">${b.vehicle_reg || '—'}</td>
      <td>${b.employee_name}</td>
      <td style="font-weight:600">${fmtCurrency(b.total_price)}</td>
      <td>
        <select class="status-select" onchange="updateBookingStatus(${b.id}, this.value)" data-current="${b.status}">
          ${['pending','confirmed','in_progress','completed','cancelled'].map(s =>
            `<option value="${s}" ${b.status===s?'selected':''}>${s.replace('_',' ')}</option>`
          ).join('')}
        </select>
      </td>
      <td class="actions">
        <button class="btn-danger" onclick="deleteBooking(${b.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

async function updateBookingStatus(id, status) {
  const res = await api('PUT', `/api/bookings/${id}/status`, { status });
  if (res.success) { toast(`Status updated to ${status}`, 'success'); loadBookings(); loadDashboard(); }
  else toast(res.error || 'Failed to update', 'error');
}

async function deleteBooking(id) {
  if (!confirm('Delete this booking?')) return;
  const res = await api('DELETE', `/api/bookings/${id}`);
  if (res.success) { toast('Booking deleted', 'success'); loadBookings(); loadDashboard(); }
  else toast(res.error, 'error');
}

// ── Tracking ──────────────────────────────────────────────────

async function loadTracking() {
  const res = await api('GET', '/api/bookings');
  if (!res.success) return;
  const today = new Date().toISOString().split('T')[0];
  const todayBookings = res.data.filter(b => b.booking_date && b.booking_date.startsWith(today));

  const lanes = { pending: [], confirmed: [], in_progress: [], completed: [] };
  todayBookings.forEach(b => {
    if (lanes[b.status] !== undefined) lanes[b.status].push(b);
  });

  const renderCard = (b) => {
    const nextStatus = { pending: 'confirmed', confirmed: 'in_progress', in_progress: 'completed' };
    const nextLabel = { pending: 'Confirm', confirmed: 'Start', in_progress: 'Complete' };
    const actions = nextStatus[b.status] ? `
      <button class="track-btn" onclick="trackAction(${b.id},'${nextStatus[b.status]}')">${nextLabel[b.status]}</button>
    ` : '';
    const cancel = b.status !== 'completed' && b.status !== 'cancelled' ? `
      <button class="track-btn" onclick="trackAction(${b.id},'cancelled')" style="color:var(--red)">Cancel</button>
    ` : '';
    return `
      <div class="track-card">
        <div class="tc-customer">${b.customer_name}</div>
        <div class="tc-service">${b.service_name}</div>
        <div class="tc-vehicle">🚗 ${b.vehicle_reg || 'N/A'}</div>
        <div class="tc-time">⏰ ${fmtTime(b.booking_time)}</div>
        <div class="tc-staff">👷 ${b.employee_name}</div>
        <div class="track-actions">${actions}${cancel}</div>
      </div>`;
  };

  ['pending','confirmed','in_progress','completed'].forEach(status => {
    const laneId = { in_progress: 'lane-inprogress' }[status] || `lane-${status}`;
    const el = document.getElementById(laneId);
    if (!el) return;
    el.innerHTML = lanes[status].length
      ? lanes[status].map(renderCard).join('')
      : '<div class="empty-lane">No items</div>';
  });
}

async function trackAction(id, status) {
  const res = await api('PUT', `/api/bookings/${id}/status`, { status });
  if (res.success) { toast(`Updated to ${status}`, 'success'); loadTracking(); loadDashboard(); }
  else toast(res.error, 'error');
}

// ── Customers ─────────────────────────────────────────────────

let allCustomers = [];

async function loadCustomers() {
  const search = (document.getElementById('customer-search') || {}).value || '';
  const url = search ? `/api/customers?search=${encodeURIComponent(search)}` : '/api/customers';
  const res = await api('GET', url);
  allCustomers = res.success ? res.data : [];
  const tbody = document.getElementById('customers-body');
  if (!allCustomers.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:32px;color:var(--text-muted);">No customers found</td></tr>';
    return;
  }
  tbody.innerHTML = allCustomers.map(c => `
    <tr>
      <td style="font-weight:600;color:var(--text-muted)">#${c.id}</td>
      <td style="font-weight:500">${c.name}</td>
      <td><span style="color:var(--accent)">${c.phone}</span></td>
      <td style="color:var(--text-muted)">${c.email || '—'}</td>
      <td style="font-family:monospace;font-size:12px">${c.vehicle_reg || '—'}</td>
      <td>${c.vehicle_type || '—'}</td>
      <td><span style="font-family:'Syne',sans-serif;font-weight:700;color:var(--green)">${c.total_visits || 0}</span></td>
      <td class="actions">
        <button class="btn-edit" onclick="editCustomer(${c.id})">Edit</button>
        <button class="btn-danger" onclick="deleteCustomer(${c.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

function editCustomer(id) {
  const c = allCustomers.find(x => x.id === id);
  if (!c) return;
  openModal('customer', c);
}

async function deleteCustomer(id) {
  if (!confirm('Delete this customer? This will also remove their bookings.')) return;
  const res = await api('DELETE', `/api/customers/${id}`);
  if (res.success) { toast('Customer deleted', 'success'); loadCustomers(); }
  else toast(res.error, 'error');
}

// ── Employees ─────────────────────────────────────────────────

let allEmployees = [];

async function loadEmployees() {
  const res = await api('GET', '/api/employees');
  allEmployees = res.success ? res.data : [];
  const grid = document.getElementById('employee-grid');
  if (!allEmployees.length) {
    grid.innerHTML = '<div style="color:var(--text-muted);padding:30px;">No employees found</div>';
    return;
  }
  grid.innerHTML = allEmployees.map(e => `
    <div class="emp-card">
      <div class="emp-avatar">${e.name[0]}</div>
      <div class="emp-name">${e.name}</div>
      <div class="emp-role">${e.role}</div>
      <div class="emp-phone">${e.phone || 'No phone'}</div>
      <div class="emp-meta">
        ${badge(e.status)}
        <span class="emp-tasks">${e.active_tasks || 0} tasks</span>
      </div>
      <div class="emp-actions">
        <button class="btn-edit" onclick="editEmployee(${e.id})">Edit</button>
        <button class="btn-danger" onclick="deleteEmployee(${e.id})">Remove</button>
      </div>
    </div>
  `).join('');

  // Update task filter dropdown
  const sel = document.getElementById('task-emp-filter');
  if (sel) {
    const curr = sel.value;
    sel.innerHTML = '<option value="">All Staff</option>' +
      allEmployees.map(e => `<option value="${e.id}" ${curr==e.id?'selected':''}>${e.name}</option>`).join('');
  }
}

function editEmployee(id) {
  const e = allEmployees.find(x => x.id === id);
  if (!e) return;
  openModal('employee', e);
}

async function deleteEmployee(id) {
  if (!confirm('Remove this employee?')) return;
  const res = await api('DELETE', `/api/employees/${id}`);
  if (res.success) { toast('Employee removed', 'success'); loadEmployees(); }
  else toast(res.error, 'error');
}

// ── Tasks ─────────────────────────────────────────────────────

async function loadTasks() {
  const empId = (document.getElementById('task-emp-filter') || {}).value || '';
  const status = (document.getElementById('task-status-filter') || {}).value || '';
  let url = '/api/tasks?';
  if (empId) url += `employee_id=${empId}&`;
  if (status) url += `status=${status}`;
  const res = await api('GET', url);
  const tasks = res.success ? res.data : [];
  const tbody = document.getElementById('tasks-body');
  if (!tasks.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:32px;color:var(--text-muted);">No tasks found</td></tr>';
    return;
  }
  tbody.innerHTML = tasks.map(t => `
    <tr>
      <td style="font-weight:600;color:var(--text-muted)">#${t.id}</td>
      <td style="font-weight:500">${t.title}</td>
      <td>${t.employee_name || '—'}</td>
      <td>${t.service_name || '—'}</td>
      <td style="font-family:monospace;font-size:12px">${t.vehicle_reg || '—'}</td>
      <td>${badge(t.priority || 'medium')}</td>
      <td>${badge(t.status)}</td>
      <td style="font-size:12px;color:var(--text-muted)">${fmtDateTime(t.assigned_at)}</td>
      <td class="actions">
        ${t.status !== 'completed' ? `
          <button class="btn-edit" onclick="updateTaskStatus(${t.id},'${t.status==='pending'?'in_progress':'completed'}')">
            ${t.status==='pending'?'Start':'Complete'}
          </button>` : '<span style="color:var(--green);font-size:12px">✓ Done</span>'
        }
      </td>
    </tr>
  `).join('');
}

async function updateTaskStatus(id, status) {
  const res = await api('PUT', `/api/tasks/${id}`, { status });
  if (res.success) { toast('Task updated', 'success'); loadTasks(); }
  else toast(res.error, 'error');
}

// ── Services ──────────────────────────────────────────────────

let allServices = [];

async function loadServices() {
  const res = await api('GET', '/api/services');
  allServices = res.success ? res.data : [];
  const grid = document.getElementById('services-grid');
  if (!allServices.length) {
    grid.innerHTML = '<div style="color:var(--text-muted);padding:30px;">No services found</div>';
    return;
  }
  grid.innerHTML = allServices.map(s => `
    <div class="svc-card">
      <div class="svc-category">${s.category}</div>
      <div class="svc-name">${s.name}</div>
      <div class="svc-desc">${s.description || 'No description'}</div>
      <div class="svc-footer">
        <div class="svc-price">KES ${parseFloat(s.price).toLocaleString()}<span>/service</span></div>
        <div class="svc-duration">⏱ ${s.duration_minutes} min</div>
      </div>
      <div class="svc-actions">
        <button class="btn-edit" onclick="editService(${s.id})">Edit</button>
        <button class="btn-danger" onclick="deleteService(${s.id})">Remove</button>
      </div>
    </div>
  `).join('');
}

function editService(id) {
  const s = allServices.find(x => x.id === id);
  if (!s) return;
  openModal('service', s);
}

async function deleteService(id) {
  if (!confirm('Deactivate this service?')) return;
  const res = await api('DELETE', `/api/services/${id}`);
  if (res.success) { toast('Service deactivated', 'success'); loadServices(); }
  else toast(res.error, 'error');
}

// ── Notifications ─────────────────────────────────────────────

async function loadNotifications() {
  const unread = document.getElementById('unread-only')?.checked;
  const url = `/api/notifications${unread ? '?unread=1' : ''}`;
  const res = await api('GET', url);
  const notifs = res.success ? res.data : [];
  const container = document.getElementById('notifications-list');
  const icons = { booking_confirmed: '✅', service_started: '🔄', service_completed: '🏁', reminder: '🔔', promotional: '🎉' };
  if (!notifs.length) {
    container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">No notifications</div>';
    return;
  }
  container.innerHTML = notifs.map(n => `
    <div class="notif-card ${!n.is_read ? 'unread' : ''}">
      <div class="notif-icon ${n.type}">${icons[n.type] || '🔔'}</div>
      <div class="notif-content">
        <div class="notif-customer">${n.customer_name || 'System'}</div>
        <div class="notif-msg">${n.message}</div>
        <div class="notif-time">${fmtDateTime(n.sent_at)}</div>
      </div>
      <div class="notif-meta">
        ${!n.is_read ? `<div class="unread-dot"></div>` : ''}
        ${!n.is_read ? `<button class="btn-sm" onclick="markRead(${n.id})">Mark read</button>` : ''}
      </div>
    </div>
  `).join('');
}

async function markRead(id) {
  await api('PUT', `/api/notifications/${id}/read`);
  loadNotifications();
  loadDashboard();
}

async function markAllRead() {
  const res = await api('PUT', '/api/notifications/read-all');
  if (res.success) { toast('All marked as read', 'success'); loadNotifications(); loadDashboard(); }
}

// ── Analytics ─────────────────────────────────────────────────

let chartRevenue = null;
let chartStatus = null;

async function loadAnalytics() {
  const res = await api('GET', '/api/analytics');
  if (!res.success) return;
  const d = res.data;

  // Revenue chart
  const revCtx = document.getElementById('chart-revenue').getContext('2d');
  if (chartRevenue) chartRevenue.destroy();
  const labels = d.revenue_7d.map(r => fmtDate(r.booking_date));
  const values = d.revenue_7d.map(r => parseFloat(r.revenue));
  chartRevenue = new Chart(revCtx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Revenue (KES)',
        data: values,
        backgroundColor: 'rgba(0,212,255,0.2)',
        borderColor: '#00d4ff',
        borderWidth: 2,
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#6b7280' } },
        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#6b7280' } }
      }
    }
  });

  // Status pie
  const statusCtx = document.getElementById('chart-status').getContext('2d');
  if (chartStatus) chartStatus.destroy();
  const statusColors = { pending:'#fbbf24', confirmed:'#3b82f6', in_progress:'#f59e0b', completed:'#10b981', cancelled:'#ef4444' };
  chartStatus = new Chart(statusCtx, {
    type: 'doughnut',
    data: {
      labels: d.status_breakdown.map(s => s.status),
      datasets: [{
        data: d.status_breakdown.map(s => s.count),
        backgroundColor: d.status_breakdown.map(s => statusColors[s.status] || '#6b7280'),
        borderWidth: 0,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom', labels: { color: '#9ca3af', padding: 16 } } },
      cutout: '65%',
    }
  });

  // Top services
  const svcsEl = document.getElementById('top-services-list');
  svcsEl.innerHTML = d.top_services.map(s => `
    <div class="svc-perf-row">
      <div class="svc-perf-name">${s.name}</div>
      <div class="svc-perf-count">${s.bookings}</div>
      <div class="svc-perf-rev">${fmtCurrency(s.revenue)}</div>
    </div>
  `).join('') || '<div style="padding:20px;color:var(--text-muted);text-align:center">No data</div>';

  // Employee performance
  const maxJobs = Math.max(...d.employee_performance.map(e => e.completed), 1);
  const empEl = document.getElementById('emp-perf-list');
  empEl.innerHTML = d.employee_performance.map(e => `
    <div class="perf-row">
      <div class="perf-avatar">${e.name[0]}</div>
      <div style="flex:1">
        <div class="perf-name">${e.name}</div>
        <div class="perf-stats">${e.completed} completed · ${fmtCurrency(e.revenue)}</div>
        <div class="perf-bar-wrap" style="margin-top:5px">
          <div class="perf-bar" style="width:${Math.round((e.completed / maxJobs) * 100)}%"></div>
        </div>
      </div>
    </div>
  `).join('') || '<div style="padding:20px;color:var(--text-muted);text-align:center">No data</div>';
}

// ── Modals ────────────────────────────────────────────────────

function openModal(type, editData = null) {
  currentModal = type;
  modalData = editData || {};
  const overlay = document.getElementById('modal-overlay');
  const title = document.getElementById('modal-title');
  const body = document.getElementById('modal-body');
  const submitBtn = document.getElementById('modal-submit');

  const isEdit = !!editData;
  const titles = { booking: 'New Booking', customer: 'Customer Details', employee: 'Employee Details', service: 'Service Details' };
  title.textContent = (isEdit ? 'Edit ' : 'New ') + (titles[type] || type);
  submitBtn.textContent = isEdit ? 'Update' : 'Save';

  const forms = {
    booking: bookingForm,
    customer: customerForm,
    employee: employeeForm,
    service: serviceForm
  };

  body.innerHTML = forms[type] ? forms[type](editData) : '<p>Unknown form type</p>';
  overlay.classList.add('open');

  // Populate dropdowns
  if (type === 'booking') {
    populateBookingDropdowns();
  }
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
  currentModal = null;
  modalData = {};
}

function bookingForm(d) {
  const today = new Date().toISOString().split('T')[0];
  return `
    <div class="form-row">
      <div class="form-group">
        <label>Customer</label>
        <select id="f-customer" required>
          <option value="">Select customer...</option>
        </select>
      </div>
      <div class="form-group">
        <label>Service</label>
        <select id="f-service" required>
          <option value="">Select service...</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Date</label>
        <input type="date" id="f-date" value="${today}" required/>
      </div>
      <div class="form-group">
        <label>Time</label>
        <input type="time" id="f-time" value="09:00" required/>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Vehicle Reg</label>
        <input type="text" id="f-vehicle" placeholder="KXX 000X" value="${d?.vehicle_reg||''}"/>
      </div>
      <div class="form-group">
        <label>Assign Staff</label>
        <select id="f-employee">
          <option value="">Auto-assign</option>
        </select>
      </div>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-notes" placeholder="Additional notes...">${d?.notes||''}</textarea>
    </div>
  `;
}

function customerForm(d) {
  return `
    <div class="form-row">
      <div class="form-group">
        <label>Full Name *</label>
        <input type="text" id="f-name" value="${d?.name||''}" required/>
      </div>
      <div class="form-group">
        <label>Phone *</label>
        <input type="tel" id="f-phone" value="${d?.phone||''}" placeholder="07XXXXXXXX" required/>
      </div>
    </div>
    <div class="form-group">
      <label>Email</label>
      <input type="email" id="f-email" value="${d?.email||''}" placeholder="optional@email.com"/>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Vehicle Reg</label>
        <input type="text" id="f-vehicle" value="${d?.vehicle_reg||''}" placeholder="KXX 000X"/>
      </div>
      <div class="form-group">
        <label>Vehicle Type</label>
        <select id="f-vtype">
          ${['Sedan','SUV','Hatchback','Pickup','Van','Truck','Motorcycle','Other']
            .map(v => `<option value="${v}" ${d?.vehicle_type===v?'selected':''}>${v}</option>`).join('')}
        </select>
      </div>
    </div>
  `;
}

function employeeForm(d) {
  return `
    <div class="form-row">
      <div class="form-group">
        <label>Full Name *</label>
        <input type="text" id="f-name" value="${d?.name||''}" required/>
      </div>
      <div class="form-group">
        <label>Phone</label>
        <input type="tel" id="f-phone" value="${d?.phone||''}" placeholder="07XXXXXXXX"/>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Role *</label>
        <select id="f-role">
          ${['Washer','Senior Washer','Detailer','Manager','Supervisor','Cashier']
            .map(r => `<option value="${r}" ${d?.role===r?'selected':''}>${r}</option>`).join('')}
        </select>
      </div>
      <div class="form-group">
        <label>Status</label>
        <select id="f-status">
          ${['active','off_duty','on_leave']
            .map(s => `<option value="${s}" ${d?.status===s?'selected':''}>${s.replace('_',' ')}</option>`).join('')}
        </select>
      </div>
    </div>
  `;
}

function serviceForm(d) {
  return `
    <div class="form-group">
      <label>Service Name *</label>
      <input type="text" id="f-name" value="${d?.name||''}" required/>
    </div>
    <div class="form-group">
      <label>Description</label>
      <textarea id="f-desc">${d?.description||''}</textarea>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Price (KES) *</label>
        <input type="number" id="f-price" value="${d?.price||''}" min="0" step="50" required/>
      </div>
      <div class="form-group">
        <label>Duration (minutes) *</label>
        <input type="number" id="f-duration" value="${d?.duration_minutes||30}" min="5" required/>
      </div>
    </div>
    <div class="form-group">
      <label>Category</label>
      <select id="f-category">
        ${['basic','standard','premium','specialty']
          .map(c => `<option value="${c}" ${d?.category===c?'selected':''}>${c}</option>`).join('')}
      </select>
    </div>
  `;
}

async function populateBookingDropdowns() {
  const [custRes, svcRes, empRes] = await Promise.all([
    api('GET', '/api/customers'),
    api('GET', '/api/services'),
    api('GET', '/api/employees')
  ]);

  const custSel = document.getElementById('f-customer');
  const svcSel = document.getElementById('f-service');
  const empSel = document.getElementById('f-employee');

  if (custRes.success && custSel) {
    custRes.data.forEach(c => {
      const o = document.createElement('option');
      o.value = c.id; o.textContent = `${c.name} — ${c.phone}`;
      custSel.appendChild(o);
    });
  }
  if (svcRes.success && svcSel) {
    svcRes.data.forEach(s => {
      const o = document.createElement('option');
      o.value = s.id; o.textContent = `${s.name} (KES ${s.price})`;
      svcSel.appendChild(o);
    });
  }
  if (empRes.success && empSel) {
    empRes.data.filter(e => e.status === 'active').forEach(e => {
      const o = document.createElement('option');
      o.value = e.id; o.textContent = e.name;
      empSel.appendChild(o);
    });
  }
}

async function submitModal() {
  const type = currentModal;
  const isEdit = !!modalData.id;
  let res;

  try {
    if (type === 'booking') {
      const data = {
        customer_id: document.getElementById('f-customer').value,
        service_id: document.getElementById('f-service').value,
        booking_date: document.getElementById('f-date').value,
        booking_time: document.getElementById('f-time').value,
        vehicle_reg: document.getElementById('f-vehicle').value,
        employee_id: document.getElementById('f-employee').value || null,
        notes: document.getElementById('f-notes').value
      };
      if (!data.customer_id || !data.service_id) { toast('Please select customer and service', 'error'); return; }
      res = await api('POST', '/api/bookings', data);
      if (res.success) { toast('Booking created!', 'success'); closeModal(); loadBookings(); loadDashboard(); }

    } else if (type === 'customer') {
      const data = {
        name: document.getElementById('f-name').value,
        phone: document.getElementById('f-phone').value,
        email: document.getElementById('f-email').value,
        vehicle_reg: document.getElementById('f-vehicle').value,
        vehicle_type: document.getElementById('f-vtype').value
      };
      if (!data.name || !data.phone) { toast('Name and phone are required', 'error'); return; }
      if (isEdit) res = await api('PUT', `/api/customers/${modalData.id}`, data);
      else res = await api('POST', '/api/customers', data);
      if (res.success) { toast(isEdit ? 'Customer updated' : 'Customer created', 'success'); closeModal(); loadCustomers(); }

    } else if (type === 'employee') {
      const data = {
        name: document.getElementById('f-name').value,
        phone: document.getElementById('f-phone').value,
        role: document.getElementById('f-role').value,
        status: document.getElementById('f-status').value
      };
      if (!data.name || !data.role) { toast('Name and role required', 'error'); return; }
      if (isEdit) res = await api('PUT', `/api/employees/${modalData.id}`, data);
      else res = await api('POST', '/api/employees', data);
      if (res.success) { toast(isEdit ? 'Employee updated' : 'Employee added', 'success'); closeModal(); loadEmployees(); }

    } else if (type === 'service') {
      const data = {
        name: document.getElementById('f-name').value,
        description: document.getElementById('f-desc').value,
        price: document.getElementById('f-price').value,
        duration_minutes: document.getElementById('f-duration').value,
        category: document.getElementById('f-category').value
      };
      if (!data.name || !data.price) { toast('Name and price required', 'error'); return; }
      if (isEdit) res = await api('PUT', `/api/services/${modalData.id}`, data);
      else res = await api('POST', '/api/services', data);
      if (res.success) { toast(isEdit ? 'Service updated' : 'Service created', 'success'); closeModal(); loadServices(); }
    }

    if (res && !res.success) toast(res.error || 'Operation failed', 'error');
  } catch (e) {
    toast('An error occurred: ' + e.message, 'error');
  }
}

// ── Init ──────────────────────────────────────────────────────

function loadChartJS() {
  return new Promise((resolve) => {
    if (window.Chart) { resolve(); return; }
    const s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    s.onload = resolve;
    document.head.appendChild(s);
  });
}

async function initApp() {
  initClock();
  showPage('dashboard');
  await loadChartJS();

  // Auto-refresh every 30 seconds
  refreshInterval = setInterval(() => {
    const activePage = document.querySelector('.nav-item.active');
    const page = activePage?.dataset?.page;
    if (page === 'dashboard') loadDashboard();
    else if (page === 'tracking') loadTracking();
  }, 30000);
}

// Auto-login check
checkAuth();

// ── Settings Page ─────────────────────────────────────────────

async function loadSettings() {
  document.getElementById('portal-url').textContent = window.location.origin + '/portal';

  const res = await api('GET', '/api/dashboard');
  if (res.success) {
    const d = res.data;
    document.getElementById('ss-customers').textContent = d.total_customers || 0;
    document.getElementById('ss-employees').textContent = d.active_employees || 0;
    document.getElementById('ss-notifs').textContent = d.unread_notifications || 0;
  }

  const ar = await api('GET', '/api/analytics');
  if (ar.success) {
    const total = (ar.data.status_breakdown || []).reduce((s, r) => s + (r.count || 0), 0);
    document.getElementById('ss-bookings').textContent = total;
    const totalRev = (ar.data.top_services || []).reduce((s, r) => s + parseFloat(r.revenue || 0), 0);
    document.getElementById('ss-revenue').textContent = 'KES ' + totalRev.toLocaleString();
    document.getElementById('ss-services').textContent = (ar.data.top_services || []).length;
  }

  const br = await api('GET', '/api/bookings');
  if (br.success) {
    document.getElementById('s-portal-count').textContent = br.data.length + ' total';
  }

  const cr = await api('GET', '/api/customers');
  if (cr.success) {
    document.getElementById('s-portal-customers').textContent = cr.data.length;
    document.getElementById('ss-customers').textContent = cr.data.length;
  }

  const badge = document.getElementById('sms-status-badge');
  if (badge) { badge.textContent = 'Sandbox Mode'; badge.className = 'sms-status-badge sandbox'; }

  loadBizInfo();
  loadBookingRules();
}

function copyPortalLink() {
  const url = window.location.origin + '/portal';
  navigator.clipboard.writeText(url).then(() => {
    toast('Portal link copied!', 'success');
  }).catch(() => {
    toast('Link: ' + url, 'success');
  });
}

async function sendTestSms() {
  const phone = (document.getElementById('s-test-phone') || {}).value || '';
  if (!phone) { toast('Enter a phone number first', 'error'); return; }
  const res = await api('POST', '/api/sms/test', { phone });
  if (res.success) toast('Test SMS sent to ' + phone, 'success');
  else toast(res.error || 'SMS not configured — set AT_USERNAME and AT_API_KEY env vars', 'error');
}

function saveBizInfo() {
  const d = {
    name:  document.getElementById('s-biz-name').value,
    phone: document.getElementById('s-biz-phone').value,
    email: document.getElementById('s-biz-email').value,
    addr:  document.getElementById('s-biz-addr').value,
    hours: document.getElementById('s-biz-hours').value
  };
  localStorage.setItem('ec_biz', JSON.stringify(d));
  toast('Business info saved', 'success');
}

function loadBizInfo() {
  try {
    const d = JSON.parse(localStorage.getItem('ec_biz') || '{}');
    if (d.name)  document.getElementById('s-biz-name').value  = d.name;
    if (d.phone) document.getElementById('s-biz-phone').value = d.phone;
    if (d.email) document.getElementById('s-biz-email').value = d.email;
    if (d.addr)  document.getElementById('s-biz-addr').value  = d.addr;
    if (d.hours) document.getElementById('s-biz-hours').value = d.hours;
  } catch(e) {}
}

function saveBookingRules() {
  const d = {
    max:         document.getElementById('s-max-bookings').value,
    open:        document.getElementById('s-open-time').value,
    close:       document.getElementById('s-close-time').value,
    autoConfirm: document.getElementById('s-auto-confirm').value
  };
  localStorage.setItem('ec_rules', JSON.stringify(d));
  toast('Booking rules saved', 'success');
}

function loadBookingRules() {
  try {
    const d = JSON.parse(localStorage.getItem('ec_rules') || '{}');
    if (d.max)   document.getElementById('s-max-bookings').value  = d.max;
    if (d.open)  document.getElementById('s-open-time').value     = d.open;
    if (d.close) document.getElementById('s-close-time').value    = d.close;
    if (d.autoConfirm !== undefined) document.getElementById('s-auto-confirm').value = d.autoConfirm;
  } catch(e) {}
}

async function changePassword() {
  const oldPass     = document.getElementById('s-old-pass').value;
  const newPass     = document.getElementById('s-new-pass').value;
  const confirmPass = document.getElementById('s-confirm-pass').value;
  if (!oldPass || !newPass || !confirmPass) { toast('Fill all password fields', 'error'); return; }
  if (newPass !== confirmPass) { toast('New passwords do not match', 'error'); return; }
  if (newPass.length < 6) { toast('Password must be at least 6 characters', 'error'); return; }
  const res = await api('POST', '/api/auth/change-password', {
    old_password: oldPass, new_password: newPass
  });
  if (res.success) {
    toast('Password changed successfully!', 'success');
    ['s-old-pass','s-new-pass','s-confirm-pass'].forEach(id => {
      document.getElementById(id).value = '';
    });
  } else {
    toast(res.error || 'Password change failed', 'error');
  }
}
