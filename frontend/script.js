// Simple JavaScript for the Store Monitoring Dashboard

const API_BASE = 'http://localhost:8000';
let currentReportId = null;

// Utility Functions
function showElement(id) {
    document.getElementById(id).classList.remove('hidden');
}

function hideElement(id) {
    document.getElementById(id).classList.add('hidden');
}

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    setTimeout(() => errorDiv.classList.add('hidden'), 5000);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleString();
}

function getPerformanceClass(percentage) {
    if (percentage >= 95) return 'excellent';
    if (percentage >= 90) return 'good';
    if (percentage >= 80) return 'fair';
    if (percentage >= 70) return 'poor';
    return 'critical';
}

function getPerformanceText(percentage) {
    if (percentage >= 95) return 'Excellent';
    if (percentage >= 90) return 'Good';
    if (percentage >= 80) return 'Fair';
    if (percentage >= 70) return 'Poor';
    return 'Critical';
}

// API Functions
async function fetchAPI(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showError(`API Error: ${error.message}`);
        throw error;
    }
}

// Load Reports
async function loadReports() {
    showElement('loading');
    hideElement('error-message');
    
    try {
        const data = await fetchAPI('/reports');
        displayReports(data.reports);
    } catch (error) {
        console.error('Failed to load reports:', error);
    } finally {
        hideElement('loading');
    }
}

function displayReports(reports) {
    const container = document.getElementById('reports-list');
    
    if (reports.length === 0) {
        container.innerHTML = '<p>No reports available. Generate a new report first.</p>';
        return;
    }
    
    container.innerHTML = reports.map(report => `
        <div class="report-card ${report.status.toLowerCase()}" onclick="selectReport('${report.report_id}')">
            <h3>📊 Report</h3>
            <p><strong>ID:</strong> ${report.report_id.substring(0, 8)}...</p>
            <p><strong>Status:</strong> ${getStatusEmoji(report.status)} ${report.status}</p>
            <p><strong>Created:</strong> ${formatDate(report.created_at)}</p>
            ${report.completed_at ? `<p><strong>Completed:</strong> ${formatDate(report.completed_at)}</p>` : ''}
            ${report.status === 'Complete' ? `
                <p class="success">✅ Ready to view</p>
                <button class="download-btn" onclick="downloadCSV('${report.report_id}')" style="margin-top: 10px;">📥 Download CSV</button>
            ` : ''}
        </div>
    `).join('');
}

function getStatusEmoji(status) {
    switch(status) {
        case 'Complete': return '✅';
        case 'Running': return '⏳';
        case 'Failed': return '❌';
        default: return '❓';
    }
}

// Select Report and Load Restaurants
async function selectReport(reportId) {
    if (!reportId) {
        showError('Invalid report ID');
        return;
    }
    
    currentReportId = reportId;
    
    try {
        const data = await fetchAPI(`/restaurants?report_id=${reportId}`);
        displayRestaurants(data.restaurants);
        showRestaurantsSection();
    } catch (error) {
        console.error('Failed to load restaurants:', error);
    }
}

function displayRestaurants(restaurants) {
    const container = document.getElementById('restaurants-list');
    
    if (restaurants.length === 0) {
        container.innerHTML = '<p>No restaurants found in this report.</p>';
        return;
    }
    
    container.innerHTML = restaurants.map(restaurant => {
        const performanceClass = getPerformanceClass(restaurant.average_uptime);
        return `
            <div class="restaurant-card" onclick="selectRestaurant('${restaurant.store_id}')">
                <div class="restaurant-id">${restaurant.store_id.substring(0, 20)}...</div>
                <div class="uptime-summary">
                    <span class="uptime-badge ${performanceClass}">
                        ${restaurant.average_uptime}% Average Uptime
                    </span>
                </div>
                <div class="uptime-details">
                    <span class="uptime-badge">Hour: ${restaurant.uptime_last_hour}%</span>
                    <span class="uptime-badge">Day: ${restaurant.uptime_last_day}%</span>
                    <span class="uptime-badge">Week: ${restaurant.uptime_last_week}%</span>
                </div>
            </div>
        `;
    }).join('');
}

