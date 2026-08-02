# goz2mdd.ps1 - ZBridge 0.8.0 图层 MDD 工具（测试用，生产环境为 C++ DLL）
# 功能:
#   1) -Dump <file>        : 探测任意文件布局（参考 MDD 用），输出前 64 字节十六进制 + 候选解释
#   2) 默认                 : 读 Base.goz + Layer_i.goz 的 POINT_LIST，生成 Layer_i.mdd
#      -BaseGoz <path> -LayerGoz <path> -OutMdd <path> [-RefMdd <path>]
#      -RefMdd 提供时按参考文件的布局写入，否则用经典布局(magic MDD\0 + frames + points + dt)
param(
    [string]$Dump,
    [string]$BaseGoz,
    [string]$LayerGoz,
    [string]$OutMdd,
    [string]$RefMdd
)

function Read-GoZPoints {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 32) { throw "Too small: $Path" }
    $magic = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 4)
    if ($magic -ne "GoZb") { throw "Not a GoZ file (magic=$magic): $Path" }
    $off = 32
    $points = $null
    while ($off -lt $bytes.Length - 16) {
        $tag   = [BitConverter]::ToUInt32($bytes, $off)
        $size  = [BitConverter]::ToUInt32($bytes, $off + 4)
        $count = [BitConverter]::ToUInt32($bytes, $off + 8)
        if ($size -lt 16 -or ($off + $size) -gt $bytes.Length) { break }
        if ($tag -eq 10000) { # GoZ_TAG_POINT_LIST
            $points = New-Object System.Collections.Generic.List[float]
            for ($i = 0; $i -lt $count; $i++) {
                $p = $off + 16 + $i * 12
                $points.Add([BitConverter]::ToSingle($bytes, $p))
                $points.Add([BitConverter]::ToSingle($bytes, $p + 4))
                $points.Add([BitConverter]::ToSingle($bytes, $p + 8))
            }
        }
        if ($tag -eq 0) { break } # END_OF_FILE
        $off += $size
    }
    if ($null -eq $points) { throw "No POINT_LIST found: $Path" }
    return $points
}

function Dump-File {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    Write-Host "Size: $($bytes.Length) bytes"
    $hex = ($bytes[0..([Math]::Min(63, $bytes.Length - 1))] | ForEach-Object { $_.ToString("X2") }) -join " "
    Write-Host "First64 hex: $hex"
    if ($bytes.Length -ge 4) {
        $m = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 4)
        Write-Host "Magic[0-3]: '$m'"
    }
    if ($bytes.Length -ge 16) {
        Write-Host "Candidate classic layout:"
        Write-Host "  frames=$([BitConverter]::ToUInt32($bytes,4)) points=$([BitConverter]::ToUInt32($bytes,8)) dt=$([BitConverter]::ToSingle($bytes,12))"
        Write-Host "Candidate no-magic layout:"
        Write-Host "  frames=$([BitConverter]::ToUInt32($bytes,0)) points=$([BitConverter]::ToUInt32($bytes,4))"
    }
}

if ($Dump) {
    Dump-File -Path $Dump
    exit 0
}

if (-not $BaseGoz -or -not $LayerGoz -or -not $OutMdd) {
    Write-Host "Usage: goz2mdd.ps1 -BaseGoz <b.goz> -LayerGoz <l.goz> -OutMdd <out.mdd> [-RefMdd <ref.mdd>]"
    Write-Host "       goz2mdd.ps1 -Dump <file>"
    exit 1
}

$base  = Read-GoZPoints -Path $BaseGoz
$layer = Read-GoZPoints -Path $LayerGoz
$count = $base.Count / 3
if ($layer.Count -ne $base.Count) {
    Write-Host "VERTEX COUNT MISMATCH: base=$($base.Count/3) layer=$($layer.Count/3)"
    exit 2
}
Write-Host "Vertex count: $count"

# 布局判定: 有参考文件则探测, 否则经典布局
$layout = "classic" # magic(4) + frames(4) + points(4) + dt(4) + data
if ($RefMdd -and (Test-Path $RefMdd)) {
    $rb = [System.IO.File]::ReadAllBytes($RefMdd)
    if ($rb.Length -ge 8) {
        $m0 = [System.Text.Encoding]::ASCII.GetString($rb, 0, 4)
        $f0 = [BitConverter]::ToUInt32($rb, 4)
        $p0 = [BitConverter]::ToUInt32($rb, 8)
        $fn = [BitConverter]::ToUInt32($rb, 0)
        $pn = [BitConverter]::ToUInt32($rb, 4)
        if ($m0 -match "^MDD") { $layout = "classic" }
        elseif ($f0 -gt 0 -and $f0 -lt 10000 -and $p0 -gt 0 -and $p0 -lt 100000000) { $layout = "classic" }
        elseif ($fn -gt 0 -and $fn -lt 10000 -and $pn -gt 0) { $layout = "times" } # frames, points, times[], data
        else { $layout = "classic" }
        Write-Host "Ref layout detected: $layout (magic='$m0' frames=$fn/$f0 points=$pn/$p0)"
    }
}
if ($RefMdd -and (Test-Path $RefMdd) -and $layout -eq "times") {
    # 布局: frames(4) + points(4) + times[frames]*4 + data
    $ms = New-Object System.IO.MemoryStream
    $bw = New-Object System.IO.BinaryWriter($ms)
    $frames = 2
    $bw.Write([uint32]$frames)
    $bw.Write([uint32]$count)
    $bw.Write([single]0.0) # time0
    $bw.Write([single]1.0) # time1
    foreach ($v in $base)  { $bw.Write([single]$v) }
    foreach ($v in $layer) { $bw.Write([single]$v) }
    [System.IO.File]::WriteAllBytes($OutMdd, $ms.ToArray())
    Write-Host "Wrote (times layout): $OutMdd  frames=2 points=$count"
} else {
    # 经典布局: "MDD\0" + frames(4) + points(4) + dt(4) + data
    $ms = New-Object System.IO.MemoryStream
    $bw = New-Object System.IO.BinaryWriter($ms)
    $bw.Write([byte]0x4D); $bw.Write([byte]0x44); $bw.Write([byte]0x44); $bw.Write([byte]0x00)
    $bw.Write([uint32]2)          # frames
    $bw.Write([uint32]$count)     # points
    $bw.Write([single]1.0)        # dt
    foreach ($v in $base)  { $bw.Write([single]$v) }
    foreach ($v in $layer) { $bw.Write([single]$v) }
    [System.IO.File]::WriteAllBytes($OutMdd, $ms.ToArray())
    Write-Host "Wrote (classic layout): $OutMdd  frames=2 points=$count"
}
