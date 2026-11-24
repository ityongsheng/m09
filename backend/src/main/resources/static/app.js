const $ = (s) => document.querySelector(s);
const state = { records: [], predictions: [], alerts: [], experiments: [], modelVersion: '—' };
const api = async (path, options = {}) => {
  const response = await fetch(path, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || body.error || `请求失败（${response.status}）`);
  return body;
};
const showToast = (message) => { const el = $('#toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2800); };
const fmt = (value, digits = 2) => value === null || value === undefined || value === '' ? '—' : Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : String(value);
const badge = (label) => `<span class="badge ${String(label).toLowerCase() === 'bad' ? 'bad' : String(label).toLowerCase() === 'good' ? 'good' : 'neutral'}">${label ?? '—'}</span>`;
const empty = (message) => `<p class="empty">${message}</p>`;
function renderRecords(target, rows, compact = false) {
  if (!rows.length) { $(target).innerHTML = empty('暂无记录'); return; }
  $(target).innerHTML = `<table class="data-table"><thead><tr><th>水果</th><th>温度</th><th>湿度</th><th>光照</th><th>CO₂</th>${compact ? '' : '<th>来源</th><th>时间</th>'}</tr></thead><tbody>${rows.map(r => `<tr><td>${r.fruit ?? '—'}</td><td>${fmt(r.temp)} °C</td><td>${fmt(r.humid)} %</td><td>${fmt(r.light, 0)}</td><td>${fmt(r.co2, 0)}</td>${compact ? '' : `<td>${r.source ?? '—'}</td><td>${r.created_at ?? r.createdAt ?? '—'}</td>`}</tr>`).join('')}</tbody></table>`;
}
function renderAlerts(target, rows, compact = false) {
  if (!rows.length) { $(target).innerHTML = empty('暂无预警'); return; }
  const labelOf = (r) => r.label ?? (((r.alert_level ?? r.level) === 'HIGH') ? 'Bad' : '—');
  const probabilityOf = (r) => r.risk_probability ?? r.riskProbability;
  const levelOf = (r) => r.alert_level ?? r.alertLevel ?? r.level ?? '—';
  const messageOf = (r) => r.alert_message ?? r.alertMessage ?? r.message ?? '风险记录';
  const timeOf = (r) => r.created_at ?? r.createdAt ?? '—';
  if (compact) { $(target).innerHTML = rows.slice(0, 4).map(r => `<div class="alert-item"><strong>${messageOf(r)}</strong><small>${labelOf(r)} · 概率 ${fmt(Number(probabilityOf(r)) * 100, 1)}% · ${timeOf(r)}</small></div>`).join(''); return; }
  $(target).innerHTML = `<table class="data-table"><thead><tr><th>标签</th><th>风险概率</th><th>预警级别</th><th>提示</th><th>时间</th></tr></thead><tbody>${rows.map(r => `<tr><td>${badge(labelOf(r))}</td><td>${fmt(Number(probabilityOf(r)) * 100, 1)}%</td><td>${levelOf(r)}</td><td>${messageOf(r)}</td><td>${timeOf(r)}</td></tr>`).join('')}</tbody></table>`;
}
function renderExperiments(rows) {
  if (!rows.length) { $('#experiments-table').innerHTML = empty('暂无实验指标。完成训练并导入指标后，这里会展示真实结果。'); return; }
  $('#experiments-table').innerHTML = `<table class="data-table"><thead><tr><th>模型</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th><th>MSE</th><th>MAE</th><th>R²</th></tr></thead><tbody>${rows.map(r => `<tr><td>${r.model_name ?? r.modelName ?? '—'}</td><td>${fmt(r.accuracy)}</td><td>${fmt(r.precision ?? r.precision_value)}</td><td>${fmt(r.recall ?? r.recall_value)}</td><td>${fmt(r.f1)}</td><td>${fmt(r.roc_auc ?? r.rocAuc)}</td><td>${fmt(r.mse)}</td><td>${fmt(r.mae)}</td><td>${fmt(r.r2)}</td></tr>`).join('')}</tbody></table>`;
}
async function loadAll() {
  try {
    const [records, predictions, alerts, experiments] = await Promise.all([api('/api/records?limit=100'), api('/api/predictions?limit=100'), api('/api/alerts?limit=100'), api('/api/experiments?limit=100')]);
    state.records = records; state.predictions = predictions; state.alerts = alerts; state.experiments = experiments;
    $('#metric-records').textContent = records.length; $('#metric-predictions').textContent = predictions.length; $('#metric-alerts').textContent = alerts.length;
    const latest = predictions[0]; state.modelVersion = latest?.model_version ?? latest?.modelVersion ?? '—'; $('#metric-model').textContent = state.modelVersion;
    renderRecords('#records-table', records); renderRecords('#overview-records', records.slice(0, 5), true); renderAlerts('#alerts-table', alerts); renderAlerts('#overview-alerts', alerts, true); renderExperiments(experiments);
  } catch (error) { ['#records-table','#overview-records','#alerts-table','#overview-alerts','#experiments-table'].forEach(id => $(id).innerHTML = empty(`接口暂不可用：${error.message}`)); showToast(error.message); }
}
async function checkHealth() {
  try { const data = await api('/api/health'); $('#health-text').textContent = '后端已连接'; $('#health-pill .dot').className = 'dot ok'; $('#hero-status').textContent = '正常'; $('#hero-status-detail').textContent = `${data.service ?? 'm09-backend'} · GET /api/health`; }
  catch (error) { $('#health-text').textContent = '后端未连接'; $('#health-pill .dot').className = 'dot bad'; $('#hero-status').textContent = '未连接'; $('#hero-status-detail').textContent = error.message; }
}
async function submitPrediction(event) {
  event.preventDefault(); const form = event.currentTarget; const message = $('#predict-message'); const data = Object.fromEntries(new FormData(form).entries());
  if (!data.fruit) { message.textContent = '请选择水果类型'; return; }
  ['temp','humid','light','co2'].forEach(key => { data[key] = Number(data[key]); }); message.textContent = '正在调用模型…';
  try { const result = await api('/api/predict', { method: 'POST', body: JSON.stringify({ record: data }) }); const probability = Number(result.riskProbability ?? result.risk_probability ?? 0); $('#prediction-result').innerHTML = `<p class="eyebrow">预测结果</p><h3>${badge(result.label)} ${result.alertMessage ?? ''}</h3><div class="risk-meter"><span style="width:${Math.max(0, Math.min(100, probability * 100))}%"></span></div><strong>风险概率 ${fmt(probability * 100, 1)}%</strong><div class="result-meta"><div><small>模型版本</small><strong>${result.modelVersion ?? '—'}</strong></div><div><small>预警级别</small><strong>${result.alertLevel ?? '—'}</strong></div></div>`; message.textContent = '预测已保存'; showToast('预测完成，记录已写入 SQLite'); await loadAll(); }
  catch (error) { message.textContent = error.message; $('#prediction-result').innerHTML = `<p class="eyebrow">预测结果</p><h3>模型调用未完成</h3>${empty(error.message)}`; }
}
function activateTab(name) { document.querySelectorAll('.tab').forEach(button => button.classList.toggle('is-active', button.dataset.tab === name)); document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.toggle('is-active', panel.id === `tab-${name}`)); }
document.addEventListener('DOMContentLoaded', () => { document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => activateTab(button.dataset.tab))); document.querySelectorAll('[data-jump]').forEach(button => button.addEventListener('click', () => activateTab(button.dataset.jump))); $('#predict-form').addEventListener('submit', submitPrediction); $('#refresh-records').addEventListener('click', loadAll); $('#refresh-alerts').addEventListener('click', loadAll); $('#refresh-experiments').addEventListener('click', loadAll); checkHealth(); loadAll(); });
