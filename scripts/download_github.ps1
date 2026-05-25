param(
  [Parameter(Mandatory=$true)]
  [string]$RepoUrl
)

$TargetDir = "./workspaces/github_repository"
$SuccessMessage = "GitHub repository downloaded successfully."
$FailureMessage = "GitHub repository could not be downloaded."

if ($RepoUrl -notmatch '^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(\.git)?$') {
  Write-Host "$FailureMessage Invalid GitHub repository URL."
  exit 2
}

if (Test-Path $TargetDir) {
  Remove-Item -LiteralPath $TargetDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path $TargetDir) | Out-Null

git clone --depth 1 -- $RepoUrl $TargetDir
if ($LASTEXITCODE -eq 0 -and (Test-Path (Join-Path $TargetDir ".git"))) {
  Write-Host $SuccessMessage
  Write-Host "Target directory: workspaces/github_repository"
  exit 0
}

Write-Host $FailureMessage
exit 1
