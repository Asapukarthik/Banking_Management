/**
 * common.js — Shared utilities for the MyBank multi-page application.
 * Loaded on every page via base.html before any page-specific scripts.
 */

// ── HTML Escaping (XSS Prevention) ───────────────────────────────────────────
/**
 * Escape HTML special characters to prevent XSS attacks.
 * Always call this before injecting any user-supplied data into the DOM.
 * @param {any} value
 * @returns {string}
 */
const escapeHtml = value =>
  String(value ?? "").replace(/[&<>"']/g, ch =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

// ── Money Formatting ──────────────────────────────────────────────────────────
/**
 * Format a number as Indian currency with 2 decimal places (e.g. "1,23,456.78").
 * @param {number|string} value
 * @returns {string}
 */
const money = value =>
  Number(value || 0).toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

// ── Date Formatting ───────────────────────────────────────────────────────────
/**
 * Format an ISO date string as a readable date and time (e.g. "30 Oct 2026, 11:30 AM").
 * @param {string} value
 * @returns {string}
 */
const formatDate = value =>
  value
    ? new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })
    : "—";

// ── Time Ago (Improvement #8) ─────────────────────────────────────────────────
/**
 * Return a human-readable relative time string.
 * Falls back to a formatted date for times older than 7 days.
 *
 * Examples: "just now", "5 min ago", "3 hr ago", "2 days ago"
 *
 * @param {string} dateStr — ISO date string
 * @returns {string}
 */
function timeAgo(dateStr) {
  if (!dateStr) return "—";
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
  if (seconds < 5)      return "just now";
  if (seconds < 60)     return `${seconds} sec ago`;
  if (seconds < 3600)   return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400)  return `${Math.floor(seconds / 3600)} hr ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} days ago`;
  return formatDate(dateStr);
}

// ── Badge Helpers ─────────────────────────────────────────────────────────────
/**
 * Return the CSS badge class for a transaction type.
 * @param {string} type
 * @returns {string}
 */
function txnBadgeClass(type) {
  if (!type) return "badge-success";
  const t = type.toLowerCase();
  if (t.includes("deposit") || t.includes("received")) return "badge-deposit";
  if (t.includes("withdraw") || t.includes("sent"))    return "badge-withdraw";
  if (t.includes("transfer"))                          return "badge-transfer";
  return "badge-success";
}

/**
 * Return the CSS badge class for an account status string.
 * @param {string} status
 * @returns {string}
 */
function statusBadgeClass(status) {
  const map = { Active: "badge-active", Frozen: "badge-frozen", Inactive: "badge-inactive" };
  return map[status] || "badge-active";
}

// ── Toast Notifications ───────────────────────────────────────────────────────
let _notifyTimer;

/**
 * Show a toast notification in the bottom-right corner.
 * Auto-dismisses after 4.5 seconds.
 *
 * @param {string} message — The message to display.
 * @param {'success'|'error'} [type='success'] — Visual style.
 */
function notify(message, type = "success") {
  const toast = document.getElementById("toast");
  if (!toast) return;
  const icon = type === "error"
    ? '<i class="fa-solid fa-circle-exclamation"></i>'
    : '<i class="fa-solid fa-circle-check"></i>';
  toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
  toast.className = `toast show ${type}`;
  clearTimeout(_notifyTimer);
  _notifyTimer = setTimeout(() => { toast.className = "toast"; }, 4500);
}

// ── API Helpers ───────────────────────────────────────────────────────────────
/**
 * Fetch a JSON endpoint and return the parsed result.
 * Throws an Error with the server's error message if the response is not OK.
 *
 * @param {string} url
 * @param {RequestInit} [options]
 * @returns {Promise<any>}
 */
async function api(url, options = {}) {
  const response = await fetch(url, options);
  const result   = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || "Something went wrong. Please try again.");
  return result;
}

/**
 * POST JSON data to an API endpoint.
 * @param {string} url
 * @param {object} data
 * @param {object} [extraHeaders]
 * @returns {Promise<any>}
 */
function apiPost(url, data, extraHeaders = {}) {
  return api(url, {
    method:  "POST",
    headers: { "Content-Type": "application/json", ...extraHeaders },
    body:    JSON.stringify(data),
  });
}

/**
 * PATCH JSON data to an API endpoint.
 * @param {string} url
 * @param {object} data
 * @param {object} [extraHeaders]
 * @returns {Promise<any>}
 */
function apiPatch(url, data, extraHeaders = {}) {
  return api(url, {
    method:  "PATCH",
    headers: Object.assign({ "Content-Type": "application/json" }, extraHeaders),
    body:    JSON.stringify(data),
  });
}

/**
 * Send a DELETE request to an API endpoint.
 * @param {string} url
 * @param {object} [extraHeaders]
 * @returns {Promise<any>}
 */
function apiDelete(url, extraHeaders = {}) {
  return api(url, {
    method:  "DELETE",
    headers: Object.assign({}, extraHeaders),
  });
}

// ── Button Loading State ──────────────────────────────────────────────────────
/**
 * Set a button to its loading state (disabled with spinner).
 * @param {HTMLButtonElement} btn
 * @param {string} loadingText
 */
function btnLoading(btn, loadingText = "Processing...") {
  btn.disabled = true;
  btn._originalHTML = btn.innerHTML;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> ${escapeHtml(loadingText)}`;
}

/**
 * Restore a button from its loading state.
 * @param {HTMLButtonElement} btn
 */
function btnReset(btn) {
  btn.disabled = false;
  if (btn._originalHTML) btn.innerHTML = btn._originalHTML;
}
