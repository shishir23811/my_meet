@echo off
echo Setting up Windows Firewall rules for LAN Communication Application
echo.
echo This script will add firewall rules to allow:
echo - TCP port 54321 (Control channel)
echo - UDP port 54322 (Media streams)
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - proceeding with firewall setup...
    echo.
) else (
    echo ERROR: This script must be run as Administrator!
    echo.
    echo Right-click on this file and select "Run as administrator"
    pause
    exit /b 1
)

echo Adding TCP port 54321 rule...
netsh advfirewall firewall add rule name="LAN Communicator TCP" dir=in action=allow protocol=TCP localport=54321
if %errorLevel% == 0 (
    echo ✓ TCP rule added successfully
) else (
    echo ✗ Failed to add TCP rule
)

echo.
echo Adding UDP port 54322 rule...
netsh advfirewall firewall add rule name="LAN Communicator UDP" dir=in action=allow protocol=UDP localport=54322
if %errorLevel% == 0 (
    echo ✓ UDP rule added successfully
) else (
    echo ✗ Failed to add UDP rule
)

echo.
echo Firewall setup complete!
echo.
echo You can now:
echo 1. Host sessions - other devices can connect to you
echo 2. Join sessions - you can connect to other hosts
echo.
echo If you still have connection issues:
echo - Make sure both devices are on the same WiFi network
echo - Verify the host application is running and shows "Server started successfully"
echo - Check that session IDs match exactly
echo.
pause