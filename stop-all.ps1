# Stop all IMS services (Redis, Python agents, Node.js backend)

Write-Host "🛑 Stopping all IMS services..." -ForegroundColor Yellow
Write-Host ""

# Stop Node.js on port 3002
Write-Host "Stopping Node.js backend..." -ForegroundColor Cyan
Get-NetTCPConnection -LocalPort 3002 -ErrorAction SilentlyContinue | 
    Select-Object -ExpandProperty OwningProcess | 
    ForEach-Object { 
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Stopped Node.js (PID: $_)" -ForegroundColor Green
    }

# Stop Python processes
Write-Host "Stopping Python agents..." -ForegroundColor Cyan
Get-Process python -ErrorAction SilentlyContinue | 
    Where-Object { $_.CommandLine -like "*CrewAIManagerService*" } |
    ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Stopped Python agent (PID: $($_.Id))" -ForegroundColor Green
    }

# Stop Redis
Write-Host "Stopping Redis..." -ForegroundColor Cyan
Get-Process redis-server -ErrorAction SilentlyContinue |
    ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Host "✅ Stopped Redis (PID: $($_.Id))" -ForegroundColor Green
    }

Write-Host ""
Write-Host "✅ All services stopped" -ForegroundColor Green
Write-Host ""

