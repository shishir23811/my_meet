@echo off
echo ============================================================
echo LAN Communicator - Windows Firewall Setup
echo ============================================================
echo.
echo This script will add firewall rules to allow LAN Communicator
echo to accept incoming connections on ports 5555 and 5556.
echo.
echo IMPORTANT: Run this script as Administrator on the HOST computer!
echo.
pause

echo Adding TCP firewall rule for port 5555...
netsh advfirewall firewall add rule name="LAN Communicator TCP" dir=in action=allow protocol=TCP localport=5555 profile=private,domain

echo Adding UDP firewall rule for port 5556...
netsh advfirewall firewall add rule name="LAN Communicator UDP" dir=in action=allow protocol=UDP localport=5556 profile=private,domain

echo.
echo ============================================================
echo Firewall rules added successfully!
echo ============================================================
echo.
echo The following rules were created:
echo - LAN Communicator TCP (port 5555)
echo - LAN Communicator UDP (port 5556)
echo.
echo These rules allow incoming connections on Private and Domain networks.
echo.
echo You can now start hosting sessions and others should be able to connect.
echo.
pause