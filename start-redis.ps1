# Start Redis Server for IMS Agent Backend
# Run this script before starting the Node.js backend

Write-Host "🚀 Starting Redis Server for IMS Agent Backend..." -ForegroundColor Cyan
Write-Host ""

# Check if Redis is installed
$redisPath = Get-Command redis-server -ErrorAction SilentlyContinue

if (-not $redisPath) {
    Write-Host "❌ Redis is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Redis using one of these methods:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Chocolatey (Windows Package Manager)" -ForegroundColor White
    Write-Host "  choco install redis-64" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2: Docker" -ForegroundColor White
    Write-Host "  docker run -d -p 6379:6379 --name redis redis:latest" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 3: WSL (Windows Subsystem for Linux)" -ForegroundColor White
    Write-Host "  wsl sudo apt install redis-server && wsl redis-server" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "✅ Redis found at: $($redisPath.Source)" -ForegroundColor Green
Write-Host ""

# Start Redis
Write-Host "📡 Starting Redis on port 6379..." -ForegroundColor Cyan
Start-Process -FilePath "redis-server" -NoNewWindow

# Wait a bit for Redis to start
Start-Sleep -Seconds 2

# Test connection
Write-Host "🧪 Testing Redis connection..." -ForegroundColor Cyan
try {
    $result = redis-cli ping
    if ($result -eq "PONG") {
        Write-Host "✅ Redis is running and responding!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📊 Redis Status:" -ForegroundColor Cyan
        redis-cli info server | Select-String "redis_version"
        Write-Host ""
        Write-Host "✅ Ready for Python agents and Node.js backend" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Redis started but connection test failed" -ForegroundColor Yellow
    Write-Host "   This might be normal - continue anyway" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Start Python agents: .\start-python-agents.ps1" -ForegroundColor White
Write-Host "   2. Start Node.js backend: npm start" -ForegroundColor White
Write-Host ""

