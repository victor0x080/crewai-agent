# Complete Production Startup Script
# Starts Redis → Python Agents → Node.js Backend

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🚀 IMS Agent Backend - Production Startup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check prerequisites
Write-Host "📋 Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

$hasRedis = Get-Command redis-server -ErrorAction SilentlyContinue
$hasPython = Get-Command python -ErrorAction SilentlyContinue
$hasNode = Get-Command node -ErrorAction SilentlyContinue

if (-not $hasRedis) {
    Write-Host "❌ Redis not found" -ForegroundColor Red
    Write-Host "   Install: choco install redis-64" -ForegroundColor Yellow
    exit 1
}

if (-not $hasPython) {
    Write-Host "❌ Python not found" -ForegroundColor Red
    Write-Host "   Install from: https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

if (-not $hasNode) {
    Write-Host "❌ Node.js not found" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All prerequisites installed" -ForegroundColor Green
Write-Host "   - Redis: $($hasRedis.Source)" -ForegroundColor Gray
Write-Host "   - Python: $(python --version)" -ForegroundColor Gray
Write-Host "   - Node.js: $(node --version)" -ForegroundColor Gray
Write-Host ""

# Step 2: Start Redis
Write-Host "📡 Starting Redis..." -ForegroundColor Cyan
Start-Process -FilePath "redis-server" -WindowStyle Minimized
Start-Sleep -Seconds 2

$redisPing = redis-cli ping 2>$null
if ($redisPing -eq "PONG") {
    Write-Host "✅ Redis running on port 6379" -ForegroundColor Green
} else {
    Write-Host "⚠️  Redis may not be ready yet" -ForegroundColor Yellow
}
Write-Host ""

# Step 3: Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Cyan

# Check if requirements.txt exists
if (Test-Path "agents\requirements.txt") {
    Write-Host "   Installing from agents\requirements.txt" -ForegroundColor Gray
    pip install -r agents\requirements.txt --quiet
} else {
    Write-Host "⚠️  agents\requirements.txt not found, creating minimal requirements" -ForegroundColor Yellow
    $requirements = @"
crewai>=0.28.0
redis>=5.0.0
python-dotenv>=1.0.0
requests>=2.31.0
pydantic>=2.0.0
"@
    $requirements | Out-File -FilePath "agents\requirements.txt" -Encoding utf8
    pip install -r agents\requirements.txt --quiet
}

Write-Host "✅ Python dependencies installed" -ForegroundColor Green
Write-Host ""

# Step 4: Start ALL Python agents (Generic + CrewAI) in background
Write-Host "🤖 Starting ALL Python CrewAI agents..." -ForegroundColor Cyan
Write-Host "   - Generic agents (Plan Review, Data Query, Stream Capture, System Call)" -ForegroundColor Gray
Write-Host "   - CrewAI Python agents (Skill, Demand-Gen, Supply, Governance, MCO, RMN)" -ForegroundColor Gray
Write-Host "   - Platform agents (Google, Meta, TikTok, LinkedIn, Pinterest, Snapchat)" -ForegroundColor Gray
Write-Host ""

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Start unified agent manager
Start-Process -FilePath "python" -ArgumentList "agents\start_all_agents.py" -WindowStyle Minimized -RedirectStandardOutput "logs\python-agents.log" -RedirectStandardError "logs\python-agents-error.log"

Start-Sleep -Seconds 5
Write-Host "✅ All Python agents started (54+ agents)" -ForegroundColor Green
Write-Host "   Logs: logs\python-agents.log" -ForegroundColor Gray
Write-Host "   Error logs: logs\python-agents-error.log" -ForegroundColor Gray
Write-Host ""

Write-Host "🚀 Starting Node.js Backend..." -ForegroundColor Cyan
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "System Status:" -ForegroundColor Cyan
Write-Host "  - Redis: ✅ Running (port 6379)" -ForegroundColor Green
Write-Host "  - Python Agents: ✅ Running (background)" -ForegroundColor Green
Write-Host "  - Node.js: 🚀 Starting..." -ForegroundColor Yellow
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 The backend will now start with REAL agents enabled" -ForegroundColor White
Write-Host "   Watch for: 'Mode: REAL Python CrewAI agents'" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop the backend (Redis and Python will keep running)" -ForegroundColor Yellow
Write-Host ""

# Start Node.js backend (this will run in foreground)
npm start

