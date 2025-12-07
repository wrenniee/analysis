import requests
import json
import time
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import threading

app = Flask(__name__)
CORS(app)

# Database setup
DB_PATH = 'tracker_history.db'

def init_db():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Positions snapshot table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_positions INTEGER,
            total_value REAL,
            total_pnl REAL
        )
    ''')
    
    # Position details table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER,
            bucket TEXT,
            outcome TEXT,
            size REAL,
            avg_price REAL,
            current_value REAL,
            cash_pnl REAL,
            percent_pnl REAL,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        )
    ''')
    
    # Bucket exposure history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bucket_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER,
            bucket TEXT,
            exposure REAL,
            yes_size REAL,
            no_size REAL,
            yes_value REAL,
            no_value REAL,
            pnl REAL,
            FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def save_snapshot_to_db(timestamp, positions, bucket_exposure, total_value, total_pnl):
    """Save snapshot to database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Insert snapshot
        cursor.execute('''
            INSERT INTO snapshots (timestamp, total_positions, total_value, total_pnl)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, len(positions), total_value, total_pnl))
        
        snapshot_id = cursor.lastrowid
        
        # Insert positions
        for pos in positions:
            cursor.execute('''
                INSERT INTO positions (snapshot_id, bucket, outcome, size, avg_price, 
                                      current_value, cash_pnl, percent_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_id,
                pos.get('title', ''),
                pos.get('outcome', 'Yes'),
                pos.get('size', 0),
                pos.get('averagePrice', 0),
                pos.get('currentValue', 0),
                pos.get('cashPnl', 0),
                pos.get('percentPnl', 0)
            ))
        
        # Insert bucket exposure
        for bucket, data in bucket_exposure.items():
            cursor.execute('''
                INSERT INTO bucket_history (snapshot_id, bucket, exposure, yes_size, 
                                           no_size, yes_value, no_value, pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_id,
                bucket,
                data['exposure'],
                data['yes_size'],
                data['no_size'],
                data['yes_value'],
                data['no_value'],
                data['pnl']
            ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving to database: {e}")

def load_history_from_db(limit=20000):
    """Load history from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get recent snapshots
        cursor.execute('''
            SELECT id, timestamp, total_positions, total_value, total_pnl
            FROM snapshots
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        
        snapshots = cursor.fetchall()
        history = []
        
        for snap_id, timestamp, total_pos, total_val, total_pnl in reversed(snapshots):
            # Get bucket exposure for this snapshot
            cursor.execute('''
                SELECT bucket, exposure, yes_size, no_size, yes_value, no_value, pnl
                FROM bucket_history
                WHERE snapshot_id = ?
            ''', (snap_id,))
            
            bucket_data = {}
            for bucket, exposure, yes_size, no_size, yes_val, no_val, pnl in cursor.fetchall():
                bucket_data[bucket] = {
                    'exposure': exposure,
                    'yes_size': yes_size,
                    'no_size': no_size,
                    'yes_value': yes_val,
                    'no_value': no_val,
                    'pnl': pnl
                }
            
            history.append({
                'timestamp': timestamp,
                'buckets': bucket_data,
                'total_positions': total_pos,
                'total_value': total_val,
                'total_pnl': total_pnl
            })
        
        conn.close()
        return history
    except Exception as e:
        print(f"Error loading from database: {e}")
        return []

# HTML Template embedded in Python
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Butterfly Strategy Live Tracker</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1rem; opacity: 0.9; }
        .status {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .status-item { text-align: center; min-width: 150px; margin: 10px; }
        .status-label { font-size: 0.9rem; opacity: 0.8; margin-bottom: 5px; }
        .status-value { font-size: 1.8rem; font-weight: bold; }
        .charts-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
        }
        .chart-container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            height: 600px;
            position: relative;
            display: flex;
            flex-direction: column;
        }
        .chart-row {
            display: flex;
            flex: 1;
            min-height: 0;
            gap: 20px;
        }
        .chart-canvas-wrapper {
            flex: 1;
            min-width: 0;
            position: relative;
        }
        .custom-legend {
            width: 160px;
            flex-shrink: 0;
            overflow-y: auto;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 10px;
            font-size: 0.85rem;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .legend-header {
            font-weight: bold;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            text-align: center;
            font-size: 0.9rem;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin-bottom: 5px;
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            transition: background 0.2s;
        }
        .legend-item:hover {
            background: rgba(255,255,255,0.1);
        }
        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 3px;
            margin-right: 8px;
            flex-shrink: 0;
        }
        .legend-text {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .legend-item.hidden {
            opacity: 0.5;
            text-decoration: line-through;
        }
        .chart-container h2 { margin-bottom: 15px; font-size: 1.3rem; }
        .full-width { grid-column: 1 / -1; }
        .position-list {
            max-height: 400px;
            overflow-y: auto;
        }
        .position-item {
            background: rgba(0, 0, 0, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .position-item.long { border-left: 4px solid #00ff88; }
        .position-item.short { border-left: 4px solid #ff3860; }
        .update-time {
            text-align: center;
            opacity: 0.7;
            margin-top: 20px;
            font-size: 0.9rem;
        }
        .loading {
            text-align: center;
            padding: 40px;
            font-size: 1.2rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦋 Butterfly Strategy Live Tracker</h1>
            <p>Monitoring Trader: <strong>BB</strong> (0x689a...779e)</p>
            <p>Market: Elon Musk Tweets (Dec 9-16, 2025)</p>
        </div>
        
        <div class="status">
            <div class="status-item">
                <div class="status-label">Active Positions</div>
                <div class="status-value" id="activePositions">-</div>
            </div>
            <div class="status-item">
                <div class="status-label">Total Invested</div>
                <div class="status-value" id="totalInvested">$-</div>
            </div>
            <div class="status-item">
                <div class="status-label">Current Value</div>
                <div class="status-value" id="totalExposure">$-</div>
            </div>
            <div class="status-item">
                <div class="status-label">Unrealized PnL</div>
                <div class="status-value" id="unrealizedPnl">$-</div>
            </div>
            <div class="status-item">
                <div class="status-label">Strategy Phase</div>
                <div class="status-value" id="strategyPhase">Loading...</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h2>📊 Net Exposure by Bucket</h2>
                    <div style="background: rgba(255,255,255,0.1); border-radius: 20px; padding: 2px; display: flex;">
                        <button id="btnShares" onclick="setChartMode('shares')" style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 5px 15px; border-radius: 15px; cursor: pointer; margin-right: 5px;">Shares</button>
                        <button id="btnInvested" onclick="setChartMode('invested')" style="background: transparent; border: none; color: rgba(255,255,255,0.6); padding: 5px 15px; border-radius: 15px; cursor: pointer;">$ Invested</button>
                    </div>
                </div>
                <canvas id="butterflyChart"></canvas>
            </div>
            
            <div class="chart-container">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h2 style="margin-bottom: 0;">📈 Position Size Timeline</h2>
                </div>
                <div id="timelineChart" style="width: 100%; height: 100%;"></div>
            </div>
            
            <div class="chart-container full-width">
                <h2>🎯 Live Positions</h2>
                <div class="position-list" id="positionList">
                    <div class="loading">Fetching positions...</div>
                </div>
            </div>
        </div>
        
        <div class="update-time">
            Last Updated: <span id="lastUpdate">-</span>
        </div>
    </div>
    
    <script>
        const POLL_INTERVAL = 2000;
        let butterflyChart;
        let currentChartMode = 'shares'; // 'shares' or 'invested'
        let lastPositions = []; // Store last positions for mode switching
        
        function setChartMode(mode) {
            currentChartMode = mode;
            
            // Update buttons
            const btnShares = document.getElementById('btnShares');
            const btnInvested = document.getElementById('btnInvested');
            
            if (mode === 'shares') {
                btnShares.style.background = 'rgba(255,255,255,0.2)';
                btnShares.style.color = 'white';
                btnInvested.style.background = 'transparent';
                btnInvested.style.color = 'rgba(255,255,255,0.6)';
            } else {
                btnInvested.style.background = 'rgba(255,255,255,0.2)';
                btnInvested.style.color = 'white';
                btnShares.style.background = 'transparent';
                btnShares.style.color = 'rgba(255,255,255,0.6)';
            }
            
            // Update chart if we have data
            if (lastPositions.length > 0) {
                updateButterflyChart(lastPositions);
            }
        }
        
        function initCharts() {
            const butterflyCtx = document.getElementById('butterflyChart').getContext('2d');
            butterflyChart = new Chart(butterflyCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Net Exposure (Shares)',
                        data: [],
                        backgroundColor: [],
                        borderColor: '#fff',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { beginAtZero: true, ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                        x: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } }
                    },
                    plugins: { legend: { labels: { color: '#fff' } } }
                }
            });
            
            // Initialize Plotly Timeline
            Plotly.newPlot('timelineChart', [], {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#fff' },
                xaxis: { 
                    gridcolor: 'rgba(255,255,255,0.1)',
                    zerolinecolor: 'rgba(255,255,255,0.1)'
                },
                yaxis: { 
                    gridcolor: 'rgba(255,255,255,0.1)',
                    zerolinecolor: 'rgba(255,255,255,0.1)'
                },
                margin: { t: 10, l: 40, r: 20, b: 40 },
                showlegend: true,
                legend: {
                    x: 1.02,
                    y: 1,
                    bgcolor: 'rgba(0,0,0,0.2)',
                    bordercolor: 'rgba(255,255,255,0.1)',
                    borderwidth: 1
                }
            }, { responsive: true, displayModeBar: true });
        }
        
        async function fetchPositions() {
            try {
                const response = await fetch('/api/current');
                const data = await response.json();
                console.log('Fetched positions:', data);
                if (data.positions && data.positions.length > 0) {
                    updateUI(data.positions);
                } else {
                    document.getElementById('strategyPhase').textContent = 'NO POSITIONS';
                    document.getElementById('positionList').innerHTML = '<div class="loading">No positions found. Trader may not have entered this market yet.</div>';
                }
            } catch (error) {
                console.error('Error:', error);
                document.getElementById('strategyPhase').textContent = 'ERROR';
            }
        }
        
        async function fetchTimeline() {
            try {
                const response = await fetch('/api/timeline');
                const data = await response.json();
                if (data.timestamps) updateTimelineChart(data);
            } catch (error) {
                console.error('Error:', error);
            }
        }
        
        function updateUI(positions) {
            lastPositions = positions; // Store for mode switching
            document.getElementById('activePositions').textContent = positions.length;
            
            const totalValue = positions.reduce((sum, pos) => sum + pos.currentValue, 0);
            document.getElementById('totalExposure').textContent = `$${totalValue.toFixed(2)}`;
            
            const totalPnl = positions.reduce((sum, pos) => sum + pos.cashPnl, 0);
            document.getElementById('unrealizedPnl').textContent = `$${totalPnl.toFixed(2)}`;
            
            // Calculate total invested from the invested field
            const totalInvested = positions.reduce((sum, pos) => sum + (pos.invested || 0), 0);
            document.getElementById('totalInvested').textContent = `$${totalInvested.toFixed(2)}`;
            
            const hasLowNo = positions.some(p => p.outcome === 'No' && (p.title.includes('20-') || p.title.includes('100-')));
            const hasHighYes = positions.some(p => p.outcome === 'Yes' && (p.title.includes('200-') || p.title.includes('140-')));
            
            let phase = 'UNKNOWN';
            if (hasLowNo && !hasHighYes) phase = 'PHASE 1: WINGS';
            else if (hasLowNo && hasHighYes) phase = 'PHASE 3: BODY';
            document.getElementById('strategyPhase').textContent = phase;
            
            updateButterflyChart(positions);
            updatePositionList(positions);
            document.getElementById('lastUpdate').textContent = new Date().toLocaleString();
        }
        
        function updateButterflyChart(positions) {
            const bucketMap = {};
            positions.forEach(pos => {
                const bucket = pos.title.match(/(\\d+-\\d+|\\d+\\+)/)?.[0] || pos.title;
                
                let value = 0;
                if (currentChartMode === 'shares') {
                    // Net exposure in shares
                    value = pos.outcome === 'Yes' ? pos.size : -pos.size;
                } else {
                    // Invested amount (always positive for long, negative for short to show direction)
                    // Or should invested always be positive? 
                    // Let's keep the directionality: Long = +Invested, Short = -Invested
                    const invested = pos.invested || 0;
                    value = pos.outcome === 'Yes' ? invested : -invested;
                }
                
                bucketMap[bucket] = (bucketMap[bucket] || 0) + value;
            });
            
            const sorted = Object.entries(bucketMap).sort((a, b) => {
                const getNum = str => parseInt(str.split('-')[0]) || 1000;
                return getNum(a[0]) - getNum(b[0]);
            });
            
            butterflyChart.data.labels = sorted.map(([bucket]) => bucket);
            butterflyChart.data.datasets[0].data = sorted.map(([, val]) => val);
            butterflyChart.data.datasets[0].label = currentChartMode === 'shares' ? 'Net Exposure (Shares)' : 'Net Invested ($)';
            butterflyChart.data.datasets[0].backgroundColor = sorted.map(([, val]) => 
                val >= 0 ? 'rgba(0, 255, 136, 0.6)' : 'rgba(255, 56, 96, 0.6)'
            );
            butterflyChart.update();
        }
        
        function updateTimelineChart(data) {
            if (!data.timestamps || data.timestamps.length === 0) return;
            
            const allBuckets = Object.keys(data.buckets).sort((a, b) => {
                const getNum = str => parseInt(str.split('-')[0]) || 1000;
                return getNum(a) - getNum(b);
            });
            
            // Get existing visibility states
            const graphDiv = document.getElementById('timelineChart');
            const visibilityMap = {};
            if (graphDiv && graphDiv.data) {
                graphDiv.data.forEach(trace => {
                    visibilityMap[trace.name] = trace.visible;
                });
            }

            const traces = allBuckets.map((bucket, idx) => {
                // Calculate color based on index (Blue -> Green -> Red)
                // Map index 0..N to Hue 240..0
                const total = allBuckets.length;
                const hue = total > 1 ? 240 - (idx / (total - 1)) * 240 : 240;
                
                const trace = {
                    x: data.timestamps,
                    y: data.buckets[bucket],
                    name: bucket,
                    type: 'scatter',
                    mode: 'lines',
                    line: {
                        color: `hsl(${hue}, 70%, 50%)`,
                        width: 2
                    }
                };

                // Restore visibility state if it exists
                if (visibilityMap[bucket] !== undefined) {
                    trace.visible = visibilityMap[bucket];
                }

                return trace;
            });
            
            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#fff' },
                xaxis: { 
                    gridcolor: 'rgba(255,255,255,0.1)',
                    zerolinecolor: 'rgba(255,255,255,0.1)',
                    title: 'Time'
                },
                yaxis: { 
                    gridcolor: 'rgba(255,255,255,0.1)',
                    zerolinecolor: 'rgba(255,255,255,0.1)',
                    title: 'Exposure'
                },
                margin: { t: 10, l: 40, r: 20, b: 40 },
                showlegend: true,
                legend: {
                    x: 1.02,
                    y: 1,
                    bgcolor: 'rgba(0,0,0,0.2)',
                    bordercolor: 'rgba(255,255,255,0.1)',
                    borderwidth: 1
                },
                datarevision: new Date().getTime() // Force update
            };
            
            Plotly.react('timelineChart', traces, layout);
        }
        
        function updatePositionList(positions) {
            const list = document.getElementById('positionList');
            list.innerHTML = '';
            
            positions.sort((a, b) => Math.abs(b.size) - Math.abs(a.size)).forEach(pos => {
                const bucket = pos.title.match(/(\\d+-\\d+|\\d+\\+)/)?.[0] || pos.title;
                const isLong = pos.outcome === 'Yes';
                const invested = pos.invested || 0;
                
                const item = document.createElement('div');
                item.className = `position-item ${isLong ? 'long' : 'short'}`;
                item.innerHTML = `
                    <div>
                        <strong>${bucket}</strong> - ${pos.outcome}
                        <br><small>${pos.size.toFixed(0)} shares @ $${pos.avgPrice.toFixed(3)}</small>
                        <br><small style="opacity: 0.8;">💰 Invested: $${invested.toFixed(2)}</small>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.2rem;">${pos.cashPnl >= 0 ? '+' : ''}$${pos.cashPnl.toFixed(2)}</div>
                        <small>${pos.percentPnl >= 0 ? '+' : ''}${pos.percentPnl.toFixed(1)}%</small>
                        <br><small style="opacity: 0.7;">Value: $${pos.currentValue.toFixed(2)}</small>
                    </div>
                `;
                list.appendChild(item);
            });
        }
        
        initCharts();
        fetchPositions();
        fetchTimeline();
        setInterval(fetchPositions, POLL_INTERVAL);
        setInterval(fetchTimeline, POLL_INTERVAL * 5);
    </script>
</body>
</html>
"""

USER_ADDRESS = '0xBE50Ea246B34b58ef36043aa34CAA8b3c1F2D592'
TARGET_SLUG = 'elon-musk-of-tweets-december-9-december-16'
API_ENDPOINT = 'https://data-api.polymarket.com/positions'
POLL_INTERVAL = 5  # seconds

# Global storage
position_history = []
current_positions = []
last_update = None

def fetch_positions():
    """Fetch positions from Polymarket API with pagination"""
    try:
        all_positions = []
        offset = 0
        batch_size = 100
        
        # Fetch all positions with pagination
        while offset < 1000:  # Safety limit
            params = {
                'user': USER_ADDRESS,
                'limit': batch_size,
                'offset': offset
            }
            response = requests.get(API_ENDPOINT, params=params, timeout=10)
            response.raise_for_status()
            batch = response.json()
            
            if not batch:
                break
            
            all_positions.extend(batch)
            
            if len(batch) < batch_size:
                break
                
            offset += batch_size
        
        # Filter for target market
        positions = [pos for pos in all_positions if pos.get('eventSlug') == TARGET_SLUG]
        return positions
    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []

def process_positions(positions):
    """Process positions and store in history"""
    global position_history, current_positions, last_update
    
    timestamp = datetime.now().isoformat()
    
    # Calculate net exposure per bucket
    bucket_exposure = {}
    for pos in positions:
        title = pos.get('title', '')
        # Extract bucket (e.g., "200-219")
        import re
        match = re.search(r'(\d+-\d+|\d+\+)', title)
        bucket = match.group(1) if match else title
        
        outcome = pos.get('outcome', 'Yes')
        size = pos.get('size', 0)
        
        # Yes = Long (positive), No = Short (negative)
        exposure = size if outcome == 'Yes' else -size
        
        if bucket not in bucket_exposure:
            bucket_exposure[bucket] = {
                'exposure': 0,
                'yes_size': 0,
                'no_size': 0,
                'yes_value': 0,
                'no_value': 0,
                'pnl': 0
            }
        
        bucket_exposure[bucket]['exposure'] += exposure
        if outcome == 'Yes':
            bucket_exposure[bucket]['yes_size'] += size
            bucket_exposure[bucket]['yes_value'] += pos.get('currentValue', 0)
        else:
            bucket_exposure[bucket]['no_size'] += size
            bucket_exposure[bucket]['no_value'] += pos.get('currentValue', 0)
        bucket_exposure[bucket]['pnl'] += pos.get('cashPnl', 0)
    
    # Store snapshot
    total_value = sum(p.get('currentValue', 0) for p in positions)
    total_pnl = sum(p.get('cashPnl', 0) for p in positions)
    
    snapshot = {
        'timestamp': timestamp,
        'buckets': bucket_exposure,
        'total_positions': len(positions),
        'total_value': total_value,
        'total_pnl': total_pnl
    }
    
    position_history.append(snapshot)
    
    # Keep last 20000 snapshots in memory (approx 27 hours at 5s interval)
    if len(position_history) > 20000:
        position_history.pop(0)
    
    # Save to database for persistence
    save_snapshot_to_db(timestamp, positions, bucket_exposure, total_value, total_pnl)
    
    current_positions = positions
    last_update = timestamp
    
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Updated: {len(positions)} positions, Total PnL: ${total_pnl:.2f} [DB saved]")

def poll_loop():
    """Background polling loop"""
    while True:
        positions = fetch_positions()
        if positions:
            process_positions(positions)
        time.sleep(POLL_INTERVAL)

@app.route('/api/current')
def get_current():
    """Get current positions with calculated fields"""
    processed = []
    for pos in current_positions:
        size = float(pos.get('size', 0))
        current_value = float(pos.get('currentValue', 0))
        cash_pnl = float(pos.get('cashPnl', 0))
        
        # Calculate invested amount from current value and PnL
        # invested = current_value - cash_pnl
        invested = current_value - cash_pnl
        
        # Calculate average price from invested amount
        avg_price = (invested / size) if size > 0 else 0
        
        # Fallback to API value if available
        api_avg_price = float(pos.get('averagePrice', 0))
        if api_avg_price > 0:
            avg_price = api_avg_price
            invested = size * avg_price
        
        processed.append({
            'title': pos.get('title', ''),
            'outcome': pos.get('outcome', 'Yes'),
            'size': size,
            'avgPrice': avg_price,
            'invested': invested,
            'currentValue': current_value,
            'cashPnl': cash_pnl,
            'percentPnl': float(pos.get('percentPnl', 0))
        })
    
    return jsonify({
        'positions': processed,
        'last_update': last_update
    })

@app.route('/api/history')
def get_history():
    """Get position history"""
    return jsonify({
        'history': position_history,
        'last_update': last_update
    })

@app.route('/api/butterfly')
def get_butterfly():
    """Get butterfly structure (net exposure per bucket)"""
    if not position_history:
        return jsonify({'error': 'No data available'}), 404
    
    latest = position_history[-1]
    
    # Sort buckets numerically
    def get_sort_key(bucket):
        if '+' in bucket:
            return 1000
        try:
            return int(bucket.split('-')[0])
        except:
            return 0
    
    sorted_buckets = sorted(latest['buckets'].items(), key=lambda x: get_sort_key(x[0]))
    
    return jsonify({
        'buckets': dict(sorted_buckets),
        'timestamp': latest['timestamp'],
        'total_positions': latest['total_positions'],
        'total_value': latest['total_value'],
        'total_pnl': latest['total_pnl']
    })

@app.route('/api/timeline')
def get_timeline():
    """Get timeline data for charts"""
    if not position_history:
        return jsonify({'error': 'No data available'}), 404
    
    # Downsample if too many points to prevent browser lag
    MAX_POINTS = 1000
    data_to_send = position_history
    if len(position_history) > MAX_POINTS:
        step = len(position_history) // MAX_POINTS
        # Ensure we include the last point
        data_to_send = position_history[::step]
        if data_to_send[-1] != position_history[-1]:
            data_to_send.append(position_history[-1])
    
    # Extract all unique buckets
    all_buckets = set()
    for snapshot in data_to_send:
        all_buckets.update(snapshot['buckets'].keys())
    
    # Build timeline data
    timeline = {
        'timestamps': [s['timestamp'] for s in data_to_send],
        'buckets': {}
    }
    
    for bucket in all_buckets:
        timeline['buckets'][bucket] = [
            s['buckets'].get(bucket, {}).get('exposure', 0) 
            for s in data_to_send
        ]
    
    return jsonify(timeline)

@app.route('/')
def index():
    """Serve the main dashboard HTML"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/debug')
def debug():
    """Debug endpoint to see raw data"""
    return jsonify({
        'total_positions': len(current_positions),
        'history_snapshots': len(position_history),
        'sample_position': current_positions[0] if current_positions else None,
        'latest_snapshot': position_history[-1] if position_history else None
    })

@app.route('/api/db/stats')
def db_stats():
    """Get database statistics"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM snapshots')
        total_snapshots = cursor.fetchone()[0]
        
        cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM snapshots')
        min_time, max_time = cursor.fetchone()
        
        cursor.execute('SELECT COUNT(DISTINCT bucket) FROM bucket_history')
        unique_buckets = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_snapshots': total_snapshots,
            'first_snapshot': min_time,
            'last_snapshot': max_time,
            'unique_buckets': unique_buckets,
            'database_path': DB_PATH
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting Butterfly Tracker Backend...")
    print(f"Monitoring: {USER_ADDRESS}")
    print(f"Market: {TARGET_SLUG}")
    print(f"Poll Interval: {POLL_INTERVAL}s")
    
    # Initialize database
    init_db()
    
    # Load previous history from database
    print("Loading history from database...")
    loaded_history = load_history_from_db(limit=20000)
    if loaded_history:
        position_history.extend(loaded_history)
        print(f"✅ Loaded {len(loaded_history)} snapshots from database")
    else:
        print("No previous history found")
    
    print("\n🦋 Dashboard available at: http://localhost:5000")
    
    # Start background polling thread
    polling_thread = threading.Thread(target=poll_loop, daemon=True)
    polling_thread.start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)
