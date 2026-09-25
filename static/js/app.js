/**
 * Frontend Controller for Smart Data Cleaner & Conversion Web App
 */

const App = {
  state: {
    sessionId: null,
    currentTab: 'upload',
    fileInfo: null,
    profileData: null,
    previewData: null,
    currentPage: 1,
    pageSize: 50,
    searchQuery: '',
    sortCol: null,
    sortDir: 'asc',
  },

  init() {
    this.initTheme();
    this.bindEvents();
    this.switchTab('upload');
  },

  initTheme() {
    const savedTheme = localStorage.getItem('dataCleanerTheme') || 'light';
    this.setTheme(savedTheme);
  },

  setTheme(theme) {
    const root = document.documentElement;
    const body = document.body;
    const icon = document.getElementById('theme-toggle-icon');
    const text = document.getElementById('theme-toggle-text');

    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
      if (body) body.setAttribute('data-theme', 'dark');
      if (icon) icon.textContent = '☀️';
      if (text) text.textContent = 'Light Mode';
      localStorage.setItem('dataCleanerTheme', 'dark');
    } else {
      root.removeAttribute('data-theme');
      if (body) body.removeAttribute('data-theme');
      if (icon) icon.textContent = '🌙';
      if (text) text.textContent = 'Dark Mode';
      localStorage.setItem('dataCleanerTheme', 'light');
    }
  },

  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    this.setTheme(nextTheme);
    this.showToast(`Switched to ${nextTheme === 'dark' ? 'Dark' : 'Clean Professional'} theme`, 'info');
  },

  bindEvents() {
    // Stepper navigation
    document.querySelectorAll('.step-item').forEach(el => {
      el.addEventListener('click', () => {
        const step = el.dataset.step;
        if (step !== 'upload' && !this.state.sessionId) {
          this.showToast('Please upload or load a dataset first.', 'error');
          return;
        }
        this.switchTab(step);
      });
    });

    // Drag and drop upload zone
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    if (dropZone && fileInput) {
      dropZone.addEventListener('click', () => fileInput.click());

      dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
      });

      dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
      });

      dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length) {
          this.handleFileUpload(e.dataTransfer.files[0]);
        }
      });

      fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
          this.handleFileUpload(fileInput.files[0]);
        }
      });
    }

    // Demo dataset buttons
    document.querySelectorAll('.btn-demo').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const type = e.currentTarget.dataset.type;
        this.handleLoadDemo(type);
      });
    });

    // Undo button
    const undoBtn = document.getElementById('btn-undo');
    if (undoBtn) {
      undoBtn.addEventListener('click', () => this.handleUndo());
    }

    // Search preview
    const searchInput = document.getElementById('preview-search');
    if (searchInput) {
      let timeout = null;
      searchInput.addEventListener('input', (e) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          this.state.searchQuery = e.target.value.trim();
          this.state.currentPage = 1;
          this.loadPreview();
        }, 300);
      });
    }

    // Sheet selector
    const sheetSelect = document.getElementById('sheet-select');
    if (sheetSelect) {
      sheetSelect.addEventListener('change', (e) => {
        this.handleSheetChange(e.target.value);
      });
    }

    // Modal close buttons
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
      btn.addEventListener('click', () => this.closeAllModals());
    });

    // PDF Converter Dropzones & Inputs
    const pdfInput = document.getElementById('pdf-converter-input');
    const pdfDropzone = document.getElementById('pdf-converter-dropzone');
    if (pdfInput) {
      pdfInput.addEventListener('change', (e) => {
        if (e.target.files.length) this.handlePdfFileSelected(e.target.files[0], false);
      });
    }
    if (pdfDropzone) {
      pdfDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        pdfDropzone.classList.add('dragover');
      });
      pdfDropzone.addEventListener('dragleave', () => {
        pdfDropzone.classList.remove('dragover');
      });
      pdfDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        pdfDropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          this.handlePdfFileSelected(e.dataTransfer.files[0], false);
        }
      });
    }

    // PDF Modal Dropzone & Input
    const pdfModalInput = document.getElementById('pdf-modal-input');
    const pdfModalDropzone = document.getElementById('pdf-modal-dropzone');
    if (pdfModalInput) {
      pdfModalInput.addEventListener('change', (e) => {
        if (e.target.files.length) this.handlePdfFileSelected(e.target.files[0], true);
      });
    }
    if (pdfModalDropzone) {
      pdfModalDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        pdfModalDropzone.classList.add('dragover');
      });
      pdfModalDropzone.addEventListener('dragleave', () => {
        pdfModalDropzone.classList.remove('dragover');
      });
      pdfModalDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        pdfModalDropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
          this.handlePdfFileSelected(e.dataTransfer.files[0], true);
        }
      });
    }
  },

  switchTab(tabId) {
    this.state.currentTab = tabId;

    // Update stepper
    document.querySelectorAll('.step-item').forEach(el => {
      if (el.dataset.step === tabId) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    // Update tab view
    document.querySelectorAll('.tab-view').forEach(view => {
      if (view.id === `tab-${tabId}`) {
        view.classList.add('active');
      } else {
        view.classList.remove('active');
      }
    });

    if (tabId === 'preview' && this.state.sessionId) {
      this.loadPreview();
    } else if (tabId === 'profiling' && this.state.sessionId) {
      this.loadProfiling();
    } else if (tabId === 'cleaning' && this.state.sessionId) {
      this.populateCleaningOptions();
    } else if (tabId === 'summary' && this.state.sessionId) {
      this.loadSummary();
    }
  },

  async handleFileUpload(file) {
    this.showToast(`Uploading ${file.name}...`, 'info');
    const formData = new FormData();
    formData.append('file', file);
    if (this.state.sessionId) {
      formData.append('session_id', this.state.sessionId);
    }

    try {
      const res = await API.uploadFile(formData);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }
      this.onDatasetLoaded(res);
    } catch (err) {
      this.showToast('Upload failed: ' + err.message, 'error');
    }
  },

  async handleLoadDemo(demoType) {
    this.showToast(`Loading demo (${demoType.toUpperCase()})...`, 'info');
    try {
      const res = await API.loadDemo(demoType);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }
      this.onDatasetLoaded(res);
    } catch (err) {
      this.showToast('Failed to load demo: ' + err.message, 'error');
    }
  },

  onDatasetLoaded(res) {
    this.state.sessionId = res.session_id;
    this.state.fileInfo = res.file_info;
    this.showToast(`Dataset loaded: ${res.file_info.file_name}`, 'success');

    // Update UI Header details
    const fileInfoBar = document.querySelectorAll('.file-info-container');
    fileInfoBar.forEach(el => el.style.display = 'block');

    this.renderFileInfoBar(res.file_info);
    this.updateSheetSelector(res.file_info.sheets, res.file_info.selected_sheet);

    // Switch to preview tab and pre-warm profiling
    this.switchTab('preview');
    this.loadProfiling();
  },

  renderFileInfoBar(info) {
    document.querySelectorAll('.val-filename').forEach(el => el.textContent = info.file_name || '—');
    document.querySelectorAll('.val-filetype').forEach(el => el.textContent = info.file_type || '—');
    document.querySelectorAll('.val-filesize').forEach(el => el.textContent = info.file_size || '—');
    document.querySelectorAll('.val-rows').forEach(el => el.textContent = (info.rows || 0).toLocaleString());
    document.querySelectorAll('.val-cols').forEach(el => el.textContent = (info.columns || 0).toLocaleString());
  },

  updateSheetSelector(sheets, selected) {
    const selectorContainer = document.getElementById('sheet-selector-container');
    const sheetSelect = document.getElementById('sheet-select');

    if (!selectorContainer || !sheetSelect) return;

    if (sheets && sheets.length > 1) {
      selectorContainer.style.display = 'flex';
      sheetSelect.innerHTML = sheets.map(s => `<option value="${s}" ${s === selected ? 'selected' : ''}>${s}</option>`).join('');
    } else {
      selectorContainer.style.display = 'none';
    }
  },

  async handleSheetChange(sheetName) {
    this.showToast(`Switching sheet to '${sheetName}'...`, 'info');
    try {
      const res = await API.selectSheet(this.state.sessionId, sheetName);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }
      this.state.fileInfo = res.file_info;
      this.renderFileInfoBar(res.file_info);
      this.loadPreview();
    } catch (err) {
      this.showToast('Failed to switch sheet: ' + err.message, 'error');
    }
  },

  async loadPreview() {
    if (!this.state.sessionId) return;

    const container = document.getElementById('preview-table-container');
    const countLabel = document.getElementById('preview-count-label');

    try {
      const data = await API.getPreview(
        this.state.sessionId,
        this.state.currentPage,
        this.state.pageSize,
        this.state.searchQuery,
        this.state.sortCol,
        this.state.sortDir
      );

      this.state.previewData = data;

      if (countLabel) {
        countLabel.textContent = `Showing ${data.rows.length} of ${data.total_rows.toLocaleString()} rows (Total dataset: ${data.dataset_total_rows.toLocaleString()})`;
      }

      this.renderTable(data, container);
      this.renderPagination(data);
    } catch (err) {
      this.showToast('Failed to load preview: ' + err.message, 'error');
    }
  },

  renderTable(data, container) {
    if (!container) return;

    if (!data.rows || data.rows.length === 0) {
      container.innerHTML = `<div style="padding: 2.5rem; text-align: center; color: var(--text-muted);">No records found.</div>`;
      return;
    }

    let html = `<table class="data-table"><thead><tr>`;
    html += `<th style="width: 50px;">#</th>`;

    data.columns.forEach(col => {
      const type = data.column_types[col] || '';
      html += `
        <th onclick="App.handleSort('${col}')" style="cursor: pointer;">
          <div class="th-content">
            <span>${col}</span>
            <span class="col-type-tag" onclick="event.stopPropagation(); App.openQuickConvertModal('${this.escapeHtml(col)}', '${type}')" title="Change column data type or string casing (Upper/Lower/Title)">${type} ✎</span>
          </div>
        </th>
      `;
    });
    html += `</tr></thead><tbody>`;

    data.rows.forEach(row => {
      html += `<tr>`;
      html += `<td style="color: var(--text-dim);">${row._row_index + 1}</td>`;
      data.columns.forEach(col => {
        const val = row[col];
        if (val === null || val === undefined) {
          html += `<td class="null-cell">null</td>`;
        } else {
          html += `<td>${this.escapeHtml(String(val))}</td>`;
        }
      });
      html += `</tr>`;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
  },

  renderPagination(data) {
    const prevBtn = document.getElementById('btn-prev-page');
    const nextBtn = document.getElementById('btn-next-page');
    const pageText = document.getElementById('current-page-text');

    if (pageText) {
      pageText.textContent = `Page ${data.current_page} of ${data.total_pages}`;
    }

    if (prevBtn) {
      prevBtn.disabled = data.current_page <= 1;
      prevBtn.onclick = () => {
        if (this.state.currentPage > 1) {
          this.state.currentPage--;
          this.loadPreview();
        }
      };
    }

    if (nextBtn) {
      nextBtn.disabled = data.current_page >= data.total_pages;
      nextBtn.onclick = () => {
        if (this.state.currentPage < data.total_pages) {
          this.state.currentPage++;
          this.loadPreview();
        }
      };
    }
  },

  handleSort(col) {
    if (this.state.sortCol === col) {
      this.state.sortDir = this.state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      this.state.sortCol = col;
      this.state.sortDir = 'asc';
    }
    this.loadPreview();
  },

  async loadProfiling() {
    if (!this.state.sessionId) return;
    try {
      const data = await API.getProfile(this.state.sessionId);
      this.state.profileData = data;
      this.renderProfilingDashboard(data);
      this.populateCleaningOptions();
    } catch (err) {
      this.showToast('Failed to load profiling: ' + err.message, 'error');
    }
  },

  renderProfilingDashboard(data) {
    if (!data || data.error) return;
    const q = data.quality || {};
    const n = data.null_analysis || { columns: [] };
    const d = data.duplicate_analysis || {};
    const t = data.data_types || [];

    // Metric cards
    const qScoreEl = document.getElementById('val-quality-score');
    if (qScoreEl) {
      qScoreEl.textContent = `${q.score || 0}%`;
      const badge = document.getElementById('badge-quality-grade');
      if (badge) {
        badge.className = `score-badge ${q.color || 'blue'}`;
        badge.textContent = q.grade || '—';
      }
    }

    if (data.file_info) {
      const rowsEl = document.getElementById('metric-total-rows');
      const colsEl = document.getElementById('metric-total-cols');
      if (rowsEl) rowsEl.textContent = (data.file_info.rows || 0).toLocaleString();
      if (colsEl) colsEl.textContent = (data.file_info.columns || 0).toLocaleString();
    }

    const nullEl = document.getElementById('metric-null-cells');
    if (nullEl) nullEl.textContent = `${(n.total_nulls || 0).toLocaleString()} (${n.overall_null_percentage || 0}%)`;

    const dupEl = document.getElementById('metric-dup-rows');
    if (dupEl) dupEl.textContent = `${(d.duplicate_rows || 0).toLocaleString()} (${d.duplicate_percentage || 0}%)`;

    const issuesEl = document.getElementById('metric-issues-count');
    if (issuesEl) issuesEl.textContent = q.columns_with_issues || 0;

    // Update metric card quick-action buttons
    const dupBtn = document.getElementById('btn-quick-clean-dups-card');
    if (dupBtn) {
      if ((d.duplicate_rows || 0) === 0) {
        dupBtn.disabled = true;
        dupBtn.innerHTML = '<span>✓ No Duplicates</span>';
        dupBtn.className = 'btn btn-secondary btn-xs';
      } else {
        dupBtn.disabled = false;
        dupBtn.innerHTML = `<span>🧹 Clean ${d.duplicate_rows} Duplicates</span>`;
        dupBtn.className = 'btn btn-danger btn-xs';
      }
    }

    const nullBtn = document.getElementById('btn-quick-clean-nulls-card');
    if (nullBtn) {
      if ((n.total_nulls || 0) === 0) {
        nullBtn.disabled = true;
        nullBtn.innerHTML = '<span>✓ No Nulls</span>';
        nullBtn.className = 'btn btn-secondary btn-xs';
      } else {
        nullBtn.disabled = false;
        nullBtn.innerHTML = `<span>⭕ Fix ${n.total_nulls} Nulls</span>`;
        nullBtn.className = 'btn btn-secondary btn-xs';
      }
    }

    const issuesBtn = document.getElementById('btn-quick-fix-all-card');
    if (issuesBtn) {
      if ((q.columns_with_issues || 0) === 0 && (d.duplicate_rows || 0) === 0 && (n.total_nulls || 0) === 0) {
        issuesBtn.disabled = true;
        issuesBtn.innerHTML = '<span>✓ All Clean</span>';
        issuesBtn.className = 'btn btn-secondary btn-xs';
      } else {
        issuesBtn.disabled = false;
        issuesBtn.innerHTML = `<span>⚡ Fix All (${q.columns_with_issues || 0} issues)</span>`;
        issuesBtn.className = 'btn btn-primary btn-xs';
      }
    }

    // Render Column Cards
    const grid = document.getElementById('profiling-columns-grid');
    if (!grid) return;

    let html = '';
    t.forEach(colInfo => {
      const nullItem = n.columns.find(c => c.column === colInfo.column) || {};
      const hasIssue = colInfo.status === '⚠' || (nullItem.null_count > 0);

      html += `
        <div class="column-card glass-panel ${hasIssue ? 'has-issue' : 'is-clean'}">
          <div class="col-card-top">
            <div>
              <div class="col-name">${this.escapeHtml(colInfo.column)}</div>
              <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">Type: <strong>${colInfo.detected_type}</strong> (${colInfo.raw_dtype})</div>
            </div>
            <span class="col-stat-pill ${hasIssue ? 'issue' : 'clean'}">
              ${hasIssue ? '⚠ Issues' : '✓ Clean'}
            </span>
          </div>

          <ul class="col-metrics-list">
            <li class="col-metrics-item">
              <span>Null Values:</span>
              <span>${(nullItem.null_count || 0).toLocaleString()} (${nullItem.null_percentage || 0}%)</span>
            </li>
            <li class="col-metrics-item">
              <span>Unique Values:</span>
              <span>${(nullItem.unique_values || 0).toLocaleString()}</span>
            </li>
            <li class="col-metrics-item">
              <span>Duplicate Values:</span>
              <span>${(nullItem.duplicate_values || 0).toLocaleString()}</span>
            </li>
          </ul>

          ${colInfo.issue ? `
            <div class="col-issue-alert">
              <span>⚠</span>
              <span>${colInfo.issue}</span>
            </div>
          ` : ''}

          <div class="col-card-actions" style="display: flex; flex-wrap: wrap; gap: 0.4rem; justify-content: flex-end; margin-top: auto; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle);">
            ${colInfo.action ? `
              <button class="btn btn-xs btn-primary btn-quick-fix" onclick="App.handleQuickCleanColumn('${this.escapeHtml(colInfo.column)}', '${colInfo.action}', '${colInfo.detected_type}')" title="Apply smart fix immediately to '${this.escapeHtml(colInfo.column)}'">
                <span>⚡ Quick Fix: ${colInfo.action}</span>
              </button>
            ` : ''}
            ${nullItem.null_count > 0 ? `
              <button class="btn btn-xs btn-secondary" onclick="App.openQuickNullsModal('${this.escapeHtml(colInfo.column)}')" title="Clean/impute nulls in this column">
                <span>⭕ Fix Nulls</span>
              </button>
            ` : ''}
            <button class="btn btn-xs btn-secondary" onclick="App.openQuickConvertModal('${this.escapeHtml(colInfo.column)}', '${colInfo.detected_type}')" title="Convert data type in place">
              <span>🔄 Convert</span>
            </button>
            <button class="btn btn-xs btn-ghost" onclick="App.openFixAction('${this.escapeHtml(colInfo.column)}', '${colInfo.action || ''}')" title="Configure in Cleaning Studio">
              <span>Studio ➔</span>
            </button>
          </div>
        </div>
      `;
    });

    grid.innerHTML = html;
  },

  openFixAction(col, action) {
    if (action.includes('Name')) {
      const select = document.getElementById('clean-name-col');
      if (select) select.value = col;
      this.switchTab('cleaning');
    } else if (action.includes('Contact')) {
      this.openContactModal(col);
    } else if (action.includes('Email')) {
      this.openEmailModal(col);
    } else if (action.includes('Date')) {
      this.openDateModal(col);
    } else if (action.includes('Trim')) {
      this.openStringModal(col);
    } else if (action.includes('Convert')) {
      const target = action.replace('Convert to ', '').trim();
      this.openConvertTypeModal(col, target);
    }
  },

  buildNullColumnOptions(selectedCol = '') {
    const fileCols = (this.state.fileInfo && this.state.fileInfo.column_names) || [];
    const nullAnalysis = this.state.profileData?.null_analysis || null;
    const totalNulls = nullAnalysis ? (nullAnalysis.total_nulls || 0) : 0;

    const colMap = {};
    if (nullAnalysis && Array.isArray(nullAnalysis.columns)) {
      nullAnalysis.columns.forEach(item => {
        colMap[item.column] = item;
      });
    }

    const colsWithNulls = [];
    const cleanCols = [];

    fileCols.forEach(c => {
      const item = colMap[c];
      const count = item ? (item.null_count || 0) : 0;
      if (count > 0) {
        colsWithNulls.push({
          col: c,
          count: count,
          pct: item ? (item.null_percentage || 0) : 0,
          type: item ? (item.data_type || '') : ''
        });
      } else {
        cleanCols.push({
          col: c,
          count: 0,
          pct: 0,
          type: item ? (item.data_type || '') : ''
        });
      }
    });

    // Sort columns with nulls descending by null count
    colsWithNulls.sort((a, b) => b.count - a.count);

    let allOptionLabel = `All Applicable Columns`;
    if (nullAnalysis) {
      allOptionLabel += ` (${totalNulls.toLocaleString()} null${totalNulls === 1 ? '' : 's'} total)`;
    }

    let html = `<option value="" ${!selectedCol ? 'selected' : ''}>${allOptionLabel}</option>`;

    if (colsWithNulls.length > 0) {
      html += `<optgroup label="⚠️ Columns with Missing / Empty Values (${colsWithNulls.length})">`;
      colsWithNulls.forEach(c => {
        const isSel = c.col === selectedCol ? 'selected' : '';
        const item = colMap[c.col];
        let countStr = `${c.count.toLocaleString()} missing`;
        if (item && item.empty_string_count > 0) {
          if (item.na_count === 0) {
            countStr = `${item.empty_string_count.toLocaleString()} empty strings`;
          } else {
            countStr = `${c.count.toLocaleString()} missing (${item.empty_string_count} empty)`;
          }
        }
        const pctStr = c.pct > 0 ? ` · ${c.pct}%` : '';
        html += `<option value="${this.escapeHtml(c.col)}" ${isSel}>⚠️ ${this.escapeHtml(c.col)} (${countStr}${pctStr})</option>`;
      });
      html += `</optgroup>`;
    }

    if (cleanCols.length > 0) {
      html += `<optgroup label="✓ Clean Columns (0 nulls) (${cleanCols.length})">`;
      cleanCols.forEach(c => {
        const isSel = c.col === selectedCol ? 'selected' : '';
        html += `<option value="${this.escapeHtml(c.col)}" ${isSel}>✓ ${this.escapeHtml(c.col)} (0 nulls)</option>`;
      });
      html += `</optgroup>`;
    }

    const totalEmptyStrings = nullAnalysis ? (nullAnalysis.total_empty_strings || 0) : 0;
    return { html, colsWithNulls, cleanCols, totalNulls, colMap, totalEmptyStrings };
  },

  populateCleaningOptions() {
    if (!this.state.fileInfo) return;
    const cols = this.state.fileInfo.column_names || [];

    const selects = ['clean-string-col', 'clean-name-col', 'clean-contact-col', 'clean-email-col', 'clean-date-col', 'clean-null-col', 'convert-col'];
    selects.forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      const currentVal = el.value;

      if (id === 'clean-null-col') {
        const nullOpts = this.buildNullColumnOptions(currentVal);
        el.innerHTML = nullOpts.html;
        if (currentVal && cols.includes(currentVal)) {
          el.value = currentVal;
        }
        this.onCleanNullColChange(el.value);
        return;
      }

      let opts = id.includes('string') ? `<option value="">All Applicable Columns</option>` : '';
      cols.forEach(c => {
        opts += `<option value="${c}">${c}</option>`;
      });
      el.innerHTML = opts;
      if (currentVal && cols.includes(currentVal)) {
        el.value = currentVal;
      }
    });

    // Auto-select smart defaults if available
    const nameEl = document.getElementById('clean-name-col');
    if (nameEl) {
      const match = cols.find(c => /name|lname|fname|surname/i.test(c));
      if (match) nameEl.value = match;
    }

    const contactEl = document.getElementById('clean-contact-col');
    if (contactEl) {
      const match = cols.find(c => /contact|phone|mobile/i.test(c));
      if (match) contactEl.value = match;
    }

    const emailEl = document.getElementById('clean-email-col');
    if (emailEl) {
      const match = cols.find(c => /email|mail/i.test(c));
      if (match) emailEl.value = match;
    }

    const dateEl = document.getElementById('clean-date-col');
    if (dateEl) {
      const match = cols.find(c => /date|dob|birth|joined/i.test(c));
      if (match) dateEl.value = match;
    }
  },

  // Cleaning Actions
  async executeCleanDuplicates() {
    const keep = document.getElementById('clean-dup-keep').value;
    this.showToast('Removing duplicate rows...', 'info');
    try {
      const res = await API.cleanDuplicates(this.state.sessionId, null, keep);
      if (res.success) {
        this.showToast(`Success! Removed ${res.rows_removed} duplicate rows.`, 'success');
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Failed to clean duplicates: ' + err.message, 'error');
    }
  },

  async viewDuplicates() {
    try {
      const data = await API.getDuplicates(this.state.sessionId);
      const modal = document.getElementById('modal-duplicates');
      const container = document.getElementById('duplicates-table-container');

      if (!data.sample_duplicates || data.sample_duplicates.length === 0) {
        this.showToast('No duplicate rows found!', 'info');
        return;
      }

      let html = `<div style="margin-bottom: 0.75rem; color: var(--amber); font-weight: 600;">Found ${data.duplicate_rows} duplicate rows (${data.duplicate_percentage}%):</div>`;
      html += `<div class="table-container" style="max-height: 400px;"><table class="data-table"><thead><tr>`;
      const cols = Object.keys(data.sample_duplicates[0]).filter(k => k !== '_row_index');
      cols.forEach(c => html += `<th>${c}</th>`);
      html += `</tr></thead><tbody>`;

      data.sample_duplicates.forEach(row => {
        html += `<tr>`;
        cols.forEach(c => {
          const val = row[c];
          if (val === null || val === undefined) {
            html += `<td class="null-cell">null</td>`;
          } else {
            html += `<td>${this.escapeHtml(String(val))}</td>`;
          }
        });
        html += `</tr>`;
      });
      html += `</tbody></table></div>`;

      container.innerHTML = html;
      modal.classList.add('active');
    } catch (err) {
      this.showToast('Failed to fetch duplicates: ' + err.message, 'error');
    }
  },

  async executeCleanStrings() {
    const col = document.getElementById('clean-string-col').value || null;
    const trimWs = document.getElementById('str-trim-ws').checked;
    const collapseSp = document.getElementById('str-collapse-sp').checked;
    const caseTr = document.getElementById('str-case').value || null;
    const stripSpecial = document.getElementById('str-strip-special')?.checked || false;
    const emptyToNull = document.getElementById('str-empty-to-null')?.checked ?? true;

    this.showToast('Cleaning strings...', 'info');
    try {
      const res = await API.cleanStrings(this.state.sessionId, {
        column: col,
        trim_whitespace: trimWs,
        remove_extra_spaces: collapseSp,
        case_transform: caseTr,
        remove_special_chars: stripSpecial,
        empty_to_null: emptyToNull,
      });

      if (res.success) {
        this.showToast(`Cleaned text! ${res.modifications_count} values updated.`, 'success');
        await this.loadProfiling();
        this.populateCleaningOptions();
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('String cleaning failed: ' + err.message, 'error');
    }
  },

  async executeConvertEmptyStringsToNull(col = null) {
    if (!this.state.sessionId) {
      this.showToast('Please upload or load a dataset first.', 'error');
      return;
    }
    const colName = col || null;
    const label = colName ? `column '${colName}'` : 'all text columns';
    this.showToast(`Converting empty/blank strings in ${label} to Null (NaN)...`, 'info');

    try {
      const res = await API.cleanEmptyStrings(this.state.sessionId, colName, true, true);
      if (res.success) {
        this.closeAllModals();
        if (res.empty_strings_converted > 0) {
          this.showToast(`Converted ${res.empty_strings_converted} empty/blank strings to Null (NaN)!`, 'success');
        } else {
          this.showToast(`No empty/blank strings found in ${label}.`, 'info');
        }
        await this.loadProfiling();
        this.populateCleaningOptions();
        this.refreshDatasetViews();
      } else {
        this.showToast(res.error || 'Failed to convert empty strings.', 'error');
      }
    } catch (err) {
      this.showToast('Failed to convert empty strings: ' + err.message, 'error');
    }
  },

  async executeCleanNames() {
    const col = document.getElementById('clean-name-col').value;
    if (!col) {
      this.showToast('Please select a name column to sanitize', 'error');
      return;
    }
    const alphabetsOnly = document.getElementById('name-alphabets-only').checked;
    const allowSpaces = document.getElementById('name-allow-spaces').checked;
    const casing = document.getElementById('name-casing').value || null;

    this.showToast(`Sanitizing names in '${col}' to alphabets only...`, 'info');
    try {
      const res = await API.cleanNames(this.state.sessionId, {
        column: col,
        alphabets_only: alphabetsOnly,
        case_transform: casing,
        allow_spaces: allowSpaces,
      });

      if (res.success) {
        this.showToast(`Name sanitization complete! ${res.cleaned_count} names cleaned.`, 'success');
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Name sanitization failed: ' + err.message, 'error');
    }
  },

  async executeCleanContact() {
    const col = document.getElementById('clean-contact-col').value;
    if (!col) {
      this.showToast('Please select a contact column', 'error');
      return;
    }
    const stripDigits = document.getElementById('contact-strip-digits').checked;
    const norm10 = document.getElementById('contact-norm-10').checked;
    const style = document.getElementById('contact-format-style').value;
    const code = document.getElementById('contact-country-code').value;

    this.showToast(`Cleaning contact column '${col}'...`, 'info');
    try {
      const res = await API.cleanContact(this.state.sessionId, {
        column: col,
        strip_non_digits: stripDigits,
        normalize_10_digits: norm10,
        format_style: style,
        country_code: code,
      });

      if (res.success) {
        let msg = `Contact cleaning complete! ${res.cleaned_count} phone numbers updated.`;
        if (res.invalid_entries && res.invalid_entries.length > 0) {
          msg += ` (${res.invalid_entries.length} abnormal numbers noted)`;
        }
        this.showToast(msg, 'success');
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Contact cleaning failed: ' + err.message, 'error');
    }
  },

  async executeCleanEmail() {
    const col = document.getElementById('clean-email-col').value;
    if (!col) {
      this.showToast('Please select an email column', 'error');
      return;
    }
    const lower = document.getElementById('email-lowercase').checked;
    const trim = document.getElementById('email-trim').checked;
    const inner = document.getElementById('email-inner-spaces').checked;
    const typos = document.getElementById('email-fix-typos').checked;

    this.showToast(`Cleaning emails in '${col}'...`, 'info');
    try {
      const res = await API.cleanEmail(this.state.sessionId, {
        column: col,
        lowercase: lower,
        trim_spaces: trim,
        remove_inner_spaces: inner,
        fix_domain_typos: typos,
      });

      if (res.success) {
        let msg = `Email cleaning complete! ${res.cleaned_count} emails standardized.`;
        if (res.invalid_entries && res.invalid_entries.length > 0) {
          msg += ` (${res.invalid_entries.length} invalid email addresses flagged)`;
        }
        this.showToast(msg, 'success');
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Email cleaning failed: ' + err.message, 'error');
    }
  },

  async executeCleanDate() {
    const col = document.getElementById('clean-date-col').value;
    if (!col) {
      this.showToast('Please select a date column', 'error');
      return;
    }
    const inFmt = document.getElementById('date-in-format').value || null;
    const outFmt = document.getElementById('date-out-format').value;
    const dayFirst = document.getElementById('date-day-first').checked;

    this.showToast(`Standardizing dates in '${col}'...`, 'info');
    try {
      const res = await API.cleanDate(this.state.sessionId, {
        column: col,
        input_format: inFmt,
        output_format: outFmt,
        day_first: dayFirst,
      });

      if (res.success) {
        let msg = `Date standardization complete! ${res.converted_count} dates converted to ${outFmt}.`;
        if (res.unparseable_records && res.unparseable_records.length > 0) {
          msg += ` (${res.unparseable_records.length} unparseable dates kept)`;
        }
        this.showToast(msg, 'success');
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Date cleaning failed: ' + err.message, 'error');
    }
  },

  onCleanNullColChange(col) {
    const infoEl = document.getElementById('clean-null-col-info');
    if (!infoEl) return;
    const nullAnalysis = this.state.profileData?.null_analysis || null;
    const totalNulls = nullAnalysis ? (nullAnalysis.total_nulls || 0) : 0;
    const item = (nullAnalysis?.columns || []).find(c => c.column === col);

    if (!col) {
      infoEl.textContent = totalNulls > 0
        ? `Scope: All columns (${totalNulls.toLocaleString()} missing cells total across dataset)`
        : `Scope: All columns (0 missing values detected)`;
    } else if (item) {
      infoEl.textContent = `${col}: ${item.null_count.toLocaleString()} null values (${item.null_percentage}% of rows) · Type: ${item.data_type}`;
    } else {
      infoEl.textContent = col ? `Selected: ${col}` : '';
    }
  },

  async executeCleanNulls() {
    const col = document.getElementById('clean-null-col').value || null;
    const strategy = document.getElementById('null-strategy').value;
    const fillVal = document.getElementById('null-custom-value').value;
    const treatEmpty = document.getElementById('clean-null-treat-empty')?.checked ?? true;

    this.showToast(`Handling null values...`, 'info');
    try {
      const res = await API.cleanNulls(this.state.sessionId, col, strategy, fillVal, treatEmpty);
      if (res.success) {
        let msg = `Handled ${res.nulls_handled} null / empty cells.`;
        if (res.rows_removed > 0) msg += ` Dropped ${res.rows_removed} rows.`;
        this.showToast(msg, 'success');
        await this.loadProfiling();
        this.populateCleaningOptions();
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Null handling failed: ' + err.message, 'error');
    }
  },

  onConvertTargetTypeChange(targetType) {
    const isString = (targetType || '').toLowerCase() === 'string';
    const isNumeric = targetType === 'Float' || targetType === 'Integer';

    const strGroup = document.getElementById('convert-string-case-group');
    const strOptions = document.getElementById('convert-string-options');
    const currGroup = document.getElementById('convert-currency-group');

    if (strGroup) strGroup.style.display = isString ? 'block' : 'none';
    if (strOptions) strOptions.style.display = isString ? 'flex' : 'none';
    if (currGroup) currGroup.style.display = isNumeric ? 'block' : 'none';
  },

  async executeConvertType(apply = false) {
    const col = document.getElementById('convert-col').value;
    const target = document.getElementById('convert-target-type').value;
    const cleanCurr = document.getElementById('convert-clean-curr')?.checked ?? true;
    const isString = (target || '').toLowerCase() === 'string';

    const caseTransform = isString ? (document.getElementById('convert-string-case')?.value || null) : null;
    const trimWs = isString ? (document.getElementById('convert-str-trim-ws')?.checked ?? true) : true;
    const collapseSp = isString ? (document.getElementById('convert-str-collapse-sp')?.checked ?? false) : false;

    if (!col) {
      this.showToast('Please select a column to convert', 'error');
      return;
    }

    try {
      const res = await API.convertType(this.state.sessionId, {
        column: col,
        target_type: target,
        apply_fix: apply,
        clean_currency_symbols: cleanCurr,
        case_transform: caseTransform,
        trim_whitespace: trimWs,
        collapse_spaces: collapseSp,
      });

      const reportBox = document.getElementById('convert-report-box');
      if (reportBox) {
        if (res.total_problematic > 0) {
          let html = `<div style="color: var(--amber); margin-bottom: 0.5rem; font-weight: 600;">⚠ Found ${res.total_problematic} problematic values that cannot be cleanly converted:</div>`;
          html += `<div style="max-height: 180px; overflow-y: auto; background: var(--bg-input); padding: 0.5rem; border-radius: var(--radius-sm); font-size: 0.8rem;">`;
          res.problematic_records.slice(0, 20).forEach(item => {
            html += `<div>Row #${item.row_index + 1}: <code style="color: var(--rose); font-weight: bold;">"${this.escapeHtml(item.original_value)}"</code> (${item.reason})</div>`;
          });
          html += `</div>`;
          reportBox.innerHTML = html;
          reportBox.style.display = 'block';
        } else if (isString && res.preview_samples && res.preview_samples.length > 0) {
          const caseLabel = caseTransform ? caseTransform.toUpperCase() : 'Preserved';
          let html = `<div style="color: var(--emerald); font-weight: 600; margin-bottom: 0.5rem;">✓ Ready to convert <code>${this.escapeHtml(col)}</code> to String (Case: ${caseLabel}, ${res.converted_count} non-null values):</div>`;
          html += `<div style="max-height: 200px; overflow-y: auto; background: var(--bg-input); padding: 0.65rem; border-radius: var(--radius-sm); font-size: 0.82rem; border: 1px solid var(--border-subtle);">`;
          res.preview_samples.forEach(item => {
            html += `
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.25rem 0; border-bottom: 1px dashed var(--border-subtle);">
                <span style="color: var(--text-muted); font-family: monospace; text-decoration: ${item.changed ? 'line-through' : 'none'};">"${this.escapeHtml(item.original_value)}"</span>
                <span style="color: var(--cyan); margin: 0 0.5rem; font-weight: bold;">➔</span>
                <span style="color: var(--emerald); font-weight: 600; font-family: monospace;">"${this.escapeHtml(item.transformed_value)}"</span>
              </div>
            `;
          });
          html += `</div>`;
          reportBox.innerHTML = html;
          reportBox.style.display = 'block';
        } else {
          reportBox.innerHTML = `<div style="color: var(--emerald); font-weight: 600;">✓ All values can be successfully converted to ${target}!</div>`;
          reportBox.style.display = 'block';
        }
      }

      if (apply) {
        const caseMsg = (isString && caseTransform) ? ` with ${caseTransform.toUpperCase()} casing` : '';
        this.showToast(`Converted column '${col}' to ${target}${caseMsg}!`, 'success');
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Type conversion failed: ' + err.message, 'error');
    }
  },

  // Modals helpers
  openContactModal(col) {
    const select = document.getElementById('clean-contact-col');
    if (select) select.value = col;
    this.switchTab('cleaning');
  },

  openEmailModal(col) {
    const select = document.getElementById('clean-email-col');
    if (select) select.value = col;
    this.switchTab('cleaning');
  },

  openDateModal(col) {
    const select = document.getElementById('clean-date-col');
    if (select) select.value = col;
    this.switchTab('cleaning');
  },

  openStringModal(col) {
    const select = document.getElementById('clean-string-col');
    if (select) select.value = col;
    this.switchTab('cleaning');
  },

  openConvertTypeModal(col, targetType = 'Float') {
    const select = document.getElementById('convert-col');
    if (select) select.value = col;
    const targetSelect = document.getElementById('convert-target-type');
    if (targetSelect && targetType) {
      const match = Array.from(targetSelect.options).find(o => o.value.toLowerCase() === targetType.toLowerCase());
      if (match) targetSelect.value = match.value;
    }
    this.onConvertTargetTypeChange(targetSelect ? targetSelect.value : targetType);
    this.switchTab('cleaning');
    this.executeConvertType(false); // Inspect
  },

  openFixNullsModal(col) {
    const select = document.getElementById('clean-null-col');
    if (select) {
      select.value = col;
      this.onCleanNullColChange(col);
    }
    this.switchTab('cleaning');
  },

  // 1-Click Auto Clean
  async handleAutoClean(showOptions = false) {
    if (!this.state.sessionId) {
      this.showToast('Please upload or load a dataset first.', 'error');
      return;
    }
    if (showOptions) {
      this.openAutoCleanModal();
      return;
    }

    this.showToast('⚡ Running 1-Click Auto Clean across dataset...', 'info');
    try {
      const res = await API.autoClean(this.state.sessionId);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }

      this.state.profileData = res.new_report;
      if (res.new_report && res.new_report.file_info) {
        this.state.fileInfo = res.new_report.file_info;
        this.renderFileInfoBar(res.new_report.file_info);
      }

      this.renderProfilingDashboard(res.new_report);
      this.showAutoCleanSummaryModal(res);
      this.showToast('✨ Auto-clean completed successfully!', 'success');
      this.refreshDatasetViews();
    } catch (err) {
      this.showToast('Auto-clean failed: ' + err.message, 'error');
    }
  },

  openAutoCleanModal() {
    if (!this.state.sessionId) {
      this.showToast('Please upload or load a dataset first.', 'error');
      return;
    }
    const modal = document.getElementById('modal-auto-clean');
    if (modal) modal.classList.add('active');
  },

  async executeAutoCleanFromModal() {
    const options = {
      clean_duplicates: document.getElementById('ac-dups')?.checked ?? true,
      clean_strings: document.getElementById('ac-strings')?.checked ?? true,
      clean_names: document.getElementById('ac-names')?.checked ?? true,
      clean_emails: document.getElementById('ac-emails')?.checked ?? true,
      clean_contacts: document.getElementById('ac-contacts')?.checked ?? true,
      clean_dates: document.getElementById('ac-dates')?.checked ?? true,
      convert_types: document.getElementById('ac-types')?.checked ?? true,
      clean_nulls: document.getElementById('ac-nulls')?.checked ?? true,
    };

    this.closeAllModals();
    this.showToast('⚡ Applying selected auto-clean passes...', 'info');

    try {
      const res = await API.autoClean(this.state.sessionId, options);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }

      this.state.profileData = res.new_report;
      if (res.new_report && res.new_report.file_info) {
        this.state.fileInfo = res.new_report.file_info;
        this.renderFileInfoBar(res.new_report.file_info);
      }

      this.renderProfilingDashboard(res.new_report);
      this.showAutoCleanSummaryModal(res);
      this.showToast('✨ Selected clean operations applied!', 'success');
      this.refreshDatasetViews();
    } catch (err) {
      this.showToast('Auto-clean failed: ' + err.message, 'error');
    }
  },

  showAutoCleanSummaryModal(res) {
    const modal = document.getElementById('modal-auto-clean-summary');
    if (!modal) return;

    const beforeScore = (res.quality_before && res.quality_before.score !== undefined) ? res.quality_before.score : 0;
    const afterScore = (res.quality_after && res.quality_after.score !== undefined) ? res.quality_after.score : 0;
    const grade = (res.quality_after && res.quality_after.grade) ? res.quality_after.grade : 'Grade A';

    const beforeEl = document.getElementById('ac-score-before');
    const afterEl = document.getElementById('ac-score-after');
    const gradeEl = document.getElementById('ac-grade-badge');
    const changesList = document.getElementById('ac-changes-list');

    if (beforeEl) beforeEl.textContent = `${beforeScore}%`;
    if (afterEl) afterEl.textContent = `${afterScore}%`;
    if (gradeEl) {
      gradeEl.textContent = grade;
      gradeEl.className = `score-badge ${res.quality_after?.color || 'emerald'}`;
    }

    if (changesList) {
      if (!res.changes || res.changes.length === 0) {
        changesList.innerHTML = `<div style="color: var(--text-dim); padding: 0.5rem;">No changes were required. Dataset is already optimal!</div>`;
      } else {
        changesList.innerHTML = res.changes.map(ch => `
          <div style="display: flex; align-items: center; gap: 0.5rem; background: rgba(255,255,255,0.03); padding: 0.45rem 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);">
            <span style="color: var(--emerald); font-weight: bold;">✓</span>
            <span>${this.escapeHtml(ch)}</span>
          </div>
        `).join('');
      }
    }

    modal.classList.add('active');
  },

  handleResetDataset() {
    if (!this.state.sessionId) return;
    const modal = document.getElementById('modal-confirm-reset');
    if (modal) modal.classList.add('active');
  },

  async executeResetDataset() {
    if (!this.state.sessionId) return;
    this.closeAllModals();
    this.showToast('Resetting dataset to original state...', 'info');
    try {
      const res = await API.resetDataset(this.state.sessionId);
      if (res.success) {
        this.showToast(res.message, 'success');
        this.loadProfiling();
        this.loadPreview();
        const info = this.state.fileInfo;
        if (info) {
          this.renderFileInfoBar(info);
        }
      } else {
        this.showToast(res.message, 'error');
      }
    } catch (err) {
      this.showToast('Reset failed: ' + err.message, 'error');
    }
  },

  // Targeted 1-Click Quick Clean for single column directly from profiling card
  async handleQuickCleanColumn(col, action, detectedType) {
    if (!this.state.sessionId) return;

    this.showToast(`⚡ Cleaning '${col}' (${action})...`, 'info');
    try {
      let res = null;
      if (action.includes('Name') || detectedType === 'Name') {
        res = await API.cleanNames(this.state.sessionId, { column: col, alphabets_only: true, case_transform: 'title', allow_spaces: true });
        if (res.success) this.showToast(`Sanitized names in '${col}'! (${res.cleaned_count} records updated to alphabets only)`, 'success');
      } else if (action.includes('Email') || detectedType === 'Email') {
        res = await API.cleanEmail(this.state.sessionId, { column: col, lowercase: true, trim_spaces: true, remove_inner_spaces: true, fix_domain_typos: true });
        if (res.success) this.showToast(`Cleaned ${res.cleaned_count} emails in '${col}'!`, 'success');
      } else if (action.includes('Contact') || action.includes('Phone') || detectedType === 'Phone') {
        res = await API.cleanContact(this.state.sessionId, { column: col, strip_non_digits: true, normalize_10_digits: true, country_code: '91' });
        if (res.success) this.showToast(`Normalized ${res.cleaned_count} phone numbers in '${col}'!`, 'success');
      } else if (action.includes('Date') || detectedType === 'Date') {
        res = await API.cleanDate(this.state.sessionId, { column: col, output_format: 'YYYY-MM-DD', day_first: true });
        if (res.success) this.showToast(`Standardized ${res.converted_count} dates in '${col}' to YYYY-MM-DD!`, 'success');
      } else if (action.includes('Trim') || action.includes('Space')) {
        res = await API.cleanStrings(this.state.sessionId, { column: col, trim_whitespace: true, remove_extra_spaces: true });
        if (res.success) this.showToast(`Trimmed whitespace in '${col}' (${res.modifications_count} cells updated)!`, 'success');
      } else if (action.includes('Convert to')) {
        const targetType = action.replace('Convert to', '').trim();
        res = await API.convertType(this.state.sessionId, { column: col, target_type: targetType, apply_fix: true, clean_currency_symbols: true });
        if (res.success) this.showToast(`Converted '${col}' to ${targetType}!`, 'success');
      } else {
        res = await API.cleanStrings(this.state.sessionId, { column: col, trim_whitespace: true, remove_extra_spaces: true });
        if (res.success) this.showToast(`Cleaned text in '${col}'!`, 'success');
      }

      this.loadProfiling();
      this.refreshDatasetViews();
    } catch (err) {
      this.showToast(`Failed to clean '${col}': ` + err.message, 'error');
    }
  },

  // Quick Nulls In-Page Modal
  async openQuickNullsModal(col = '') {
    const modal = document.getElementById('modal-quick-nulls');
    const select = document.getElementById('quick-null-col');
    if (!modal || !select) return;

    // Ensure profile data is loaded so we have exact null counts
    if (!this.state.profileData && this.state.sessionId) {
      try {
        const profile = await API.getProfile(this.state.sessionId);
        this.state.profileData = profile;
      } catch (err) {
        console.warn('Could not pre-fetch profile data for null modal:', err);
      }
    }

    const { html, colsWithNulls, cleanCols, totalNulls, colMap, totalEmptyStrings } = this.buildNullColumnOptions(col);
    select.innerHTML = html;
    select.value = col || '';

    // Summary banner
    const summaryBanner = document.getElementById('quick-null-summary-banner');
    if (summaryBanner) {
      if (totalNulls > 0) {
        summaryBanner.className = 'null-summary-banner mb-3';
        summaryBanner.style.display = 'flex';
        const totalEmpty = totalEmptyStrings || 0;
        let note = `<strong>${totalNulls.toLocaleString()} missing cells</strong> detected across <strong>${colsWithNulls.length}</strong> columns.`;
        if (totalEmpty > 0) {
          note += ` (Including <strong>${totalEmpty.toLocaleString()} empty/blank strings</strong>).`;
        }
        summaryBanner.innerHTML = `
          <span style="font-size: 1.15rem;">⚠️</span>
          <div>${note}</div>
        `;
      } else {
        summaryBanner.className = 'null-summary-banner clean mb-3';
        summaryBanner.style.display = 'flex';
        summaryBanner.innerHTML = `
          <span style="font-size: 1.15rem;">✓</span>
          <div>
            <strong>No missing values detected!</strong> All columns in this dataset are 100% complete.
          </div>
        `;
      }
    }

    // Quick selection chips
    const chipsContainer = document.getElementById('quick-null-col-chips');
    const chipsWrapper = document.getElementById('quick-null-chips-wrapper');
    if (chipsContainer) {
      if (colsWithNulls.length > 0) {
        if (chipsWrapper) chipsWrapper.style.display = 'block';
        let chipsHtml = `
          <button type="button" class="null-chip ${!col ? 'active' : ''}" onclick="App.onQuickNullChipClick('')">
            <span>All Columns</span>
            <span class="null-chip-badge">${totalNulls.toLocaleString()}</span>
          </button>
        `;
        colsWithNulls.forEach(c => {
          const isActive = c.col === col ? 'active' : '';
          chipsHtml += `
            <button type="button" class="null-chip has-nulls ${isActive}" onclick="App.onQuickNullChipClick('${this.escapeHtml(c.col)}')">
              <span>${this.escapeHtml(c.col)}</span>
              <span class="null-chip-badge">${c.count.toLocaleString()}</span>
            </button>
          `;
        });
        chipsContainer.innerHTML = chipsHtml;
      } else {
        if (chipsWrapper) chipsWrapper.style.display = 'none';
        chipsContainer.innerHTML = '';
      }
    }

    // Update selected column details info
    this.onQuickNullColChange(select.value);

    // Default strategy
    const stratSelect = document.getElementById('quick-null-strategy');
    if (stratSelect) stratSelect.value = 'replace';
    this.onQuickNullStrategyChange('replace');

    modal.classList.add('active');
  },

  onQuickNullChipClick(col) {
    const select = document.getElementById('quick-null-col');
    if (select) {
      select.value = col;
      this.onQuickNullColChange(col);
    }
  },

  onQuickNullColChange(col) {
    // Update chip active classes
    const chips = document.querySelectorAll('#quick-null-col-chips .null-chip');
    chips.forEach(chip => {
      const onclickAttr = chip.getAttribute('onclick') || '';
      if (!col && onclickAttr.includes("App.onQuickNullChipClick('')")) {
        chip.classList.add('active');
      } else if (col && onclickAttr.includes(`App.onQuickNullChipClick('${col}')`)) {
        chip.classList.add('active');
      } else {
        chip.classList.remove('active');
      }
    });

    const badgeEl = document.getElementById('quick-null-col-badge');
    const infoEl = document.getElementById('quick-null-selected-info');
    const nullAnalysis = this.state.profileData?.null_analysis || null;
    const totalNulls = nullAnalysis ? (nullAnalysis.total_nulls || 0) : 0;
    const item = (nullAnalysis?.columns || []).find(c => c.column === col);

    if (!col) {
      if (badgeEl) badgeEl.textContent = `${totalNulls.toLocaleString()} nulls total`;
      if (infoEl) {
        infoEl.innerHTML = `
          <div><strong>Scope:</strong> All applicable columns (${totalNulls.toLocaleString()} missing cells total across dataset)</div>
          <div class="text-xs" style="color: var(--text-muted); margin-top: 2px;">Selected strategy will apply across every column containing missing values.</div>
        `;
      }
    } else if (item) {
      const count = item.null_count || 0;
      const pct = item.null_percentage || 0;
      const dtype = item.data_type || 'unknown';
      const isNum = dtype.includes('int') || dtype.includes('float');
      const emptyCount = item.empty_string_count || 0;

      if (badgeEl) badgeEl.textContent = `${count.toLocaleString()} nulls (${pct}%)`;
      if (infoEl) {
        let emptyNote = '';
        if (emptyCount > 0) {
          emptyNote = `<div class="text-xs" style="color: #fca5a5; margin-top: 2px;">⚠️ Contains <strong>${emptyCount.toLocaleString()}</strong> empty/blank string cells ("").</div>`;
        }
        infoEl.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
              <strong>${this.escapeHtml(col)}:</strong>
              <span style="color: ${count > 0 ? 'var(--rose)' : 'var(--emerald)'}; font-weight: 600;">
                ${count.toLocaleString()} missing ${count === 1 ? 'cell' : 'cells'} (${pct}%)
              </span>
            </div>
            <span class="badge-subtle" style="font-size: 0.7rem;">Type: ${dtype}</span>
          </div>
          ${emptyNote}
          <div class="text-xs" style="color: var(--cyan); margin-top: 3px;">
            ${isNum ? '💡 Numeric column: Median or Mean imputation is recommended.' : '💡 Text column: Mode (most frequent) or custom placeholder is recommended.'}
          </div>
        `;
      }
    } else {
      if (badgeEl) badgeEl.textContent = '';
      if (infoEl) {
        infoEl.innerHTML = `<div>Selected column: <strong>${this.escapeHtml(col)}</strong></div>`;
      }
    }
  },

  onQuickNullStrategyChange(strategy) {
    const group = document.getElementById('quick-null-custom-value-group');
    if (group) {
      group.style.display = (strategy === 'replace') ? 'block' : 'none';
    }
  },

  async executeQuickNulls() {
    const col = document.getElementById('quick-null-col').value || null;
    const strategy = document.getElementById('quick-null-strategy').value;
    const fillVal = document.getElementById('quick-null-custom-value').value;
    const treatEmpty = document.getElementById('quick-null-treat-empty')?.checked ?? true;

    this.showToast('Handling null values...', 'info');
    try {
      const res = await API.cleanNulls(this.state.sessionId, col, strategy, fillVal, treatEmpty);
      if (res.success) {
        this.closeAllModals();
        let msg = `Handled ${res.nulls_handled} null / empty cells.`;
        if (res.rows_removed > 0) msg += ` Dropped ${res.rows_removed} rows.`;
        this.showToast(msg, 'success');
        await this.loadProfiling();
        this.populateCleaningOptions();
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Null handling failed: ' + err.message, 'error');
    }
  },

  onQuickConvertTargetTypeChange(targetType) {
    const isString = (targetType || '').toLowerCase() === 'string';
    const isNumeric = targetType === 'Float' || targetType === 'Integer';

    const strGroup = document.getElementById('quick-convert-string-group');
    const currGroup = document.getElementById('quick-convert-currency-group');

    if (strGroup) strGroup.style.display = isString ? 'block' : 'none';
    if (currGroup) currGroup.style.display = isNumeric ? 'block' : 'none';
  },

  // Quick Convert In-Page Modal
  openQuickConvertModal(col, detectedType = 'Float') {
    const modal = document.getElementById('modal-quick-convert');
    const select = document.getElementById('quick-convert-col');
    const targetSelect = document.getElementById('quick-convert-target');
    const reportBox = document.getElementById('quick-convert-report-box');

    if (!modal || !select) return;

    const cols = (this.state.fileInfo && this.state.fileInfo.column_names) || [];
    select.innerHTML = cols.map(c => `<option value="${c}" ${c === col ? 'selected' : ''}>${c}</option>`).join('');

    if (targetSelect && detectedType) {
      const match = Array.from(targetSelect.options).find(o => o.value.toLowerCase() === detectedType.toLowerCase());
      if (match) targetSelect.value = match.value;
    }

    this.onQuickConvertTargetTypeChange(targetSelect ? targetSelect.value : detectedType);

    if (reportBox) reportBox.style.display = 'none';

    modal.classList.add('active');
  },

  async inspectQuickConvert() {
    const col = document.getElementById('quick-convert-col').value;
    const target = document.getElementById('quick-convert-target').value;
    const cleanCurr = document.getElementById('quick-convert-clean-curr')?.checked ?? true;
    const isString = (target || '').toLowerCase() === 'string';

    const caseTransform = isString ? (document.getElementById('quick-convert-string-case')?.value || null) : null;
    const trimWs = isString ? (document.getElementById('quick-convert-trim-ws')?.checked ?? true) : true;
    const collapseSp = isString ? (document.getElementById('quick-convert-collapse-sp')?.checked ?? false) : false;

    try {
      const res = await API.convertType(this.state.sessionId, {
        column: col,
        target_type: target,
        apply_fix: false,
        clean_currency_symbols: cleanCurr,
        case_transform: caseTransform,
        trim_whitespace: trimWs,
        collapse_spaces: collapseSp,
      });

      const reportBox = document.getElementById('quick-convert-report-box');
      if (reportBox) {
        if (res.total_problematic > 0) {
          let html = `<div style="color: var(--amber); margin-bottom: 0.5rem; font-weight: 600;">⚠ Found ${res.total_problematic} problematic values that cannot be cleanly converted:</div>`;
          html += `<div style="max-height: 140px; overflow-y: auto; background: var(--bg-input); padding: 0.5rem; border-radius: var(--radius-sm); font-size: 0.8rem;">`;
          res.problematic_records.slice(0, 15).forEach(item => {
            html += `<div>Row #${item.row_index + 1}: <code style="color: var(--rose); font-weight: bold;">"${this.escapeHtml(item.original_value)}"</code> (${item.reason})</div>`;
          });
          html += `</div>`;
          reportBox.innerHTML = html;
          reportBox.style.display = 'block';
        } else if (isString && res.preview_samples && res.preview_samples.length > 0) {
          const caseLabel = caseTransform ? caseTransform.toUpperCase() : 'Preserved';
          let html = `<div style="color: var(--emerald); font-weight: 600; margin-bottom: 0.5rem;">✓ Ready to convert <code>${this.escapeHtml(col)}</code> to String (${caseLabel}):</div>`;
          html += `<div style="max-height: 140px; overflow-y: auto; background: var(--bg-input); padding: 0.5rem; border-radius: var(--radius-sm); font-size: 0.8rem; border: 1px solid var(--border-subtle);">`;
          res.preview_samples.forEach(item => {
            html += `
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 0.2rem 0; border-bottom: 1px dashed var(--border-subtle);">
                <span style="color: var(--text-muted); font-family: monospace; text-decoration: ${item.changed ? 'line-through' : 'none'};">"${this.escapeHtml(item.original_value)}"</span>
                <span style="color: var(--cyan); margin: 0 0.4rem;">➔</span>
                <span style="color: var(--emerald); font-weight: 600; font-family: monospace;">"${this.escapeHtml(item.transformed_value)}"</span>
              </div>
            `;
          });
          html += `</div>`;
          reportBox.innerHTML = html;
          reportBox.style.display = 'block';
        } else {
          reportBox.innerHTML = `<div style="color: var(--emerald); font-weight: 600;">✓ All values can be successfully converted to ${target}!</div>`;
          reportBox.style.display = 'block';
        }
      }
    } catch (err) {
      this.showToast('Inspection failed: ' + err.message, 'error');
    }
  },

  async executeQuickConvert() {
    const col = document.getElementById('quick-convert-col').value;
    const target = document.getElementById('quick-convert-target').value;
    const cleanCurr = document.getElementById('quick-convert-clean-curr')?.checked ?? true;
    const isString = (target || '').toLowerCase() === 'string';

    const caseTransform = isString ? (document.getElementById('quick-convert-string-case')?.value || null) : null;
    const trimWs = isString ? (document.getElementById('quick-convert-trim-ws')?.checked ?? true) : true;
    const collapseSp = isString ? (document.getElementById('quick-convert-collapse-sp')?.checked ?? false) : false;

    const caseMsg = (isString && caseTransform) ? ` with ${caseTransform.toUpperCase()} casing` : '';
    this.showToast(`Converting '${col}' to ${target}${caseMsg}...`, 'info');
    try {
      const res = await API.convertType(this.state.sessionId, {
        column: col,
        target_type: target,
        apply_fix: true,
        clean_currency_symbols: cleanCurr,
        case_transform: caseTransform,
        trim_whitespace: trimWs,
        collapse_spaces: collapseSp,
      });

      if (res.success) {
        this.closeAllModals();
        this.showToast(`Converted column '${col}' to ${target}${caseMsg}!`, 'success');
        this.loadProfiling();
        this.refreshDatasetViews();
      }
    } catch (err) {
      this.showToast('Conversion failed: ' + err.message, 'error');
    }
  },

  closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
  },

  async handleUndo() {
    if (!this.state.sessionId) return;
    try {
      const res = await API.undoAction(this.state.sessionId);
      if (res.success) {
        this.showToast(res.message, 'success');
        this.refreshDatasetViews();
      } else {
        this.showToast(res.message, 'info');
      }
    } catch (err) {
      this.showToast('Undo failed: ' + err.message, 'error');
    }
  },

  refreshDatasetViews() {
    if (this.state.sessionId) {
      API.getPreview(this.state.sessionId, 1, 1).then(data => {
        if (data && data.dataset_total_rows !== undefined) {
          document.querySelectorAll('.val-rows').forEach(el => el.textContent = data.dataset_total_rows.toLocaleString());
          if (this.state.fileInfo) {
            this.state.fileInfo.rows = data.dataset_total_rows;
          }
        }
      }).catch(() => {});
    }

    if (this.state.currentTab === 'preview') {
      this.loadPreview();
    } else if (this.state.currentTab === 'profiling') {
      this.loadProfiling();
    } else if (this.state.currentTab === 'summary') {
      this.loadSummary();
    }
  },

  async loadSummary() {
    if (!this.state.sessionId) return;
    try {
      const summary = await API.getSummary(this.state.sessionId);

      document.getElementById('sum-dup-removed').textContent = summary.duplicate_rows_removed.toLocaleString();
      document.getElementById('sum-null-handled').textContent = summary.null_values_handled.toLocaleString();
      document.getElementById('sum-ws-fixed').textContent = summary.whitespace_issues_fixed.toLocaleString();
      const sumNamesEl = document.getElementById('sum-names-cleaned');
      if (sumNamesEl) sumNamesEl.textContent = (summary.name_values_cleaned || 0).toLocaleString();
      document.getElementById('sum-contact-cleaned').textContent = summary.contact_values_cleaned.toLocaleString();
      document.getElementById('sum-email-cleaned').textContent = summary.email_values_cleaned.toLocaleString();
      document.getElementById('sum-dates-converted').textContent = summary.date_values_converted.toLocaleString();
      document.getElementById('sum-types-fixed').textContent = summary.data_types_fixed.toLocaleString();

      document.getElementById('sum-rows-before').textContent = summary.rows_before.toLocaleString();
      document.getElementById('sum-rows-after').textContent = summary.rows_after.toLocaleString();

      const timeline = document.getElementById('audit-timeline-container');
      if (timeline) {
        if (!summary.history || summary.history.length === 0) {
          timeline.innerHTML = `<div style="color: var(--text-dim); font-size: 0.85rem;">No cleaning actions recorded yet.</div>`;
        } else {
          timeline.innerHTML = summary.history.map(item => `
            <div class="timeline-item">
              <div>
                <div class="timeline-desc">${this.escapeHtml(item.action)}</div>
                <div style="font-size: 0.75rem; color: var(--text-dim); margin-top: 2px;">Rows remaining: ${item.rows_remaining.toLocaleString()}</div>
              </div>
              <div class="timeline-time">${item.timestamp}</div>
            </div>
          `).join('');
        }
      }

      // Configure Export links
      const exportExcelBtn = document.getElementById('btn-export-excel');
      const exportParquetBtn = document.getElementById('btn-export-parquet');
      const exportCsvBtn = document.getElementById('btn-export-csv');
      if (exportExcelBtn) {
        exportExcelBtn.href = `/api/export/excel?session_id=${this.state.sessionId}`;
      }
      if (exportParquetBtn) {
        exportParquetBtn.href = `/api/export/parquet?session_id=${this.state.sessionId}`;
      }
      if (exportCsvBtn) {
        exportCsvBtn.href = `/api/export/csv?session_id=${this.state.sessionId}`;
      }

      document.getElementById('export-rows-badge').textContent = `${summary.rows_after.toLocaleString()} Rows`;
    } catch (err) {
      this.showToast('Failed to load summary: ' + err.message, 'error');
    }
  },

  // ===================================================================
  // PDF CONVERTER CONTROLLER
  // ===================================================================
  openPdfConverterModal() {
    this.closeAllModals();
    const modal = document.getElementById('modal-pdf-converter');
    if (modal) modal.classList.add('active');
  },

  async handlePdfFileSelected(file, isModal = false) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      this.showToast('Please select a valid .pdf file.', 'error');
      return;
    }
    this.showToast(`Inspecting PDF: ${file.name}...`, 'info');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await API.inspectPdf(formData);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }
      this.renderPdfInspectResults(res, isModal);
      this.showToast(`Found ${res.data.total_tables} table(s) across ${res.data.total_pages} page(s)!`, 'success');
    } catch (err) {
      this.showToast('Failed to inspect PDF: ' + err.message, 'error');
    }
  },

  async loadDemoPdfInConverter(isModal = false) {
    this.showToast('Inspecting Demo Sales PDF...', 'info');
    const formData = new FormData();
    formData.append('demo', 'true');

    try {
      const res = await API.inspectPdf(formData);
      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }
      this.renderPdfInspectResults(res, isModal);
      this.showToast(`Loaded Demo PDF with ${res.data.total_tables} table(s)!`, 'success');
    } catch (err) {
      this.showToast('Failed to load demo PDF: ' + err.message, 'error');
    }
  },

  renderPdfInspectResults(res, isModal = false) {
    const prefix = isModal ? 'pdf-modal-' : 'pdf-res-';
    const container = document.getElementById(isModal ? 'pdf-modal-results' : 'pdf-converter-results');
    const actions = isModal ? document.getElementById('pdf-modal-actions') : null;

    if (isModal) {
      this.state.pdfModalData = res;
    } else {
      this.state.pdfData = res;
    }

    const data = res.data;
    const tables = data.tables || [];

    const fnEl = document.getElementById(prefix + 'filename');
    const pgEl = document.getElementById(prefix + 'pages');
    const tbEl = document.getElementById(prefix + 'tables');

    if (fnEl) fnEl.textContent = res.filename || data.file_name || 'Document.pdf';
    if (pgEl) pgEl.textContent = data.total_pages;
    if (tbEl) tbEl.textContent = data.total_tables;

    // Populate table select dropdown
    const select = document.getElementById(isModal ? 'pdf-modal-table-select' : 'pdf-table-select');
    if (select) {
      let optHtml = '';
      if (tables.length > 1) {
        optHtml += `<option value="all">All Tables (Combined)</option>`;
      }
      tables.forEach(t => {
        optHtml += `<option value="${t.name}">${t.name} (${t.rows} rows, ${t.columns} cols)</option>`;
      });
      select.innerHTML = optHtml;
    }

    // Set first selection or all
    const defaultSelection = tables.length > 0 ? (tables.length > 1 ? 'all' : tables[0].name) : '';
    this.updatePdfPreviewTable(defaultSelection, isModal);

    if (container) container.style.display = 'block';
    if (actions) actions.style.display = 'flex';
  },

  onPdfTableSelectChange(selection, isModal = false) {
    this.updatePdfPreviewTable(selection, isModal);
  },

  updatePdfPreviewTable(selection, isModal = false) {
    const pdfObj = isModal ? this.state.pdfModalData : this.state.pdfData;
    if (!pdfObj || !pdfObj.data) return;

    const prefix = isModal ? 'pdf-modal-' : 'pdf-res-';
    const tables = pdfObj.data.tables || [];

    let targetTable = null;
    if (selection === 'all' || !selection) {
      targetTable = tables[0];
    } else {
      targetTable = tables.find(t => t.name === selection || t.id === selection) || tables[0];
    }

    if (!targetTable) return;

    const rwEl = document.getElementById(prefix + 'rows');
    const clEl = document.getElementById(prefix + 'cols');
    if (rwEl) {
      if (selection === 'all' && tables.length > 1) {
        const totalRows = tables.reduce((acc, t) => acc + t.rows, 0);
        rwEl.textContent = `${totalRows} (All)`;
      } else {
        rwEl.textContent = targetTable.rows;
      }
    }
    if (clEl) clEl.textContent = targetTable.columns;

    const wrapper = document.getElementById(isModal ? 'pdf-modal-preview-wrapper' : 'pdf-preview-table-wrapper');
    const colCountEl = document.getElementById('pdf-preview-col-count');
    if (colCountEl) colCountEl.textContent = `${targetTable.columns} columns`;

    if (wrapper) {
      const headers = targetTable.column_names || [];
      const rows = targetTable.preview || [];

      let tableHtml = '<table class="pdf-inspect-table"><thead><tr>';
      headers.forEach(h => {
        tableHtml += `<th>${this.escapeHtml(h)}</th>`;
      });
      tableHtml += '</tr></thead><tbody>';

      if (rows.length === 0) {
        tableHtml += `<tr><td colspan="${headers.length}" style="text-align: center; color: var(--text-dim);">No preview rows available</td></tr>`;
      } else {
        rows.forEach(r => {
          tableHtml += '<tr>';
          headers.forEach(h => {
            const val = r[h];
            tableHtml += `<td>${val !== null && val !== undefined ? this.escapeHtml(val) : '<span style="color:var(--text-dim);">&mdash;</span>'}</td>`;
          });
          tableHtml += '</tr>';
        });
      }

      tableHtml += '</tbody></table>';
      wrapper.innerHTML = tableHtml;
    }
  },

  async executePdfConvert(format = 'xlsx', isModal = false) {
    const pdfObj = isModal ? this.state.pdfModalData : this.state.pdfData;
    if (!pdfObj) {
      this.showToast('Please select or upload a PDF first.', 'error');
      return;
    }

    const select = document.getElementById(isModal ? 'pdf-modal-table-select' : 'pdf-table-select');
    const selection = select ? select.value : 'all';

    const fmtLabel = format.toUpperCase();
    this.showToast(`Converting PDF to ${fmtLabel}...`, 'info');

    // Trigger download via hidden form POST
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/api/pdf/convert';
    form.style.display = 'none';

    if (pdfObj.is_demo) {
      const demoInput = document.createElement('input');
      demoInput.name = 'demo';
      demoInput.value = 'true';
      form.appendChild(demoInput);
    } else if (pdfObj.temp_path) {
      const pathInput = document.createElement('input');
      pathInput.name = 'temp_path';
      pathInput.value = pdfObj.temp_path;
      form.appendChild(pathInput);
    }

    const fmtInput = document.createElement('input');
    fmtInput.name = 'format';
    fmtInput.value = format;
    form.appendChild(fmtInput);

    if (selection) {
      const selInput = document.createElement('input');
      selInput.name = 'selection';
      selInput.value = selection;
      form.appendChild(selInput);
    }

    document.body.appendChild(form);
    form.submit();
    setTimeout(() => form.remove(), 1500);
    this.showToast(`Downloading converted ${fmtLabel} file!`, 'success');
  },

  async executePdfLoadToCleaner(isModal = false) {
    const pdfObj = isModal ? this.state.pdfModalData : this.state.pdfData;
    if (!pdfObj) {
      this.showToast('Please select or upload a PDF first.', 'error');
      return;
    }

    const select = document.getElementById(isModal ? 'pdf-modal-table-select' : 'pdf-table-select');
    const selection = select ? select.value : 'all';

    this.showToast('Ingesting PDF into Data Cleaner Studio...', 'info');
    try {
      const res = await API.loadPdfToCleaner({
        temp_path: pdfObj.temp_path,
        is_demo: !!pdfObj.is_demo,
        selection: selection,
      });

      if (res.error) {
        this.showToast(res.error, 'error');
        return;
      }

      this.closeAllModals();
      this.onDatasetLoaded(res);
      this.showToast('PDF loaded into Data Cleaner! Ready for profiling & cleaning.', 'success');
    } catch (err) {
      this.showToast('Failed to load PDF into cleaner: ' + err.message, 'error');
    }
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
    toast.innerHTML = `<span>${icon}</span><span>${this.escapeHtml(message)}</span>`;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },
};

window.addEventListener('DOMContentLoaded', () => {
  App.init();
});
