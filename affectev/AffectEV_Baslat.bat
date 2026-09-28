@echo off
title AffectEV - Tam Sistem Baslatici
color 0B
echo.
echo  ====================================
echo   AffectEV - Emotion-Aware EV Router
echo  ====================================
echo.

echo  [1/2] FastAPI Backend (Python) baslatiliyor...
cd /d "D:\4. Sınıf\RoutingPlaning"
start "AffectEV Backend" cmd /c "python api.py"

echo  [2/2] React UI baslatiliyor...
cd /d "D:\4. Sınıf\RoutingPlaning\affectev"

echo.
echo  Tarayiciniz otomatik olarak acilacaktir: http://localhost:5173
echo.
start "" "http://localhost:5173"

"C:\Program Files\nodejs\npm.cmd" run dev
pause
