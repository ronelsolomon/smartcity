// Vacancy Watch Dashboard JavaScript
class DashboardApp {
    constructor() {
        this.data = null;
        this.charts = {};
        this.init();
    }

    async init() {
        lucide.createIcons();
        this.setupEventListeners();
        await this.loadData();
        this.renderDashboard();
    }

    setupEventListeners() {
        document.getElementById('refresh-btn').addEventListener('click', () => this.refreshData());
        document.getElementById('export-btn').addEventListener('click', () => this.exportData());
        
        // Montgomery Data button
        const montgomeryDataBtn = document.getElementById('montgomery-data-btn');
        if (montgomeryDataBtn) {
            montgomeryDataBtn.addEventListener('click', () => this.showMontgomeryData());
        }
        
        // Montgomery data section event listeners
        const discoverDatasetsBtn = document.getElementById('discover-datasets-btn');
        if (discoverDatasetsBtn) {
            discoverDatasetsBtn.addEventListener('click', () => this.discoverMontgomeryDatasets());
        }
        
        const crawlMontgomeryBtn = document.getElementById('crawl-montgomery-btn');
        if (crawlMontgomeryBtn) {
            crawlMontgomeryBtn.addEventListener('click', () => this.crawlMontgomeryData());
        }
        
        const analyzeMontgomeryBtn = document.getElementById('analyze-montgomery-btn');
        if (analyzeMontgomeryBtn) {
            analyzeMontgomeryBtn.addEventListener('click', () => this.analyzeMontgomeryData());
        }
        
        // Add zoning-related event listeners
        const zoningBtn = document.getElementById('zoning-btn');
        if (zoningBtn) {
            zoningBtn.addEventListener('click', () => this.showZoningModal());
        }
        
        const enrichZoningBtn = document.getElementById('enrich-zoning-btn');
        if (enrichZoningBtn) {
            enrichZoningBtn.addEventListener('click', () => this.enrichWithZoning());
        }
        
        // Surplus Properties button
        const surplusPropertiesBtn = document.getElementById('surplus-properties-btn');
        if (surplusPropertiesBtn) {
            surplusPropertiesBtn.addEventListener('click', () => this.showSurplusProperties());
        }
        
        // Surplus properties section event listeners
        const discoverSurplusBtn = document.getElementById('discover-surplus-btn');
        if (discoverSurplusBtn) {
            discoverSurplusBtn.addEventListener('click', () => this.discoverSurplusDatasets());
        }
        
        const crawlSurplusBtn = document.getElementById('crawl-surplus-btn');
        if (crawlSurplusBtn) {
            crawlSurplusBtn.addEventListener('click', () => this.crawlSurplusProperties());
        }
        
        const analyzeSurplusBtn = document.getElementById('analyze-surplus-btn');
        if (analyzeSurplusBtn) {
            analyzeSurplusBtn.addEventListener('click', () => this.analyzeSurplusProperties());
        }
        
        const surplusReportBtn = document.getElementById('surplus-report-btn');
        if (surplusReportBtn) {
            surplusReportBtn.addEventListener('click', () => this.generateSurplusReport());
        }
        
        // Surplus filters
        const applySurplusFilters = document.getElementById('apply-surplus-filters');
        if (applySurplusFilters) {
            applySurplusFilters.addEventListener('click', () => this.applySurplusFilters());
        }
        
        const clearSurplusFilters = document.getElementById('clear-surplus-filters');
        if (clearSurplusFilters) {
            clearSurplusFilters.addEventListener('click', () => this.clearSurplusFilters());
        }
        
        // Surplus pagination
        const surplusPrevPage = document.getElementById('surplus-prev-page');
        if (surplusPrevPage) {
            surplusPrevPage.addEventListener('click', () => this.surplusPreviousPage());
        }
        
        const surplusNextPage = document.getElementById('surplus-next-page');
        if (surplusNextPage) {
            surplusNextPage.addEventListener('click', () => this.surplusNextPage());
        }
        
        // Surplus map controls
        const toggleSurplusViewBtn = document.getElementById('toggle-surplus-view-btn');
        if (toggleSurplusViewBtn) {
            toggleSurplusViewBtn.addEventListener('click', () => this.toggleSurplusMapView());
        }
        
        const toggleSurplusMap = document.getElementById('toggle-surplus-map');
        if (toggleSurplusMap) {
            toggleSurplusMap.addEventListener('click', () => this.toggleSurplusMap());
        }
        
        const resetSurplusMap = document.getElementById('reset-surplus-map');
        if (resetSurplusMap) {
            resetSurplusMap.addEventListener('click', () => this.resetSurplusMap());
        }
        
        // Modal close listeners
        const closeZoningModal = document.getElementById('close-zoning-modal');
        if (closeZoningModal) {
            closeZoningModal.addEventListener('click', () => this.hideZoningModal());
        }
        
        const closeZoningBtn = document.getElementById('close-zoning-btn');
        if (closeZoningBtn) {
            closeZoningBtn.addEventListener('click', () => this.hideZoningModal());
        }
        
        // Close modal on background click
        const zoningModal = document.getElementById('zoning-modal');
        if (zoningModal) {
            zoningModal.addEventListener('click', (e) => {
                if (e.target === zoningModal) {
                    this.hideZoningModal();
                }
            });
        }
    }

    async loadData() {
        this.showLoading(true);
        try {
            // Try to load the most recent report
            const response = await fetch('/api/latest-report');
            if (response.ok) {
                this.data = await response.json();
            } else {
                // Fallback to demo data
                await this.loadDemoData();
            }
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            await this.loadDemoData();
        } finally {
            this.showLoading(false);
        }
    }

    async loadDemoData() {
        try {
            const response = await fetch('demo_report.json');
            if (response.ok) {
                this.data = await response.json();
            } else {
                // Generate minimal demo data if file doesn't exist
                this.data = this.generateMinimalDemoData();
            }
        } catch (error) {
            this.data = this.generateMinimalDemoData();
        }
    }

    generateMinimalDemoData() {
        return {
            generated_at: new Date().toISOString(),
            total_properties: 0,
            high_risk_vacancies: [],
            construction_hotspots: [],
            traffic_alerts: [],
            real_estate_trends: {
                sources_crawled: 0,
                listing_keywords: {},
                price_range: { min: 0, max: 0 },
                vacancy_mentions: 0
            },
            summary: {
                total_city_vacant_properties: 0,
                high_risk_count: 0,
                total_violations_indexed: 0,
                permits_last_90_days: 0,
                traffic_incidents_last_30d: 0,
                avg_vacancy_score: 0.0
            }
        };
    }

