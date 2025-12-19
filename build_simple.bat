@echo off
chcp 65001
echo ========================================
echo Простая сборка Save Money Bot
echo ========================================

REM Очищаем предыдущие сборки
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "SaveMoneyBot.spec" del "SaveMoneyBot.spec"

echo.
echo Запуск PyInstaller...

pyinstaller --onefile --windowed --icon="ico.ico" --name "SaveMoneyBot" --hidden-import=pyserial --hidden-import=PIL --hidden-import=configparser --clean --noconfirm "Save Money.py"

echo.
if exist "dist\SaveMoneyBot.exe" (
    echo ✅ Сборка успешна!
    echo Файл: dist\SaveMoneyBot.exe
) else (
    echo ❌ Ошибка сборки!
)

echo.
pause
