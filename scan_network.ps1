# Quick Network Scanner for MES VM
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Scanning for MES VM..." -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Your IP: 192.168.0.125" -ForegroundColor Yellow
Write-Host "Scanning range: 192.168.0.230-245" -ForegroundColor Yellow
Write-Host ""

$found = @()

# Quick ping scan
Write-Host "Scanning..." -NoNewline
230..245 | ForEach-Object {
    Write-Host "." -NoNewline
    $ip = "192.168.0.$_"
    $ping = Test-Connection -ComputerName $ip -Count 1 -Quiet -TimeoutSeconds 1
    if ($ping) {
        $found += $ip
        Write-Host ""
        Write-Host "✓ FOUND: $ip" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host ""

if ($found.Count -eq 0) {
    Write-Host "❌ No active hosts found in range 192.168.0.230-245" -ForegroundColor Red
    Write-Host ""
    Write-Host "This means the VM is likely:" -ForegroundColor Yellow
    Write-Host "  1. Powered OFF (most likely)" -ForegroundColor Yellow
    Write-Host "  2. On a different IP range" -ForegroundColor Yellow
    Write-Host "  3. Network adapter disconnected" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  • Check VM power status in your hypervisor" -ForegroundColor White
    Write-Host "  • Or access VM console directly" -ForegroundColor White
} else {
    Write-Host "Found $($found.Count) active host(s)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Testing SSH on found hosts..." -ForegroundColor Cyan

    foreach ($ip in $found) {
        Write-Host "Testing $ip..." -NoNewline
        $tcpTest = Test-NetConnection -ComputerName $ip -Port 22 -WarningAction SilentlyContinue -InformationLevel Quiet -TimeoutSeconds 2
        if ($tcpTest) {
            Write-Host " SSH port OPEN! ✓" -ForegroundColor Green
            Write-Host ""
            Write-Host "*** THIS MIGHT BE YOUR VM! ***" -ForegroundColor Yellow -BackgroundColor DarkGreen
            Write-Host "Try: ssh giritharan@$ip" -ForegroundColor Yellow
            Write-Host ""
        } else {
            Write-Host " SSH port closed" -ForegroundColor Gray
        }
    }
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Read-Host "Press Enter to exit"
