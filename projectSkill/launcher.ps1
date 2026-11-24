param(
    [Parameter(Mandatory=$true)][ValidateSet('start','stop')][string]$Action,
    [Parameter(Mandatory=$true)][string]$ProjectRoot
)

$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($ProjectRoot)
$configPath=Join-Path $root 'launcher.json'
if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) { throw "缺少启动配置：$configPath" }
$config=Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
$stateDir=Join-Path $root '.paper-launcher'
$statePath=Join-Path $stateDir 'state.json'

function LocalPath([string]$relative) {
    if ([IO.Path]::IsPathRooted($relative)) { throw "配置必须使用项目内相对路径：$relative" }
    $full=[IO.Path]::GetFullPath((Join-Path $root $relative))
    if (-not $full.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw "配置路径越出本项目：$relative"
    }
    return $full
}

function ProcessForState($state) {
    if ([string]$state.project -ne [string]$config.project -or
        [string]$state.kind -ne [string]$config.kind) {
        throw '运行状态不属于本项目，拒绝操作'
    }
    $stateExe=[IO.Path]::GetFullPath([string]$state.exe)
    if (-not $stateExe.StartsWith($root.TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw '记录的可执行文件不在本项目中，拒绝操作'
    }
    $pidNumber=[int]$state.pid
    $item=Get-CimInstance Win32_Process -Filter "ProcessId=$pidNumber"
    if (-not $item) { return $null }
    if (-not $item.ExecutablePath -or
        -not [string]::Equals([IO.Path]::GetFullPath($item.ExecutablePath),$stateExe,[StringComparison]::OrdinalIgnoreCase)) {
        throw "PID $pidNumber 已不属于该项目，拒绝操作"
    }
    $started=(Get-Process -Id $pidNumber).StartTime.ToUniversalTime().Ticks
    if ([string]$started -ne [string]$state.started_ticks) {
        throw "PID $pidNumber 的启动时间已变化，拒绝操作"
    }
    return $item
}

function ReadState() {
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { return $null }
    return Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function SafeArchiveEntry([string]$entry) {
    if (-not $entry -or [IO.Path]::IsPathRooted($entry) -or $entry.Contains('..') -or $entry.StartsWith('/')) {
        throw "ZIP 入口路径不安全：$entry"
    }
    return $entry
}

function ResolveEntry() {
    foreach ($entry in $config.entries) {
        $path=LocalPath ([string]$entry.path)
        if (Test-Path -LiteralPath $path -PathType Leaf) {
            return @{ path=$path; args=[string]$entry.args; workdir=$root }
        }
    }
    if (-not $config.archive) { return $null }
    $archive=LocalPath ([string]$config.archive)
    if (-not (Test-Path -LiteralPath $archive -PathType Leaf)) { return $null }
    $entryName=SafeArchiveEntry ([string]$config.archive_entry)
    $package=Join-Path $stateDir 'package'
    $target=[IO.Path]::GetFullPath((Join-Path $package $entryName))
    if (-not $target.StartsWith([IO.Path]::GetFullPath($package).TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
        throw 'ZIP 中的可执行文件路径越界'
    }
    $stamp=Join-Path $stateDir 'archive-stamp.json'
    $archiveInfo=Get-Item -LiteralPath $archive
    $signature=($archiveInfo.Length.ToString()+':'+$archiveInfo.LastWriteTimeUtc.Ticks.ToString())
    $oldStamp=$null
    if (Test-Path -LiteralPath $stamp) {
        try { $oldStamp=Get-Content -LiteralPath $stamp -Raw | ConvertFrom-Json } catch { }
    }
    if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or -not $oldStamp -or $oldStamp.signature -ne $signature) {
        New-Item -ItemType Directory -Path $package -Force | Out-Null
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $zip=[IO.Compression.ZipFile]::OpenRead($archive)
        try {
            foreach ($member in $zip.Entries) {
                $candidate=[IO.Path]::GetFullPath((Join-Path $package $member.FullName))
                if (-not $candidate.StartsWith([IO.Path]::GetFullPath($package).TrimEnd('\')+'\',[StringComparison]::OrdinalIgnoreCase)) {
                    throw "ZIP 成员路径越界：$($member.FullName)"
                }
            }
        } finally { $zip.Dispose() }
        Write-Host "首次解压本项目离线包：$archive"
        Expand-Archive -LiteralPath $archive -DestinationPath $package -Force
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "离线包缺少入口：$entryName" }
        @{signature=$signature;archive=$archive} | ConvertTo-Json | Set-Content -LiteralPath $stamp -Encoding UTF8
    }
    return @{ path=$target; args=[string]$config.archive_args; workdir=(Split-Path -Parent $target) }
}

function SendCtrlC([int]$targetPid) {
    if (-not ('PaperConsoleControl' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class PaperConsoleControl {
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool FreeConsole();
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool AttachConsole(uint pid);
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool SetConsoleCtrlHandler(IntPtr handler,bool add);
    [DllImport("kernel32.dll",SetLastError=true)] public static extern bool GenerateConsoleCtrlEvent(uint eventType,uint processGroupId);
}
'@
    }
    [PaperConsoleControl]::FreeConsole() | Out-Null
    if (-not [PaperConsoleControl]::AttachConsole([uint32]$targetPid)) {
        throw "无法连接到 PID $targetPid 的独立控制台；未强制终止进程"
    }
    try {
        [PaperConsoleControl]::SetConsoleCtrlHandler([IntPtr]::Zero,$true) | Out-Null
        if (-not [PaperConsoleControl]::GenerateConsoleCtrlEvent(0,0)) {
            throw "向 PID $targetPid 发送 Ctrl+C 失败"
        }
        Start-Sleep -Milliseconds 500
    } finally { [PaperConsoleControl]::FreeConsole() | Out-Null }
}

if ($Action -eq 'stop') {
    $state=ReadState
    if (-not $state) { Write-Host '没有由 start.cmd 启动的本项目实例'; exit 0 }
    $item=ProcessForState $state
    if (-not $item) {
        Remove-Item -LiteralPath $statePath -Force
        Write-Host '原实例已退出，已清理过期状态'; exit 0
    }
    if ($state.kind -eq 'console') {
        SendCtrlC ([int]$state.pid)
    } else {
        $process=Get-Process -Id ([int]$state.pid)
        $closed=$process.CloseMainWindow()
        if (-not $closed) {
            # Windows venv python.exe is a redirector: the Qt window belongs to
            # its direct child, while the tracked launcher remains the parent.
            $children=Get-CimInstance Win32_Process -Filter "ParentProcessId=$($state.pid)"
            foreach ($child in $children) {
                $window=Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue
                if ($window -and $window.MainWindowHandle -ne 0 -and $window.CloseMainWindow()) {
                    $closed=$true
                    break
                }
            }
        }
        if (-not $closed) { throw '未找到可关闭的主窗口；请在该项目窗口手动退出' }
    }
    $limit=[int]$config.stop_wait_seconds
    if ($limit -le 0) { $limit=60 }
    $deadline=(Get-Date).AddSeconds($limit)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)")) {
            Remove-Item -LiteralPath $statePath -Force
            Write-Host "本项目已正常停止：$($config.project)"; exit 0
        }
        Start-Sleep -Milliseconds 500
    }
    throw "等待 $limit 秒后进程仍在运行；未强制终止，检查项目日志或窗口"
}

if ($config.kind -eq 'pending') { Write-Host ([string]$config.missing_message); exit 2 }
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$state=ReadState
if ($state) {
    $item=ProcessForState $state
    if ($item) { Write-Host "本项目已运行：PID $($state.pid)"; exit 0 }
    Remove-Item -LiteralPath $statePath -Force
}
$selected=ResolveEntry
if (-not $selected) { Write-Host ([string]$config.missing_message); exit 2 }
if ($config.ready_url) {
    $ready=[uri][string]$config.ready_url
    $client=New-Object Net.Sockets.TcpClient
    try {
        $connect=$client.BeginConnect($ready.Host,$ready.Port,$null,$null)
        if ($connect.AsyncWaitHandle.WaitOne(700,$false)) {
            try { $client.EndConnect($connect); throw "端口 $($ready.Port) 已被占用，请先停止占用程序" } catch [Net.Sockets.SocketException] { }
        }
    } finally { $client.Close() }
}
$stdout=Join-Path $stateDir 'stdout.log'
$stderr=Join-Path $stateDir 'stderr.log'
$startArgs=@{FilePath=$selected.path;WorkingDirectory=$selected.workdir;PassThru=$true;
             RedirectStandardOutput=$stdout;RedirectStandardError=$stderr}
if ($selected.args) { $startArgs.ArgumentList=$selected.args }
if ($config.kind -eq 'console') { $startArgs.WindowStyle='Hidden' }
$process=Start-Process @startArgs
$started=$process.StartTime.ToUniversalTime().Ticks
@{pid=$process.Id;exe=[IO.Path]::GetFullPath($selected.path);started_ticks=$started;
  kind=[string]$config.kind;project=[string]$config.project} | ConvertTo-Json |
  Set-Content -LiteralPath $statePath -Encoding UTF8
$wait=[int]$config.start_wait_seconds
if ($wait -le 0) { $wait=5 }
$deadline=(Get-Date).AddSeconds($wait)
do {
    if ($process.HasExited) {
        Remove-Item -LiteralPath $statePath -Force
        $tail=Get-Content -LiteralPath $stderr -Tail 12 -ErrorAction SilentlyContinue
        throw "程序提前退出：$($config.project)`n$tail"
    }
    if ($config.ready_url) {
        try {
            $response=Invoke-WebRequest -UseBasicParsing -Uri ([string]$config.ready_url) -TimeoutSec 2
            if ($response.StatusCode -eq 200) { Write-Host "已启动 $($config.project)：$($config.ready_url)"; exit 0 }
        } catch { }
    }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)
if ($config.ready_url) { throw "进程已启动但页面尚未就绪；可稍后查看 $($config.ready_url) 或 .paper-launcher 日志" }
Write-Host "已启动 $($config.project)：PID $($process.Id)"
