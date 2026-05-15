param(
    [switch]$SkipFetch,
    [switch]$SkipEnrich,
    [switch]$SkipIngest,
    [switch]$SkipRebuildMarkdowns,
    [switch]$SkipRebuildGoldTruth,
    [switch]$RunBroadEval,
    [switch]$StatsOnly,
    [switch]$ContinueOnError,
    [switch]$ForceFetch,
    [switch]$ForceIngest,
    [int]$SnapshotFreshHours = 24,
    [double]$EvalThreshold = 7.5,
    [string]$TavilyApiKey,
    [string]$TavilyProjectId,
    [string]$LogDir = "logs/sync"
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] [$Level] $Message"
    Write-Host $line
    Add-Content -Path $script:LogFile -Value $line
}

function Invoke-Step {
    param(
        [string]$Name,
        [string]$Command,
        [string[]]$Arguments,
        [switch]$StreamOutput
    )

    $effectiveArguments = $Arguments
    if ($StreamOutput -and $Command -eq "python" -and -not ($Arguments -contains "-u")) {
        $effectiveArguments = @("-u") + $Arguments
    }

    Write-Log "START: $Name" "STEP"
    Write-Log "Command: $Command $($effectiveArguments -join ' ')"

    $start = Get-Date
    if ($StreamOutput) {
        $output = & $Command @effectiveArguments 2>&1 | Tee-Object -FilePath $script:LogFile -Append
    }
    else {
        $output = & $Command @effectiveArguments 2>&1
    }
    $exitCode = $LASTEXITCODE
    $duration = [math]::Round(((Get-Date) - $start).TotalSeconds, 2)

    if ($null -ne $output -and -not $StreamOutput) {
        foreach ($line in $output) {
            Add-Content -Path $script:LogFile -Value $line
            Write-Host $line
        }
    }

    $outputText = ($output | Out-String)

    $result = [pscustomobject]@{
        Step = $Name
        ExitCode = $exitCode
        DurationSec = $duration
        Status = $(if ($exitCode -eq 0) { "OK" } else { "FAILED" })
        OutputText = $outputText
    }

    if ($exitCode -eq 0) {
        Write-Log "DONE: $Name (exit=$exitCode, ${duration}s)" "OK"
        $script:StepResults += $result
        return $result
    }

    Write-Log "FAILED: $Name (exit=$exitCode, ${duration}s)" "ERR"
    $script:StepResults += $result

    if (-not $ContinueOnError) {
        throw "Step failed: $Name"
    }

    return $result
}

function Get-PendingCount {
    param([string]$StatsOutput)

    if ($StatsOutput -match "Pending enrichment:\s+(\d+)") {
        return [int]$matches[1]
    }

    return -1
}

function Test-SnapshotsFresh {
    param([int]$Hours)

    $snapshotRoot = Join-Path $script:RepoRoot "data/api_snapshots"
    if (-not (Test-Path $snapshotRoot)) {
        return $false
    }

    $files = Get-ChildItem -Path $snapshotRoot -Recurse -File -Filter "*.json" -ErrorAction SilentlyContinue
    if (-not $files -or $files.Count -eq 0) {
        return $false
    }

    $latest = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $ageHours = ((Get-Date) - $latest.LastWriteTime).TotalHours
    Write-Log "Latest snapshot file: $($latest.FullName)"
    Write-Log "Snapshot age: $([math]::Round($ageHours, 2)) hours"

    return ($ageHours -lt $Hours)
}

function Get-IngestStatus {
    $output = & python ingestion/ingest_status.py 2>&1
    $exitCode = $LASTEXITCODE

    if ($null -ne $output) {
        foreach ($line in $output) {
            Add-Content -Path $script:LogFile -Value $line
        }
    }

    if ($exitCode -ne 0) {
        Write-Log "Could not compute ingest status; defaulting to conservative ingest behavior" "WARN"
        return $null
    }

    $jsonText = ($output | Out-String)
    $jsonStart = $jsonText.IndexOf('{')
    if ($jsonStart -ge 0) {
        $jsonText = $jsonText.Substring($jsonStart)
    }
    try {
        return $jsonText | ConvertFrom-Json
    }
    catch {
        Write-Log "Failed to parse ingest status JSON; defaulting to conservative ingest behavior" "WARN"
        return $null
    }
}

$script:RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $script:RepoRoot

if ($TavilyApiKey) {
    $env:TAVILY_API_KEY = $TavilyApiKey
}
if ($TavilyProjectId) {
    $env:TAVILY_PROJECT_ID = $TavilyProjectId
}

