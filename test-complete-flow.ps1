# ============================================================================
# Complete Backend Test - From Query to Agent Allocation
# Tests: Intent Classification → Template Discovery → Agent Allocation
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🧪 Complete Backend Flow Test" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$baseUrl = "http://localhost:3002"
$testResults = @()

# ============================================================================
# Test Business Queries
# ============================================================================

$businessQueries = @(
    @{
        name = "Forecasting Query"
        query = "What is the demand forecast for Nike Air Max shoes in Q3 2025?"
        expectedTemplate = "Demand Forecasting Workflow"
        expectedAgents = @("fqa", "sda", "ssa", "ira")
        expectedDomain = "supply_chain"
    },
    @{
        name = "Marketing Budget Query"
        query = "How should I allocate my $100,000 marketing budget across Google Ads and Meta?"
        expectedTemplate = "Marketing Budget Optimization"
        expectedAgents = @("marketing-plan", "budget", "elasticity-uplift", "google-ads", "meta-ads")
        expectedDomain = "marketing"
    },
    @{
        name = "Inventory Query"
        query = "Do I have enough inventory for the holiday season demand?"
        expectedTemplate = "Inventory Optimization Workflow"
        expectedAgents = @("inventory-position", "ira", "capacity-leadtime", "opt", "asa")
        expectedDomain = "supply_chain"
    },
    @{
        name = "What-If Scenario"
        query = "What if we reduce prices by 15% for the summer sale?"
        expectedTemplate = "Pricing Impact Analysis"
        expectedAgents = @("elasticity-uplift", "ssa", "ira", "price-promo-guardrail", "asa")
        expectedDomain = "pricing"
    },
    @{
        name = "Campaign Analysis"
        query = "Why did my Black Friday campaign underperform expectations?"
        expectedTemplate = "Campaign Performance Analysis"
        expectedAgents = @("campaign-sku-mapper", "caa", "elasticity-uplift", "asa")
        expectedDomain = "marketing"
    },
    @{
        name = "Sales Pipeline"
        query = "What is the revenue forecast for my sales pipeline next quarter?"
        expectedTemplate = "Sales Pipeline Forecasting"
        expectedAgents = @("sales-pipeline", "fqa", "caa", "asa")
        expectedDomain = "sales"
    },
    @{
        name = "Amazon RMN"
        query = "Should I increase my Amazon Sponsored Products budget?"
        expectedTemplate = "Amazon RMN Campaign Optimization"
        expectedAgents = @("amazon-rmn", "budget", "elasticity-uplift", "asa")
        expectedDomain = "rmn"
    },
    @{
        name = "Root Cause Analysis"
        query = "Why did our revenue drop 20% last month?"
        expectedTemplate = "Root Cause Analysis"
        expectedAgents = @("rca-change-detective", "sda", "caa", "data-gap-mapping", "asa")
        expectedDomain = "analytics"
    },
    @{
        name = "Quick Question"
        query = "What was our total revenue last quarter?"
        expectedTemplate = "Data Retrieval Query"
        expectedAgents = @("sda", "asa")
        expectedDomain = "general"
    },
    @{
        name = "Multi-Platform Comparison"
        query = "Which advertising platform has the best ROI - Google, Meta, or TikTok?"
        expectedTemplate = "Multi-Platform Advertising Analysis"
        expectedAgents = @("google-ads", "meta-ads", "tiktok-ads", "linkedin-ads", "budget", "asa")
        expectedDomain = "marketing"
    }
)

# ============================================================================
# Helper Functions
# ============================================================================

function Test-BackendHealth {
    Write-Host "📡 Checking backend health..." -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/api/health" -Method Get -TimeoutSec 5
        if ($response.status -eq "healthy") {
            Write-Host "   ✅ Backend is healthy" -ForegroundColor Green
            Write-Host "   Services:" -ForegroundColor Gray
            Write-Host "      - Supabase: $($response.supabase)" -ForegroundColor Gray
            Write-Host "      - OpenAI: $($response.openai)" -ForegroundColor Gray
            Write-Host "      - AgentOrchestrator: $($response.agentOrchestrator)" -ForegroundColor Gray
            return $true
        }
    } catch {
        Write-Host "   ❌ Backend not reachable: $_" -ForegroundColor Red
        return $false
    }
}

