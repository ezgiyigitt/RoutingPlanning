@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=%LOCALAPPDATA%\Python\bin\python.exe
echo.
echo OpenCV onariliyor. Once acik olan tum AffectEV pencerelerini kapatin.
echo.
echo 1/2  Cakisan OpenCV paketleri kaldiriliyor...
"%PY%" -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python opencv-contrib-python-headless
echo 2/2  OpenCV yeniden kuruluyor...
"%PY%" -m pip install --no-cache-dir opencv-contrib-python
echo.
"%PY%" -c "import cv2; cv2.CascadeClassifier; print('OpenCV hazir:', cv2.__version__)" || echo OpenCV hala sorunlu. Bu pencerenin ciktisini Claude'a gonderin.
echo.
pause
