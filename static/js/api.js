/**
 * REST API Client for Smart Data Cleaner & Conversion Web App
 */

const API = {
  async uploadFile(formData) {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    return res.json();
  },

  async loadDemo(demoType = 'csv') {
    const formData = new FormData();
    formData.append('demo', 'true');
    formData.append('demo_type', demoType);
    return this.uploadFile(formData);
  },

  async selectSheet(sessionId, sheetName) {
    const res = await fetch('/api/select-sheet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, sheet_name: sheetName }),
    });
    return res.json();
  },

  async getPreview(sessionId, page = 1, pageSize = 50, search = '', sortCol = null, sortDir = 'asc') {
    const params = new URLSearchParams({
      session_id: sessionId,
      page,
      page_size: pageSize,
      search,
      sort_dir: sortDir,
    });
    if (sortCol) params.append('sort_col', sortCol);

    const res = await fetch(`/api/preview?${params.toString()}`);
    return res.json();
  },

  async getProfile(sessionId) {
    const res = await fetch(`/api/profile?session_id=${sessionId}`);
    return res.json();
  },

  async getDuplicates(sessionId) {
    const res = await fetch(`/api/duplicates?session_id=${sessionId}`);
    return res.json();
  },

  async cleanDuplicates(sessionId, subset = null, keep = 'first') {
    const res = await fetch('/api/clean/duplicates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, subset, keep }),
    });
    return res.json();
  },

  async cleanNulls(sessionId, column, strategy, fillValue = 'Unknown', treatEmptyAsNull = true) {
    const res = await fetch('/api/clean/nulls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        strategy,
        fill_value: fillValue,
        treat_empty_as_null: treatEmptyAsNull,
      }),
    });
    return res.json();
  },

  async cleanEmptyStrings(sessionId, column = null, includeWhitespace = true, includePlaceholders = true) {
    const res = await fetch('/api/clean/empty-strings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        include_whitespace: includeWhitespace,
        include_placeholders: includePlaceholders,
      }),
    });
    return res.json();
  },

  async cleanStrings(sessionId, { column = null, trim_whitespace = true, remove_extra_spaces = true, case_transform = null, remove_special_chars = false, empty_to_null = true }) {
    const res = await fetch('/api/clean/strings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        trim_whitespace,
        remove_extra_spaces,
        case_transform,
        remove_special_chars,
        empty_to_null,
      }),
    });
    return res.json();
  },

  async cleanNames(sessionId, { column = null, alphabets_only = true, case_transform = 'title', allow_spaces = true }) {
    const res = await fetch('/api/clean/names', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        alphabets_only,
        case_transform,
        allow_spaces,
      }),
    });
    return res.json();
  },

  async cleanContact(sessionId, { column, strip_non_digits = true, normalize_10_digits = false, format_style = 'digits_only', country_code = '91' }) {
    const res = await fetch('/api/clean/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        strip_non_digits,
        normalize_10_digits,
        format_style,
        country_code,
      }),
    });
    return res.json();
  },

  async cleanEmail(sessionId, { column, lowercase = true, trim_spaces = true, remove_inner_spaces = true, fix_domain_typos = true }) {
    const res = await fetch('/api/clean/email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        lowercase,
        trim_spaces,
        remove_inner_spaces,
        fix_domain_typos,
      }),
    });
    return res.json();
  },

  async cleanDate(sessionId, { column, input_format = null, output_format = 'YYYY-MM-DD', day_first = true }) {
    const res = await fetch('/api/clean/date', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        input_format,
        output_format,
        day_first,
      }),
    });
    return res.json();
  },

  async convertType(sessionId, { column, target_type, apply_fix = false, clean_currency_symbols = true, fill_unconvertible = null }) {
    const res = await fetch('/api/convert/type', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        column,
        target_type,
        apply_fix,
        clean_currency_symbols,
        fill_unconvertible,
      }),
    });
    return res.json();
  },

  async undoAction(sessionId) {
    const res = await fetch('/api/undo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    return res.json();
  },

  async autoClean(sessionId, options = {}) {
    const res = await fetch('/api/clean/auto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        ...options,
      }),
    });
    return res.json();
  },

  async resetDataset(sessionId) {
    const res = await fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    });
    return res.json();
  },

  async getSummary(sessionId) {
    const res = await fetch(`/api/summary?session_id=${sessionId}`);
    return res.json();
  },
};
