# Start Python CrewAI Agents for IMS Agent Backend
# Run this AFTER Redis is running

Write-Host "🤖 Starting Python CrewAI Agents..." -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
$pythonPath = Get-Command python -ErrorAction SilentlyContinue

if (-not $pythonPath) {
    Write-Host "❌ Python is not installed!" -ForegroundColor Red
    Write-Host "   Please install Python 3.8+ from https://www.python.org/" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host "✅ Python found: $($pythonPath.Source)" -ForegroundColor Green
$pythonVersion = python --version
Write-Host "   Version: $pythonVersion" -ForegroundColor Gray
Write-Host ""

# Check if Redis is running
Write-Host "🧪 Checking Redis connection..." -ForegroundColor Cyan
try {
    $redisPing = redis-cli ping 2>$null
    if ($redisPing -ne "PONG") {
        Write-Host "❌ Redis is not running!" -ForegroundColor Red
        Write-Host "   Please start Redis first: .\start-redis.ps1" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    Write-Host "✅ Redis is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Redis is not running or redis-cli not found!" -ForegroundColor Red
    Write-Host "   Please start Redis first: .\start-redis.ps1" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
Write-Host ""

# Navigate to agents directory
$agentsDir = "agents\crewai"
if (-not (Test-Path $agentsDir)) {
    Write-Host "❌ Agents directory not found: $agentsDir" -ForegroundColor Red
    exit 1
}

Set-Location $agentsDir

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Cyan
Write-Host "   (This may take a minute on first run)" -ForegroundColor Gray
Write-Host ""

$requirements = @"
crewai>=0.1.0
redis>=5.0.0
python-dotenv>=1.0.0
requests>=2.31.0
"@

$requirements | Out-File -FilePath "requirements.txt" -Encoding utf8
pip install -r requirements.txt --quiet

Write-Host "✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Start the CrewAI Manager Service
Write-Host "🚀 Starting CrewAI Manager Service..." -ForegroundColor Cyan
Write-Host "   This will run Python agents and listen for tasks from Node.js" -ForegroundColor Gray
Write-Host ""
Write-Host "📡 Agents will communicate via Redis Streams:" -ForegroundColor Cyan
Write-Host "   - Incoming tasks: stream:crewai:tasks:*" -ForegroundColor Gray
Write-Host "   - Outgoing results: stream:crewai:responses" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop the agents" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

# Start the service
python CrewAIManagerService.py

