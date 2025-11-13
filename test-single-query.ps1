# ============================================================================
# Quick Single Query Test
# Usage: .\test-single-query.ps1 -Query "Your business question here"
# ============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$Query = "What is the demand forecast for Q3 2025?",
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:3001"
)

Write-Host ""
Write-Host "Testing Query: `"$Query`"" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date

try {
    # Prepare request
    $body = @{
        message = $Query
        conversationId = "test-$(Get-Date -Format 'yyyyMMddHHmmss')"
        userId = "test-user"
    } | ConvertTo-Json
    
    # Send request
    Write-Host "Sending request..." -ForegroundColor Yellow
    $response = Invoke-RestMethod -Uri "$BaseUrl/api/process-message" `
        -Method Post `
        -Body $body `
        -ContentType "application/json" `
        -TimeoutSec 30
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalMilliseconds
    
    Write-Host "[OK] Response received in $([math]::Round($duration))ms" -ForegroundColor Green
    Write-Host ""
    
    # Display results
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "RESULTS" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Intent
    Write-Host "Intent Classification:" -ForegroundColor Yellow
    Write-Host "   Intent: $($response.intent)" -ForegroundColor White
    Write-Host ""
    
    # Agents
    Write-Host "Agents Allocated: $($response.meta.agents.Count)" -ForegroundColor Yellow
    foreach ($agent in $response.meta.agents) {
        $modeIcon = switch ($agent.mode) {
            "real_python_crewai" { "[REAL]" }
            "simulated" { "[SIMULATED]" }
            default { "[MODE: $($agent.mode)]" }
        }
        Write-Host "   $modeIcon - $($agent.agentName)" -ForegroundColor White
        Write-Host "       ID: $($agent.agentId)" -ForegroundColor Gray
        if ($agent.contribution) {
            Write-Host "       Role: $($agent.contribution)" -ForegroundColor Gray
        }
    }
    Write-Host ""
    
    # Acknowledgment
    if ($response.ack) {
        Write-Host "Acknowledgment:" -ForegroundColor Yellow
        Write-Host "   $($response.ack)" -ForegroundColor White
        Write-Host ""
    }
    
    # Plan
    if ($response.plan) {
        Write-Host "Execution Plan:" -ForegroundColor Yellow
        if ($response.plan.declarative -and $response.plan.declarative.Count -gt 0) {
            Write-Host "   Declarative:" -ForegroundColor Gray
            foreach ($item in $response.plan.declarative) {
                Write-Host "      • $item" -ForegroundColor White
            }
        }
        if ($response.plan.procedural -and $response.plan.procedural.Count -gt 0) {
            Write-Host "   Procedural:" -ForegroundColor Gray
            foreach ($item in $response.plan.procedural) {
                Write-Host "      • $item" -ForegroundColor White
            }
        }
        Write-Host ""
    }
    
    # Memory Context
    if ($response.memory -and $response.memory.context) {
        Write-Host "Memory Context:" -ForegroundColor Yellow
        Write-Host "   $($response.memory.context)" -ForegroundColor White
        Write-Host ""
    }
    
    # Metadata
    Write-Host "Metadata:" -ForegroundColor Yellow
    Write-Host "   Turn ID: $($response.turnId)" -ForegroundColor Gray
    Write-Host "   Conversation ID: $($response.conversationId)" -ForegroundColor Gray
    Write-Host "   Timestamp: $($response.timestamp)" -ForegroundColor Gray
    Write-Host "   Total Execution Time: $([math]::Round($duration))ms" -ForegroundColor Gray
    Write-Host ""
    
    # Template info (if available)
    if ($response.meta.template) {
        Write-Host "Template Used:" -ForegroundColor Yellow
        Write-Host "   Name: $($response.meta.template.name)" -ForegroundColor White
        Write-Host "   Domain: $($response.meta.template.domain)" -ForegroundColor Gray
        Write-Host ""
    }
    
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Full JSON (optional)
    Write-Host "Full Response (JSON):" -ForegroundColor DarkGray
    Write-Host ($response | ConvertTo-Json -Depth 10) -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "[OK] Test completed successfully!" -ForegroundColor Green
    
} catch {
    Write-Host ""
    Write-Host "[ERROR] Error occurred:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Is the backend running?" -ForegroundColor Yellow
    Write-Host "Start it with: npm start" -ForegroundColor White
    Write-Host ""
    exit 1
}

