'use strict';

// Shared local-prototype API and session utilities. No JWT secrets belong here.
window.LegalSession = (() => {
  const API_BASE = 'http://127.0.0.1:8000';
  // Resolve paths from this script, whether served locally or at a nested URL.
  const scriptURL = new URL(document.currentScript.src);
  const loginURL = new URL('/', scriptURL).href;
  const chatURL = new URL('/chat', scriptURL).href;
  const TOKEN_KEY = 'legal-assistant-access-token';
  const USER_KEY = 'legal-assistant-user';

  function getToken() {
    try { return sessionStorage.getItem(TOKEN_KEY) || ''; }
    catch { return ''; }
  }

  function clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
      sessionStorage.removeItem(USER_KEY);
    } catch { /* Navigation still works when storage is unavailable. */ }
  }

  function save(data, fallbackName = '') {
    // The backend issues and validates the token; this frontend never decodes it.
    if (!data || typeof data.access_token !== 'string' || !data.access_token.trim() ||
        typeof data.token_type !== 'string' || data.token_type.toLowerCase() !== 'bearer') {
      throw new Error('invalidSession');
    }
    clear();
    try {
      sessionStorage.setItem(USER_KEY, JSON.stringify({
        user_id: data.user_id,
        name: typeof data.name === 'string' ? data.name : fallbackName
      }));
      sessionStorage.setItem(TOKEN_KEY, data.access_token);
    } catch {
      clear();
      throw new Error('storageError');
    }
  }

  function logout() {
    clear();
    document.documentElement.style.visibility = 'hidden';
    window.location.replace(loginURL);
  }

  function requireSession() {
    if (getToken()) return true;
    logout();
    return false;
  }

  function parseIdentifier(value) {
    const identifier = value.trim();
    const phone = /^(?:05\d{8}|9665\d{8}|\+9665\d{8})$/;
    const email = /^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/;
    // Preserve the accepted phone format; the backend should normalize consistently.
    if (phone.test(identifier)) return {identifier, email: null, phone: identifier};
    if (email.test(identifier)) return {identifier, email: identifier, phone: null};
    return null;
  }

  function errorMessage(data) {
    // Render backend messages as text, never HTML. Do not echo validation inputs.
    if (!data || typeof data !== 'object') return '';
    if (typeof data.detail === 'string') return data.detail;
    if (Array.isArray(data.detail)) {
      return data.detail.map(item => typeof item?.msg === 'string' ? item.msg : '')
        .filter(Boolean).join('\n');
    }
    if (typeof data.message === 'string') return data.message;
    if (typeof data.error === 'string') return data.error;
    return '';
  }

  async function readJSON(response) {
    try { return await response.json(); }
    catch { return null; }
  }

  return Object.freeze({API_BASE, loginURL, chatURL, getToken, clear, save,
    logout, requireSession, parseIdentifier, errorMessage, readJSON});
})();