    renderDashboard() {
        if (!this.data) return;

        this.updateMetrics();
        this.renderCharts();
        this.renderRealEstateTrends();
        this.renderPropertiesTable();
        this.renderHotspots();
        this.renderTrafficAlerts();
    }

    updateMetrics() {
        const summary = this.data.summary || {};
        
        document.getElementById('total-properties').textContent = 
            summary.total_city_vacant_properties || 0;
        document.getElementById('high-risk-count').textContent = 
            summary.high_risk_count || 0;
        document.getElementById('avg-score').textContent = 
            (summary.avg_vacancy_score || 0).toFixed(1);
        document.getElementById('active-permits').textContent = 
            summary.permits_last_90_days || 0;
    }

    renderCharts() {
        this.renderRiskChart();
        this.renderConstructionChart();
    }

    renderRiskChart() {
        const ctx = document.getElementById('riskChart').getContext('2d');
        
        // Calculate risk distribution
        const properties = this.data.high_risk_vacancies || [];
        const lowRisk = properties.filter(p => p.vacancy_score < 30).length;
        const mediumRisk = properties.filter(p => p.vacancy_score >= 30 && p.vacancy_score < 50).length;
        const highRisk = properties.filter(p => p.vacancy_score >= 50).length;

        if (this.charts.risk) {
            this.charts.risk.destroy();
        }

        this.charts.risk = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk (0-29)', 'Medium Risk (30-49)', 'High Risk (50+)'],
                datasets: [{
                    data: [lowRisk, mediumRisk, highRisk],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderConstructionChart() {
        const ctx = document.getElementById('constructionChart').getContext('2d');
        
        // Group permits by type
        const permits = this.data.construction_hotspots || [];
        const permitTypes = {};
        
        permits.forEach(permit => {
            const type = permit.type || 'General';
            permitTypes[type] = (permitTypes[type] || 0) + 1;
        });

        if (this.charts.construction) {
            this.charts.construction.destroy();
        }

        this.charts.construction = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(permitTypes),
                datasets: [{
                    label: 'Permits',
                    data: Object.values(permitTypes),
                    backgroundColor: '#3b82f6',
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    renderRealEstateTrends() {
        const trends = this.data.real_estate_trends || {};
        
        document.getElementById('min-price').textContent = 
            trends.price_range?.min ? `$${trends.price_range.min.toLocaleString()}` : '-';
        document.getElementById('max-price').textContent = 
            trends.price_range?.max ? `$${trends.price_range.max.toLocaleString()}` : '-';
        document.getElementById('vacancy-mentions').textContent = 
            trends.vacancy_mentions || 0;

        // Render keywords
        const keywords = trends.listing_keywords || {};
        const container = document.getElementById('keywords-container');
        container.innerHTML = '';

        Object.entries(keywords).slice(0, 5).forEach(([keyword, count]) => {
            const item = document.createElement('div');
            item.className = 'flex justify-between items-center';
            item.innerHTML = `
                <span class="text-sm text-gray-600">${keyword}</span>
                <span class="text-sm font-medium text-gray-900">${count}</span>
            `;
            container.appendChild(item);
        });

        // Update other metrics
        const summary = this.data.summary || {};
        document.getElementById('traffic-incidents').textContent = 
            summary.traffic_incidents_last_30d || 0;
        document.getElementById('code-violations').textContent = 
            summary.total_violations_indexed || 0;
    }

    renderPropertiesTable() {
        const properties = this.data.high_risk_vacancies || [];
        const tbody = document.getElementById('properties-table');
        tbody.innerHTML = '';

        if (properties.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-4 text-center text-gray-500">
                        No high-risk properties found
                    </td>
                </tr>
            `;
            return;
        }

        properties.slice(0, 10).forEach(property => {
            const row = document.createElement('tr');
            row.className = this.getRiskClass(property.vacancy_score);
            
            const signals = Array.isArray(property.signals) ? property.signals.slice(0, 3) : [];
            
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ${property.address || 'Unknown'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${this.getScoreClass(property.vacancy_score)}">
                        ${property.vacancy_score?.toFixed(1) || '0.0'}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    ${property.open_violations || 0}
                </td>
                <td class="px-6 py-4 text-sm text-gray-900">
                    <div class="flex flex-wrap gap-1">
                        ${signals.map(signal => `
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                                ${signal}
                            </span>
                        `).join('')}
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    $${(property.assessed_value || 0).toLocaleString()}
                </td>
            `;
            tbody.appendChild(row);
        });
    }

    renderHotspots() {
        const hotspots = this.data.construction_hotspots || [];
        const container = document.getElementById('hotspots-container');
        container.innerHTML = '';

        if (hotspots.length === 0) {
            container.innerHTML = '<p class="text-gray-500">No construction hotspots found</p>';
            return;
        }

        hotspots.slice(0, 5).forEach(hotspot => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg';
            item.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="p-2 bg-blue-100 rounded-lg">
                        <i data-lucide="hard-hat" class="w-4 h-4 text-blue-600"></i>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-900">${hotspot.address || 'Unknown'}</p>
                        <p class="text-xs text-gray-500">Construction activity</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-lg font-semibold text-blue-600">${hotspot.permit_count || 0}</p>
                    <p class="text-xs text-gray-500">permits</p>
                </div>
            `;
            container.appendChild(item);
        });

        lucide.createIcons();
    }

    renderTrafficAlerts() {
        const alerts = this.data.traffic_alerts || [];
        const container = document.getElementById('traffic-container');
        container.innerHTML = '';

        if (alerts.length === 0) {
            container.innerHTML = '<p class="text-gray-500">No recent traffic incidents</p>';
            return;
        }

        alerts.slice(0, 5).forEach(alert => {
            const item = document.createElement('div');
            item.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg';
            item.innerHTML = `
                <div class="flex items-center space-x-3">
                    <div class="p-2 bg-yellow-100 rounded-lg">
                        <i data-lucide="alert-triangle" class="w-4 h-4 text-yellow-600"></i>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-900">${alert.location || 'Unknown'}</p>
                        <p class="text-xs text-gray-500">${alert.type || 'Incident'} • ${alert.date || 'Unknown'}</p>
                    </div>
                </div>
                <div class="text-right">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${this.getSeverityClass(alert.severity)}">
                        ${alert.severity || 'Unknown'}
                    </span>
                </div>
            `;
            container.appendChild(item);
        });

        lucide.createIcons();
    }

    getRiskClass(score) {
        if (score >= 50) return 'risk-high';
        if (score >= 30) return 'risk-medium';
        return 'risk-low';
    }

    getScoreClass(score) {
        if (score >= 50) return 'bg-red-100 text-red-800';
        if (score >= 30) return 'bg-yellow-100 text-yellow-800';
        return 'bg-green-100 text-green-800';
    }

    getSeverityClass(severity) {
        const classes = {
            'major': 'bg-red-100 text-red-800',
            'moderate': 'bg-yellow-100 text-yellow-800',
            'minor': 'bg-green-100 text-green-800'
        };
        return classes[severity] || 'bg-gray-100 text-gray-800';
    }

    async refreshData() {
        const btn = document.getElementById('refresh-btn');
        const icon = btn.querySelector('i');
        icon.classList.add('animate-spin');
        
        try {
            await this.loadData();
            this.renderDashboard();
        } finally {
            icon.classList.remove('animate-spin');
        }
    }

    exportData() {
        if (!this.data) return;

        const dataStr = JSON.stringify(this.data, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `vacancy_watch_dashboard_${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }

    // Zoning-related methods
    async showZoningModal() {
        const modal = document.getElementById('zoning-modal');
        if (!modal) return;

        modal.classList.remove('hidden');
        await this.loadZoningDistricts();
        lucide.createIcons();
    }

    hideZoningModal() {
        const modal = document.getElementById('zoning-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    async loadZoningDistricts() {
        try {
            const response = await fetch('/api/zoning/districts');
            if (response.ok) {
                const zoningData = await response.json();
                this.renderZoningDistricts(zoningData);
            } else {
                console.error('Failed to load zoning districts');
            }
        } catch (error) {
            console.error('Error loading zoning districts:', error);
        }
    }

    renderZoningDistricts(zoningData) {
        const container = document.getElementById('zoning-districts-container');
        if (!container) return;

        const districts = zoningData.data || [];
        
        container.innerHTML = districts.map(district => `
            <div class="border rounded-lg p-4 hover:bg-gray-50">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <h3 class="font-semibold text-lg">${district.zone_code} - ${district.zone_description}</h3>
                        <p class="text-sm text-gray-600">${district.description || ''}</p>
                    </div>
                    <span class="px-2 py-1 text-xs font-medium rounded-full ${
                        district.land_use === 'Residential' ? 'bg-green-100 text-green-800' :
                        district.land_use === 'Commercial' ? 'bg-blue-100 text-blue-800' :
                        'bg-gray-100 text-gray-800'
                    }">
                        ${district.land_use}
                    </span>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mt-3 text-sm">
                    <div>
                        <span class="font-medium">Min Lot Size:</span> 
                        ${district.minimum_lot_size ? `${district.minimum_lot_size.toLocaleString()} sq ft` : 'N/A'}
                    </div>
                    <div>
                        <span class="font-medium">Max Height:</span> 
                        ${district.maximum_building_height ? `${district.maximum_building_height} ft` : 'N/A'}
                    </div>
                </div>
                
                ${district.permitted_uses && district.permitted_uses.length > 0 ? `
                    <div class="mt-3">
                        <span class="font-medium text-sm">Permitted Uses:</span>
                        <div class="flex flex-wrap gap-1 mt-1">
                            ${district.permitted_uses.slice(0, 3).map(use => 
                                `<span class="px-2 py-1 bg-gray-100 text-xs rounded">${use}</span>`
                            ).join('')}
                            ${district.permitted_uses.length > 3 ? 
                                `<span class="px-2 py-1 bg-gray-100 text-xs rounded">+${district.permitted_uses.length - 3} more</span>` : ''
                            }
                        </div>
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    async enrichWithZoning() {
        const btn = document.getElementById('enrich-zoning-btn');
        if (!btn) return;

        btn.disabled = true;
        btn.textContent = 'Enriching...';
        
        try {
            const response = await fetch('/api/zoning/enrich', { method: 'POST' });
            if (response.ok) {
                const result = await response.json();
                alert(`Successfully enriched ${result.message || 'properties with zoning data'}`);
                await this.loadData();
                this.renderDashboard();
            } else {
                const error = await response.json();
                alert(`Failed to enrich: ${error.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error enriching with zoning:', error);
            alert('Error enriching properties with zoning data');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Enrich with Zoning';
        }
    }

    async showMontgomeryData() {
        const btn = document.getElementById('montgomery-data-btn');
        if (!btn) return;

        btn.disabled = true;
        btn.textContent = 'Loading...';
        
        try {
            // Run Montgomery data analysis
            const response = await fetch('/api/montgomery/analyze', { method: 'POST' });
            if (response.ok) {
                const result = await response.json();
                this.showMontgomeryDataModal(result);
            } else {
                const error = await response.json();
                alert(`Failed to analyze Montgomery data: ${error.error || 'Unknown error'}`);
            }
        } catch (error) {
            console.error('Error analyzing Montgomery data:', error);
            alert('Error analyzing Montgomery open data');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Montgomery Data';
        }
    }

    showMontgomeryDataModal(data) {
        // Create modal overlay
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] w-full mx-4 overflow-hidden">
                <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                    <div>
                        <h2 class="text-xl font-semibold text-gray-900">Montgomery County Data Analysis</h2>
                        <p class="text-sm text-gray-500 mt-1">Construction Permits & Code Violations Insights</p>
                    </div>
                    <button id="close-montgomery-modal" class="text-gray-400 hover:text-gray-600">
                        <i data-lucide="x" class="w-6 h-6"></i>
                    </button>
                </div>
                
                <div class="p-6 overflow-y-auto max-h-[70vh]">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <!-- Permits Analysis -->
                        <div class="bg-gray-50 rounded-lg p-4">
                            <h3 class="font-semibold text-lg mb-3">📋 Construction Permits</h3>
                            <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Total Permits:</span>
                                    <span class="text-sm font-medium">${data.permits?.total_permits?.toLocaleString() || 'N/A'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Total Value:</span>
                                    <span class="text-sm font-medium">$${data.permits?.cost_analysis?.total_value?.toLocaleString() || 'N/A'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Average Cost:</span>
                                    <span class="text-sm font-medium">$${Math.round(data.permits?.cost_analysis?.mean_cost || 0).toLocaleString()}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Major Projects:</span>
                                    <span class="text-sm font-medium">${data.permits?.cost_analysis?.projects_over_100k || 'N/A'} >$100K</span>
                                </div>
                            </div>
                            
                            ${data.permits?.project_types ? `
                                <div class="mt-4">
                                    <h4 class="font-medium text-sm mb-2">Top Project Types:</h4>
                                    <div class="space-y-1">
                                        ${Object.entries(data.permits.project_types).slice(0, 5).map(([type, count]) => `
                                            <div class="flex justify-between text-xs">
                                                <span class="text-gray-600">${type}:</span>
                                                <span class="font-medium">${count}</span>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                        
                        <!-- Violations Analysis -->
                        <div class="bg-gray-50 rounded-lg p-4">
                            <h3 class="font-semibold text-lg mb-3">⚠️ Code Violations</h3>
                            <div class="space-y-2">
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Total Violations:</span>
                                    <span class="text-sm font-medium">${data.violations?.total_violations?.toLocaleString() || 'N/A'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Open Cases:</span>
                                    <span class="text-sm font-medium text-red-600">${data.violations?.case_status?.OPEN || 'N/A'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Closed Cases:</span>
                                    <span class="text-sm font-medium text-green-600">${data.violations?.case_status?.CLOSED || 'N/A'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-sm text-gray-600">Liens Filed:</span>
                                    <span class="text-sm font-medium text-orange-600">${data.violations?.lien_status?.['Lien Filed'] || 'N/A'}</span>
                                </div>
                            </div>
                            
                            ${data.violations?.case_types ? `
                                <div class="mt-4">
                                    <h4 class="font-medium text-sm mb-2">Violation Types:</h4>
                                    <div class="space-y-1">
                                        ${Object.entries(data.violations.case_types).slice(0, 5).map(([type, count]) => `
                                            <div class="flex justify-between text-xs">
                                                <span class="text-gray-600">${type}:</span>
                                                <span class="font-medium">${count}</span>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                    
                    ${data.violations?.common_complaints ? `
                        <div class="mt-6 bg-blue-50 rounded-lg p-4">
                            <h3 class="font-semibold text-sm mb-3">🔍 Common Complaint Keywords</h3>
                            <div class="flex flex-wrap gap-2">
                                ${Object.entries(data.violations.common_complaints)
                                    .sort((a, b) => b[1] - a[1])
                                    .slice(0, 10)
                                    .map(([keyword, count]) => `
                                        <span class="px-3 py-1 bg-white text-xs font-medium rounded-full border border-blue-200">
                                            ${keyword}: ${count}
                                        </span>
                                    `).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="mt-6 text-center">
                        <p class="text-xs text-gray-500">
                            Data sourced from Montgomery County Open Data Portal • Updated ${new Date().toLocaleString()}
                        </p>
                    </div>
                </div>
                
                <div class="px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <div class="flex justify-end">
                        <button id="close-montgomery-btn" class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        lucide.createIcons();
        
        // Setup close handlers
        const closeModal = () => {
            document.body.removeChild(modal);
        };
        
        document.getElementById('close-montgomery-modal').addEventListener('click', closeModal);
        document.getElementById('close-montgomery-btn').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }

    // Montgomery Data Methods
    showMontgomeryData() {
        const section = document.getElementById('montgomery-data-section');
        if (section.classList.contains('hidden')) {
            section.classList.remove('hidden');
            this.loadMontgomeryStatus();
        } else {
            section.classList.add('hidden');
        }
    }

    async loadMontgomeryStatus() {
        try {
            const response = await fetch('/api/montgomery/status');
            if (response.ok) {
                const status = await response.json();
                this.updateMontgomeryStatus(status);
            }
        } catch (error) {
            console.error('Error loading Montgomery status:', error);
        }
    }

    updateMontgomeryStatus(status) {
        document.getElementById('montgomery-has-data').textContent = status.has_data ? 'Yes' : 'No';
        document.getElementById('montgomery-total-records').textContent = status.total_records.toLocaleString();
        document.getElementById('montgomery-file-count').textContent = status.file_count;
        document.getElementById('montgomery-last-crawl').textContent = status.last_crawl ? 
            new Date(status.last_crawl).toLocaleDateString() : 'Never';
    }

    async discoverMontgomeryDatasets() {
        this.showMontgomeryLoading(true);
        try {
            const response = await fetch('/api/montgomery/discover');
            if (response.ok) {
                const result = await response.json();
                this.displayMontgomeryDatasets(result);
            } else {
                this.showError('Failed to discover Montgomery datasets');
            }
        } catch (error) {
            console.error('Error discovering Montgomery datasets:', error);
            this.showError('Error discovering Montgomery datasets');
        } finally {
            this.showMontgomeryLoading(false);
        }
    }

    displayMontgomeryDatasets(result) {
        const categoriesDiv = document.getElementById('montgomery-categories');
        categoriesDiv.innerHTML = '';

        // Display category summary
        Object.entries(result.categories).forEach(([category, count]) => {
            if (count > 0) {
                const categoryCard = document.createElement('div');
                categoryCard.className = 'bg-white border border-gray-200 rounded-lg p-4';
                categoryCard.innerHTML = `
                    <h4 class="font-medium text-gray-900 capitalize">${category.replace('_', ' ')}</h4>
                    <p class="text-2xl font-bold text-blue-600">${count}</p>
                    <p class="text-sm text-gray-500">datasets found</p>
                `;
                categoriesDiv.appendChild(categoryCard);
            }
        });

        // Show sample datasets
        const sampleDatasets = result.datasets.slice(0, 6);
        sampleDatasets.forEach(dataset => {
            const datasetCard = document.createElement('div');
            datasetCard.className = 'bg-white border border-gray-200 rounded-lg p-4';
            datasetCard.innerHTML = `
                <h4 class="font-medium text-gray-900 text-sm">${dataset.name}</h4>
                <p class="text-xs text-gray-500 mt-1">${dataset.format.toUpperCase()}</p>
                ${dataset.record_count ? `<p class="text-xs text-gray-500">${dataset.record_count.toLocaleString()} records</p>` : ''}
            `;
            categoriesDiv.appendChild(datasetCard);
        });
    }

    async crawlMontgomeryData() {
        this.showMontgomeryLoading(true);
        try {
            const response = await fetch('/api/montgomery/crawl', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ max_datasets: 3 })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.displayCrawlResults(result);
                // Reload status after crawl
                setTimeout(() => this.loadMontgomeryStatus(), 1000);
            } else {
                this.showError('Failed to crawl Montgomery data');
            }
        } catch (error) {
            console.error('Error crawling Montgomery data:', error);
            this.showError('Error crawling Montgomery data');
        } finally {
            this.showMontgomeryLoading(false);
        }
    }

    displayCrawlResults(result) {
        const summary = result.results.summary;
        this.showNotification(`Crawl completed: ${summary.successful_downloads}/${summary.total_downloads} downloads successful (${summary.total_records} records)`, 'success');
        
        // Display saved files
        if (result.saved_files) {
            const filesList = Object.entries(result.saved_files)
                .map(([type, filename]) => `${type}: ${filename}`)
                .join(', ');
            this.showNotification(`Files saved: ${filesList}`, 'info');
        }
    }

    async analyzeMontgomeryData() {
        this.showMontgomeryLoading(true);
        try {
            const response = await fetch('/api/montgomery/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            if (response.ok) {
                const result = await response.json();
                this.displayMontgomeryAnalysis(result);
            } else {
                this.showError('Failed to analyze Montgomery data');
            }
        } catch (error) {
            console.error('Error analyzing Montgomery data:', error);
            this.showError('Error analyzing Montgomery data');
        } finally {
            this.showMontgomeryLoading(false);
        }
    }

    displayMontgomeryAnalysis(result) {
        const analysisDiv = document.getElementById('montgomery-analysis');
        const contentDiv = document.getElementById('montgomery-analysis-content');
        
        contentDiv.innerHTML = '';
        
        Object.entries(result.analysis).forEach(([dataType, data]) => {
            const analysisCard = document.createElement('div');
            analysisCard.className = 'bg-gray-50 rounded-lg p-4';
            
            let analysisHtml = `
                <h5 class="font-medium text-gray-900 capitalize">${dataType.replace('_', ' ')}</h5>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
                    <div>
                        <p class="text-xs text-gray-500">Records</p>
                        <p class="text-lg font-bold text-blue-600">${data.record_count.toLocaleString()}</p>
                    </div>
                    <div>
                        <p class="text-xs text-gray-500">File Size</p>
                        <p class="text-sm font-medium">${this.formatFileSize(data.file_size)}</p>
                    </div>
                    <div>
                        <p class="text-xs text-gray-500">Last Updated</p>
                        <p class="text-sm font-medium">${new Date(data.last_modified).toLocaleDateString()}</p>
                    </div>
                </div>
            `;
            
            // Add specific analysis if available
            if (data.analysis) {
                analysisHtml += '<div class="mt-3 space-y-2">';
                Object.entries(data.analysis).forEach(([key, value]) => {
                    if (typeof value === 'object') {
                        analysisHtml += `
                            <div>
                                <p class="text-xs text-gray-500 capitalize">${key.replace('_', ' ')}</p>
                                <div class="text-sm">
                                    ${Object.entries(value).slice(0, 3).map(([k, v]) => 
                                        `<span class="inline-block bg-white px-2 py-1 rounded mr-1 mb-1">${k}: ${v}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        `;
                    } else {
                        analysisHtml += `
                            <div class="flex justify-between">
                                <span class="text-xs text-gray-500 capitalize">${key.replace('_', ' ')}</span>
                                <span class="text-sm font-medium">${typeof value === 'number' ? value.toLocaleString() : value}</span>
                            </div>
                        `;
                    }
                });
                analysisHtml += '</div>';
            }
            
            analysisCard.innerHTML = analysisHtml;
            contentDiv.appendChild(analysisCard);
        });
        
        analysisDiv.classList.remove('hidden');
    }

    showMontgomeryLoading(show) {
        const loadingDiv = document.getElementById('montgomery-loading');
        if (show) {
            loadingDiv.classList.remove('hidden');
        } else {
            loadingDiv.classList.add('hidden');
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async lookupPropertyZoning(addresses) {
        try {
            const response = await fetch('/api/zoning/lookup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ addresses })
            });
            
            if (response.ok) {
                return await response.json();
            } else {
                throw new Error('Failed to lookup zoning');
            }
        } catch (error) {
            console.error('Error looking up zoning:', error);
            return null;
        }
    }

    // Surplus Properties Methods
    showSurplusProperties() {
        // Hide other sections
        document.getElementById('montgomery-data-section').classList.add('hidden');
        
        // Show surplus properties section
        const surplusSection = document.getElementById('surplus-properties-section');
        surplusSection.classList.remove('hidden');
        
        // Load initial data
        this.loadSurplusProperties();
    }

    async discoverSurplusDatasets() {
        try {
            this.showLoading('Discovering surplus datasets...');
            
            const response = await fetch('/api/surplus/discover');
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Found ${data.datasets.length} surplus datasets`, 'success');
                console.log('Discovered datasets:', data.datasets);
            } else {
                this.showNotification('Failed to discover datasets', 'error');
            }
        } catch (error) {
            console.error('Error discovering datasets:', error);
            this.showNotification('Error discovering datasets', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async crawlSurplusProperties() {
        try {
            this.showLoading('Crawling surplus properties...');
            
            const response = await fetch('/api/surplus/crawl', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ max_datasets: 3 })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Crawled ${data.properties_count} surplus properties`, 'success');
                if (data.demo_data) {
                    this.showNotification('Using demo data - real datasets not available', 'info');
                }
                await this.loadSurplusProperties();
            } else {
                this.showNotification('Failed to crawl properties', 'error');
            }
        } catch (error) {
            console.error('Error crawling properties:', error);
            this.showNotification('Error crawling properties', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async analyzeSurplusProperties() {
        try {
            this.showLoading('Analyzing surplus properties...');
            
            const response = await fetch('/api/surplus/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Analysis complete', 'success');
                this.displaySurplusAnalysis(data.analysis);
            } else {
                this.showNotification('Failed to analyze properties', 'error');
            }
        } catch (error) {
            console.error('Error analyzing properties:', error);
            this.showNotification('Error analyzing properties', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async generateSurplusReport() {
        try {
            this.showLoading('Generating surplus property report...');
            
            const response = await fetch('/api/surplus/report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ report_type: 'acquisition' })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(`Report generated: ${data.report_file}`, 'success');
                this.displaySurplusReportSummary(data.summary);
            } else {
                this.showNotification('Failed to generate report', 'error');
            }
        } catch (error) {
            console.error('Error generating report:', error);
            this.showNotification('Error generating report', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadSurplusProperties() {
        try {
            const response = await fetch('/api/surplus/properties');
            const data = await response.json();
            
            if (data.success) {
                this.surplusPropertiesData = data.properties;
                this.surplusPagination = data.pagination;
                this.updateSurplusMetrics(data.properties);
                this.renderSurplusPropertiesTable(data.properties);
                this.updateSurplusPagination(data.pagination);
            } else {
                console.error('Failed to load surplus properties');
            }
        } catch (error) {
            console.error('Error loading surplus properties:', error);
        }
    }

    updateSurplusMetrics(properties) {
        const total = properties.length;
        const highOpportunity = properties.filter(p => 
            p.development_potential?.overall_score > 80
        ).length;
        const eligible = properties.filter(p => 
            p.acquisition_eligibility?.eligible
        ).length;
        const avgScore = properties.length > 0 ? 
            properties.reduce((sum, p) => sum + (p.development_potential?.overall_score || 0), 0) / properties.length : 0;

        document.getElementById('surplus-total').textContent = total;
        document.getElementById('surplus-high-opportunity').textContent = highOpportunity;
        document.getElementById('surplus-eligible').textContent = eligible;
        document.getElementById('surplus-avg-score').textContent = avgScore.toFixed(1);
    }

    renderSurplusPropertiesTable(properties) {
        const tbody = document.getElementById('surplus-properties-tbody');
        
        if (properties.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="px-4 py-8 text-center text-sm text-gray-500">
                        No surplus properties found. Click "Crawl Properties" to load data.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = properties.map(property => `
            <tr class="hover:bg-gray-50">
                <td class="px-4 py-2 text-sm font-medium">${property.parcel_id}</td>
                <td class="px-4 py-2 text-sm">${property.address}</td>
                <td class="px-4 py-2 text-sm">$${property.assessed_value?.toLocaleString() || '0'}</td>
                <td class="px-4 py-2 text-sm">${property.property_type || 'N/A'}</td>
                <td class="px-4 py-2 text-sm">${property.zoning || 'N/A'}</td>
                <td class="px-4 py-2 text-sm">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                        ${property.development_potential?.overall_score > 80 ? 'bg-green-100 text-green-800' : 
                          property.development_potential?.overall_score > 60 ? 'bg-yellow-100 text-yellow-800' : 
                          'bg-gray-100 text-gray-800'}">
                        ${property.development_potential?.overall_score?.toFixed(1) || '0'}%
                    </span>
                </td>
                <td class="px-4 py-2 text-sm">
                    <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                        ${property.acquisition_eligibility?.eligible ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                        ${property.acquisition_eligibility?.grade || 'N/A'}
                    </span>
                </td>
                <td class="px-4 py-2 text-sm">
                    <button onclick="dashboard.viewSurplusPropertyDetail('${property.parcel_id}')" 
                            class="text-blue-600 hover:text-blue-800 text-xs font-medium">
                        View Details
                    </button>
                </td>
            </tr>
        `).join('');
    }

    updateSurplusPagination(pagination) {
        if (!pagination) return;
        
        document.getElementById('surplus-start').textContent = 
            (pagination.page - 1) * pagination.per_page + 1;
        document.getElementById('surplus-end').textContent = 
            Math.min(pagination.page * pagination.per_page, pagination.total);
        document.getElementById('surplus-total-records').textContent = pagination.total;
        
        document.getElementById('surplus-prev-page').disabled = pagination.page <= 1;
        document.getElementById('surplus-next-page').disabled = pagination.page >= pagination.pages;
    }

    async applySurplusFilters() {
        const filters = {
            status: document.getElementById('surplus-status-filter').value,
            property_type: document.getElementById('surplus-type-filter').value,
            min_value: document.getElementById('surplus-value-filter').value,
            eligible: document.getElementById('surplus-eligibility-filter').value
        };

        // Remove empty filters
        Object.keys(filters).forEach(key => {
            if (!filters[key]) delete filters[key];
        });

        try {
            const params = new URLSearchParams(filters);
            const response = await fetch(`/api/surplus/properties?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.surplusPropertiesData = data.properties;
                this.surplusPagination = data.pagination;
                this.renderSurplusPropertiesTable(data.properties);
                this.updateSurplusPagination(data.pagination);
            }
        } catch (error) {
            console.error('Error applying filters:', error);
            this.showNotification('Error applying filters', 'error');
        }
    }

    clearSurplusFilters() {
        document.getElementById('surplus-status-filter').value = '';
        document.getElementById('surplus-type-filter').value = '';
        document.getElementById('surplus-value-filter').value = '';
        document.getElementById('surplus-eligibility-filter').value = '';
        
        this.loadSurplusProperties();
    }

    surplusPreviousPage() {
        if (this.surplusPagination && this.surplusPagination.page > 1) {
            this.loadSurplusPage(this.surplusPagination.page - 1);
        }
    }

    surplusNextPage() {
        if (this.surplusPagination && this.surplusPagination.page < this.surplusPagination.pages) {
            this.loadSurplusPage(this.surplusPagination.page + 1);
        }
    }

    async loadSurplusPage(page) {
        try {
            const response = await fetch(`/api/surplus/properties?page=${page}&per_page=20`);
            const data = await response.json();
            
            if (data.success) {
                this.surplusPropertiesData = data.properties;
                this.surplusPagination = data.pagination;
                this.renderSurplusPropertiesTable(data.properties);
                this.updateSurplusPagination(data.pagination);
            }
        } catch (error) {
            console.error('Error loading page:', error);
        }
    }

    viewSurplusPropertyDetail(parcelId) {
        const property = this.surplusPropertiesData.find(p => p.parcel_id === parcelId);
        if (property) {
            this.showSurplusPropertyModal(property);
        }
    }

    showSurplusPropertyModal(property) {
        // Create modal HTML
        const modalHtml = `
            <div id="surplus-property-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
                    <div class="mt-3">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-medium text-gray-900">Property Details: ${property.parcel_id}</h3>
                            <button onclick="dashboard.closeSurplusPropertyModal()" class="text-gray-400 hover:text-gray-600">
                                <i data-lucide="x" class="w-6 h-6"></i>
                            </button>
                        </div>
                        
                        <div class="space-y-4">
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <p class="text-sm font-medium text-gray-500">Address</p>
                                    <p class="text-sm">${property.address}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-500">Assessed Value</p>
                                    <p class="text-sm">$${property.assessed_value?.toLocaleString() || '0'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-500">Property Type</p>
                                    <p class="text-sm">${property.property_type || 'N/A'}</p>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-gray-500">Zoning</p>
                                    <p class="text-sm">${property.zoning || 'N/A'}</p>
                                </div>
                            </div>
                            
                            <div class="border-t pt-4">
                                <h4 class="text-sm font-medium text-gray-900 mb-2">Development Potential</h4>
                                <div class="grid grid-cols-2 gap-4">
                                    <div>
                                        <p class="text-sm font-medium text-gray-500">Overall Score</p>
                                        <div class="w-full bg-gray-200 rounded-full h-2">
                                            <div class="bg-blue-600 h-2 rounded-full" style="width: ${property.development_potential?.overall_score || 0}%"></div>
                                        </div>
                                        <p class="text-xs text-gray-500">${property.development_potential?.overall_score?.toFixed(1) || '0'}%</p>
                                    </div>
                                    <div>
                                        <p class="text-sm font-medium text-gray-500">Market Potential</p>
                                        <p class="text-sm capitalize">${property.development_potential?.market_potential || 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                            
                            <div class="border-t pt-4">
                                <h4 class="text-sm font-medium text-gray-900 mb-2">Acquisition Eligibility</h4>
                                <div class="grid grid-cols-2 gap-4">
                                    <div>
                                        <p class="text-sm font-medium text-gray-500">Eligible</p>
                                        <p class="text-sm">${property.acquisition_eligibility?.eligible ? 'Yes' : 'No'}</p>
                                    </div>
                                    <div>
                                        <p class="text-sm font-medium text-gray-500">Grade</p>
                                        <p class="text-sm">${property.acquisition_eligibility?.grade || 'N/A'}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        lucide.createIcons();
    }

    closeSurplusPropertyModal() {
        const modal = document.getElementById('surplus-property-modal');
        if (modal) {
            modal.remove();
        }
    }

    displaySurplusAnalysis(analysis) {
        // Create analysis display
        let analysisHtml = '<div class="bg-white rounded-lg p-6 mb-6"><h4 class="text-lg font-medium mb-4">Surplus Properties Analysis</h4>';
        
        // Key metrics
        analysisHtml += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">';
        analysisHtml += `
            <div class="bg-blue-50 p-4 rounded">
                <p class="text-sm font-medium text-blue-800">Total Properties</p>
                <p class="text-2xl font-bold text-blue-900">${analysis.total_properties}</p>
            </div>
            <div class="bg-green-50 p-4 rounded">
                <p class="text-sm font-medium text-green-800">Total Value</p>
                <p class="text-2xl font-bold text-green-900">$${analysis.total_assessed_value?.toLocaleString() || '0'}</p>
            </div>
            <div class="bg-purple-50 p-4 rounded">
                <p class="text-sm font-medium text-purple-800">Avg Value</p>
                <p class="text-2xl font-bold text-purple-900">$${Math.round(analysis.average_assessed_value || 0).toLocaleString()}</p>
            </div>
        `;
        analysisHtml += '</div>';
        
        // Investment opportunities
        if (analysis.investment_opportunities && analysis.investment_opportunities.length > 0) {
            analysisHtml += '<div class="mb-6"><h5 class="text-md font-medium mb-3">Top Investment Opportunities</h5>';
            analysisHtml += '<div class="space-y-2">';
            analysis.investment_opportunities.forEach(opp => {
                analysisHtml += `
                    <div class="border rounded p-3">
                        <div class="flex justify-between">
                            <span class="text-sm font-medium">${opp.address}</span>
                            <span class="text-sm text-green-600">$${opp.assessed_value?.toLocaleString() || '0'}</span>
                        </div>
                        <div class="text-xs text-gray-500">Score: ${opp.potential_score?.toFixed(1) || '0'}%</div>
                    </div>
                `;
            });
            analysisHtml += '</div></div>';
        }
        
        analysisHtml += '</div>';
        
        // Insert after the metrics section
        const metricsSection = document.getElementById('surplus-metrics');
        metricsSection.insertAdjacentHTML('afterend', analysisHtml);
    }

    displaySurplusReportSummary(summary) {
        // Create report summary display
        let summaryHtml = '<div class="bg-orange-50 border border-orange-200 rounded-lg p-6 mb-6">';
        summaryHtml += '<h4 class="text-lg font-medium text-orange-900 mb-4">Acquisition Report Summary</h4>';
        
        if (summary.key_findings) {
            summaryHtml += '<div class="mb-4"><h5 class="text-md font-medium text-orange-800 mb-2">Key Findings</h5>';
            summaryHtml += '<ul class="list-disc list-inside text-sm text-orange-700">';
            summary.key_findings.forEach(finding => {
                summaryHtml += `<li>${finding}</li>`;
            });
            summaryHtml += '</ul></div>';
        }
        
        if (summary.recommendations) {
            summaryHtml += '<div><h5 class="text-md font-medium text-orange-800 mb-2">Recommendations</h5>';
            summaryHtml += '<ul class="list-disc list-inside text-sm text-orange-700">';
            summary.recommendations.forEach(rec => {
                summaryHtml += `<li>${rec}</li>`;
            });
            summaryHtml += '</ul></div>';
        }
        
        summaryHtml += '</div>';
        
        // Insert after the surplus section
        const surplusSection = document.getElementById('surplus-properties-section');
        surplusSection.insertAdjacentHTML('beforeend', summaryHtml);
    }

    // Map functionality for surplus properties
    toggleSurplusMapView() {
        const mapContainer = document.getElementById('surplus-map-container');
        const tableContainer = document.getElementById('surplus-properties-table-container');
        const toggleBtn = document.getElementById('toggle-surplus-view-btn');
        
        if (mapContainer.classList.contains('hidden')) {
            // Show map, hide table
            mapContainer.classList.remove('hidden');
            tableContainer.classList.add('hidden');
            toggleBtn.innerHTML = '<i data-lucide="table" class="w-4 h-4"></i> Table View';
            this.initializeSurplusMap();
        } else {
            // Show table, hide map
            mapContainer.classList.add('hidden');
            tableContainer.classList.remove('hidden');
            toggleBtn.innerHTML = '<i data-lucide="map" class="w-4 h-4"></i> Map View';
        }
        
        lucide.createIcons();
    }

    toggleSurplusMap() {
        const mapContainer = document.getElementById('surplus-map-container');
        const toggleBtn = document.getElementById('toggle-surplus-map');
        
        if (mapContainer.classList.contains('hidden')) {
            mapContainer.classList.remove('hidden');
            toggleBtn.textContent = 'Hide Map';
            this.initializeSurplusMap();
        } else {
            mapContainer.classList.add('hidden');
            toggleBtn.textContent = 'Show Map';
        }
    }

    resetSurplusMap() {
        if (this.surplusMap) {
            // Reset map to default view
            this.surplusMap.setView([32.3617, -86.2792], 12);
        }
    }

    initializeSurplusMap() {
        // Simple map implementation using CSS and JavaScript
        // In production, you'd use Leaflet, Google Maps, or Mapbox
        const mapElement = document.getElementById('surplus-map');
        
        if (!this.surplusPropertiesData || this.surplusPropertiesData.length === 0) {
            mapElement.innerHTML = `
                <div class="absolute inset-0 flex items-center justify-center text-gray-500">
                    <div class="text-center">
                        <i data-lucide="map-pin" class="w-12 h-12 mx-auto mb-2"></i>
                        <p>No properties to display on map</p>
                        <p class="text-sm">Load surplus properties first</p>
                    </div>
                </div>
            `;
            return;
        }

        // Create a simple CSS-based map visualization
        mapElement.innerHTML = `
            <div class="relative w-full h-full bg-gradient-to-br from-green-50 to-blue-50 rounded-lg overflow-hidden">
                <div class="absolute inset-0 p-4">
                    <div class="grid grid-cols-3 gap-2 h-full">
                        ${this.createMapGrid()}
                    </div>
                </div>
                <div class="absolute top-2 right-2 bg-white rounded shadow p-2">
                    <div class="text-xs font-medium text-gray-700">Montgomery, AL</div>
                    <div class="text-xs text-gray-500">${this.surplusPropertiesData.length} Properties</div>
                </div>
            </div>
        `;

        // Add click handlers for property markers
        this.addMapMarkerHandlers();
    }

    createMapGrid() {
        // Group properties by general area for visualization
        const areas = {
            'Downtown': [],
            'East': [],
            'West': [],
            'North': [],
            'South': [],
            'Central': []
        };

        this.surplusPropertiesData.forEach(property => {
            // Simple area assignment based on property characteristics
            if (property.neighborhood && property.neighborhood.toLowerCase().includes('downtown')) {
                areas['Downtown'].push(property);
            } else if (property.assessed_value > 100000) {
                areas['Central'].push(property);
            } else if (Math.random() > 0.5) {
                areas['East'].push(property);
            } else {
                areas['West'].push(property);
            }
        });

        let gridHtml = '';
        Object.entries(areas).forEach(([area, properties]) => {
            if (properties.length > 0) {
                const highPotential = properties.filter(p => p.development_potential?.overall_score > 80).length;
                const eligible = properties.filter(p => p.acquisition_eligibility?.eligible).length;
                
                gridHtml += `
                    <div class="bg-white rounded-lg shadow-sm p-3 hover:shadow-md transition-shadow cursor-pointer" 
                         onclick="dashboard.showAreaProperties('${area}')">
                        <div class="text-sm font-medium text-gray-900">${area}</div>
                        <div class="text-xs text-gray-500 mt-1">
                            <div>${properties.length} properties</div>
                            <div class="flex space-x-2 mt-1">
                                <span class="text-green-600">${highPotential} high potential</span>
                                <span class="text-blue-600">${eligible} eligible</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            <div class="w-full bg-gray-200 rounded-full h-1">
                                <div class="bg-green-500 h-1 rounded-full" style="width: ${(highPotential / properties.length) * 100}%"></div>
                            </div>
                        </div>
                    </div>
                `;
            }
        });

        return gridHtml;
    }

    showAreaProperties(area) {
        // Filter properties by area and show in modal
        const areaProperties = this.surplusPropertiesData.filter(property => {
            // Simple area filtering logic
            if (area === 'Downtown') {
                return property.neighborhood && property.neighborhood.toLowerCase().includes('downtown');
            } else if (area === 'Central') {
                return property.assessed_value > 100000;
            }
            return true; // Show all for other areas
        });

        this.showAreaPropertiesModal(area, areaProperties);
    }

    showAreaPropertiesModal(area, properties) {
        const modalHtml = `
            <div id="area-properties-modal" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
                <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-2/3 shadow-lg rounded-md bg-white">
                    <div class="mt-3">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="text-lg font-medium text-gray-900">Properties in ${area}</h3>
                            <button onclick="dashboard.closeAreaPropertiesModal()" class="text-gray-400 hover:text-gray-600">
                                <i data-lucide="x" class="w-6 h-6"></i>
                            </button>
                        </div>
                        
                        <div class="overflow-x-auto">
                            <table class="min-w-full divide-y divide-gray-200">
                                <thead class="bg-gray-50">
                                    <tr>
                                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Address</th>
                                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Opportunity</th>
                                        <th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Eligible</th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200">
                                    ${properties.map(property => `
                                        <tr class="hover:bg-gray-50">
                                            <td class="px-4 py-2 text-sm">${property.address}</td>
                                            <td class="px-4 py-2 text-sm">$${property.assessed_value?.toLocaleString() || '0'}</td>
                                            <td class="px-4 py-2 text-sm">${property.property_type || 'N/A'}</td>
                                            <td class="px-4 py-2 text-sm">
                                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                                                    ${property.development_potential?.overall_score > 80 ? 'bg-green-100 text-green-800' : 
                                                      property.development_potential?.overall_score > 60 ? 'bg-yellow-100 text-yellow-800' : 
                                                      'bg-gray-100 text-gray-800'}">
                                                    ${property.development_potential?.overall_score?.toFixed(1) || '0'}%
                                                </span>
                                            </td>
                                            <td class="px-4 py-2 text-sm">
                                                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                                                    ${property.acquisition_eligibility?.eligible ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}">
                                                    ${property.acquisition_eligibility?.eligible ? 'Yes' : 'No'}
                                                </span>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        lucide.createIcons();
    }

    closeAreaPropertiesModal() {
        const modal = document.getElementById('area-properties-modal');
        if (modal) {
            modal.remove();
        }
    }

    addMapMarkerHandlers() {
        // Add interactive elements to map
        const mapElement = document.getElementById('surplus-map');
        const markers = mapElement.querySelectorAll('[onclick*="showAreaProperties"]');
        
        markers.forEach(marker => {
            marker.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.05)';
                this.style.transition = 'transform 0.2s';
            });
            
            marker.addEventListener('mouseleave', function() {
                this.style.transform = 'scale(1)';
            });
        });
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardApp();
});
