const $ = id => document.getElementById(id);
let cachedAccounts = [];
let chart;
let adminKey = "";
const money = value => Number(value || 0).toLocaleString("en-IN", {minimumFractionDigits:2, maximumFractionDigits:2});
const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const formatDate = value => value ? new Date(value).toLocaleString("en-IN", {dateStyle:"medium", timeStyle:"medium"}) : "—";

function notify(message, type="success") {
  const toast = $("toast");
  toast.textContent = message;
  toast.className = `toast show ${type}`;
  window.clearTimeout(notify.timer);
  notify.timer = window.setTimeout(() => toast.className = "toast", 4500);
}
async function api(url, options={}) {
  const response = await fetch(url, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || "Something went wrong. Please try again.");
  return result;
}
function renderAccounts(accounts) {
  cachedAccounts = accounts;
  const term = ($("accountSearch")?.value || "").toLowerCase();
  const filtered = accounts.filter(a => `${a.number} ${a.customer.name} ${a.type}`.toLowerCase().includes(term));
  $("accounts").innerHTML = filtered.map(a => `<tr><td class="mono">${escapeHtml(a.number)}</td><td>${escapeHtml(a.customer.name)}</td><td>${escapeHtml(a.type)}</td><td>${escapeHtml(a.customer.phone)}</td><td>₹${money(a.balance)}</td><td><span class="tag ${a.status === "Active" ? "good" : "warning"}">${escapeHtml(a.status || "Active")}</span></td></tr>`).join("") || '<tr><td colspan="6">No matching accounts.</td></tr>';
  if (adminKey) renderAdminAccounts();
}
function renderTransactions(transactions) {
  $("transactionsList").innerHTML = transactions.map(t => `<tr><td class="mono">${escapeHtml(t.transaction_id || "—")}</td><td>${escapeHtml(t.account)}</td><td>${escapeHtml(t.type || t.action)}</td><td>₹${money(t.amount)}</td><td>${escapeHtml(formatDate(t.date_time))}</td><td><span class="tag good">${escapeHtml(t.status || "Success")}</span></td></tr>`).join("") || '<tr><td colspan="6">No transactions yet.</td></tr>';
}
function renderChart(monthly) {
  const labels = monthly.map(x => x.month);
  if (chart) chart.destroy();
  chart = new Chart($("activityChart"), {type:"bar", data:{labels, datasets:[
    {label:"Deposits", data:monthly.map(x => x.deposits), borderRadius:5},
    {label:"Withdrawals", data:monthly.map(x => x.withdrawals), borderRadius:5}
  ]}, options:{responsive:true, maintainAspectRatio:false, scales:{y:{beginAtZero:true, ticks:{callback:v => "₹"+v.toLocaleString("en-IN")}}}}});
}
async function refresh() {
  try {
    const data = await api("/api/data");
    $("total").textContent = money(data.total);
    $("accountCount").textContent = data.account_count;
    $("activeCount").textContent = data.active_count;
    $("depositTotal").textContent = money(data.deposit_total);
    $("withdrawalTotal").textContent = money(data.withdrawal_total);
    renderAccounts(data.accounts);
    renderTransactions(data.transactions);
    renderChart(data.monthly || []);
  } catch (error) { notify(error.message, "error"); }
}
$("createForm").addEventListener("submit", async e => {
  e.preventDefault(); const button = e.submitter; button.disabled = true;
  try {
    const result = await api("/api/create", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    notify(`Account created successfully. Account number: ${result.number}`); e.target.reset(); await refresh();
  } catch(error) { notify(error.message, "error"); } finally { button.disabled = false; }
});
$("actionForm").addEventListener("submit", async e => {
  e.preventDefault(); const button = e.submitter; button.disabled = true;
  try {
    const result = await api("/api/action", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    notify(`${result.message}. Transaction ID: ${result.transaction.transaction_id}`); e.target.reset(); await refresh();
  } catch(error) { notify(error.message, "error"); } finally { button.disabled = false; }
});
$("transferForm").addEventListener("submit", async e => {
  e.preventDefault(); const button = e.submitter; button.disabled = true;
  try {
    const result = await api("/api/transfer", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});
    notify(`${result.message}. Reference: ${result.transfer.transfer_id}`); e.target.reset(); await refresh();
  } catch(error) { notify(error.message, "error"); } finally { button.disabled = false; }
});
$("customerForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const number = new FormData(e.target).get("number");
    const data = await api(`/api/customer/${encodeURIComponent(number)}`);
    const a = data.account;
    $("customerDetails").className = "customer-panel";
    $("customerDetails").innerHTML = `<div class="customer-summary"><div><small>ACCOUNT HOLDER</small><h3>${escapeHtml(a.customer.name)}</h3><span>${escapeHtml(a.number)} · ${escapeHtml(a.type)}</span></div><div><small>AVAILABLE BALANCE</small><h3>₹${money(a.balance)}</h3><span class="tag">${escapeHtml(a.status || "Active")}</span></div></div><div class="mini-stats"><div>Deposits <b>₹${money(data.deposit_total)}</b></div><div>Withdrawals <b>₹${money(data.withdrawal_total)}</b></div></div><h4>Recent activity</h4><div class="tablewrap"><table><thead><tr><th>Transaction</th><th>Amount</th><th>Date & time</th></tr></thead><tbody>${data.transactions.map(t=>`<tr><td>${escapeHtml(t.type)}</td><td>₹${money(t.amount)}</td><td>${escapeHtml(formatDate(t.date_time))}</td></tr>`).join("") || '<tr><td colspan="3">No activity yet.</td></tr>'}</tbody></table></div>`;
  } catch(error) { notify(error.message, "error"); }
});
$("accountSearch").addEventListener("input", () => renderAccounts(cachedAccounts));
$("refreshButton").addEventListener("click", refresh);
function renderAdminAccounts() {
  $("adminAccounts").innerHTML = cachedAccounts.map(a => `<tr><td>${escapeHtml(a.number)}</td><td>${escapeHtml(a.customer.name)}</td><td>${escapeHtml(a.status || "Active")}</td><td><select data-account="${escapeHtml(a.number)}" class="admin-select"><option ${a.status === "Active" ? "selected" : ""}>Active</option><option ${a.status === "Frozen" ? "selected" : ""}>Frozen</option><option ${a.status === "Inactive" ? "selected" : ""}>Inactive</option></select><button class="button small secondary" data-update="${escapeHtml(a.number)}">Update</button></td></tr>`).join("") || '<tr><td colspan="4">No accounts.</td></tr>';
}
$("adminForm").addEventListener("submit", async e => {
  e.preventDefault(); adminKey = new FormData(e.target).get("admin_key");
  try { await api("/api/admin/overview", {headers:{"X-Admin-Key":adminKey}}); $("adminStatus").textContent = "Admin authorization successful. Account controls unlocked."; renderAdminAccounts(); notify("Admin access granted"); }
  catch(error) { adminKey = ""; $("adminStatus").textContent = "Admin authorization failed."; notify(error.message, "error"); }
});
$("adminAccounts").addEventListener("click", async e => {
  const number = e.target.dataset.update; if (!number) return;
  const select = $("adminAccounts").querySelector(`select[data-account="${CSS.escape(number)}"]`);
  try {
    const result = await api(`/api/admin/account/${encodeURIComponent(number)}/status`, {method:"PATCH", headers:{"Content-Type":"application/json", "X-Admin-Key":adminKey}, body:JSON.stringify({status:select.value})});
    notify(result.message); await refresh();
  } catch(error) { notify(error.message, "error"); }
});
refresh();
