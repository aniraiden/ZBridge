param([string]$FilePath)

$bytes = [System.IO.File]::ReadAllBytes($FilePath)
Write-Host "Size: $($bytes.Length) bytes"
Write-Host "BOM: 0x$($bytes[0].ToString('X2')) 0x$($bytes[1].ToString('X2')) 0x$($bytes[2].ToString('X2'))"

$open = 0
$close = 0
foreach ($b in $bytes) {
    if ($b -eq 91) { $open++ }
    if ($b -eq 93) { $close++ }
}
Write-Host "[: $open  ]: $close  Balance: $($open - $close)"
if ($open -ne $close) {
    Write-Host "ERROR: Bracket mismatch!" -ForegroundColor Red
    
    # Find approximate position of mismatch
    $depth = 0
    for ($i = 0; $i -lt $bytes.Length; $i++) {
        if ($bytes[$i] -eq 91) { $depth++ }
        if ($bytes[$i] -eq 93) { $depth-- }
        if ($depth -lt 0) { Write-Host "Extra ] at byte $i" -ForegroundColor Yellow; break }
    }
    if ($depth -gt 0) { Write-Host "Unclosed [ (depth: $depth)" -ForegroundColor Yellow }

    # Find line numbers
    $line = 1
    $col = 1
    for ($i = 0; $i -lt $bytes.Length; $i++) {
        if ($bytes[$i] -eq 91) { $depth++ }
        if ($bytes[$i] -eq 93) { $depth-- }
        if ($bytes[$i] -eq 10) { $line++; $col = 1 }
        else { $col++ }
        if ($depth -lt 0) { Write-Host "First extra ] at line $line, col $col" -ForegroundColor Yellow; break }
    }
} else {
    Write-Host "Brackets OK" -ForegroundColor Green
}

# Check CRLF
$crlf = [regex]::Matches([System.Text.Encoding]::UTF8.GetString($bytes), "`r`n").Count
$lf = [regex]::Matches([System.Text.Encoding]::UTF8.GetString($bytes), "(?<!`r)`n").Count
Write-Host "CRLF: $crlf, bare LF: $lf"
