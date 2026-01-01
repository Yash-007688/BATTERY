// Battery Monitor - Real-time Web Interface
// WebSocket connection and UI updates

class BatteryMonitor {
    constructor() {
        this.socket = null;
        this.currentDevice = 'laptop';
        this.chart = null;
        this.chartData = {
            labels: [],
            datasets: [{
                label: 'Battery %',
                data: [],
                borderColor: '#ffd700',
                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                tension: 0.4,
                fill: true
            }]
        };
        
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.initChart();
        this.setupEventListeners();
        this.loadTheme();
    }
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.socket = new WebSocket(wsUrl);
        
        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleUpdate(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus(false);
        };
        
        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus(false);
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    handleUpdate(data) {
        if (data.type === 'battery_update') {
            this.updateBatteryDisplay(data);
            this.updateChart(data);
        } else if (data.type === 'notification') {
            this.addNotification(data);
        } else if (data.type === 'stats') {
            this.updateStats(data);
        }
    }
    
    updateBatteryDisplay(data) {
        const percentage = data.percentage || 0;
        const isCharging = data.is_charging || false;
        const voltage = data.voltage ? (data.voltage / 1000).toFixed(2) : 'N/A';
        const temperature = data.temperature ? (data.temperature / 10).toFixed(1) : 'N/A';
        
        // Update percentage
        document.getElementById('battery-percentage').textContent = `${Math.round(percentage)}%`;
        
        // Update battery fill
        const batteryFill = document.getElementById('battery-fill');
        batteryFill.style.height = `${percentage}%`;
        
        // Update fill color based on percentage
        batteryFill.classList.remove('warning', 'danger');
        if (percentage <= 20) {
            batteryFill.classList.add('danger');
        } else if (percentage <= 50) {
            batteryFill.classList.add('warning');
        }
        
        // Update status
        const statusText = isCharging ? '⚡ Charging' : '🔋 On Battery';
        document.getElementById('battery-status').textContent = statusText;
        
        // Update details
        document.getElementById('voltage-value').textContent = `${voltage}V`;
        document.getElementById('temperature-value').textContent = `${temperature}°C`;
        
        // Update time to threshold
        if (data.time_to_threshold) {
            document.getElementById('time-value').textContent = data.time_to_threshold;
        }
        
        // Update delta
        if (data.delta_1m !== undefined) {
            const deltaElement = document.getElementById('delta-value');
            deltaElement.textContent = `${data.delta_1m > 0 ? '+' : ''}${data.delta_1m.toFixed(1)}%`;
            deltaElement.style.color = data.delta_1m > 0 ? '#4ade80' : '#f87171';
        }
    }
    
    updateChart(data) {
        const now = new Date().toLocaleTimeString();
        const percentage = data.percentage || 0;
        
        // Add new data point
        this.chartData.labels.push(now);
        this.chartData.datasets[0].data.push(percentage);
        
        // Keep only last 20 data points
        if (this.chartData.labels.length > 20) {
            this.chartData.labels.shift();
            this.chartData.datasets[0].data.shift();
        }
        
        // Update chart
        if (this.chart) {
            this.chart.update('none'); // Update without animation for smoother updates
        }
    }
    
    updateStats(data) {
        if (data.avg_percentage !== undefined) {
            document.getElementById('avg-percentage').textContent = `${data.avg_percentage.toFixed(1)}%`;
        }
        if (data.charge_cycles !== undefined) {
            document.getElementById('charge-cycles').textContent = data.charge_cycles;
        }
        if (data.health_score !== undefined) {
            document.getElementById('health-score').textContent = `${data.health_score.toFixed(0)}%`;
        }
        if (data.avg_charge_time !== undefined) {
            document.getElementById('avg-charge-time').textContent = data.avg_charge_time;
        }
    }
    
    addNotification(data) {
        const notificationsList = document.getElementById('notifications-list');
        
        const notificationItem = document.createElement('div');
        notificationItem.className = 'notification-item fade-in';
        
        const time = new Date().toLocaleTimeString();
        
        notificationItem.innerHTML = `
            <div class="notification-header">
                <span class="notification-title">${data.title || 'Notification'}</span>
                <span class="notification-time">${time}</span>
            </div>
            <div class="notification-message">${data.message || ''}</div>
        `;
        
        notificationsList.insertBefore(notificationItem, notificationsList.firstChild);
        
        // Keep only last 10 notifications
        while (notificationsList.children.length > 10) {
            notificationsList.removeChild(notificationsList.lastChild);
        }
    }
    
    initChart() {
        const ctx = document.getElementById('battery-chart');
        if (!ctx) return;
        
        this.chart = new Chart(ctx, {
            type: 'line',
            data: this.chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#ffd700',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: 'rgba(255, 255, 255, 0.8)',
                            maxRotation: 45,
                            minRotation: 45
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }
    
    setupEventListeners() {
        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        // Device selector buttons
        const deviceButtons = document.querySelectorAll('.device-btn');
        deviceButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                deviceButtons.forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentDevice = e.target.dataset.device;
                this.switchDevice(this.currentDevice);
            });
        });
        
        // Settings form
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveSettings();
            });
        }
    }
    
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Update button text
        const themeToggle = document.getElementById('theme-toggle');
        themeToggle.textContent = newTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
    }
    
    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.textContent = savedTheme === 'dark' ? '☀️ Light' : '🌙 Dark';
        }
    }
    
    switchDevice(device) {
        // Send device switch request to server
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'switch_device',
                device: device
            }));
        }
    }
    
    saveSettings() {
        const formData = new FormData(document.getElementById('settings-form'));
        const settings = Object.fromEntries(formData);
        
        // Send settings to server
        fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showToast('Settings saved successfully!', 'success');
            } else {
                this.showToast('Failed to save settings', 'error');
            }
        })
        .catch(error => {
            console.error('Error saving settings:', error);
            this.showToast('Error saving settings', 'error');
        });
    }
    
    updateConnectionStatus(connected) {
        const statusDot = document.querySelector('.status-dot');
        if (statusDot) {
            if (connected) {
                statusDot.classList.remove('disconnected');
            } else {
                statusDot.classList.add('disconnected');
            }
        }
    }
    
    showToast(message, type = 'info') {
        // Simple toast notification
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 2rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            z-index: 9999;
            animation: fadeIn 0.3s ease-out;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Export data functionality
    exportData(format = 'json') {
        fetch(`/api/export?format=${format}`)
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `battery_data_${new Date().toISOString().split('T')[0]}.${format}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                a.remove();
            })
            .catch(error => {
                console.error('Error exporting data:', error);
                this.showToast('Failed to export data', 'error');
            });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.batteryMonitor = new BatteryMonitor();
});

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-20px);
        }
    }
`;
document.head.appendChild(style);
