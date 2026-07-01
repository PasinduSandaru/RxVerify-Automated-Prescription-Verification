/**
 * RxVerify Single Page Application (SPA) Controller
 */

class RxVerifyApp {
    constructor() {
        this.token = localStorage.getItem('rx_token') || null;
        this.user = JSON.parse(localStorage.getItem('rx_user')) || null;
        this.activeRxId = null;
        this.activeRxItems = [];
        
        this.apiBase = ''; // relative paths
        
        // Element bindings
        this.views = {
            auth: document.getElementById('auth-view'),
            dashboard: document.getElementById('dashboard-view'),
            upload: document.getElementById('upload-view'),
            validation: document.getElementById('validation-view')
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupTheme();
        this.checkAuth();
    }

    setupEventListeners() {
        // Theme toggler
        document.getElementById('theme-btn').addEventListener('click', () => this.toggleTheme());
        
        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
        
        // Tab selectors in Auth
        const tabLogin = document.getElementById('tab-login');
        const tabRegister = document.getElementById('tab-register');
        
        tabLogin.addEventListener('click', () => this.toggleAuthTab('login'));
        tabRegister.addEventListener('click', () => this.toggleAuthTab('register'));
        
        // Auth form submit
        document.getElementById('auth-form').addEventListener('submit', (e) => this.handleAuthSubmit(e));
        
        // Dashboard upload trigger
        document.getElementById('go-upload-btn').addEventListener('click', () => this.showPanel('upload'));
        
        // Dashboard database refresh trigger
        document.getElementById('refresh-db-btn').addEventListener('click', () => {
            this.loadDashboardData();
            this.loadAuditLogs();
        });
        
        // Drag and Drop Upload Zone
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('rx-image');
        
        dropZone.addEventListener('click', () => fileInput.click());
        
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                this.updateDropZoneFile(fileInput.files[0]);
            }
        });
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                this.updateDropZoneFile(e.dataTransfer.files[0]);
            }
        });
        
        // Upload form submit
        document.getElementById('upload-form').addEventListener('submit', (e) => this.handleUploadSubmit(e));
        
        // Manual entry table actions
        document.getElementById('add-drug-row-btn').addEventListener('click', () => this.addDispenseRow());
        document.getElementById('dispense-form').addEventListener('submit', (e) => this.handleValidationSubmit(e));
    }

    setupTheme() {
        const savedTheme = localStorage.getItem('rx_theme');
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
        }
    }

    toggleTheme() {
        document.body.classList.toggle('light-mode');
        const currentTheme = document.body.classList.contains('light-mode') ? 'light' : 'dark';
        localStorage.setItem('rx_theme', currentTheme);
    }

    checkAuth() {
        if (this.token && this.user) {
            document.getElementById('logout-btn').classList.remove('hide');
            
            const badge = document.getElementById('user-display');
            badge.textContent = `${this.user.role}: ${this.user.username}`;
            badge.classList.remove('hide');
            
            this.showPanel('dashboard');
            this.loadDashboardData();
            this.loadAuditLogs();
        } else {
            this.showPanel('auth');
        }
    }

    showPanel(panelName) {
        // Hide all views
        Object.values(this.views).forEach(view => view.classList.add('hide'));
        
        // Show target view
        if (this.views[panelName]) {
            this.views[panelName].classList.remove('hide');
            this.views[panelName].classList.add('active');
        }
        
        // Adjust Header components based on auth view
        if (panelName === 'auth') {
            document.getElementById('logout-btn').classList.add('hide');
            document.getElementById('user-display').classList.add('hide');
        } else {
            document.getElementById('logout-btn').classList.remove('hide');
            document.getElementById('user-display').classList.remove('hide');
        }
    }

    toggleAuthTab(mode) {
        const tabLogin = document.getElementById('tab-login');
        const tabRegister = document.getElementById('tab-register');
        const emailGroup = document.getElementById('email-group');
        const roleGroup = document.getElementById('role-group');
        const title = document.getElementById('auth-title');
        const subtitle = document.getElementById('auth-subtitle');
        const submit = document.getElementById('auth-submit');
        
        document.getElementById('auth-alert').classList.add('hide');

        if (mode === 'login') {
            tabLogin.classList.add('active');
            tabRegister.classList.remove('active');
            emailGroup.classList.add('hide');
            roleGroup.classList.add('hide');
            title.textContent = 'Welcome Back';
            subtitle.textContent = 'Log in to process and validate prescriptions safely.';
            submit.textContent = 'Sign In';
            this.authMode = 'login';
        } else {
            tabLogin.classList.remove('active');
            tabRegister.classList.add('active');
            emailGroup.classList.remove('hide');
            roleGroup.classList.remove('hide');
            title.textContent = 'Create Security Profile';
            subtitle.textContent = 'Register a new clinical profile to initialize audits.';
            submit.textContent = 'Register Profile';
            this.authMode = 'register';
        }
    }

    async handleAuthSubmit(e) {
        e.preventDefault();
        const alertBox = document.getElementById('auth-alert');
        alertBox.classList.add('hide');
        
        const username = document.getElementById('auth-username').value;
        const password = document.getElementById('auth-password').value;
        
        // Basic frontend sanitization
        const cleanUsername = this.sanitizeXSS(username);
        
        try {
            let response, result;
            if (this.authMode === 'register') {
                const email = document.getElementById('auth-email').value;
                const role = document.getElementById('auth-role').value;
                
                response = await fetch('/api/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: cleanUsername, email, password, role })
                });
                
                result = await response.json();
                
                if (!response.ok) throw new Error(result.message || 'Registration failed');
                
                // Switch to login tab on success
                this.toggleAuthTab('login');
                alertBox.className = 'alert alert-success';
                alertBox.textContent = 'Registration successful! Please log in.';
                alertBox.classList.remove('hide');
            } else {
                response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: cleanUsername, password })
                });
                
                result = await response.json();
                
                if (!response.ok) throw new Error(result.message || 'Login failed');
                
                // Store session
                this.token = result.access_token;
                this.user = result.user;
                localStorage.setItem('rx_token', this.token);
                localStorage.setItem('rx_user', JSON.stringify(this.user));
                
                this.checkAuth();
            }
        } catch (err) {
            alertBox.className = 'alert alert-danger';
            alertBox.textContent = err.message;
            alertBox.classList.remove('hide');
        }
    }

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('rx_token');
        localStorage.removeItem('rx_user');
        this.showPanel('auth');
    }

    updateDropZoneFile(file) {
        const fileInfo = document.getElementById('file-info');
        const text = document.querySelector('.drop-text');
        
        fileInfo.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
        fileInfo.classList.remove('hide');
        text.classList.add('hide');
    }

    async handleUploadSubmit(e) {
        e.preventDefault();
        
        const loader = document.getElementById('ocr-loader');
        const resultsArea = document.getElementById('ocr-results-area');
        const submitBtn = document.getElementById('upload-submit-btn');
        
        loader.classList.remove('hide');
        resultsArea.classList.add('hide');
        submitBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('patient_name', this.sanitizeXSS(document.getElementById('rx-patient').value));
        formData.append('doctor_name', this.sanitizeXSS(document.getElementById('rx-doctor').value));
        formData.append('prescription_date', document.getElementById('rx-date').value);
        formData.append('image', document.getElementById('rx-image').files[0]);
        
        try {
            const response = await fetch('/api/prescriptions/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${this.token}` },
                body: formData
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || 'File upload failed');
            
            this.activeRxId = result.prescription.id;
            this.activeRxItems = result.parsed_drugs;
            
            // Render OCR outputs
            let itemsHtml = '';
            if (result.parsed_drugs.length > 0) {
                result.parsed_drugs.forEach((drug, i) => {
                    itemsHtml += `<div style="padding:0.4rem; border-bottom:1px solid var(--border-panel)">
                        <strong>${i+1}. ${this.escapeHTML(drug.drug_name)}</strong> - ${this.escapeHTML(drug.dosage)} ${this.escapeHTML(drug.dosage_unit)}
                    </div>`;
                });
            } else {
                itemsHtml = '<p class="text-danger">No drugs could be parsed.</p>';
            }

            resultsArea.innerHTML = `
                <div class="ocr-meta-tag">
                    🔒 AES-256 Encrypted: <code>${this.escapeHTML(result.prescription.image_filename)}</code>
                </div>
                ${result.ocr_simulated ? '<div class="alert alert-warning">Tesseract binary missing locally. Showing Simulated OCR output.</div>' : ''}
                <h4>Raw Preprocessed Text Output</h4>
                <div class="terminal-box">${this.escapeHTML(result.extracted_text)}</div>
                
                <h4>Extracted Structured Drugs</h4>
                <div style="background-color:var(--input-bg); padding:1rem; border-radius:var(--radius-sm); border:1px solid var(--border-panel)">
                    ${itemsHtml}
                </div>
                
                <button onclick="app.initializeValidation()" class="btn btn-primary btn-block mt-4">
                    Proceed to Dispensing Entry →
                </button>
            `;
            
        } catch (err) {
            resultsArea.innerHTML = `<div class="alert alert-danger">${this.escapeHTML(err.message)}</div>`;
        } finally {
            loader.classList.add('hide');
            resultsArea.classList.remove('hide');
            submitBtn.disabled = false;
        }
    }

    initializeValidation() {
        this.showPanel('validation');
        
        document.getElementById('validation-rx-patient').textContent = `Prescription ID: ${this.activeRxId}`;
        
        const tbody = document.querySelector('#dispense-entry-table tbody');
        tbody.innerHTML = '';
        
        // Pre-fill pharmacist manual entries matching parsed OCR list for convenient verification testing
        if (this.activeRxItems && this.activeRxItems.length > 0) {
            this.activeRxItems.forEach(item => {
                this.addDispenseRow(item.drug_name, item.dosage, item.dosage_unit, 30);
            });
        } else {
            this.addDispenseRow(); // Add empty row
        }
        
        // Clear old results
        document.getElementById('validation-results-area').innerHTML = `
            <div class="placeholder-text">Press 'Run Rule Validation' to verify dispensed medicines.</div>
        `;
    }

    addDispenseRow(drugName = '', dosage = '', unit = 'mg', qty = '') {
        const tbody = document.querySelector('#dispense-entry-table tbody');
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td><input type="text" class="form-group-input drug-name" required placeholder="Metformin" value="${this.escapeHTML(drugName)}"></td>
            <td><input type="text" class="form-group-input drug-dosage" required placeholder="500" style="width: 70px" value="${this.escapeHTML(dosage.toString())}"></td>
            <td>
                <select class="form-group-input drug-unit" style="width: 80px">
                    <option value="mg" ${unit.toLowerCase() === 'mg' ? 'selected' : ''}>mg</option>
                    <option value="ml" ${unit.toLowerCase() === 'ml' ? 'selected' : ''}>ml</option>
                    <option value="g" ${unit.toLowerCase() === 'g' ? 'selected' : ''}>g</option>
                    <option value="mcg" ${unit.toLowerCase() === 'mcg' ? 'selected' : ''}>mcg</option>
                </select>
            </td>
            <td><input type="number" class="form-group-input drug-qty" required placeholder="30" style="width: 70px" value="${qty}"></td>
            <td><button type="button" class="icon-btn text-danger remove-row-btn">✖</button></td>
        `;
        
        tr.querySelector('.remove-row-btn').addEventListener('click', () => {
            tr.remove();
            if (tbody.children.length === 0) this.addDispenseRow();
        });
        
        tbody.appendChild(tr);
    }

    async handleValidationSubmit(e) {
        e.preventDefault();
        
        const loader = document.getElementById('validation-loader');
        const resultsArea = document.getElementById('validation-results-area');
        const verifyBtn = document.getElementById('verify-dispense-btn');
        
        loader.classList.remove('hide');
        resultsArea.classList.add('hide');
        verifyBtn.disabled = true;
        
        // Extract inputs from table
        const dispensedItems = [];
        const rows = document.querySelectorAll('#dispense-entry-table tbody tr');
        
        rows.forEach(row => {
            const drugName = this.sanitizeXSS(row.querySelector('.drug-name').value);
            const dosage = this.sanitizeXSS(row.querySelector('.drug-dosage').value);
            const dosageUnit = row.querySelector('.drug-unit').value;
            const qty = row.querySelector('.drug-qty').value;
            
            if (drugName) {
                dispensedItems.push({
                    drug_name: drugName,
                    dosage: dosage,
                    dosage_unit: dosageUnit,
                    quantity: qty ? parseInt(qty) : null
                });
            }
        });
        
        try {
            const response = await fetch(`/api/validation/${this.activeRxId}/validate`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ dispensed_items: dispensedItems })
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || 'Validation failed');
            
            this.renderValidationReport(result);
            
        } catch (err) {
            resultsArea.innerHTML = `<div class="alert alert-danger">${this.escapeHTML(err.message)}</div>`;
        } finally {
            loader.classList.add('hide');
            resultsArea.classList.remove('hide');
            verifyBtn.disabled = false;
        }
    }

    renderValidationReport(result) {
        const resultsArea = document.getElementById('validation-results-area');
        const status = result.status; // PASS, WARNING, FAIL
        const details = result.mismatch_details;
        
        let statusClass = 'alert-success';
        let statusTitle = '✅ Validation Passed';
        let statusDesc = 'Dispensed medicines match the prescription perfectly.';
        
        if (status === 'WARNING') {
            statusClass = 'alert-warning';
            statusTitle = '⚠️ Warnings Identified (Typos Caught)';
            statusDesc = 'Minor string typos detected. Double-check drug names.';
        } else if (status === 'FAIL') {
            statusClass = 'alert-danger';
            statusTitle = '❌ Validation Failed (Dispensing Discrepancy)';
            statusDesc = 'Critical mismatches caught! Correct the dispensing error immediately.';
        }
        
        // Build match rows HTML
        let matchesHtml = '';
        if (details.matches.length > 0) {
            details.matches.forEach(m => {
                const spellingClass = m.spelling_match ? 'text-success' : 'text-warning';
                const dosageClass = m.dosage_match ? 'text-success' : 'text-danger';
                
                matchesHtml += `<li style="padding:0.5rem 0; border-bottom:1px solid var(--border-panel); font-size:0.85rem">
                    <div>Prescribed: <strong>${this.escapeHTML(m.prescribed_name)} (${this.escapeHTML(m.prescribed_dosage)})</strong></div>
                    <div>Dispensed: <strong class="${spellingClass}">${this.escapeHTML(m.dispensed_name)}</strong> 
                                   (<strong class="${dosageClass}">${this.escapeHTML(m.dispensed_dosage)}</strong>)</div>
                    <div style="font-size:0.75rem; color:var(--text-muted)">Jaro-Winkler Similarity: ${(m.similarity * 100).toFixed(1)}%</div>
                </li>`;
            });
        }
        
        // Build missing HTML
        let missingHtml = '';
        if (details.missing_drugs.length > 0) {
            details.missing_drugs.forEach(d => {
                missingHtml += `<li class="text-danger">❌ ${this.escapeHTML(d.drug_name)} (${this.escapeHTML(d.dosage)} ${this.escapeHTML(d.dosage_unit)})</li>`;
            });
        }
        
        // Build extra HTML
        let extraHtml = '';
        if (details.extra_drugs.length > 0) {
            details.extra_drugs.forEach(d => {
                extraHtml += `<li class="text-danger">⚠️ ${this.escapeHTML(d.drug_name)} (${this.escapeHTML(d.dosage)} ${this.escapeHTML(d.dosage_unit)})</li>`;
            });
        }

        resultsArea.innerHTML = `
            <div class="alert ${statusClass}">
                <h4 style="margin-bottom:0.25rem">${statusTitle}</h4>
                <p style="font-size:0.85rem">${statusDesc}</p>
            </div>
            
            <div class="report-summary-block">
                <div class="report-section">
                    <h4>Drug Matching Analysis</h4>
                    <ul class="report-list">${matchesHtml || '<li>No matching drugs evaluated.</li>'}</ul>
                </div>
                
                ${missingHtml ? `
                <div class="report-section">
                    <h4 class="text-danger">Missing Medications (Prescribed but not Dispensed)</h4>
                    <ul class="report-list">${missingHtml}</ul>
                </div>
                ` : ''}
                
                ${extraHtml ? `
                <div class="report-section">
                    <h4 class="text-danger">Extra Medications (Dispensed but not Prescribed!)</h4>
                    <ul class="report-list">${extraHtml}</ul>
                </div>
                ` : ''}
            </div>
        `;
    }

    async loadDashboardData() {
        try {
            const response = await fetch('/api/prescriptions', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (!response.ok) throw new Error('Failed to load validation history');
            
            const list = await response.json();
            
            // Populate stats
            document.getElementById('stat-total-rx').textContent = list.length;
            
            const passed = list.filter(rx => rx.status === 'Validated' && rx.integrity_intact).length; // simple pass stats
            document.getElementById('stat-passed').textContent = passed;
            
            const mismatches = list.filter(rx => !rx.integrity_intact).length;
            document.getElementById('stat-mismatches').textContent = mismatches;
            
            const tamperedCount = list.filter(rx => !rx.integrity_intact && rx.image_hash_sha256).length;
            const integrityBadge = document.getElementById('stat-integrity');
            if (tamperedCount > 0) {
                integrityBadge.textContent = 'ALARM TAMPERED';
                integrityBadge.className = 'text-danger font-bold';
            } else {
                integrityBadge.textContent = '100% SECURE';
                integrityBadge.className = 'text-success font-bold';
            }

            // Populate table
            const tbody = document.querySelector('#prescription-table tbody');
            tbody.innerHTML = '';
            
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="placeholder-text">No validation records registered yet.</td></tr>`;
                return;
            }
            
            list.forEach(rx => {
                let statusBadge = `<span class="badge badge-pending">Pending</span>`;
                if (rx.status === 'Validated') {
                    statusBadge = `<span class="badge badge-pass">Validated</span>`;
                }
                
                // Integrity badge
                let integrityBadge = `<span class="badge badge-pass">Intact</span>`;
                if (!rx.integrity_intact && rx.image_hash_sha256) {
                    integrityBadge = `<span class="badge badge-tampered">Tampered</span>`;
                } else if (!rx.image_hash_sha256) {
                    integrityBadge = `<span class="badge badge-pending">Unsigned</span>`;
                }

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${rx.id}</td>
                    <td>${rx.created_at.split('T')[0]}</td>
                    <td><strong>${this.escapeHTML(rx.patient_name || '-')}</strong></td>
                    <td>${this.escapeHTML(rx.doctor_name || '-')}</td>
                    <td>${statusBadge}</td>
                    <td>${integrityBadge}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm" onclick="app.viewPrescription(${rx.id})">Open</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
        } catch (err) {
            console.error(err);
        }
    }

    async viewPrescription(rxId) {
        this.activeRxId = rxId;
        // Fetch details
        try {
            const response = await fetch(`/api/prescriptions`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            const list = await response.json();
            const rx = list.find(item => item.id === rxId);
            
            if (rx) {
                this.activeRxItems = rx.items;
                this.initializeValidation();
            }
        } catch (e) {
            console.error(e);
        }
    }

    async loadAuditLogs() {
        const auditPanel = document.getElementById('audit-log-panel');
        if (!this.user || (this.user.role !== 'Admin' && this.user.role !== 'Supervisor')) {
            auditPanel.classList.add('hide');
            return;
        }
        
        auditPanel.classList.remove('hide');
        
        try {
            const response = await fetch('/api/db/audits', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (!response.ok) throw new Error('Unauthorised access');
            
            const logs = await response.json();
            const tbody = document.querySelector('#audit-table tbody');
            tbody.innerHTML = '';
            
            logs.forEach(log => {
                const tr = document.createElement('tr');
                
                // Color actions
                let actionColor = '';
                if (log.action.includes('FAILURE') || log.action.includes('TAMPER')) actionColor = 'text-danger';
                else if (log.action.includes('SUCCESS') || log.action.includes('SEED')) actionColor = 'text-success';
                else if (log.action.includes('VERIFY') || log.action.includes('UPLOAD')) actionColor = 'text-accent';

                tr.innerHTML = `
                    <td style="font-size:0.8rem; font-family:monospace">${log.timestamp.replace('T', ' ').split('.')[0]}</td>
                    <td>${this.escapeHTML(log.ip_address || 'local')}</td>
                    <td><strong>${this.escapeHTML(log.username)}</strong></td>
                    <td class="${actionColor} font-bold">${this.escapeHTML(log.action)}</td>
                    <td style="font-size:0.85rem">${this.escapeHTML(log.details)}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error(e);
        }
    }

    // Sanitize values on input fields
    sanitizeXSS(str) {
        return str.trim(); // basic trim. html.escape is handled on backend. 
    }

    escapeHTML(str) {
        if (!str) return '';
        return str.toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Initialise the app
document.addEventListener('DOMContentLoaded', () => {
    window.app = new RxVerifyApp();
});
