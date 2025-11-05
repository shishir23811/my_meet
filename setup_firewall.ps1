# PowerShell script to setup Windows Firewall for LAN Communication Application
# Run as Administrator

Write-Host "Setting up Windows Firewall for LAN Communication Application" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Running as Administrator - proceeding with firewall setup..." -ForegroundColor Green
Write-Host ""

# Remove existing rules (in case they exist)
Write-Host "Removing any existing rules..." -ForegroundColor Yellow
try {
    Remove-NetFirewallRule -DisplayName "LAN Communicator TCP" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -DisplayName "LAN Communicator UDP" -ErrorAction SilentlyContinue
    Write-Host "✓ Existing rules removed" -ForegroundColor Green
} catch {
    Write-Host "No existing rules to remove" -ForegroundColor Gray
}

# Add TCP rule
Write-Host "Adding TCP port 54321 rule..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "LAN Communicator TCP" -Direction Inbound -Protocol TCP -LocalPort 54321 -Action Allow -Profile Any
    Write-Host "✓ TCP rule added successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to add TCP rule: $($_.Exception.Message)" -ForegroundColor Red
}

# Add UDP rule
Write-Host "Adding UDP port 54322 rule..." -ForegroundColor Yellow
try {
    New-NetFirewallRule -DisplayName "LAN Communicator UDP" -Direction Inbound -Protocol UDP -LocalPort 54322 -Action Allow -Profile Any
    Write-Host "✓ UDP rule added successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to add UDP rule: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Firewall setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Firewall rules added for:" -ForegroundColor Cyan
Write-Host "• TCP port 54321 (Control channel)" -ForegroundColor White
Write-Host "• UDP port 54322 (Media streams)" -ForegroundColor White
Write-Host ""
Write-Host "You can now:" -ForegroundColor Cyan
Write-Host "1. Host sessions - other devices can connect to you" -ForegroundColor White
Write-Host "2. Join sessions - you can connect to other hosts" -ForegroundColor White
Write-Host ""
Write-Host "If you still have connection issues:" -ForegroundColor Yellow
Write-Host "• Make sure both devices are on the same WiFi network" -ForegroundColor White
Write-Host "• Verify the host application is running" -ForegroundColor White
Write-Host "• Check that session IDs match exactly" -ForegroundColor White
Write-Host ""

# Test the rules
Write-Host "Testing firewall rules..." -ForegroundColor Yellow
$tcpRule = Get-NetFirewallRule -DisplayName "LAN Communicator TCP" -ErrorAction SilentlyContinue
$udpRule = Get-NetFirewallRule -DisplayName "LAN Communicator UDP" -ErrorAction SilentlyContinue

if ($tcpRule -and $udpRule) {
    Write-Host "✓ Both firewall rules are active and configured correctly" -ForegroundColor Green
} else {
    Write-Host "✗ Some firewall rules may not be configured correctly" -ForegroundColor Red
}

Read-Host "Press Enter to exit"