$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'Publishing RAFTBOUND A08 to https://github.com/hungtvb/raftbound'
git status --short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
git push -u origin main
exit $LASTEXITCODE
