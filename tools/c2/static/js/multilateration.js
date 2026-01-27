/**
 * Trilateration visualization for ESPILON C2
 * Renders scanner positions and target location on a 2D canvas
 */

class TrilaterationViz {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');

        // Coordinate system bounds (auto-adjusted based on data)
        this.bounds = { minX: -2, maxX: 15, minY: -2, maxY: 15 };
        this.padding = 40;

        // Data
        this.scanners = [];
        this.target = null;

        // Colors
        this.colors = {
            background: '#010409',
            grid: '#21262d',
            gridText: '#484f58',
            scanner: '#58a6ff',
            scannerCircle: 'rgba(88, 166, 255, 0.15)',
            target: '#f85149',
            targetGlow: 'rgba(248, 81, 73, 0.3)',
            text: '#c9d1d9'
        };

        this.resize();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width - 32;  // Account for padding
        this.canvas.height = 500;
        this.draw();
    }

    // Convert world coordinates to canvas coordinates
    worldToCanvas(x, y) {
        const w = this.canvas.width - this.padding * 2;
        const h = this.canvas.height - this.padding * 2;
        const rangeX = this.bounds.maxX - this.bounds.minX;
        const rangeY = this.bounds.maxY - this.bounds.minY;

        return {
            x: this.padding + ((x - this.bounds.minX) / rangeX) * w,
            y: this.canvas.height - this.padding - ((y - this.bounds.minY) / rangeY) * h
        };
    }

    // Convert distance to canvas pixels
    distanceToPixels(distance) {
        const w = this.canvas.width - this.padding * 2;
        const rangeX = this.bounds.maxX - this.bounds.minX;
        return (distance / rangeX) * w;
    }

    updateBounds() {
        if (this.scanners.length === 0) {
            this.bounds = { minX: -2, maxX: 15, minY: -2, maxY: 15 };
            return;
        }

        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        for (const s of this.scanners) {
            minX = Math.min(minX, s.position.x);
            maxX = Math.max(maxX, s.position.x);
            minY = Math.min(minY, s.position.y);
            maxY = Math.max(maxY, s.position.y);
        }

        if (this.target) {
            minX = Math.min(minX, this.target.x);
            maxX = Math.max(maxX, this.target.x);
            minY = Math.min(minY, this.target.y);
            maxY = Math.max(maxY, this.target.y);
        }

        // Add margin
        const marginX = Math.max(2, (maxX - minX) * 0.2);
        const marginY = Math.max(2, (maxY - minY) * 0.2);

        this.bounds = {
            minX: minX - marginX,
            maxX: maxX + marginX,
            minY: minY - marginY,
            maxY: maxY + marginY
        };
    }

    draw() {
        const ctx = this.ctx;
        const w = this.canvas.width;
        const h = this.canvas.height;

        // Clear
        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        // Draw grid
        this.drawGrid();

        // Draw scanner range circles
        for (const scanner of this.scanners) {
            if (scanner.estimated_distance) {
                this.drawRangeCircle(scanner);
            }
        }

        // Draw scanners
        for (const scanner of this.scanners) {
            this.drawScanner(scanner);
        }

        // Draw target
        if (this.target) {
            this.drawTarget();
        }
    }

    drawGrid() {
        const ctx = this.ctx;
        ctx.strokeStyle = this.colors.grid;
        ctx.lineWidth = 1;
        ctx.font = '10px monospace';
        ctx.fillStyle = this.colors.gridText;

        // Determine grid spacing
        const rangeX = this.bounds.maxX - this.bounds.minX;
        const rangeY = this.bounds.maxY - this.bounds.minY;
        const gridStep = Math.pow(10, Math.floor(Math.log10(Math.max(rangeX, rangeY) / 5)));

        // Vertical lines
        for (let x = Math.ceil(this.bounds.minX / gridStep) * gridStep; x <= this.bounds.maxX; x += gridStep) {
            const p = this.worldToCanvas(x, 0);
            ctx.beginPath();
            ctx.moveTo(p.x, this.padding);
            ctx.lineTo(p.x, this.canvas.height - this.padding);
            ctx.stroke();
            ctx.fillText(x.toFixed(1), p.x - 10, this.canvas.height - this.padding + 15);
        }

        // Horizontal lines
        for (let y = Math.ceil(this.bounds.minY / gridStep) * gridStep; y <= this.bounds.maxY; y += gridStep) {
            const p = this.worldToCanvas(0, y);
            ctx.beginPath();
            ctx.moveTo(this.padding, p.y);
            ctx.lineTo(this.canvas.width - this.padding, p.y);
            ctx.stroke();
            ctx.fillText(y.toFixed(1), 5, p.y + 4);
        }
    }

    drawRangeCircle(scanner) {
        const ctx = this.ctx;
        const pos = this.worldToCanvas(scanner.position.x, scanner.position.y);
        const radius = this.distanceToPixels(scanner.estimated_distance);

        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
        ctx.strokeStyle = this.colors.scannerCircle;
        ctx.lineWidth = 2;
        ctx.stroke();
    }

    drawScanner(scanner) {
        const ctx = this.ctx;
        const pos = this.worldToCanvas(scanner.position.x, scanner.position.y);

        // Scanner dot
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
        ctx.fillStyle = this.colors.scanner;
        ctx.fill();

        // Label
        ctx.font = '12px monospace';
        ctx.fillStyle = this.colors.text;
        ctx.textAlign = 'center';
        ctx.fillText(scanner.id, pos.x, pos.y - 15);

        // RSSI info
        if (scanner.last_rssi !== null) {
            ctx.font = '10px monospace';
            ctx.fillStyle = this.colors.gridText;
            ctx.fillText(`${scanner.last_rssi} dBm`, pos.x, pos.y + 20);
        }

        ctx.textAlign = 'left';
    }

    drawTarget() {
        const ctx = this.ctx;
        const pos = this.worldToCanvas(this.target.x, this.target.y);

        // Glow effect
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 20, 0, Math.PI * 2);
        ctx.fillStyle = this.colors.targetGlow;
        ctx.fill();

        // Cross marker
        ctx.strokeStyle = this.colors.target;
        ctx.lineWidth = 3;

        ctx.beginPath();
        ctx.moveTo(pos.x - 12, pos.y - 12);
        ctx.lineTo(pos.x + 12, pos.y + 12);
        ctx.stroke();

        ctx.beginPath();
        ctx.moveTo(pos.x + 12, pos.y - 12);
        ctx.lineTo(pos.x - 12, pos.y + 12);
        ctx.stroke();

        // Label
        ctx.font = 'bold 12px monospace';
        ctx.fillStyle = this.colors.target;
        ctx.textAlign = 'center';
        ctx.fillText('TARGET', pos.x, pos.y - 25);
        ctx.textAlign = 'left';
    }

    update(state) {
        this.scanners = state.scanners || [];
        this.target = state.target?.position || null;
        this.updateBounds();
        this.draw();
    }
}