# Avoid Windows cp1252 write failures from Unicode output in child Python scripts.
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$script:LogFile = Join-Path $LogDir "sync_$timestamp.log"
$script:StepResults = @()

"LinkedIn sync run log - $timestamp" | Set-Content -Path $script:LogFile

Write-Log "Repository root: $script:RepoRoot"
Write-Log "PowerShell: $($PSVersionTable.PSVersion)"
Write-Log "ContinueOnError: $ContinueOnError"
Write-Log "StatsOnly: $StatsOnly"
Write-Log "SkipFetch: $SkipFetch, SkipEnrich: $SkipEnrich, SkipIngest: $SkipIngest"
Write-Log "SkipRebuildMarkdowns: $SkipRebuildMarkdowns, SkipRebuildGoldTruth: $SkipRebuildGoldTruth"
Write-Log "RunBroadEval: $RunBroadEval, EvalThreshold: $EvalThreshold/10"
Write-Log "ForceFetch: $ForceFetch, ForceIngest: $ForceIngest"
Write-Log "SnapshotFreshHours: $SnapshotFreshHours"
if ($TavilyProjectId) {
    Write-Log "TavilyProjectId provided for this run"
}

try {
    Invoke-Step -Name "Pre-check: Python version" -Command "python" -Arguments @("--version") | Out-Null

    $tavilyDiag = Invoke-Step -Name "Tavily usage diagnostics" -Command "python" -Arguments @("enrichment/tavily_usage_status.py")
    if ($tavilyDiag.ExitCode -ne 0 -and -not $ContinueOnError) {
        throw "Cannot continue without Tavily diagnostics"
    }

    $companiesStats = Invoke-Step -Name "Companies enrichment stats" -Command "python" -Arguments @("enrichment/enrich_companies_api.py", "--stats")
    $connectionsStats = Invoke-Step -Name "Connections enrichment stats" -Command "python" -Arguments @("enrichment/enrich_connections_api.py", "--stats")

    $pendingCompanies = Get-PendingCount -StatsOutput $companiesStats.OutputText
    $pendingConnections = Get-PendingCount -StatsOutput $connectionsStats.OutputText

    if ($pendingCompanies -ge 0) {
        Write-Log "Pending companies parsed from stats: $pendingCompanies"
    }
    else {
        Write-Log "Could not parse pending companies from stats output" "WARN"
    }

    if ($pendingConnections -ge 0) {
        Write-Log "Pending connections parsed from stats: $pendingConnections"
    }
    else {
        Write-Log "Could not parse pending connections from stats output" "WARN"
    }

    if ($StatsOnly) {
        Invoke-Step -Name "ChromaDB stats" -Command "python" -Arguments @("ingest.py", "--stats") | Out-Null
    }
    else {
        $didFetch = $false
        $didEnrich = $false
        $ingestStatus = $null

        $pendingTotal = 0
        if ($pendingCompanies -gt 0) { $pendingTotal += $pendingCompanies }
        if ($pendingConnections -gt 0) { $pendingTotal += $pendingConnections }

        if ($pendingTotal -eq 0) {
            Write-Log "Checking whether local parsed chunks already need ingest before considering fetch"
            $ingestStatus = Get-IngestStatus
            if ($ingestStatus -and $ingestStatus.collections) {
                foreach ($prop in $ingestStatus.collections.PSObject.Properties) {
                    $name = $prop.Name
                    $row = $prop.Value
                    Write-Log "Ingest status [$name]: parsed=$($row.parsed), current=$($row.current), missing=$($row.missing), changed=$($row.changed), unchanged=$($row.unchanged)"
                }
            }
        }

        if ($SkipFetch) {
            Write-Log "Skipping fetch stage by request" "WARN"
        }
        elseif (-not $ForceFetch -and $ingestStatus -and $ingestStatus.ingest_needed) {
            Write-Log "Skipping fetch: local parsed chunk differences already require ingest; use -ForceFetch to refresh snapshots first" "WARN"
        }
        elseif (-not $ForceFetch -and (Test-SnapshotsFresh -Hours $SnapshotFreshHours)) {
            Write-Log "Skipping fetch: snapshots are fresh (< $SnapshotFreshHours hours)" "WARN"
        }
        else {
            $fetchResult = Invoke-Step -Name "Fetch snapshots" -Command "python" -Arguments @("ingest.py", "--fetch-only")
            if ($fetchResult.ExitCode -eq 0) {
                $didFetch = $true
            }
        }

        if ($SkipEnrich) {
            Write-Log "Skipping enrich stage by request" "WARN"
        }
        elseif ($pendingTotal -eq 0 -and $pendingCompanies -ge 0 -and $pendingConnections -ge 0) {
            Write-Log "Skipping enrich: no pending companies/connections" "WARN"
        }
        else {
            $enrichResult = Invoke-Step -Name "Enrich pending entities" -Command "python" -Arguments @("ingest.py", "--enrich-only")
            if ($enrichResult.ExitCode -eq 0) {
                $didEnrich = $true
            }
        }

        if ($SkipRebuildMarkdowns) {
            Write-Log "Skipping rebuild enriched markdowns by request" "WARN"
        }
        elseif ($didEnrich) {
            Invoke-Step -Name "Rebuild enriched markdowns" -Command "python" -Arguments @("scripts/rebuild_enriched_markdowns.py", "--yes") | Out-Null
        }
        else {
            Write-Log "Skipping rebuild enriched markdowns: no enrichment changes" "WARN"
        }

        if (-not $didFetch -and -not $didEnrich -and -not $ingestStatus) {
            Write-Log "Checking whether parsed chunks differ from stored chunks before deciding ingest"
            $ingestStatus = Get-IngestStatus
            if ($ingestStatus -and $ingestStatus.collections) {
                foreach ($prop in $ingestStatus.collections.PSObject.Properties) {
                    $name = $prop.Name
                    $row = $prop.Value
                    Write-Log "Ingest status [$name]: parsed=$($row.parsed), current=$($row.current), missing=$($row.missing), changed=$($row.changed), unchanged=$($row.unchanged)"
                }
            }
        }

        if ($SkipIngest) {
            Write-Log "Skipping ingest stage by request" "WARN"
        }
        elseif (-not $ForceIngest -and -not $didFetch -and -not $didEnrich -and $ingestStatus -and -not $ingestStatus.ingest_needed) {
            Write-Log "Skipping ingest: no upstream changes (fetch/enrich skipped)" "WARN"
        }
        else {
            Invoke-Step -Name "Ingest into ChromaDB" -Command "python" -Arguments @("ingest.py", "--ingest-only") -StreamOutput | Out-Null
        }

        Invoke-Step -Name "Post-run ChromaDB stats" -Command "python" -Arguments @("ingest.py", "--stats") | Out-Null

        if ($SkipRebuildGoldTruth) {
            Write-Log "Skipping rebuild gold truth by request" "WARN"
        }
        else {
            Invoke-Step -Name "Rebuild gold truth sets" -Command "python" -Arguments @("evaluation/rebuild_gold_truth_sets_strict.py") | Out-Null
        }

        if ($RunBroadEval) {
            $evalResult = Invoke-Step -Name "Run broad recall evaluation" -Command "python" -Arguments @("evaluation/eval_broad_recall.py")
            if ($evalResult.ExitCode -eq 0) {
                $scorePattern = "Average.*?([0-9]+\.[0-9]+)"
                if ($evalResult.OutputText -match $scorePattern) {
                    $avgScore = [double]$matches[1]
                    Write-Log "Broad recall evaluation score: $avgScore/10 (threshold: $EvalThreshold/10)" "INFO"
                    if ($avgScore -lt $EvalThreshold) {
                        Write-Log "FAILED: Broad recall score ($avgScore) below threshold ($EvalThreshold)" "ERR"
                        throw "Evaluation threshold not met: $avgScore < $EvalThreshold"
                    }
                }
            }
        }
        else {
            Write-Log "Skipping broad recall evaluation; use -RunBroadEval to enable" "WARN"
        }
    }
}
catch {
    Write-Log "Pipeline aborted: $($_.Exception.Message)" "ERR"
}
finally {
    Write-Log "Execution summary:"
    foreach ($row in $script:StepResults) {
        Write-Log " - $($row.Step): $($row.Status), exit=$($row.ExitCode), duration=$($row.DurationSec)s"
    }

    $failedCount = ($script:StepResults | Where-Object { $_.Status -eq "FAILED" } | Measure-Object).Count
    if ($failedCount -gt 0) {
        Write-Log "Run completed with $failedCount failed step(s)." "ERR"
        Write-Log "Log file: $script:LogFile"
        exit 1
    }

    Write-Log "Run completed successfully." "OK"
    Write-Log "Log file: $script:LogFile"
    exit 0
}
