param([string]$FilePath)

$txt = [System.IO.File]::ReadAllText($FilePath)
$utf8Bom = New-Object System.Text.UTF8Encoding $true
$fixed = $txt.Replace("`r`n", "`n").Replace("`n", "`r`n")
[System.IO.File]::WriteAllText($FilePath, $fixed, $utf8Bom)

# Verify
$bytes = [System.IO.File]::ReadAllBytes($FilePath)
$bomOK = ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
$crlf = [regex]::Matches($fixed, "`r`n").Count
Write-Host "BOM: $bomOK, CRLF: $crlf, Size: $($bytes.Length)"
