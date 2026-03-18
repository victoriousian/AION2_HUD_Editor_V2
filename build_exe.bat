@echo off
echo ========================================
echo   AION2 HUD Editor - Build EXE
echo ========================================
echo.

cd /d "%~dp0"

echo Building executable...
pyinstaller --onefile --windowed --name "AION2_HUD_Editor" --clean aion2_hud_editor.py

echo.
if exist "dist\AION2_HUD_Editor.exe" (
    echo Build successful!
    echo Output: dist\AION2_HUD_Editor.exe
    echo.
    for %%A in ("dist\AION2_HUD_Editor.exe") do echo Size: %%~zA bytes
) else (
    echo Build FAILED!
)
echo.
pause
