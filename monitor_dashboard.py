#!/usr/bin/env python3
"""
Service Monitor Dashboard - Web interface for service monitoring
"""

from flask import Flask, render_template_string, jsonify
import requests
import json
from datetime import datetime

app = Flask(__name__)

MONITOR_URL = "http://localhost:9090"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Service Monitor Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 2rem;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #f1f5f9;
            margin-bottom: 2rem;
            text-align: center;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        .service-card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.75rem;
            padding: 1.5rem;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .service-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }
        .service-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .service-name {
            font-size: 1.25rem;
            font-weight: 600;
        }
        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        .status-healthy {
            background: #22c55e;
            color: #052e16;
        }
        .status-unhealthy {
            background: #ef4444;
            color: #450a0a;
        }
        .service-details {
            color: #94a3b8;
            font-size: 0.875rem;
        }
        .service-type {
            display: inline-block;
            background: #334155;
            padding: 0.125rem 0.5rem;
            border-radius: 0.25rem;
            margin-top: 0.5rem;
        }
        .recovery-info {
            margin-top: 0.5rem;
            color: #f59e0b;
            font-size: 0.875rem;
        }
        .incidents-section {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.75rem;
            padding: 1.5rem;
        }
        .incidents-section h2 {
            color: #f1f5f9;
            margin-bottom: 1rem;
        }
        .incident {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .incident:last-child {
            margin-bottom: 0;
        }
        .incident-time {
            color: #64748b;
            font-size: 0.875rem;
        }
        .incident-service {
            color: #f1f5f9;
            font-weight: 600;
            margin-top: 0.25rem;
        }
        .incident-details {
            color: #94a3b8;
            font-size: 0.875rem;
            margin-top: 0.5rem;
        }
        .refresh-info {
            text-align: center;
            color: #64748b;
            font-size: 0.875rem;
            margin-top: 2rem;
        }
        .error-message {
            background: #7f1d1d;
            color: #fecaca;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 2rem;
            text-align: center;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .loading {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Service Monitor Dashboard</h1>
        
        <div id="error-container"></div>
        
        <div class="status-grid" id="services-grid">
            <div class="loading">Loading services...</div>
        </div>
        
        <div class="incidents-section">
            <h2>Recent Incidents</h2>
            <div id="incidents-list">
                <div class="loading">Loading incidents...</div>
            </div>
        </div>
        
        <div class="refresh-info">
            Last updated: <span id="last-update">Never</span> | Auto-refresh every 10 seconds
        </div>
    </div>
    
    <script>
        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateServices(data);
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('error-container').innerHTML = 
                    '<div class="error-message">Error fetching service status: ' + error.message + '</div>';
            }
        }
        
        async function fetchIncidents() {
            try {
                const response = await fetch('/api/incidents');
                const data = await response.json();
                updateIncidents(data);
            } catch (error) {
                console.error('Error fetching incidents:', error);
            }
        }
        
        function updateServices(data) {
            const grid = document.getElementById('services-grid');
            grid.innerHTML = '';
            
            if (!data.services || Object.keys(data.services).length === 0) {
                grid.innerHTML = '<div>No services configured</div>';
                return;
            }
            
            for (const [name, service] of Object.entries(data.services)) {
                const card = document.createElement('div');
                card.className = 'service-card';
                
                const healthyClass = service.healthy ? 'status-healthy' : 'status-unhealthy';
                const healthyText = service.healthy ? 'Healthy' : 'Unhealthy';
                
                let recoveryInfo = '';
                if (service.recovery_attempts > 0) {
                    recoveryInfo = `<div class="recovery-info">Recovery attempts: ${service.recovery_attempts}</div>`;
                }
                
                card.innerHTML = `
                    <div class="service-header">
                        <div class="service-name">${name}</div>
                        <div class="status-badge ${healthyClass}">${healthyText}</div>
                    </div>
                    <div class="service-details">
                        ${service.message}
                        <div class="service-type">${service.type.replace('_', ' ')}</div>
                        ${recoveryInfo}
                    </div>
                `;
                
                grid.appendChild(card);
            }
            
            document.getElementById('last-update').textContent = 
                new Date().toLocaleTimeString();
        }
        
        function updateIncidents(incidents) {
            const list = document.getElementById('incidents-list');
            
            if (!incidents || incidents.length === 0) {
                list.innerHTML = '<div style="color: #64748b;">No recent incidents</div>';
                return;
            }
            
            list.innerHTML = '';
            
            // Show only last 10 incidents
            incidents.slice(-10).reverse().forEach(incident => {
                const incidentDiv = document.createElement('div');
                incidentDiv.className = 'incident';
                
                const time = new Date(incident.timestamp).toLocaleString();
                const actions = incident.actions_taken.join(', ');
                
                incidentDiv.innerHTML = `
                    <div class="incident-time">${time}</div>
                    <div class="incident-service">${incident.service}</div>
                    <div class="incident-details">
                        Status: ${incident.status}<br>
                        Recovery attempts: ${incident.recovery_attempts}<br>
                        Actions: ${actions}
                    </div>
                `;
                
                list.appendChild(incidentDiv);
            });
        }
        
        // Initial load
        fetchStatus();
        fetchIncidents();
        
        // Auto refresh
        setInterval(fetchStatus, 10000);
        setInterval(fetchIncidents, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def api_status():
    try:
        response = requests.get(f"{MONITOR_URL}/status", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/incidents')
def api_incidents():
    try:
        response = requests.get(f"{MONITOR_URL}/incidents", timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify([]), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9091, debug=False)