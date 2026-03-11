// Bright Data Crawl API Integration Client
class BrightDataApp {
    constructor() {
        this.settings = {};
        this.activeCrawl = null;
        this.pollingInterval = null;
        this.diagnostics = {
            requests: [],
            errors: [],
            lastRequest: null,
            lastError: null,
            totalRequests: 0,
            successfulRequests: 0
        };
        this.init();
    }

    async init() {
        await this.loadSettings();
        this.setupEventListeners();
        this.updateUI();
        this.updateStatusBar();
        lucide.createIcons();
    }

    setupEventListeners() {
        // Settings modal
        document.getElementById('settings-btn').addEventListener('click', () => this.showSettings());
        document.getElementById('close-settings').addEventListener('click', () => this.hideSettings());
        document.getElementById('save-settings').addEventListener('click', () => this.saveSettings());
        document.getElementById('test-scraper').addEventListener('click', () => this.testScraper());
        document.getElementById('reset-settings').addEventListener('click', () => this.resetSettings());

        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Toggle switches
        document.getElementById('use-selenium-toggle').addEventListener('click', (e) => this.toggleSwitch(e.target));
        document.getElementById('headless-toggle').addEventListener('click', (e) => this.toggleSwitch(e.target));
        document.getElementById('rotate-user-agents-toggle').addEventListener('click', (e) => this.toggleSwitch(e.target));
        document.getElementById('respect-robots-toggle').addEventListener('click', (e) => this.toggleSwitch(e.target));

        // Crawl runner
        document.getElementById('start-crawl-btn').addEventListener('click', () => this.startCrawl());
        document.getElementById('cancel-crawl-btn').addEventListener('click', () => this.cancelCrawl());
        document.getElementById('load-sample-urls').addEventListener('click', () => this.loadSampleUrls());
        document.getElementById('clear-urls').addEventListener('click', () => this.clearUrls());
        document.getElementById('url-input').addEventListener('input', () => this.updateUrlCount());

        // Results
        document.getElementById('view-format').addEventListener('change', () => this.renderResults());
        document.getElementById('download-results').addEventListener('click', () => this.downloadResults());

        // Diagnostics
        document.getElementById('diagnostics-btn').addEventListener('click', () => this.showDiagnostics());
        document.getElementById('close-diagnostics').addEventListener('click', () => this.hideDiagnostics());

        // Close modals on backdrop click
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
            backdrop.addEventListener('click', (e) => {
                if (e.target === backdrop) {
                    this.hideSettings();
                    this.hideDiagnostics();
                }
            });
        });
    }

    // Settings Management
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            this.settings = await response.json();
            this.populateSettingsForm();
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.showToast('Failed to load settings', 'error');
        }
    }

    async saveSettings() {
        const formData = this.getSettingsFormData();
        
        try {
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            this.settings = formData;
            this.showToast('Settings saved successfully', 'success');
            this.updateStatusBar();
        } catch (error) {
            console.error('Failed to save settings:', error);
            this.showToast('Failed to save settings', 'error');
        }
    }

    getSettingsFormData() {
        return {
            use_selenium: document.getElementById('use-selenium-toggle').classList.contains('bg-blue-600'),
            headless: document.getElementById('headless-toggle').classList.contains('bg-blue-600'),
            timeout: parseInt(document.getElementById('timeout').value) || 30,
            delay_min: parseInt(document.getElementById('delay-min').value) || 1,
            delay_max: parseInt(document.getElementById('delay-max').value) || 3,
            max_retries: parseInt(document.getElementById('max-retries').value) || 3,
            rotate_user_agents: document.getElementById('rotate-user-agents-toggle').classList.contains('bg-blue-600'),
            respect_robots_txt: document.getElementById('respect-robots-toggle').classList.contains('bg-blue-600'),
        };
    }

    populateSettingsForm() {
        document.getElementById('timeout').value = this.settings.timeout || 30;
        document.getElementById('delay-min').value = this.settings.delay_min || 1;
        document.getElementById('delay-max').value = this.settings.delay_max || 3;
        document.getElementById('max-retries').value = this.settings.max_retries || 3;

        // Set toggle states
        this.setToggleState('use-selenium-toggle', this.settings.use_selenium);
        this.setToggleState('headless-toggle', this.settings.headless);
        this.setToggleState('rotate-user-agents-toggle', this.settings.rotate_user_agents);
        this.setToggleState('respect-robots-toggle', this.settings.respect_robots_txt);
    }

    setToggleState(toggleId, state) {
        const toggle = document.getElementById(toggleId);
        const span = toggle.querySelector('span');
        
        if (state) {
            toggle.classList.add('bg-blue-600');
            toggle.classList.remove('bg-gray-200');
            span.classList.add('translate-x-6');
            span.classList.remove('translate-x-1');
        } else {
            toggle.classList.remove('bg-blue-600');
            toggle.classList.add('bg-gray-200');
            span.classList.remove('translate-x-6');
            span.classList.add('translate-x-1');
        }
    }

    toggleSwitch(toggle) {
        const isOn = toggle.classList.contains('bg-blue-600');
        this.setToggleState(toggle.id, !isOn);
    }

    toggleApiKeyVisibility() {
        // Not needed for free scraper
    }

    toggleAdvancedSettings() {
        const content = document.getElementById('scraper-advanced-settings');
        const chevron = document.getElementById('scraper-advanced-chevron');
        
        content.classList.toggle('hidden');
        chevron.classList.toggle('rotate-90');
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            if (btn.dataset.tab === tabName) {
                btn.classList.add('border-blue-500', 'text-blue-600');
                btn.classList.remove('border-transparent', 'text-gray-500');
            } else {
                btn.classList.remove('border-blue-500', 'text-blue-600');
                btn.classList.add('border-transparent', 'text-gray-500');
            }
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.add('hidden');
        });
        document.getElementById(`${tabName}-tab`).classList.remove('hidden');
    }

    // UI State Management
    showSettings() {
        document.getElementById('settings-modal').classList.remove('hidden');
    }

    hideSettings() {
        document.getElementById('settings-modal').classList.add('hidden');
    }

    showDiagnostics() {
        document.getElementById('diagnostics-modal').classList.remove('hidden');
        this.updateDiagnosticsPanel();
    }

    hideDiagnostics() {
        document.getElementById('diagnostics-modal').classList.add('hidden');
    }

    updateUI() {
        // Update button states - free scraper is always ready
        document.getElementById('start-crawl-btn').disabled = this.activeCrawl;
        document.getElementById('test-scraper').disabled = false;
    }

    updateStatusBar() {
        // Free scraper is always ready
        document.getElementById('scraper-status').textContent = 'Ready';
        document.getElementById('scraper-status').className = 'text-2xl font-semibold text-green-600';
    }

    // Crawl Runner
    updateUrlCount() {
        const textarea = document.getElementById('url-input');
        const urls = textarea.value.split('\n').filter(url => url.trim());
        document.getElementById('url-count').textContent = urls.length;
    }

    loadSampleUrls() {
        const sampleUrls = [
            'https://www.zillow.com/montgomery-al/',
            'https://www.realtor.com/realestateandhomes-search/Montgomery_AL',
            'https://www.trulia.com/AL/Montgomery/',
            'https://www.redfin.com/city/32927/AL/Montgomery/filter/viewport=32.19544:32.46088,-86.44751:-86.22135',
            'https://www.apartments.com/montgomery-al/'
        ];
        document.getElementById('url-input').value = sampleUrls.join('\n');
        this.updateUrlCount();
    }

    clearUrls() {
        document.getElementById('url-input').value = '';
        this.updateUrlCount();
    }

    async startCrawl() {
        const urls = document.getElementById('url-input').value
            .split('\n')
            .map(url => url.trim())
            .filter(url => url);

        if (urls.length === 0) {
            this.showToast('Please enter at least one URL', 'error');
            return;
        }

        try {
            this.showProgress();
            this.updateCrawlStatus('Starting crawl...');
            
            const response = await this.apiCall('/api/scraper/crawl', 'POST', { urls });
            
            if (response.summary) {
                this.activeCrawl = {
                    jobId: `job_${Date.now()}`,
                    startTime: Date.now(),
                    urls: urls,
                    results: response
                };
                
                document.getElementById('snapshot-id').textContent = this.activeCrawl.jobId;
                
                // Free scraper is synchronous, so show results immediately
                this.currentResults = response.results;
                this.hideProgress();
                this.showResults();
                this.showToast(`Crawl completed: ${response.summary.successful}/${response.summary.total_urls} successful`, 'success');
            }
        } catch (error) {
            this.hideProgress();
            this.showToast('Failed to start crawl: ' + error.message, 'error');
        }
    }

    async cancelCrawl() {
        // Free scraper is synchronous, so no cancellation needed
        this.activeCrawl = null;
        this.hideProgress();
        this.showToast('Crawl cancelled', 'info');
    }

    startPolling() {
        if (this.pollingInterval) clearInterval(this.pollingInterval);
        
        const poll = async () => {
            if (!this.activeCrawl) return;

            try {
                const progress = await this.apiCall(`/api/brightdata/progress/${this.activeCrawl.snapshotId}`);
                this.updateProgress(progress);

                if (progress.status === 'ready') {
                    await this.downloadResults();
                    this.stopPolling();
                    this.showToast('Crawl completed successfully', 'success');
                } else if (progress.status === 'failed') {
                    this.stopPolling();
                    this.showToast('Crawl failed', 'error');
                    this.updateCrawlStatus('Failed');
                }
            } catch (error) {
                console.error('Polling error:', error);
                this.stopPolling();
                this.showToast('Polling error: ' + error.message, 'error');
            }
        };

        // Initial poll
        poll();
        
        // Set up exponential backoff polling
        let delay = 1000; // Start with 1 second
        const maxDelay = 10000; // Max 10 seconds
        
        this.pollingInterval = setInterval(() => {
            poll();
            delay = Math.min(delay * 1.5, maxDelay);
        }, delay);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
        this.activeCrawl = null;
        document.getElementById('cancel-crawl-btn').disabled = true;
        document.getElementById('start-crawl-btn').disabled = false;
    }

    updateProgress(progress) {
        const status = progress.status || 'unknown';
        this.updateCrawlStatus(status.charAt(0).toUpperCase() + status.slice(1));
        
        // Update elapsed time
        if (this.activeCrawl) {
            const elapsed = Math.floor((Date.now() - this.activeCrawl.startTime) / 1000);
            document.getElementById('elapsed-time').textContent = this.formatDuration(elapsed);
        }

        // Update progress bar (estimated)
        let progressPercent = 0;
        if (status === 'starting') progressPercent = 10;
        else if (status === 'running') progressPercent = 50;
        else if (status === 'ready') progressPercent = 100;
        
        document.getElementById('progress-bar').style.width = `${progressPercent}%`;
    }

    updateCrawlStatus(status) {
        document.getElementById('progress-status').textContent = status;
        document.getElementById('crawl-status').textContent = status;
    }

    showProgress() {
        document.getElementById('progress-section').classList.remove('hidden');
        document.getElementById('results-section').classList.add('hidden');
        document.getElementById('start-crawl-btn').disabled = true;
        document.getElementById('cancel-crawl-btn').disabled = false;
    }

    hideProgress() {
        document.getElementById('progress-section').classList.add('hidden');
        document.getElementById('start-crawl-btn').disabled = false;
        document.getElementById('cancel-crawl-btn').disabled = true;
    }

    async downloadResults() {
        if (!this.activeCrawl) return;

        try {
            const results = await this.apiCall(`/api/brightdata/download/${this.activeCrawl.snapshotId}`);
            this.currentResults = results;
            this.showResults();
        } catch (error) {
            this.showToast('Failed to download results: ' + error.message, 'error');
        }
    }

    showResults() {
        document.getElementById('results-section').classList.remove('hidden');
        this.renderResults();
    }

    renderResults() {
        const format = document.getElementById('view-format').value;
        const content = document.getElementById('results-content');
        
        if (!this.currentResults) return;

        switch (format) {
            case 'json':
                content.innerHTML = `<pre class="text-sm"><code>${JSON.stringify(this.currentResults, null, 2)}</code></pre>`;
                break;
            case 'markdown':
                this.renderMarkdownResults(content);
                break;
            case 'raw':
                content.innerHTML = `<pre class="text-sm"><code>${JSON.stringify(this.currentResults)}</code></pre>`;
                break;
        }
    }

    renderMarkdownResults(container) {
        const results = Array.isArray(this.currentResults) ? this.currentResults : [this.currentResults];
        let html = '<div class="markdown-content space-y-4">';
        
        results.forEach((result, index) => {
            html += `
                <div class="border-l-4 border-blue-500 pl-4">
                    <h4>Result ${index + 1}</h4>
                    <p><strong>URL:</strong> ${result.url || 'N/A'}</p>
                    ${result.markdown ? `<div>${this.markdownToHtml(result.markdown)}</div>` : ''}
                    ${result.html ? `<details><summary>HTML Source</summary><pre class="text-xs bg-gray-100 p-2 mt-2">${this.escapeHtml(result.html.substring(0, 1000))}${result.html.length > 1000 ? '...' : ''}</pre></details>` : ''}
                </div>
            `;
        });
        
        html += '</div>';
        container.innerHTML = html;
    }

    markdownToHtml(markdown) {
        // Simple markdown to HTML conversion
        return markdown
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')
            .replace(/\n\n/gim, '</p><p>')
            .replace(/\n/gim, '<br>')
            .replace(/^(.+)$/gim, '<p>$1</p>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async downloadResults() {
        if (!this.currentResults) return;

        const format = document.getElementById('view-format').value;
        const filename = `crawl_results_${new Date().toISOString().slice(0, 19)}.${format}`;
        
        let content;
        switch (format) {
            case 'json':
                content = JSON.stringify(this.currentResults, null, 2);
                break;
            case 'raw':
                content = JSON.stringify(this.currentResults);
                break;
            default:
                content = JSON.stringify(this.currentResults, null, 2);
        }

        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // API Management
    async testScraper() {
        try {
            this.showToast('Testing scraper...', 'info');
            const response = await this.apiCall('/api/scraper/test', 'POST');
            
            if (response.status === 'success') {
                this.showToast('Scraper test successful!', 'success');
            } else {
                this.showToast('Scraper test failed: ' + response.message, 'error');
            }
        } catch (error) {
            this.showToast('Scraper test failed: ' + error.message, 'error');
        }
    }

    async resetSettings() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            // Reset to default values
            const defaultSettings = {
                use_selenium: false,
                headless: true,
                timeout: 30,
                delay_min: 1,
                delay_max: 3,
                max_retries: 3,
                rotate_user_agents: true,
                respect_robots_txt: true,
            };
            
            this.settings = defaultSettings;
            this.populateSettingsForm();
            await this.saveSettings();
            this.showToast('Settings reset to defaults', 'info');
        }
    }

    // Diagnostics
    updateDiagnosticsPanel() {
        const recentRequests = document.getElementById('recent-requests');
        const errorLog = document.getElementById('error-log');
        
        // Clear existing content
        recentRequests.innerHTML = '';
        errorLog.innerHTML = '';

        // Populate recent requests
        this.diagnostics.requests.slice(-10).reverse().forEach(req => {
            const div = document.createElement('div');
            div.className = 'p-2 bg-gray-50 rounded text-sm';
            div.innerHTML = `
                <div class="flex justify-between">
                    <span class="font-medium">${req.method} ${req.endpoint}</span>
                    <span class="${req.status >= 200 && req.status < 300 ? 'text-green-600' : 'text-red-600'}">${req.status}</span>
                </div>
                <div class="text-xs text-gray-500">${new Date(req.timestamp).toLocaleString()}</div>
                <div class="text-xs text-gray-600">${req.duration}ms</div>
            `;
            recentRequests.appendChild(div);
        });

        // Populate error log
        this.diagnostics.errors.slice(-10).reverse().forEach(error => {
            const div = document.createElement('div');
            div.className = 'p-2 bg-red-50 rounded text-sm';
            div.innerHTML = `
                <div class="font-medium text-red-800">${error.error}</div>
                <div class="text-xs text-gray-600">${new Date(error.timestamp).toLocaleString()}</div>
                ${error.endpoint ? `<div class="text-xs text-gray-500">${error.method} ${error.endpoint}</div>` : ''}
            `;
            errorLog.appendChild(div);
        });

        // Update statistics
        document.getElementById('last-request-time').textContent = 
            this.diagnostics.lastRequest ? new Date(this.diagnostics.lastRequest).toLocaleString() : 'Never';
        document.getElementById('last-error-time').textContent = 
            this.diagnostics.lastError ? new Date(this.diagnostics.lastError).toLocaleString() : 'Never';
        document.getElementById('total-requests').textContent = this.diagnostics.totalRequests;
        
        const successRate = this.diagnostics.totalRequests > 0 ? 
            (this.diagnostics.successfulRequests / this.diagnostics.totalRequests * 100).toFixed(1) : 0;
        document.getElementById('success-rate').textContent = `${successRate}%`;
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const startTime = Date.now();
        const timestamp = startTime;
        
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(endpoint, options);
            const duration = Date.now() - startTime;
            
            // Log request
            this.diagnostics.requests.push({
                method,
                endpoint,
                status: response.status,
                duration,
                timestamp
            });
            this.diagnostics.lastRequest = timestamp;
            this.diagnostics.totalRequests++;

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || `HTTP ${response.status}`);
            }

            this.diagnostics.successfulRequests++;
            return await response.json();
            
        } catch (error) {
            const duration = Date.now() - startTime;
            
            // Log error
            this.diagnostics.errors.push({
                error: error.message,
                method,
                endpoint,
                timestamp
            });
            this.diagnostics.lastError = timestamp;

            throw error;
        }
    }

    // Utilities
    formatDuration(seconds) {
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        
        const bgColor = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            info: 'bg-blue-500',
            warning: 'bg-yellow-500'
        }[type] || 'bg-gray-500';

        toast.className = `${bgColor} text-white px-4 py-3 rounded-lg shadow-lg fade-in`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => container.removeChild(toast), 200);
        }, 3000);
    }
}

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    new BrightDataApp();
});
