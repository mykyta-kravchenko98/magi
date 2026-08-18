param(
    [string]$SecretId = "magi/stage",
    [string]$Region = "eu-central-1",
    [switch]$NoGpu
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$stageManifest = Join-Path $repositoryRoot "deploy/stage.env"

$imageLine = Get-Content -LiteralPath $stageManifest |
    Where-Object { $_ -match '^MAGI_IMAGE=.+' } |
    Select-Object -First 1

if ([string]::IsNullOrWhiteSpace($imageLine)) {
    throw "deploy/stage.env has no pinned MAGI_IMAGE; wait for a successful publish workflow."
}

$imageReference = $imageLine.Substring("MAGI_IMAGE=".Length)
$registry = ($imageReference -split '/', 2)[0]
if ($registry -notmatch '\.dkr\.ecr\.[^.]+\.amazonaws\.com$') {
    throw "MAGI_IMAGE does not point to a private Amazon ECR registry."
}

. (Join-Path $PSScriptRoot "load-compose-secrets.ps1") -SecretId $SecretId -Region $Region

aws ecr get-login-password --region $Region |
    docker login --username AWS --password-stdin $registry
if ($LASTEXITCODE -ne 0) {
    throw "Failed to authenticate Docker to ECR."
}

$composeArgs = @(
    "compose",
    "--env-file", $stageManifest,
    "-f", (Join-Path $repositoryRoot "compose.yaml"),
    "-f", (Join-Path $repositoryRoot "compose.production.yaml")
)
if (-not $NoGpu) {
    $composeArgs += @("--profile", "gpu")
}

& docker @composeArgs pull api migrations
if ($LASTEXITCODE -ne 0) {
    throw "Failed to pull the pinned stage image."
}

& docker @composeArgs up --detach --wait
if ($LASTEXITCODE -ne 0) {
    throw "Stage deployment failed."
}

Write-Host "Stage is running from $imageReference"
