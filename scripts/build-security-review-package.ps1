$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$stage = Join-Path $root '.testdeps\security-review-package'
$release = Join-Path $root 'release'
$zip = Join-Path $release 'agentsolis-security-review-package.zip'

if (-not $stage.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Refusing to clean a staging directory outside the repository.'
}
if (Test-Path -LiteralPath $stage) {
    Remove-Item -LiteralPath $stage -Recurse -Force
}
New-Item -ItemType Directory -Path $stage -Force | Out-Null

$files = @(
    'contracts\AgentNotaryMainnetEscrow.sol',
    'contracts\AgentNotaryValidatorQuorum.sol',
    'contracts\AgentNotaryAIReviewResolver.sol',
    'artifacts\AgentNotaryMainnetEscrow.json',
    'artifacts\AgentNotaryValidatorQuorum.json',
    'artifacts\AgentNotaryAIReviewResolver.json',
    'release\mainnet-release.json',
    'release\arbiscan-verification\verification-report.json',
    'release\arbiscan-verification\README.md',
    'ai_review.py',
    'mainnet.py',
    'test_ai_review.py',
    'test_mainnet.py',
    'test_mainnet_contract_security.py',
    'policies\automatic-json-evidence-v1.json',
    'policies\buyer-review-v1.json',
    'AI_REVIEW_TR.md',
    'AI_REVIEW_SETUP_TR.md',
    'SECURITY_REVIEW_SCOPE.md',
    'MAINNET_FINAL_STEPS_TR.md',
    'requirements.txt',
    'package.json',
    'pnpm-lock.yaml'
)

foreach ($relative in $files) {
    $source = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing review input: $relative" }
    $destination = Join-Path $stage $relative
    New-Item -ItemType Directory -Path (Split-Path $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination
}

$commit = (git -C $root rev-parse HEAD).Trim()
@(
    'AgentSolis independent security review request package',
    "Generated UTC: $([DateTime]::UtcNow.ToString('o'))",
    "Base commit: $commit",
    'Network: Arbitrum One (42161)',
    'Public funding gate: closed',
    'This package is audit input, not proof that an independent audit occurred.'
) | Set-Content -LiteralPath (Join-Path $stage 'PACKAGE_INFO.txt') -Encoding utf8

$hashLines = Get-ChildItem -LiteralPath $stage -Recurse -File |
    Sort-Object FullName |
    ForEach-Object {
        $relative = $_.FullName.Substring($stage.Length + 1).Replace('\', '/')
        $hash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $relative"
    }
$hashLines | Set-Content -LiteralPath (Join-Path $stage 'SHA256SUMS.txt') -Encoding ascii

if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
$zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$zipHash  $(Split-Path $zip -Leaf)" | Set-Content -LiteralPath "$zip.sha256" -Encoding ascii
Write-Output "Created $zip"
Write-Output "SHA-256 $zipHash"
