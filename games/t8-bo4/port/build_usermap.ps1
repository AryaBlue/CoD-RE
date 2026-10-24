# BO3 Mod Tools usermap build without the Launcher: compile -> light -> link (mirrors modlauncher.exe's commands)
param([Parameter(Mandatory)][string]$Map, [ValidateSet('low','medium','high')][string]$Light = 'low', [switch]$SkipLight, [switch]$SkipCompile, [string[]]$CompileArgs = @())
$ErrorActionPreference = 'Stop'
$R = 'F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III 455130\'
$env:TA_GAME_PATH = $R; $env:TA_TOOLS_PATH = $R; $env:TA_LOCAL_ASSET_CACHE = $R + 'share\assetconvert'
$logs = Join-Path $PSScriptRoot "logs\$Map"; New-Item -ItemType Directory -Force $logs | Out-Null
$mapFile = "$($R)map_source\$($Map.Substring(0,2))\$Map.map"
# BoD shell: Umbra's backface test misfires on single-sided BO4 walls and hides props near walls
if (-not $CompileArgs.Count -and $Map -like 'zm_alcatraz_bod*') { $CompileArgs = @('-umbraBackfaceLimit','100','-umbraSmallestOccluder','512') }

function Step($name, $exe, $argv) {
    # bin\ as cwd: cod2map resolves default_navmesh_settings.json relative to it
    # Radiant never exits when it shares our console (-NoNewWindow), so it gets its own
    $console = @{ NoNewWindow = $exe -ne 'radiant_modtools.exe' }
    $p = Start-Process -FilePath ($R + "bin\$exe") -WorkingDirectory ($R + 'bin') -ArgumentList $argv -PassThru -Wait @console `
        -RedirectStandardOutput "$logs\$name.log" -RedirectStandardError "$logs\$name.err"
    "{0}: exit {1} in {2}s" -f $name, $p.ExitCode, [int]($p.ExitTime - $p.StartTime).TotalSeconds
}

# the Launcher refreshes the asset database first so new/edited GDTs (APE assets) reach the linker
$p = Start-Process -FilePath ($R + 'gdtdb\gdtdb.exe') -WorkingDirectory ($R + 'gdtdb') -ArgumentList '/update' -PassThru -Wait -NoNewWindow `
    -RedirectStandardOutput "$logs\gdtdb.log" -RedirectStandardError "$logs\gdtdb.err"
"gdtdb: exit {0}" -f $p.ExitCode
# cod2map stalls (0 CPU after "Connected to data signature database") while BO4 + Greyhound run; -SkipCompile reuses the last BSP
if (-not $SkipCompile) {
    $res = Step 'compile' 'cod2map64.exe' (@('-platform','pc','-navmesh','-navvolume') + $CompileArgs + @('-loadFrom',"`"$mapFile`"","`"$($R)share\raw\maps\$($Map.Substring(0,2))\$Map.d3dbsp`""))
    $res
    # a failed compile leaves Radiant waiting on an error dialog, so stop here
    if ($res -notmatch 'exit 0 ') { Get-Content "$logs\compile.log" -Tail 5; exit 1 }
}
# no -platform for Radiant: its Qt takes -platform as the Qt platform plugin and aborts
if (-not $SkipLight) {
    # a map Radiant didn't save itself ends on a hidden "unsaved changes" prompt, so stop Radiant once the .led has settled
    $led = "$($R)share\raw\maps\$($Map.Substring(0,2))\$Map.led"
    $t0 = Get-Date
    $p = Start-Process -FilePath ($R + 'bin\radiant_modtools.exe') -WorkingDirectory ($R + 'bin') -PassThru `
        -ArgumentList @('-ledSilent',"+$Light",'+localprobes','+forceclean',"`"$mapFile`"") -RedirectStandardOutput "$logs\light.log" -RedirectStandardError "$logs\light.err"
    while (-not $p.HasExited) {
        Start-Sleep 5
        $f = Get-Item $led -ErrorAction SilentlyContinue
        if ($f -and $f.LastWriteTime -gt $t0 -and ((Get-Date) - $f.LastWriteTime).TotalSeconds -gt 20) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue; break }
    }
    "light: {0} in {1}s" -f ($(if ($p.HasExited -and $p.ExitCode -eq 0) { 'exit 0' } else { 'stopped after .led' })), [int]((Get-Date) - $t0).TotalSeconds
}
Step 'link' 'linker_modtools.exe' @('-language','english','-modsource',$Map)
Get-ChildItem "$($R)usermaps\$Map\zone" -Filter *.ff | Select-Object Name, Length, LastWriteTime
# the Mod Tools (455130) are a separate install here; the game only reads usermaps\ under its own root
$game = 'F:\SteamLibrary\steamapps\common\Call of Duty Black Ops III\'
if (-not (Get-Process BlackOps3 -ErrorAction SilentlyContinue)) {
    robocopy "$($R)usermaps\$Map\zone" "$($game)usermaps\$Map\zone" /E /NJH /NJS /NP /NFL /NDL | Out-Null
    if ($LASTEXITCODE -ge 8) { "deploy FAILED (robocopy $LASTEXITCODE)"; exit 1 }
    "deployed to $($game)usermaps\$Map\zone"
    $global:LASTEXITCODE = 0  # robocopy's 1 means "copied"
} else { "BlackOps3 is running: not deployed (files are locked)" }
