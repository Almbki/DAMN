@echo off
chcp 65001 >nul
title DAMN 开发服务器
cd /d D:\reactnative\damn-app

echo.
echo  ============================================
echo    DAMN 开发服务器
echo  ============================================
echo    手机   : 打开 Expo Go，扫描下面的二维码
echo    浏览器 : 在这个窗口里按一下  w  键
echo    关闭   : 按 Ctrl+C，如果问 Y/N 就输 Y 回车
echo  ============================================
echo.

npx expo start

echo.
echo  开发服务器已停止，可以关窗口了。
pause
