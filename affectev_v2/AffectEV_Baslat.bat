@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=%LOCALAPPDATA%\Python\bin\python.exe
echo Gerekli paketler kontrol ediliyor...
"%PY%" -m pip install -r requirements.txt --quiet --disable-pip-version-check
"%PY%" -c "import cv2; cv2.CascadeClassifier" >nul 2>nul
if errorlevel 1 (
  echo OpenCV eksik veya bozuk, onariliyor...
  "%PY%" -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless >nul 2>nul
  "%PY%" -m pip install --quiet --disable-pip-version-check opencv-contrib-python
)
echo AffectEV baslatiliyor...
"%PY%" run.py
pause