function Test-Query {
    param($testCase)
    
    Write-Host ""
    Write-Host "─────────────────────────────────────────" -ForegroundColor DarkGray
    Write-Host "🔍 Test: $($testCase.name)" -ForegroundColor Cyan
    Write-Host "   Query: `"$($testCase.query)`"" -ForegroundColor White
    Write-Host ""
    
    $startTime = Get-Date
    
    try {
        # Send request
        $body = @{
            message = $testCase.query
            conversationId = "test-$(Get-Date -Format 'yyyyMMddHHmmss')"
            userId = "test-user"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$baseUrl/api/process-message" `
            -Method Post `
            -Body $body `
            -ContentType "application/json" `
            -TimeoutSec 30
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalMilliseconds
        
        # Parse response
        $intent = $response.intent
        $agents = $response.meta.agents
        $agentIds = $agents | ForEach-Object { $_.agentId }
        $agentMode = $agents[0].mode
        
        Write-Host "   ⏱️  Response Time: $([math]::Round($duration))ms" -ForegroundColor Gray
        Write-Host ""
        Write-Host "   📊 Results:" -ForegroundColor Yellow
        Write-Host "      Intent Classified: $intent" -ForegroundColor White
        Write-Host "      Agents Allocated: $($agentIds.Count)" -ForegroundColor White
        Write-Host "      Execution Mode: $agentMode" -ForegroundColor White
        Write-Host ""
        Write-Host "   🤖 Agents Used:" -ForegroundColor Yellow
        foreach ($agent in $agents) {
            $modeIcon = if ($agent.mode -eq "real_python_crewai") { "✅" } else { "🎭" }
            Write-Host "      $modeIcon $($agent.agentName) ($($agent.agentId))" -ForegroundColor White
        }
        
        # Validation
        Write-Host ""
        Write-Host "   ✓ Validation:" -ForegroundColor Yellow
        
        $allPassed = $true
        
        # Check if expected agents are present
        foreach ($expectedAgent in $testCase.expectedAgents) {
            $found = $agentIds -contains $expectedAgent
            if ($found) {
                Write-Host "      ✅ Agent '$expectedAgent' allocated" -ForegroundColor Green
            } else {
                Write-Host "      ❌ Agent '$expectedAgent' NOT allocated" -ForegroundColor Red
                $allPassed = $false
            }
        }
        
        # Check response structure
        if ($response.ack) {
            Write-Host "      ✅ Acknowledgment present" -ForegroundColor Green
        } else {
            Write-Host "      ⚠️  No acknowledgment" -ForegroundColor Yellow
        }
        
        if ($response.plan) {
            Write-Host "      ✅ Execution plan generated" -ForegroundColor Green
        } else {
            Write-Host "      ⚠️  No execution plan" -ForegroundColor Yellow
        }
        
        # Overall result
        Write-Host ""
        if ($allPassed) {
            Write-Host "   ✅ TEST PASSED" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  TEST PASSED WITH WARNINGS" -ForegroundColor Yellow
        }
        
        return @{
            testName = $testCase.name
            passed = $allPassed
            duration = $duration
            agentsAllocated = $agentIds.Count
            expectedAgents = $testCase.expectedAgents.Count
            mode = $agentMode
            response = $response
        }
        
    } catch {
        Write-Host "   ❌ TEST FAILED" -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
        
        return @{
            testName = $testCase.name
            passed = $false
            duration = 0
            agentsAllocated = 0
            expectedAgents = $testCase.expectedAgents.Count
            mode = "error"
            error = $_.Exception.Message
        }
    }
}

# ============================================================================
# Main Test Execution
# ============================================================================

# Step 1: Check backend health
if (-not (Test-BackendHealth)) {
    Write-Host ""
    Write-Host "❌ Backend is not running. Please start it first:" -ForegroundColor Red
    Write-Host "   cd 'New folder'" -ForegroundColor Yellow
    Write-Host "   npm start" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "🚀 Starting Tests" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# Step 2: Run all tests
foreach ($testCase in $businessQueries) {
    $result = Test-Query -testCase $testCase
    $testResults += $result
    Start-Sleep -Seconds 2  # Pause between tests
}

# ============================================================================
# Test Summary
# ============================================================================

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "📊 Test Summary" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$totalTests = $testResults.Count
$passedTests = ($testResults | Where-Object { $_.passed }).Count
$failedTests = $totalTests - $passedTests
$avgDuration = ($testResults | Measure-Object -Property duration -Average).Average
$totalAgents = ($testResults | Measure-Object -Property agentsAllocated -Sum).Sum

Write-Host "Total Tests:        $totalTests" -ForegroundColor White
Write-Host "Passed:            $passedTests" -ForegroundColor Green
Write-Host "Failed:            $failedTests" -ForegroundColor $(if ($failedTests -eq 0) { "Green" } else { "Red" })
Write-Host "Avg Response Time: $([math]::Round($avgDuration))ms" -ForegroundColor White
Write-Host "Total Agents Used: $totalAgents" -ForegroundColor White
Write-Host ""

# Detailed results table
Write-Host "Detailed Results:" -ForegroundColor Yellow
Write-Host ""
Write-Host "Test Name                     | Agents | Mode              | Time    | Status" -ForegroundColor Gray
Write-Host "─────────────────────────────────────────────────────────────────────────────" -ForegroundColor Gray

foreach ($result in $testResults) {
    $statusIcon = if ($result.passed) { "✅" } else { "❌" }
    $testName = $result.testName.PadRight(28)
    $agents = "$($result.agentsAllocated)/$($result.expectedAgents)".PadRight(6)
    $mode = $result.mode.PadRight(17)
    $time = "$([math]::Round($result.duration))ms".PadRight(7)
    
    $color = if ($result.passed) { "Green" } else { "Red" }
    Write-Host "$testName | $agents | $mode | $time | $statusIcon" -ForegroundColor $color
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan

# Check if using real agents
$realAgentTests = $testResults | Where-Object { $_.mode -eq "real_python_crewai" }
$simulatedTests = $testResults | Where-Object { $_.mode -eq "simulated" }

if ($realAgentTests.Count -gt 0) {
    Write-Host "🎉 Using REAL Python CrewAI agents!" -ForegroundColor Green
    Write-Host "   Real agent tests: $($realAgentTests.Count)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Using SIMULATED agents (Redis/Python not available)" -ForegroundColor Yellow
    Write-Host "   To use real agents:" -ForegroundColor Yellow
    Write-Host "   1. Start Redis: .\start-redis.ps1" -ForegroundColor White
    Write-Host "   2. Start Python agents: python agents\start_all_agents.py" -ForegroundColor White
}

Write-Host ""

# Overall status
if ($failedTests -eq 0) {
    Write-Host "✅ ALL TESTS PASSED!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ SOME TESTS FAILED" -ForegroundColor Red
    exit 1
}