// Initialize visualization
const viz = new TrilaterationViz('trilat-canvas');

// UI Update functions
function updateTargetInfo(target) {
    if (target && target.position) {
        document.getElementById('target-x').textContent = target.position.x.toFixed(2) + ' m';
        document.getElementById('target-y').textContent = target.position.y.toFixed(2) + ' m';
        document.getElementById('target-confidence').textContent = ((target.confidence || 0) * 100).toFixed(0) + '%';
        document.getElementById('target-age').textContent = (target.age_seconds || 0).toFixed(1) + 's ago';
    } else {
        document.getElementById('target-x').textContent = '-';
        document.getElementById('target-y').textContent = '-';
        document.getElementById('target-confidence').textContent = '-';
        document.getElementById('target-age').textContent = '-';
    }
}

function updateScannerList(scanners) {
    const list = document.getElementById('scanner-list');
    document.getElementById('scanner-count').textContent = scanners.length;

    if (scanners.length === 0) {
        list.innerHTML = '<div class="empty" style="padding: 20px;"><p>No scanners active</p></div>';
        return;
    }

    list.innerHTML = scanners.map(s => `
        <div class="scanner-item">
            <div class="scanner-id">${s.id}</div>
            <div class="scanner-details">
                Pos: (${s.position.x}, ${s.position.y}) |
                RSSI: ${s.last_rssi !== null ? s.last_rssi + ' dBm' : '-'} |
                Dist: ${s.estimated_distance !== null ? s.estimated_distance + 'm' : '-'}
            </div>
        </div>
    `).join('');
}

function updateConfig(config) {
    document.getElementById('config-rssi').value = config.rssi_at_1m;
    document.getElementById('config-n').value = config.path_loss_n;
    document.getElementById('config-smooth').value = config.smoothing_window;
}

// API functions
async function fetchState() {
    try {
        const res = await fetch('/api/multilat/state');
        const state = await res.json();

        viz.update(state);
        updateTargetInfo(state.target);
        updateScannerList(state.scanners);

        if (state.config) {
            updateConfig(state.config);
        }
    } catch (e) {
        console.error('Failed to fetch trilateration state:', e);
    }
}

async function saveConfig() {
    const config = {
        rssi_at_1m: parseFloat(document.getElementById('config-rssi').value),
        path_loss_n: parseFloat(document.getElementById('config-n').value),
        smoothing_window: parseInt(document.getElementById('config-smooth').value)
    };

    try {
        await fetch('/api/multilat/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        console.log('Config saved');
    } catch (e) {
        console.error('Failed to save config:', e);
    }
}

async function clearData() {
    try {
        await fetch('/api/multilat/clear', { method: 'POST' });
        fetchState();
    } catch (e) {
        console.error('Failed to clear data:', e);
    }
}

// Start polling
fetchState();
setInterval(fetchState, 2000);
