@echo off
echo 正在清除右键菜单注册项，请稍候...

REM 删除“文件夹”右键菜单主项和子项
reg delete "HKCR\Directory\shell\文件转移工具2.0" /f

REM 删除“空白区域”右键菜单主项和子项
reg delete "HKCR\Directory\Background\shell\文件转移工具2.0" /f

echo 所有右键菜单项已清除！
pause
