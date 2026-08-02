$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$file = Join-Path $root "src\zscript\ZBridge.txt"
$text = [System.IO.File]::ReadAllText($file)

$badPattern = '\[MemWriteString,zbShellMem,0,\[StrMerge,'
if ([regex]::IsMatch($text, $badPattern)) {
    throw "Invalid request MemWriteString argument order: use [MemWriteString,zbShellMem,[StrMerge,...],0]"
}

foreach ($action in @("Action=prepare", "Action=pack", "Action=unpack", "Action=cleanup")) {
    if (-not $text.Contains($action)) {
        throw "Missing request action: $action"
    }
}

Write-Host "ZScript request checks passed"
