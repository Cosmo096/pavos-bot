param(
    [Parameter(Mandatory = $true)][string]$LogFile
)

if (-not (Test-Path -LiteralPath $LogFile -PathType Leaf)) {
    exit 0
}

$text = Get-Content -LiteralPath $LogFile -Raw
$matches = [regex]::Matches($text, "New display:.*\(id=(\d+)\)")
if ($matches.Count -gt 0) {
    [Console]::WriteLine($matches[$matches.Count - 1].Groups[1].Value)
}