// Select Restaurant and Show Details
async function selectRestaurant(storeId) {
    if (!currentReportId || !storeId) {
        showError('Missing report ID or store ID');
        return;
    }
    
    try {
        const data = await fetchAPI(`/restaurant/${storeId}?report_id=${currentReportId}`);
        displayRestaurantDetail(data);
        showRestaurantDetail();
    } catch (error) {
        console.error('Failed to load restaurant details:', error);
    }
}

function displayRestaurantDetail(restaurant) {
    const container = document.getElementById('restaurant-info');
    const performanceClass = getPerformanceClass(restaurant.summary.average_uptime_percentage);
    const performanceText = getPerformanceText(restaurant.summary.average_uptime_percentage);
    
    container.innerHTML = `
        <div class="restaurant-header">
            <h3>🏪 ${restaurant.store_id}</h3>
            <span class="status-badge ${performanceClass}">${performanceText}</span>
        </div>
        
        <div class="detail-grid">
            <div class="detail-card">
                <h3>📊 Average Uptime</h3>
                <div class="big-number ${performanceClass}">${restaurant.summary.average_uptime_percentage}%</div>
            </div>
            
            <div class="detail-card">
                <h3>⏰ Last Hour</h3>
                <div class="big-number">${restaurant.uptime_data.last_hour.uptime_percentage}%</div>
                <p>${restaurant.uptime_data.last_hour.uptime_minutes} min uptime</p>
                <p>${restaurant.uptime_data.last_hour.downtime_minutes} min downtime</p>
            </div>
            
            <div class="detail-card">
                <h3>📅 Last Day</h3>
                <div class="big-number">${restaurant.uptime_data.last_day.uptime_percentage}%</div>
                <p>${restaurant.uptime_data.last_day.uptime_hours} hrs uptime</p>
                <p>${restaurant.uptime_data.last_day.downtime_hours} hrs downtime</p>
            </div>
            
            <div class="detail-card">
                <h3>📈 Last Week</h3>
                <div class="big-number">${restaurant.uptime_data.last_week.uptime_percentage}%</div>
                <p>${restaurant.uptime_data.last_week.uptime_hours} hrs uptime</p>
                <p>${restaurant.uptime_data.last_week.downtime_hours} hrs downtime</p>
            </div>
        </div>
        
        <div class="detail-card">
            <h3>📋 Summary</h3>
            <p><strong>Total Business Hours (Week):</strong> ${restaurant.summary.total_business_hours_week} hours</p>
            <p><strong>Performance Status:</strong> <span class="${performanceClass}">${performanceText}</span></p>
        </div>
    `;
}

// Navigation Functions
function showReports() {
    hideElement('restaurants-section');
    hideElement('restaurant-detail');
    showElement('reports-section');
}

function showRestaurantsSection() {
    hideElement('reports-section');
    hideElement('restaurant-detail');
    showElement('restaurants-section');
}

function showRestaurants() {
    hideElement('restaurant-detail');
    showElement('restaurants-section');
}

function showRestaurantDetail() {
    hideElement('restaurants-section');
    showElement('restaurant-detail');
}

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Store Monitoring Dashboard loaded');
    loadReports();
});

// CSV Download Function
async function downloadCSV(reportId) {
    try {
        showElement('loading');
        
        const response = await fetch(`${API_BASE}/get_report?report_id=${reportId}`);
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        // Get the CSV data as blob
        const csvBlob = await response.blob();
        
        // Create download link
        const url = window.URL.createObjectURL(csvBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `store_monitoring_report_${reportId.substring(0, 8)}.csv`;
        
        // Trigger download
        document.body.appendChild(link);
        link.click();
        
        // Cleanup
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        console.log(`✅ CSV downloaded: store_monitoring_report_${reportId.substring(0, 8)}.csv`);
        
    } catch (error) {
        console.error('Download failed:', error);
        showError(`Download failed: ${error.message}`);
    } finally {
        hideElement('loading');
    }
}

// Add some helpful functions for testing
window.debugAPI = {
    testConnection: () => fetchAPI('/health'),
    generateReport: () => fetchAPI('/trigger_report'),
    checkStats: () => fetchAPI('/stats'),
    downloadCSV: (reportId) => downloadCSV(reportId)
};
