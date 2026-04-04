param(
    [switch]$Force
)

$repoRoot = Split-Path -Parent $PSScriptRoot

$templatePairs = @(
    @{
        Source = "backend\Req_codeMapping\.env.example"
        Target = "backend\Req_codeMapping\.env"
    },
    @{
        Source = "backend\JIRA_tokenFetching\.env.example"
        Target = "backend\JIRA_tokenFetching\.env"
    },
    @{
        Source = "Manager_Dashboard\.env.example"
        Target = "Manager_Dashboard\.env"
    }
)

Write-Host "DevHouse26 local bootstrap"
Write-Host "Repo root: $repoRoot"
Write-Host ""

foreach ($pair in $templatePairs) {
    $sourcePath = Join-Path $repoRoot $pair.Source
    $targetPath = Join-Path $repoRoot $pair.Target

    if (-not (Test-Path -LiteralPath $sourcePath)) {
        Write-Warning "Template not found: $sourcePath"
        continue
    }

    if ((Test-Path -LiteralPath $targetPath) -and -not $Force) {
        Write-Host "[skip] $($pair.Target) already exists"
        continue
    }

    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    Write-Host "[ok]   created $($pair.Target)"
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Fill backend\Req_codeMapping\.env with Supabase values."
Write-Host "2. Fill Manager_Dashboard\.env with VITE_API_BASE_URL=http://127.0.0.1:8000."
Write-Host "3. Fill backend\JIRA_tokenFetching\.env only if you plan to demo Jira sync."
Write-Host "4. Apply the SQL files listed in docs\LOCAL_SETUP.md."
Write-Host "5. Start the backend on http://127.0.0.1:8000 and check /api/health."
Write-Host "6. Start the dashboard on http://127.0.0.1:5173."
Write-Host "7. Use docs\FIRST_10_MINUTES.md for the evaluator path."
