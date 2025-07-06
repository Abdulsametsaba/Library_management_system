@echo off
echo Kutuphane Yonetim Sistemi Server Testleri Baslatiliyor...
echo.


where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python bulunamadi! Lutfen Python'un yuklu oldugundan emin olun.
    pause
    exit /b 1
)


echo Gerekli paketler kontrol ediliyor...
python -m pip install pytest requests >nul 2>nul


echo Server testleri calistiriliyor...
python run_tests.py


if %errorlevel% neq 0 (
    echo.
    echo Server testleri basarisiz oldu!
) else (
    echo.
    echo Server testleri basariyla tamamlandi!
)

pause 