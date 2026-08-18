param(
    [Parameter(Mandatory = $true)]
    [string]$SecretId,

    [string]$Region = "eu-central-1"
)

$ErrorActionPreference = "Stop"

$secretOutput = aws secretsmanager get-secret-value `
    --secret-id $SecretId `
    --region $Region `
    --query SecretString `
    --output text

if ($LASTEXITCODE -ne 0) {
    throw "Failed to read AWS Secrets Manager secret '$SecretId'."
}

$secretString = $secretOutput -join [Environment]::NewLine
$secret = $secretString | ConvertFrom-Json
if ($secret -is [array]) {
    if ($secret.Count -ne 1) {
        throw "Secrets Manager value must be a JSON object or a one-element array."
    }
    $secret = $secret[0]
}
$requiredNames = @(
    "MAGI_POSTGRES_PASSWORD",
    "MAGI_OBJECT_STORAGE_ACCESS_KEY",
    "MAGI_OBJECT_STORAGE_SECRET_KEY",
    "MAGI_QDRANT_API_KEY"
)

foreach ($name in $requiredNames) {
    $property = $secret.PSObject.Properties[$name]
    if ($null -eq $property -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
        throw "Secrets Manager value is missing required string '$name'."
    }
}

foreach ($property in $secret.PSObject.Properties) {
    if ($property.Name -notlike "MAGI_*") {
        throw "Unexpected secret key '$($property.Name)'; all keys must use the MAGI_ prefix."
    }
    if ($property.Value -isnot [string]) {
        throw "Secret value '$($property.Name)' must be a string."
    }
    [Environment]::SetEnvironmentVariable($property.Name, $property.Value, "Process")
}

[Environment]::SetEnvironmentVariable(
    "POSTGRES_PASSWORD",
    $secret.MAGI_POSTGRES_PASSWORD,
    "Process"
)
[Environment]::SetEnvironmentVariable(
    "MINIO_ROOT_USER",
    $secret.MAGI_OBJECT_STORAGE_ACCESS_KEY,
    "Process"
)
[Environment]::SetEnvironmentVariable(
    "MINIO_ROOT_PASSWORD",
    $secret.MAGI_OBJECT_STORAGE_SECRET_KEY,
    "Process"
)
[Environment]::SetEnvironmentVariable(
    "QDRANT_API_KEY",
    $secret.MAGI_QDRANT_API_KEY,
    "Process"
)
[Environment]::SetEnvironmentVariable("AWS_REGION", $Region, "Process")
[Environment]::SetEnvironmentVariable("MAGI_SECRETS_MANAGER_SECRET_ID", $SecretId, "Process")

$credentialsJson = aws configure export-credentials --format process
if ($LASTEXITCODE -ne 0) {
    throw "Failed to export temporary AWS credentials for the application container."
}
$credentials = $credentialsJson | ConvertFrom-Json
[Environment]::SetEnvironmentVariable("AWS_ACCESS_KEY_ID", $credentials.AccessKeyId, "Process")
[Environment]::SetEnvironmentVariable(
    "AWS_SECRET_ACCESS_KEY",
    $credentials.SecretAccessKey,
    "Process"
)
[Environment]::SetEnvironmentVariable("AWS_SESSION_TOKEN", $credentials.SessionToken, "Process")

Write-Host "Loaded Compose secrets from AWS Secrets Manager into the current process."
